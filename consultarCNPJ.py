import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
import requests
import time
import os
import urllib3

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# https://opencnpj.org/
# =====================================================================
# UTIL: Formata data yyyy-mm-dd para dd/mm/yyyy
# =====================================================================
def dfmt(data):
    if not data or data == "" or data is None:
        return "*******"
    try:
        ano, mes, dia = data.split("-")
        return f"{dia}/{mes}/{ano}"
    except Exception:
        return data


# =====================================================================
# UTIL: Normaliza CNPJ
# =====================================================================
def normaliza_cnpj(cnpj):
    if pd.isna(cnpj):
        return ""
    digits = "".join([c for c in str(cnpj) if c.isdigit()])
    return digits.zfill(14)


# =====================================================================
# API OpenCNPJ (SSL desabilitado apenas aqui)
# =====================================================================
def consulta_opencnpj(cnpj):
    url = f"https://api.opencnpj.org/{cnpj}"

    try:
        r = requests.get(url, timeout=15, verify=False)
    except Exception as e:
        return {"erro": f"Falha de conexão: {e}"}

    try:
        return r.json()
    except Exception:
        return {"erro": "Erro ao interpretar JSON", "detalhe": r.text[:500]}


# =====================================================================
# PDF – Layout único alinhado ao modelo da Receita + status destacado
# =====================================================================
def gerar_pdf_cnpj(cnpj, d, pasta):

    # Situação cadastral destacada
    situacao = d.get("situacao_cadastral", "*******").strip()
    situacao_fmt = f"<b>{situacao.upper()}</b>"

    # Nome do arquivo com alerta se não for ATIVA
    nome_extra = ""
    if situacao.upper() != "ATIVA":
        nome_extra = f"_{situacao.upper().replace(' ', '_')}"

    nome_pdf = os.path.join(pasta, f"cartao_{cnpj}{nome_extra}.pdf")

    doc = SimpleDocTemplate(
        nome_pdf,
        pagesize=A4,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    # Estilos
    st_lbl = ParagraphStyle(name="lbl", fontName="Helvetica-Bold", fontSize=9, leading=11)
    st_txt = ParagraphStyle(name="txt", fontName="Helvetica", fontSize=9, leading=11)
    st_titulo = ParagraphStyle(name="titulo", fontName="Helvetica-Bold", fontSize=14, leading=16, alignment=1)
    st_sub = ParagraphStyle(name="sub", fontName="Helvetica-Bold", fontSize=12, leading=14, alignment=1)
    st_ass = ParagraphStyle(name="ass", fontName="Helvetica-Oblique", fontSize=9, leading=11, alignment=1)

    def L(texto):
        return Paragraph(f"<b>{texto}</b>", st_lbl)

    def T(texto):
        return Paragraph(texto if texto else "*******", st_txt)

    # CNPJ com máscara
    c = normaliza_cnpj(cnpj)
    cnpj_m = f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

    # Campos
    data_abertura = dfmt(d.get("data_inicio_atividade"))
    data_sit = dfmt(d.get("data_situacao_cadastral"))

    cnae_princ = d.get("cnae_principal") or ""
    cnae_desc = d.get("cnae_principal_descricao") or ""
    cnae_full = f"{cnae_princ} - {cnae_desc}" if cnae_desc else cnae_princ

    cnaes_sec = ", ".join(d.get("cnaes_secundarios", [])) or "Não informada"

    logr = d.get("logradouro") or "*******"
    num = d.get("numero") or "*******"
    comp = d.get("complemento") or "*******"
    cep = d.get("cep") or "*******"
    bairro = d.get("bairro") or "*******"
    mun = d.get("municipio") or "*******"
    uf = d.get("uf") or "*******"

    email = d.get("email") or "*******"

    tels = []
    for t in d.get("telefones", []):
        tels.append(f"({t.get('ddd')}) {t.get('numero')}")
    telefones = " / ".join(tels) if tels else "*******"

    qsa = d.get("QSA", [])

    # =================================================================
    # Construção da tabela-mãe (6 colunas) com SPANs
    # =================================================================
    data_rows = []

    # Cabeçalhos
    data_rows.append([Paragraph("REPÚBLICA FEDERATIVA DO BRASIL", st_titulo), "", "", "", "", ""])
    data_rows.append([Paragraph("CADASTRO NACIONAL DA PESSOA JURÍDICA", st_sub), "", "", "", "", ""])

    # Inscrição / Título / Abertura
    data_rows.append([
        Paragraph(f"<b>NÚMERO DE INSCRIÇÃO</b><br/>{cnpj_m}<br/>FILIAL", st_txt),
        "",
        Paragraph("<b>COMPROVANTE DE INSCRIÇÃO E DE SITUAÇÃO CADASTRAL</b>", st_sub),
        "",
        Paragraph(f"<b>DATA DE ABERTURA</b><br/>{data_abertura}", st_txt),
        "",
    ])

    # Nome Empresarial
    data_rows.append([
        Paragraph(f"<b>NOME EMPRESARIAL</b><br/>{d.get('razao_social') or '*******'}", st_txt),
        "", "", "", "", "",
    ])

    # Fantasia + Porte
    fantasia = d.get("nome_fantasia") or "*******"
    porte = d.get("porte_empresa") or "*******"
    data_rows.append([
        Paragraph(f"<b>TÍTULO DO ESTABELECIMENTO (NOME DE FANTASIA)</b><br/>{fantasia}", st_txt),
        "", "",  # fantasia ocupa 0-3
        Paragraph(f"<b>PORTE</b><br/>{porte}", st_txt),
        "",  # 4-5
    ])

    # CNAE principal
    data_rows.append([Paragraph(f"<b>CÓDIGO E DESCRIÇÃO DA ATIVIDADE ECONÔMICA PRINCIPAL</b><br/>{cnae_full}", st_txt),
                      "", "", "", "", ""])

    # CNAEs secundários
    data_rows.append([Paragraph(f"<b>CÓDIGO E DESCRIÇÃO DAS ATIVIDADES ECONÔMICAS SECUNDÁRIAS</b><br/>{cnaes_sec}", st_txt),
                      "", "", "", "", ""])

    # Natureza jurídica
    natureza = d.get("natureza_juridica") or "*******"
    data_rows.append([Paragraph(f"<b>CÓDIGO E DESCRIÇÃO DA NATUREZA JURÍDICA</b><br/>{natureza}", st_txt),
                      "", "", "", "", ""])

    # Endereço – linha 1
    data_rows.append([
        Paragraph("<b>LOGRADOURO</b><br/>" + logr, st_txt),
        "", "",
        Paragraph("<b>NÚMERO</b><br/>" + num, st_txt),
        Paragraph("<b>COMPLEMENTO</b><br/>" + comp, st_txt),
        "",
    ])

    # Endereço – linha 2
    data_rows.append([
        Paragraph("<b>CEP</b><br/>" + cep, st_txt),
        Paragraph("<b>BAIRRO/DISTRITO</b><br/>" + bairro, st_txt),
        "",
        Paragraph("<b>MUNICÍPIO</b><br/>" + mun, st_txt),
        "",
        Paragraph("<b>UF</b><br/>" + uf, st_txt),
    ])

    # E-mail + telefone
    data_rows.append([
        Paragraph("<b>ENDEREÇO ELETRÔNICO</b><br/>" + email, st_txt),
        "", "",
        Paragraph("<b>TELEFONE</b><br/>" + telefones, st_txt),
        "",
    ])

    # EFR
    data_rows.append([
        Paragraph("<b>ENTE FEDERATIVO RESPONSÁVEL (EFR)</b><br/>*******", st_txt),
        "", "", "", "", "",
    ])

    # Situação cadastral – com valor em negrito
    data_rows.append([
        Paragraph("<b>SITUAÇÃO CADASTRAL</b><br/>" + situacao_fmt, st_txt),
        "", "",
        Paragraph("<b>DATA DA SITUAÇÃO CADASTRAL</b><br/>" + data_sit, st_txt),
        "",
    ])

    # Motivo
    data_rows.append([
        Paragraph("<b>MOTIVO DA SITUAÇÃO CADASTRAL</b><br/>*******", st_txt),
        "", "", "", "", "",
    ])

    # Situação especial
    data_rows.append([
        Paragraph("<b>SITUAÇÃO ESPECIAL</b><br/>*******", st_txt),
        "", "",
        Paragraph("<b>DATA DA SITUAÇÃO ESPECIAL</b><br/>*******", st_txt),
        "",
    ])

    # QSA
    data_rows.append([Paragraph("QUADRO SOCIETÁRIO (QSA)", st_sub), "", "", "", "", ""])

    base_qsa = len(data_rows)
    if qsa:
        for q in qsa:
            data_rows.append([
                Paragraph(f"<b>Nome:</b> {q.get('nome_socio')}", st_txt),
                "", "",
                Paragraph(f"<b>Documento:</b> {q.get('cnpj_cpf_socio')}", st_txt),
                Paragraph(f"<b>Entrada:</b> {dfmt(q.get('data_entrada_sociedade'))}", st_txt),
                "",
            ])
    else:
        data_rows.append([Paragraph("Nenhum sócio informado", st_txt), "", "", "", "", ""])

    # Assinatura
    idx_ass = len(data_rows)
    data_rows.append([
        Paragraph(
            "Documento emitido automaticamente por Igarapé Digital.<br/>"
            "Assinatura Digital Interna – Validado pelo sistema de automação.<br/>"
            "Documento não oficial – uso interno.",
            st_ass,
        ),
        "", "", "", "", "",
    ])

    # =================================================================
    # SPANs
    # =================================================================
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),

        ("SPAN", (0, 0), (5, 0)),
        ("SPAN", (0, 1), (5, 1)),
        ("SPAN", (0, 2), (1, 2)),
        ("SPAN", (2, 2), (4, 2)),
        ("SPAN", (4, 2), (5, 2)),
        ("SPAN", (0, 3), (5, 3)),
        ("SPAN", (0, 4), (3, 4)),
        ("SPAN", (4, 4), (5, 4)),
        ("SPAN", (0, 5), (5, 5)),
        ("SPAN", (0, 6), (5, 6)),
        ("SPAN", (0, 7), (5, 7)),
        ("SPAN", (0, 8), (2, 8)),
        ("SPAN", (1, 9), (2, 9)),
        ("SPAN", (3, 9), (4, 9)),
        ("SPAN", (0, 10), (2, 10)),
        ("SPAN", (3, 10), (5, 10)),
        ("SPAN", (0, 11), (5, 11)),
        ("SPAN", (0, 12), (2, 12)),
        ("SPAN", (3, 12), (5, 12)),
        ("SPAN", (0, 13), (5, 13)),
        ("SPAN", (0, 14), (2, 14)),
        ("SPAN", (3, 14), (5, 14)),
        ("SPAN", (0, 15), (5, 15)),
    ]

    # QSA spans
    if qsa:
        for i in range(len(qsa)):
            r = base_qsa + i
            style_cmds.append(("SPAN", (0, r), (2, r)))
            style_cmds.append(("SPAN", (3, r), (3, r)))
            style_cmds.append(("SPAN", (4, r), (5, r)))
    else:
        style_cmds.append(("SPAN", (0, base_qsa), (5, base_qsa)))

    style_cmds.append(("SPAN", (0, idx_ass), (5, idx_ass)))

    tabela = Table(
        data_rows,
        colWidths=[5.5 * cm, 5.5 * cm, 3 * cm, 2.5 * cm, 1.5 * cm, 1 * cm],
    )
    tabela.setStyle(TableStyle(style_cmds))

    doc.build([tabela])
    return nome_pdf


# =====================================================================
# APP CustomTkinter (Play, Pause, Stop)
# =====================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Igarapé Digital - Consulta CNPJ")
        self.geometry("900x700")

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.playing = False
        self.paused = False
        self.stop_flag = False
        self.arquivo_excel = None

        self.build_ui()

    # -------------------------------------------------------------
    def build_ui(self):

        titulo = ctk.CTkLabel(
            self, text="Consulta de CNPJs em Lote - OpenCNPJ", font=("Calibri", 24, "bold")
        )
        titulo.pack(pady=15)

        frame_file = ctk.CTkFrame(self)
        frame_file.pack(pady=5)

        btn_sel = ctk.CTkButton(
            frame_file, text="Selecionar Excel", command=self.selecionar_excel, width=200
        )
        btn_sel.grid(row=0, column=0, padx=10)

        self.label_arq = ctk.CTkLabel(self, text="Nenhum arquivo selecionado", font=("Calibri", 14))
        self.label_arq.pack(pady=8)

        frame_qtd = ctk.CTkFrame(self)
        frame_qtd.pack(pady=8)

        ctk.CTkLabel(frame_qtd, text="Quantidade a processar:", font=("Calibri", 14)).grid(
            row=0, column=0, padx=5
        )
        self.entry_qtd = ctk.CTkEntry(frame_qtd, width=120, placeholder_text="todos")
        self.entry_qtd.grid(row=0, column=1, padx=5)

        self.barra = ctk.CTkProgressBar(self, width=820)
        self.barra.set(0)
        self.barra.pack(pady=12)

        self.log = ctk.CTkTextbox(self, width=840, height=320)
        self.log.pack(pady=10)

        frame_btn = ctk.CTkFrame(self)
        frame_btn.pack(pady=10)

        ctk.CTkButton(frame_btn, text="Play", command=self.play, width=180).grid(row=0, column=0, padx=8)
        ctk.CTkButton(frame_btn, text="Pause", command=self.pause, width=180).grid(row=0, column=1, padx=8)
        ctk.CTkButton(frame_btn, text="Stop", command=self.stop, width=180).grid(row=0, column=2, padx=8)

    # -------------------------------------------------------------
    def selecionar_excel(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xls")])
        if p:
            self.arquivo_excel = p
            self.label_arq.configure(text=f"Arquivo selecionado:\n{p}")

    # -------------------------------------------------------------
    def play(self):
        if not self.arquivo_excel:
            messagebox.showerror("Erro", "Selecione um arquivo Excel.")
            return
        self.playing = True
        self.paused = False
        self.stop_flag = False
        self.iniciar_processamento()

    # -------------------------------------------------------------
    def pause(self):
        self.paused = True
        self.log.insert("end", "Processo pausado.\n")

    # -------------------------------------------------------------
    def stop(self):
        self.stop_flag = True
        self.paused = False
        self.log.insert("end", "Processo interrompido.\n")

    # -------------------------------------------------------------
    def iniciar_processamento(self):

        try:
            df = pd.read_excel(self.arquivo_excel)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return

        lista = df.iloc[:, 0].tolist()

        qtd = self.entry_qtd.get().strip()
        if qtd.isdigit():
            lista = lista[: int(qtd)]

        total = len(lista)

        pasta_base = os.path.dirname(self.arquivo_excel)
        pasta_saida = os.path.join(pasta_base, "resultado_cnpj")
        os.makedirs(pasta_saida, exist_ok=True)

        self.log.delete("1.0", "end")
        resultados = []

        for i, raw in enumerate(lista):

            if self.stop_flag:
                break

            while self.paused:
                time.sleep(0.3)
                self.update()

            cnpj = normaliza_cnpj(raw)
            self.log.insert("end", f"Consultando {cnpj}...\n")
            self.update()

            dados = consulta_opencnpj(cnpj)

            if "erro" in dados:
                resultados.append({"cnpj": cnpj, "erro": dados["erro"]})
                self.log.insert("end", f"Erro: {dados['erro']}\n")
            else:
                resultados.append(dados)
                self.log.insert("end", f"Gerando PDF {cnpj}...\n")
                gerar_pdf_cnpj(cnpj, dados, pasta_saida)

            self.barra.set((i + 1) / total)
            self.update()
            time.sleep(0.2)

        saida = os.path.join(pasta_saida, "resultado_cnpj.xlsx")
        df_out = pd.DataFrame(resultados)
        df_out.to_excel(saida, index=False)

        self.log.insert("end", f"\nFINALIZADO.\nArquivo salvo em:\n{saida}\n")
        messagebox.showinfo("Fim", f"Processo concluído.\n{saida}")


# =====================================================================
# INICIAR APP
# =====================================================================
if __name__ == "__main__":
    app = App()
    app.mainloop()
