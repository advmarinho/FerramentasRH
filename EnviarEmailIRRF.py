# envio_informes_desligados_v3_2_ctk.py
# ------------------------------------------------------------
# Sempre cria rascunho no Outlook (sem abrir janelas)
# Rodapé com Anderson Marinho | Igarapé Digital
# ------------------------------------------------------------

import re
import csv
import time
import traceback
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Callable

import pandas as pd
import pikepdf
import win32com.client as win32

import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk


# ============================================================
# CUSTOMER THINKER - CONFIG
# ============================================================

APP_NAME = "Envio Informes Desligados"
VERSAO = "3.2"

COL_CPF = "CPF"
COL_MATRICULA = "Matrícula"
COL_NOME = "Nome"
COL_EMAIL = "Email Alternativo"

SUBPASTA_PROTEGIDOS = "protegidos"
LOG_NAME = "log_envio_informes.csv"

RH_CHAMADO_URL = "https://forms.gle/dh8ZPsHohwyuKV6J8"

SUBJECT_TEMPLATE = "Informe de Rendimentos {ano_base} - Matrícula {matricula}"
BODY_TEMPLATE = (
    "Olá {nome},\n\n"
    "Segue em anexo o seu Informe de Rendimentos (ano-base {ano_base}).\n"
    "O arquivo está protegido.\n"
    "Senha: seu CPF (somente números, sem ponto e sem traço).\n\n"
    "Caso identifique divergência de valores/dados ou tenha dificuldade de acesso, abra um chamado para o RH por esse e-mail\n"
    #"{url_chamado}\n\n"
    "Atenciosamente,\n"
    "Recursos Humanos\n"
)

FOOTER_UI = "Anderson Marinho | Igarapé Digital"


# ============================================================
# CUSTOMER THINKER - MODELOS
# ============================================================

@dataclass
class Colaborador:
    matricula: str
    cpf: str
    nome: str
    email: str


@dataclass
class ResultadoProcesso:
    pdf_original: str
    cpf_pdf: str
    encontrado_base: bool
    email: str
    pdf_protegido: str
    status: str
    detalhe: str


# ============================================================
# CUSTOMER THINKER - UTIL
# ============================================================

def normalizar_cpf(valor) -> str:
    if valor is None:
        return ""
    s = str(valor).strip()
    s = re.sub(r"\D", "", s)
    if not s:
        return ""
    if len(s) < 11:
        s = s.zfill(11)
    return s


def extrair_cpf_do_nome_arquivo(nome_arquivo: str) -> str:
    m = re.search(r"(\d{11})", nome_arquivo)
    return m.group(1) if m else ""


def extrair_ano_base_do_nome_arquivo(nome_arquivo: str) -> str:
    m = re.search(r"(20\d{2})", nome_arquivo)
    if m:
        return m.group(1)
    ano_atual = int(time.strftime("%Y"))
    return str(ano_atual - 1)


def garantir_pasta(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def validar_email_basico(email: str) -> bool:
    if not email:
        return False
    e = email.strip()
    if " " in e:
        return False
    if e.count("@") != 1:
        return False

    local, dom = e.split("@")
    if not local or not dom:
        return False
    if "." not in dom:
        return False
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", dom):
        return False

    tld = dom.rsplit(".", 1)[-1]
    if len(tld) < 2 or not re.fullmatch(r"[A-Za-z]{2,}", tld):
        return False

    if not re.fullmatch(r"[A-Za-z0-9._%+\-]+", local):
        return False

    return True


def limpar_nome_anexo_removendo_cpf(nome_arquivo: str, cpf11: str) -> str:
    base = nome_arquivo.replace(cpf11, "")
    base = re.sub(r"__+", "_", base)
    base = re.sub(r"_\.", ".", base)
    base = re.sub(r"_-", "_", base)
    base = re.sub(r"_+", "_", base)
    base = base.strip("_").strip()
    return base


def ler_base_colaboradores(arquivo_path: Path) -> Dict[str, Colaborador]:
    ext = arquivo_path.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(
            arquivo_path,
            dtype=str,
            sep=None,
            engine="python",
            encoding="utf-8",
            keep_default_na=False
        )
    elif ext in [".xls", ".xlsx", ".xlsm"]:
        df = pd.read_excel(arquivo_path, dtype=str, engine=None).fillna("")
    elif ext == ".xlsb":
        df = pd.read_excel(arquivo_path, dtype=str, engine="pyxlsb").fillna("")
    else:
        raise ValueError(f"Formato não suportado: {ext}. Use CSV/XLS/XLSX/XLSM/XLSB.")

    cols = list(df.columns)
    obrig = [COL_CPF, COL_MATRICULA, COL_NOME, COL_EMAIL]
    faltantes = [c for c in obrig if c not in cols]
    if faltantes:
        raise ValueError(
            "Base sem colunas obrigatórias. Esperado exatamente:\n"
            f"{' | '.join(obrig)}\n\n"
            f"Encontrado:\n{' | '.join([str(c) for c in cols])}"
        )

    base: Dict[str, Colaborador] = {}
    for _, row in df.iterrows():
        cpf = normalizar_cpf(row.get(COL_CPF, ""))
        if not cpf:
            continue
        base[cpf] = Colaborador(
            matricula=str(row.get(COL_MATRICULA, "")).strip(),
            cpf=cpf,
            nome=str(row.get(COL_NOME, "")).strip(),
            email=str(row.get(COL_EMAIL, "")).strip(),
        )

    return base


def proteger_pdf_com_senha(pdf_path: Path, senha: str, saida_dir: Path) -> Path:
    garantir_pasta(saida_dir)
    out_name = pdf_path.stem + "_protegido.pdf"
    out_path = saida_dir / out_name

    if out_path.exists():
        out_path.unlink()

    with pikepdf.open(pdf_path) as pdf:
        pdf.save(
            out_path,
            encryption=pikepdf.Encryption(owner=senha, user=senha, R=4)
        )
    return out_path


def outlook_criar_rascunho_sem_exibir(
    para: str,
    assunto: str,
    corpo: str,
    anexo_path: Path,
    display_name: str
) -> None:
    """
    Cria APENAS rascunho: Save() sem Display().
    Não abre janela, mesmo com 100 casos.
    """
    outlook = win32.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = para
    mail.Subject = assunto
    mail.Body = corpo

    # Attachments.Add(Source, Type, Position, DisplayName)
    mail.Attachments.Add(str(anexo_path.resolve()), 1, 1, display_name)

    mail.Save()


def escrever_log_csv(log_path: Path, resultados: List[ResultadoProcesso]) -> None:
    garantir_pasta(log_path.parent)
    existe = log_path.exists()

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        if not existe:
            writer.writerow([
                "timestamp",
                "pdf_original",
                "cpf_pdf",
                "encontrado_base",
                "email",
                "pdf_protegido",
                "status",
                "detalhe",
            ])

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for r in resultados:
            writer.writerow([
                ts,
                r.pdf_original,
                r.cpf_pdf,
                "SIM" if r.encontrado_base else "NAO",
                r.email,
                r.pdf_protegido,
                r.status,
                r.detalhe,
            ])


def resumir_resultados(resultados: List[ResultadoProcesso]) -> str:
    total = len(resultados)
    ok = sum(1 for r in resultados if r.status == "OK")
    pulado = sum(1 for r in resultados if r.status == "PULADO")
    falha = sum(1 for r in resultados if r.status == "FALHA")

    return "\n".join([
        f"{APP_NAME} v{VERSAO}",
        f"Total PDFs: {total}",
        f"OK (rascunhos criados): {ok}",
        f"PULADOS (ativos/não listados na base): {pulado}",
        f"Falhas reais (problema de dado/arquivo): {falha}",
    ])


# ============================================================
# CUSTOMER THINKER - PROCESSO
# ============================================================

def processar_pasta(
    pasta_pdfs: Path,
    base_path: Path,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_log: Optional[Callable[[str], None]] = None
) -> Tuple[List[ResultadoProcesso], Path]:
    base = ler_base_colaboradores(base_path)

    saida_dir = pasta_pdfs / SUBPASTA_PROTEGIDOS
    garantir_pasta(saida_dir)

    resultados: List[ResultadoProcesso] = []

    pdfs = sorted([p for p in pasta_pdfs.glob("*.pdf") if p.is_file()])
    if not pdfs:
        raise ValueError("Nenhum PDF encontrado na pasta selecionada.")

    total = len(pdfs)

    for i, pdf in enumerate(pdfs, start=1):
        if on_progress:
            on_progress(i, total)

        cpf_pdf = normalizar_cpf(extrair_cpf_do_nome_arquivo(pdf.name))

        if not cpf_pdf or len(cpf_pdf) != 11:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                encontrado_base=False,
                email="",
                pdf_protegido="",
                status="FALHA",
                detalhe="CPF não encontrado no nome do arquivo (11 dígitos)."
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe}")
            continue

        colab = base.get(cpf_pdf)
        if not colab:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                encontrado_base=False,
                email="",
                pdf_protegido="",
                status="PULADO",
                detalhe="CPF não está na base (provável ativo/não listado)."
            )
            resultados.append(r)
            if on_log:
                on_log(f"PULADO: {pdf.name} | {r.detalhe}")
            continue

        if not colab.email:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                encontrado_base=True,
                email="",
                pdf_protegido="",
                status="FALHA",
                detalhe="Email Alternativo vazio na base."
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe}")
            continue

        if not validar_email_basico(colab.email):
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                encontrado_base=True,
                email=colab.email,
                pdf_protegido="",
                status="FALHA",
                detalhe="E-mail inválido (validação de sintaxe/domínio)."
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe} | email={colab.email}")
            continue

        try:
            ano_base = extrair_ano_base_do_nome_arquivo(pdf.name)
            assunto = SUBJECT_TEMPLATE.format(ano_base=ano_base, matricula=(colab.matricula or "N/A"))
            corpo = BODY_TEMPLATE.format(
                nome=(colab.nome or "Colaborador(a)"),
                ano_base=ano_base,
                url_chamado=RH_CHAMADO_URL
            )

            protegido = proteger_pdf_com_senha(pdf, cpf_pdf, saida_dir)
            display_name = limpar_nome_anexo_removendo_cpf(pdf.name, cpf_pdf)

            outlook_criar_rascunho_sem_exibir(
                para=colab.email,
                assunto=assunto,
                corpo=corpo,
                anexo_path=protegido,
                display_name=display_name
            )

            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                encontrado_base=True,
                email=colab.email,
                pdf_protegido=protegido.name,
                status="OK",
                detalhe="RASCUNHO"
            )
            resultados.append(r)
            if on_log:
                on_log(f"OK: {pdf.name} | RASCUNHO | para={colab.email}")

        except Exception as e:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                encontrado_base=True,
                email=colab.email,
                pdf_protegido="",
                status="FALHA",
                detalhe=f"Erro ao proteger/criar rascunho: {e}"
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe}")

    log_path = pasta_pdfs / LOG_NAME
    escrever_log_csv(log_path, resultados)
    return resultados, log_path


# ============================================================
# CUSTOMER THINKER - UI (CustomTkinter)
# ============================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} | v{VERSAO}")
        self.geometry("980x600")
        self.resizable(False, False)

        self.pasta_pdfs: Optional[Path] = None
        self.base_path: Optional[Path] = None

        self._montar_ui()

    def _montar_ui(self):
        self.grid_columnconfigure(0, weight=1)

        frame_top = ctk.CTkFrame(self)
        frame_top.grid(row=0, column=0, padx=16, pady=12, sticky="ew")

        lbl_titulo = ctk.CTkLabel(frame_top, text=f"{APP_NAME}  |  v{VERSAO}", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_titulo.grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")

        lbl_sub = ctk.CTkLabel(
            frame_top,
            text="Lote de PDFs por CPF no nome + base desligados (CPF/Matrícula/Nome/Email Alternativo)",
            font=ctk.CTkFont(size=12)
        )
        lbl_sub.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

        frame_sel = ctk.CTkFrame(self)
        frame_sel.grid(row=1, column=0, padx=16, pady=8, sticky="ew")
        frame_sel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_sel, text="Pasta PDFs").grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.ent_pasta = ctk.CTkEntry(frame_sel)
        self.ent_pasta.grid(row=0, column=1, padx=12, pady=10, sticky="ew")
        self._set_entry_readonly(self.ent_pasta, "")

        btn_pasta = ctk.CTkButton(frame_sel, text="Selecionar", command=self._selecionar_pasta, width=120)
        btn_pasta.grid(row=0, column=2, padx=12, pady=10)

        ctk.CTkLabel(frame_sel, text="Base (CSV/XLS/XLSX/XLSM/XLSB)").grid(row=1, column=0, padx=12, pady=10, sticky="w")

        self.ent_base = ctk.CTkEntry(frame_sel)
        self.ent_base.grid(row=1, column=1, padx=12, pady=10, sticky="ew")
        self._set_entry_readonly(self.ent_base, "")

        btn_base = ctk.CTkButton(frame_sel, text="Selecionar", command=self._selecionar_base, width=120)
        btn_base.grid(row=1, column=2, padx=12, pady=10)

        frame_exec = ctk.CTkFrame(self)
        frame_exec.grid(row=2, column=0, padx=16, pady=8, sticky="ew")
        frame_exec.grid_columnconfigure(1, weight=1)

        self.btn_iniciar = ctk.CTkButton(frame_exec, text="Iniciar (somente rascunho)", command=self._iniciar, width=240)
        self.btn_iniciar.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.progress = ctk.CTkProgressBar(frame_exec)
        self.progress.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        self.progress.set(0)

        self.lbl_prog = ctk.CTkLabel(frame_exec, text="0/0")
        self.lbl_prog.grid(row=0, column=2, padx=12, pady=12, sticky="e")

        frame_log = ctk.CTkFrame(self)
        frame_log.grid(row=3, column=0, padx=16, pady=(8, 10), sticky="nsew")
        frame_log.grid_columnconfigure(0, weight=1)
        frame_log.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(frame_log, text="Log em tempo real").grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        self.txt_log = ctk.CTkTextbox(frame_log, height=260)
        self.txt_log.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.txt_log.configure(state="disabled")

        # Rodapé
        footer = ctk.CTkLabel(self, text=FOOTER_UI, font=ctk.CTkFont(size=11))
        footer.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="e")

    def _set_entry_readonly(self, entry: ctk.CTkEntry, value: str):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="readonly")

    def _selecionar_pasta(self):
        p = filedialog.askdirectory(title="Selecione a pasta com os PDFs")
        if p:
            self.pasta_pdfs = Path(p)
            self._set_entry_readonly(self.ent_pasta, str(self.pasta_pdfs))

    def _selecionar_base(self):
        p = filedialog.askopenfilename(
            title="Selecione a base (CSV/XLS/XLSX/XLSM/XLSB)",
            filetypes=[
                ("Bases suportadas", "*.csv *.xls *.xlsx *.xlsm *.xlsb"),
                ("Todos", "*.*")
            ]
        )
        if p:
            self.base_path = Path(p)
            self._set_entry_readonly(self.ent_base, str(self.base_path))

    def _log(self, msg: str):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _on_progress(self, atual: int, total: int):
        if total <= 0:
            self.progress.set(0)
            self.lbl_prog.configure(text="0/0")
            return
        self.progress.set(atual / total)
        self.lbl_prog.configure(text=f"{atual}/{total}")
        self.update_idletasks()

    def _iniciar(self):
        if not self.pasta_pdfs or not self.base_path:
            self._log("Erro: selecione a pasta dos PDFs e a base antes de iniciar.")
            tk.messagebox.showerror("Erro", "Selecione a pasta dos PDFs e a base antes de iniciar.")
            return

        self.btn_iniciar.configure(state="disabled")
        self.progress.set(0)
        self.lbl_prog.configure(text="0/0")

        self._log("Iniciando processamento...")
        self._log(f"Pasta: {self.pasta_pdfs}")
        self._log(f"Base: {self.base_path}")
        self._log("Modo: RASCUNHOS (sem abrir janelas)")
        self._log("")

        def worker():
            try:
                resultados, log_path = processar_pasta(
                    pasta_pdfs=self.pasta_pdfs,
                    base_path=self.base_path,
                    on_progress=lambda a, t: self.after(0, self._on_progress, a, t),
                    on_log=lambda m: self.after(0, self._log, m)
                )

                resumo = resumir_resultados(resultados)
                self.after(0, self._log, "")
                self.after(0, self._log, resumo)
                self.after(0, self._log, f"Log salvo em: {log_path}")

                self.after(0, tk.messagebox.showinfo, "Processo concluído", resumo + f"\n\nLog: {log_path}")

            except Exception as e:
                msg = f"Ocorreu um erro: {e}\n\n{traceback.format_exc()}"
                self.after(0, self._log, msg)
                self.after(0, tk.messagebox.showerror, "Erro", msg)
            finally:
                self.after(0, self.btn_iniciar.configure, {"state": "normal"})

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
