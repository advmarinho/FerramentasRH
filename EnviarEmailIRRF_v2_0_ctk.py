from __future__ import annotations

import csv
import re
import sys
import time
import traceback
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from customtkinter import CTkEntry, CTkLabel, CTkButton, CTkTextbox, CTkFrame, CTkScrollableFrame

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except Exception:
    ctk = None
    CTK_AVAILABLE = False

import pandas as pd

import tkinter as tk
from tkinter import filedialog, messagebox


APP_NAME = "CustomerThinker | PDF Protect + Outlook"
VERSAO = "2.0"
SUBPASTA_PROTEGIDOS = "protegidos"
LOG_NAME = "log_envio_informes.csv"
FOOTER_UI = "Anderson Marinho | Igarapé Digital"
RH_CHAMADO_URL = ""

SUBJECT_TEMPLATE = "Informe de Rendimentos {ano_base} - Matrícula {matricula}"
BODY_TEMPLATE = (
    "Olá {nome},\n\n"
    "Segue em anexo o seu Informe de Rendimentos (ano-base {ano_base}).\n"
    "O arquivo está protegido.\n"
    "Senha: seu CPF (somente números, sem ponto e sem traço).\n\n"
    "Caso identifique divergência de valores/dados ou tenha dificuldade de acesso, "
    "abra um chamado para o RH por este canal.\n"
    "{url_chamado}\n\n"
    "Atenciosamente,\n"
    "Recursos Humanos\n"
)


@dataclass
class Colaborador:
    matricula: str
    cpf: str
    nome: str
    email: str


@dataclass
class IdentificacaoPDF:
    cpf_encontrado: str
    nome_encontrado: str
    origem_cpf: str
    cpf_nome_arquivo: str
    divergencia_nome_arquivo: bool
    total_cpfs_validos: int
    texto_extraido: str


@dataclass
class ResultadoProcesso:
    pdf_original: str
    cpf_pdf: str
    nome_pdf: str
    cpf_nome_arquivo: str
    origem_cpf: str
    encontrado_base: bool
    matricula: str
    email: str
    pdf_protegido: str
    status: str
    detalhe: str


# ============================================================
# UTIL GERAL
# ============================================================

def normalizar_texto_simples(valor: str) -> str:
    valor = str(valor or "").strip().upper()
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(ch for ch in valor if not unicodedata.combining(ch))
    valor = re.sub(r"[^A-Z0-9 ]", " ", valor)
    valor = re.sub(r"\s+", " ", valor).strip()
    return valor


def normalizar_cpf(valor) -> str:
    if valor is None:
        return ""
    s = re.sub(r"\D", "", str(valor).strip())
    if not s:
        return ""
    if len(s) < 11:
        s = s.zfill(11)
    return s


def formatar_cpf(cpf: str) -> str:
    cpf = normalizar_cpf(cpf)
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def limpar_nome_extraido(nome: str) -> str:
    nome = " ".join(str(nome or "").split()).strip(" -:")
    cortes = [
        " Natureza do Rendimento",
        " CPF",
        " CNPJ",
        " Valores",
        " Ano Calendário",
    ]
    for marcador in cortes:
        pos = nome.upper().find(marcador.upper())
        if pos > 0:
            nome = nome[:pos].strip(" -:")
    return nome


def validar_cpf(cpf: str) -> bool:
    cpf = normalizar_cpf(cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma1 * 10) % 11
    dig1 = 0 if dig1 == 10 else dig1
    if dig1 != int(cpf[9]):
        return False

    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma2 * 10) % 11
    dig2 = 0 if dig2 == 10 else dig2
    return dig2 == int(cpf[10])


def garantir_pasta(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def extrair_ano_base_do_nome_arquivo(nome_arquivo: str) -> str:
    m = re.search(r"(20\d{2})", nome_arquivo)
    if m:
        return m.group(1)
    ano_atual = int(time.strftime("%Y"))
    return str(ano_atual - 1)


def validar_email_basico(email: str) -> bool:
    if not email:
        return False
    e = email.strip()
    if " " in e or e.count("@") != 1:
        return False
    local, dom = e.split("@")
    if not local or not dom or "." not in dom:
        return False
    if not re.fullmatch(r"[A-Za-z0-9._%+\-]+", local):
        return False
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", dom):
        return False
    tld = dom.rsplit(".", 1)[-1]
    if len(tld) < 2 or not re.fullmatch(r"[A-Za-z]{2,}", tld):
        return False
    return True


def limpar_nome_anexo_removendo_cpf(nome_arquivo: str, cpf11: str) -> str:
    base = nome_arquivo
    if cpf11:
        base = base.replace(cpf11, "")
        base = base.replace(formatar_cpf(cpf11), "")
    base = re.sub(r"__+", "_", base)
    base = re.sub(r"_\.", ".", base)
    base = re.sub(r"_-", "_", base)
    base = re.sub(r"_+", "_", base)
    base = base.strip("_").strip()
    return base or nome_arquivo


# ============================================================
# LEITURA DE TEXTO DO PDF
# ============================================================

def _extrair_texto_pypdf2(pdf_path: Path) -> str:
    try:
        try:
            from PyPDF2 import PdfReader
        except Exception:
            from pypdf import PdfReader
    except Exception:
        return ""

    textos = []
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        for pagina in reader.pages:
            try:
                txt = pagina.extract_text() or ""
            except Exception:
                txt = ""
            textos.append(txt)
    return "\n".join(textos)


def _extrair_texto_pdfplumber(pdf_path: Path) -> str:
    try:
        import pdfplumber
    except Exception:
        return ""

    textos = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                try:
                    txt = pagina.extract_text() or ""
                except Exception:
                    txt = ""
                textos.append(txt)
    except Exception:
        return ""
    return "\n".join(textos)


def extrair_texto_pdf(pdf_path: Path) -> str:
    texto1 = _extrair_texto_pypdf2(pdf_path)
    if texto1 and len(re.sub(r"\s+", "", texto1)) >= 20:
        return texto1

    texto2 = _extrair_texto_pdfplumber(pdf_path)
    if texto2 and len(re.sub(r"\s+", "", texto2)) > len(re.sub(r"\s+", "", texto1)):
        return texto2

    return texto1 or texto2 or ""


# ============================================================
# EXTRAÇÃO UNIVERSAL DE CPF / NOME
# ============================================================

def extrair_cpf_do_nome_arquivo(nome_arquivo: str) -> str:
    candidatos = re.findall(r"\b\d{11}\b|\b\d{3}\.?\d{3}\.?\d{3}\-?\d{2}\b", nome_arquivo)
    for c in candidatos:
        cpf = normalizar_cpf(c)
        if validar_cpf(cpf):
            return cpf
    return ""


def extrair_identidade_secao_beneficiario(texto: str) -> Tuple[str, str]:
    if not texto:
        return "", ""

    match_secao = re.search(
        r"2\.\s*PESSOA\s+F[IÍ]SICA\s+BENEFICI[ÁA]RIA\s+DOS\s+RENDIMENTOS",
        texto,
        flags=re.IGNORECASE,
    )

    chunks = []
    if match_secao:
        ini = max(0, match_secao.start() - 250)
        meio = match_secao.end()
        fim = min(len(texto), match_secao.end() + 1200)
        chunks.append(texto[meio:fim])      # prioriza o conteúdo após o cabeçalho
        chunks.append(texto[ini:fim])       # fallback para layouts que colam dados antes do título
    else:
        chunks.append(texto)

    padroes = [
        (r"CPF\s*:?\s*([\d\.\-]{11,14}).{0,180}?NOME(?:\s+COMPLETO)?\s*:?\s*([A-ZÀ-Ú][A-ZÀ-Ú'\-\s]{5,})", "cpf_nome"),
        (r"NOME(?:\s+COMPLETO)?\s*:?\s*([A-ZÀ-Ú][A-ZÀ-Ú'\-\s]{5,}).{0,180}?CPF\s*:?\s*([\d\.\-]{11,14})", "nome_cpf"),
        (r"([\d\.\-]{11,14})\s*CPF\s*:?\s*([A-ZÀ-Ú][A-ZÀ-Ú'\-\s]{5,})\s*NOME", "cpf_nome_fechando"),
    ]

    for chunk in chunks:
        for padrao, modo in padroes:
            m = re.search(padrao, chunk, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue

            if modo == "cpf_nome":
                cpf, nome = m.group(1), m.group(2)
            elif modo == "nome_cpf":
                nome, cpf = m.group(1), m.group(2)
            else:
                cpf, nome = m.group(1), m.group(2)

            cpf = normalizar_cpf(cpf)
            nome = limpar_nome_extraido(nome)
            if validar_cpf(cpf):
                return cpf, nome

    for chunk in chunks:
        linhas = [l.strip() for l in chunk.splitlines() if l.strip()]
        cpf, nome = "", ""
        for i, linha in enumerate(linhas):
            up = normalizar_texto_simples(linha)

            if up == "CPF" and i + 1 < len(linhas):
                candidato = normalizar_cpf(linhas[i + 1])
                if validar_cpf(candidato):
                    cpf = candidato

            if up in {"NOME", "NOME COMPLETO"} and i + 1 < len(linhas):
                prox = linhas[i + 1]
                prox_up = normalizar_texto_simples(prox)
                if prox_up not in {"CPF", "NOME", "NOME COMPLETO"} and len(prox_up) > 4:
                    nome = limpar_nome_extraido(prox)

        if cpf:
            return cpf, nome

    return "", ""


def encontrar_cpfs_no_texto(texto: str) -> List[Dict[str, object]]:
    resultados: List[Dict[str, object]] = []
    if not texto:
        return resultados

    padrao = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}\-?\d{2}\b|\b\d{11}\b")

    for match in padrao.finditer(texto):
        bruto = match.group(0)
        cpf = normalizar_cpf(bruto)

        if not validar_cpf(cpf):
            continue

        ini = max(0, match.start() - 160)
        fim = min(len(texto), match.end() + 160)
        contexto = texto[ini:fim]

        resultados.append(
            {
                "cpf": cpf,
                "cpf_bruto": bruto,
                "posicao": match.start(),
                "contexto": contexto,
            }
        )

    vistos = set()
    unicos: List[Dict[str, object]] = []
    for item in resultados:
        cpf = str(item["cpf"])
        if cpf not in vistos:
            vistos.add(cpf)
            unicos.append(item)

    return unicos


def pontuar_contexto_cpf(contexto: str) -> int:
    contexto_up = normalizar_texto_simples(contexto)
    score = 0

    termos_fortes = {
        "CPF": 20,
        "NOME": 10,
        "BENEFICIARIA": 12,
        "BENEFICIARIO": 12,
        "PESSOA FISICA": 12,
        "RENDIMENTOS": 8,
        "COLABORADOR": 8,
        "FUNCIONARIO": 8,
        "FUNCIONARIOA": 8,
        "TITULAR": 8,
    }

    termos_negativos = {
        "RESPONSAVEL": -15,
        "CONTADOR": -15,
        "REPRESENTANTE": -12,
        "PROCURADOR": -10,
        "FONTE PAGADORA": -6,
        "CNPJ": -6,
    }

    for termo, peso in termos_fortes.items():
        if termo in contexto_up:
            score += peso

    for termo, peso in termos_negativos.items():
        if termo in contexto_up:
            score += peso

    if re.search(r"NOME\s*:?\s*.*?CPF", contexto, flags=re.IGNORECASE | re.DOTALL):
        score += 30
    if re.search(r"CPF\s*:?\s*\d", contexto, flags=re.IGNORECASE):
        score += 20
    if re.search(r"2\.?\s*PESSOA\s+F[IÍ]SICA\s+BENEFICI[ÁA]RIA", contexto, flags=re.IGNORECASE):
        score += 30

    return score


def escolher_cpf_mais_provavel(texto: str) -> Optional[Dict[str, object]]:
    candidatos = encontrar_cpfs_no_texto(texto)
    if not candidatos:
        return None

    for item in candidatos:
        item["score"] = pontuar_contexto_cpf(str(item["contexto"]))

    candidatos.sort(key=lambda x: (int(x["score"]), -int(x["posicao"])), reverse=True)
    return candidatos[0]


def extrair_nome_proximo_ao_cpf(texto: str, cpf: str) -> str:
    if not texto or not cpf:
        return ""

    cpf_fmt = formatar_cpf(cpf)
    padroes = [
        rf"Nome\s*:?\s*([A-ZÀ-Úa-zà-ú'\-\s]+?)\s+CPF\s*:?\s*{re.escape(cpf_fmt)}",
        rf"Nome\s*:?\s*([A-ZÀ-Úa-zà-ú'\-\s]+?)\s+CPF\s*:?\s*{re.escape(cpf)}",
        rf"Nome\s*:?\s*([A-ZÀ-Úa-zà-ú'\-\s]+?)\s+CPF\s*:?\s*\d{{3}}\.?\d{{3}}\.?\d{{3}}\-?\d{{2}}",
        rf"NOME COMPLETO\s*:?\s*([A-ZÀ-Úa-zà-ú'\-\s]+?)\s+CPF",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto, flags=re.IGNORECASE | re.DOTALL)
        if m:
            nome = " ".join(m.group(1).split()).strip(" -:")
            if nome:
                return limpar_nome_extraido(nome)

    indice = texto.find(cpf_fmt)
    if indice < 0:
        indice = texto.find(cpf)

    if indice >= 0:
        trecho_ini = max(0, indice - 200)
        trecho = texto[trecho_ini:indice + 50]
        linhas = [l.strip() for l in trecho.splitlines() if l.strip()]
        for linha in reversed(linhas):
            linha_up = normalizar_texto_simples(linha)
            if "NOME" in linha_up and "CPF" not in linha_up:
                candidato = re.sub(r"^.*?NOME\s*:?", "", linha, flags=re.IGNORECASE).strip(" -:")
                candidato = " ".join(candidato.split())
                if candidato:
                    return candidato

    return ""


def identificar_pdf(pdf_path: Path) -> IdentificacaoPDF:
    texto = extrair_texto_pdf(pdf_path)
    cpf_nome_arquivo = extrair_cpf_do_nome_arquivo(pdf_path.name)

    cpf_secao, nome_secao = extrair_identidade_secao_beneficiario(texto)
    if cpf_secao:
        divergencia = bool(cpf_nome_arquivo and cpf_secao and cpf_nome_arquivo != cpf_secao)
        return IdentificacaoPDF(
            cpf_encontrado=cpf_secao,
            nome_encontrado=nome_secao,
            origem_cpf="secao_beneficiario",
            cpf_nome_arquivo=cpf_nome_arquivo,
            divergencia_nome_arquivo=divergencia,
            total_cpfs_validos=len(encontrar_cpfs_no_texto(texto)),
            texto_extraido=texto,
        )

    melhor = escolher_cpf_mais_provavel(texto)
    if melhor:
        cpf_texto = str(melhor["cpf"])
        nome_texto = extrair_nome_proximo_ao_cpf(texto, cpf_texto)
        origem = "conteudo_pdf"
        divergencia = bool(cpf_nome_arquivo and cpf_texto and cpf_nome_arquivo != cpf_texto)
        return IdentificacaoPDF(
            cpf_encontrado=cpf_texto,
            nome_encontrado=nome_texto,
            origem_cpf=origem,
            cpf_nome_arquivo=cpf_nome_arquivo,
            divergencia_nome_arquivo=divergencia,
            total_cpfs_validos=len(encontrar_cpfs_no_texto(texto)),
            texto_extraido=texto,
        )

    if cpf_nome_arquivo:
        return IdentificacaoPDF(
            cpf_encontrado=cpf_nome_arquivo,
            nome_encontrado="",
            origem_cpf="nome_arquivo_fallback",
            cpf_nome_arquivo=cpf_nome_arquivo,
            divergencia_nome_arquivo=False,
            total_cpfs_validos=0,
            texto_extraido=texto,
        )

    return IdentificacaoPDF(
        cpf_encontrado="",
        nome_encontrado="",
        origem_cpf="nao_encontrado",
        cpf_nome_arquivo=cpf_nome_arquivo,
        divergencia_nome_arquivo=False,
        total_cpfs_validos=0,
        texto_extraido=texto,
    )


# ============================================================
# BASE DE COLABORADORES
# ============================================================

def _normalizar_cabecalho(cab: str) -> str:
    return normalizar_texto_simples(cab).replace(" ", "")


def _mapear_colunas(df: pd.DataFrame) -> Dict[str, str]:
    aliases = {
        "cpf": ["CPF"],
        "matricula": ["Matrícula", "Matricula", "Matr", "Registro"],
        "nome": ["Nome", "Nome Completo", "Colaborador", "Funcionario", "Funcionário"],
        "email": ["Email Alternativo", "Email", "E-mail", "Email Pessoal", "E-mail Alternativo"],
    }

    colunas_norm = {_normalizar_cabecalho(c): c for c in df.columns}
    resolvidas: Dict[str, str] = {}

    for chave, possiveis in aliases.items():
        encontrado = None
        for nome in possiveis:
            alvo = _normalizar_cabecalho(nome)
            if alvo in colunas_norm:
                encontrado = colunas_norm[alvo]
                break
        if not encontrado:
            raise ValueError(
                "Não foi possível localizar as colunas obrigatórias na base. "
                f"Coluna ausente: {chave}. Colunas encontradas: {', '.join(map(str, df.columns))}"
            )
        resolvidas[chave] = encontrado

    return resolvidas


def ler_base_colaboradores_arquivo(arquivo_path: Path) -> Dict[str, Colaborador]:
    ext = arquivo_path.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(
            arquivo_path,
            dtype=str,
            sep=None,
            engine="python",
            encoding="utf-8",
            keep_default_na=False,
        )
    elif ext in [".xls", ".xlsx", ".xlsm"]:
        df = pd.read_excel(arquivo_path, dtype=str).fillna("")
    elif ext == ".xlsb":
        df = pd.read_excel(arquivo_path, dtype=str, engine="pyxlsb").fillna("")
    else:
        raise ValueError("Formato não suportado. Use CSV/XLS/XLSX/XLSM/XLSB.")

    return _converter_dataframe_em_base(df)


def ler_base_colaboradores_texto(texto: str) -> Dict[str, Colaborador]:
    linhas = [linha.rstrip() for linha in texto.splitlines() if linha.strip()]
    if not linhas:
        raise ValueError("Nenhum dado foi colado na área de texto.")

    delimitador = "\t" if "\t" in linhas[0] else ";"
    cabecalhos = [c.strip() for c in linhas[0].split(delimitador)]
    dados = []

    for linha in linhas[1:]:
        partes = [p.strip() for p in linha.split(delimitador)]
        if len(partes) < len(cabecalhos):
            partes += [""] * (len(cabecalhos) - len(partes))
        dados.append(partes[: len(cabecalhos)])

    df = pd.DataFrame(dados, columns=cabecalhos)
    return _converter_dataframe_em_base(df)


def _converter_dataframe_em_base(df: pd.DataFrame) -> Dict[str, Colaborador]:
    if df.empty:
        raise ValueError("A base está vazia.")

    mapa = _mapear_colunas(df)
    base: Dict[str, Colaborador] = {}

    for _, row in df.fillna("").iterrows():
        cpf = normalizar_cpf(row.get(mapa["cpf"], ""))
        if not cpf:
            continue

        base[cpf] = Colaborador(
            matricula=str(row.get(mapa["matricula"], "")).strip(),
            cpf=cpf,
            nome=str(row.get(mapa["nome"], "")).strip(),
            email=str(row.get(mapa["email"], "")).strip(),
        )

    if not base:
        raise ValueError("Nenhum CPF válido foi identificado na base.")

    return base


def obter_base(base_path: Optional[Path], base_texto: str) -> Dict[str, Colaborador]:
    if base_texto and base_texto.strip():
        return ler_base_colaboradores_texto(base_texto)
    if base_path:
        return ler_base_colaboradores_arquivo(base_path)
    raise ValueError("Informe uma base por arquivo ou cole os dados diretamente na tela.")


# ============================================================
# PROTEÇÃO / OUTLOOK / LOG
# ============================================================

def proteger_pdf_com_senha(pdf_path: Path, senha: str, saida_dir: Path) -> Path:
    try:
        import pikepdf
    except Exception as e:
        raise RuntimeError("pikepdf não está instalado. Instale com: pip install pikepdf") from e

    garantir_pasta(saida_dir)
    out_name = pdf_path.stem + "_protegido.pdf"
    out_path = saida_dir / out_name

    if out_path.exists():
        out_path.unlink()

    with pikepdf.open(pdf_path) as pdf:
        pdf.save(out_path, encryption=pikepdf.Encryption(owner=senha, user=senha, R=4))

    return out_path


def outlook_criar_rascunho_sem_exibir(
    para: str,
    assunto: str,
    corpo: str,
    anexo_path: Path,
    display_name: str,
) -> None:
    try:
        import win32com.client as win32
    except Exception as e:
        raise RuntimeError(
            "win32com.client não está disponível. Instale pywin32 para integração com Outlook."
        ) from e

    outlook = win32.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = para
    mail.Subject = assunto
    mail.Body = corpo
    mail.Attachments.Add(str(anexo_path.resolve()), 1, 1, display_name)
    mail.Save()


def escrever_log_csv(log_path: Path, resultados: List[ResultadoProcesso]) -> None:
    garantir_pasta(log_path.parent)
    existe = log_path.exists()

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        if not existe:
            writer.writerow(
                [
                    "timestamp",
                    "pdf_original",
                    "cpf_pdf",
                    "nome_pdf",
                    "cpf_nome_arquivo",
                    "origem_cpf",
                    "encontrado_base",
                    "matricula",
                    "email",
                    "pdf_protegido",
                    "status",
                    "detalhe",
                ]
            )

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for r in resultados:
            writer.writerow(
                [
                    ts,
                    r.pdf_original,
                    r.cpf_pdf,
                    r.nome_pdf,
                    r.cpf_nome_arquivo,
                    r.origem_cpf,
                    "SIM" if r.encontrado_base else "NAO",
                    r.matricula,
                    r.email,
                    r.pdf_protegido,
                    r.status,
                    r.detalhe,
                ]
            )


def resumir_resultados(resultados: List[ResultadoProcesso], modo: str) -> str:
    total = len(resultados)
    ok = sum(1 for r in resultados if r.status == "OK")
    pulado = sum(1 for r in resultados if r.status == "PULADO")
    falha = sum(1 for r in resultados if r.status == "FALHA")

    linhas = [
        f"{APP_NAME} v{VERSAO}",
        f"Modo: {modo}",
        f"Total PDFs: {total}",
        f"OK: {ok}",
        f"PULADOS: {pulado}",
        f"FALHAS: {falha}",
    ]
    return "\n".join(linhas)


# ============================================================
# PROCESSAMENTO
# ============================================================

def listar_pdfs(origem: Path) -> List[Path]:
    if origem.is_file():
        if origem.suffix.lower() != ".pdf":
            raise ValueError("O arquivo selecionado não é um PDF.")
        return [origem]

    if origem.is_dir():
        pdfs = sorted([p for p in origem.glob("*.pdf") if p.is_file()])
        if not pdfs:
            raise ValueError("Nenhum PDF encontrado na pasta selecionada.")
        return pdfs

    raise ValueError("Origem inválida para PDFs.")


def localizar_colaborador(base: Dict[str, Colaborador], cpf: str) -> Optional[Colaborador]:
    cpf = normalizar_cpf(cpf)
    if not cpf:
        return None
    return base.get(cpf)


def processar_arquivos(
    origem_pdf: Path,
    base_path: Optional[Path] = None,
    base_texto: str = "",
    criar_rascunho: bool = True,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Tuple[List[ResultadoProcesso], Path]:
    pdfs = listar_pdfs(origem_pdf)
    base: Dict[str, Colaborador] = {}

    if criar_rascunho:
        base = obter_base(base_path, base_texto)

    pasta_saida = origem_pdf.parent if origem_pdf.is_file() else origem_pdf
    saida_dir = pasta_saida / SUBPASTA_PROTEGIDOS
    garantir_pasta(saida_dir)

    resultados: List[ResultadoProcesso] = []
    total = len(pdfs)

    for i, pdf in enumerate(pdfs, start=1):
        if on_progress:
            on_progress(i, total)

        try:
            identificacao = identificar_pdf(pdf)
        except Exception as e:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf="",
                nome_pdf="",
                cpf_nome_arquivo="",
                origem_cpf="erro_extracao",
                encontrado_base=False,
                matricula="",
                email="",
                pdf_protegido="",
                status="FALHA",
                detalhe=f"Erro ao ler PDF: {e}",
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe}")
            continue

        cpf_pdf = normalizar_cpf(identificacao.cpf_encontrado)
        nome_pdf = identificacao.nome_encontrado
        detalhe_base = []

        if identificacao.divergencia_nome_arquivo:
            detalhe_base.append(
                f"CPF do conteúdo diverge do nome do arquivo ({formatar_cpf(identificacao.cpf_nome_arquivo)})."
            )

        if not cpf_pdf:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf="",
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=False,
                matricula="",
                email="",
                pdf_protegido="",
                status="FALHA",
                detalhe="CPF não encontrado no conteúdo do PDF nem no nome do arquivo.",
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe}")
            continue

        if not criar_rascunho:
            detalhe = f"CPF identificado por {identificacao.origem_cpf}."
            if nome_pdf:
                detalhe += f" Nome lido: {nome_pdf}."
            if detalhe_base:
                detalhe += " " + " ".join(detalhe_base)

            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=False,
                matricula="",
                email="",
                pdf_protegido="",
                status="OK",
                detalhe=detalhe,
            )
            resultados.append(r)
            if on_log:
                on_log(
                    f"OK: {pdf.name} | CPF={formatar_cpf(cpf_pdf)} | origem={identificacao.origem_cpf}"
                )
            continue

        colab = localizar_colaborador(base, cpf_pdf)
        if not colab:
            detalhe = "CPF encontrado no PDF, mas não está na base informada."
            if detalhe_base:
                detalhe += " " + " ".join(detalhe_base)
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=False,
                matricula="",
                email="",
                pdf_protegido="",
                status="PULADO",
                detalhe=detalhe,
            )
            resultados.append(r)
            if on_log:
                on_log(f"PULADO: {pdf.name} | CPF={formatar_cpf(cpf_pdf)} não localizado na base")
            continue

        if not colab.email:
            detalhe = "Email vazio na base para o CPF localizado."
            if detalhe_base:
                detalhe += " " + " ".join(detalhe_base)
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=True,
                matricula=colab.matricula,
                email="",
                pdf_protegido="",
                status="FALHA",
                detalhe=detalhe,
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | e-mail vazio na base")
            continue

        if not validar_email_basico(colab.email):
            detalhe = f"E-mail inválido na base: {colab.email}"
            if detalhe_base:
                detalhe += " " + " ".join(detalhe_base)
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=True,
                matricula=colab.matricula,
                email=colab.email,
                pdf_protegido="",
                status="FALHA",
                detalhe=detalhe,
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | e-mail inválido | {colab.email}")
            continue

        try:
            ano_base = extrair_ano_base_do_nome_arquivo(pdf.name)
            assunto = SUBJECT_TEMPLATE.format(ano_base=ano_base, matricula=(colab.matricula or "N/A"))
            corpo = BODY_TEMPLATE.format(
                nome=(colab.nome or nome_pdf or "Colaborador(a)"),
                ano_base=ano_base,
                url_chamado=RH_CHAMADO_URL,
            )

            protegido = proteger_pdf_com_senha(pdf, cpf_pdf, saida_dir)
            display_name = limpar_nome_anexo_removendo_cpf(pdf.name, cpf_pdf)

            outlook_criar_rascunho_sem_exibir(
                para=colab.email,
                assunto=assunto,
                corpo=corpo,
                anexo_path=protegido,
                display_name=display_name,
            )

            detalhe = "Rascunho criado com PDF protegido."
            if detalhe_base:
                detalhe += " " + " ".join(detalhe_base)

            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=True,
                matricula=colab.matricula,
                email=colab.email,
                pdf_protegido=protegido.name,
                status="OK",
                detalhe=detalhe,
            )
            resultados.append(r)
            if on_log:
                on_log(
                    f"OK: {pdf.name} | CPF={formatar_cpf(cpf_pdf)} | email={colab.email} | rascunho salvo"
                )

        except Exception as e:
            r = ResultadoProcesso(
                pdf_original=pdf.name,
                cpf_pdf=cpf_pdf,
                nome_pdf=nome_pdf,
                cpf_nome_arquivo=identificacao.cpf_nome_arquivo,
                origem_cpf=identificacao.origem_cpf,
                encontrado_base=True,
                matricula=colab.matricula,
                email=colab.email,
                pdf_protegido="",
                status="FALHA",
                detalhe=f"Erro ao proteger PDF ou criar rascunho: {e}",
            )
            resultados.append(r)
            if on_log:
                on_log(f"FALHA: {pdf.name} | {r.detalhe}")

    log_path = pasta_saida / LOG_NAME
    escrever_log_csv(log_path, resultados)
    return resultados, log_path


# ============================================================
# UI
# ============================================================

if CTK_AVAILABLE:

    class App(ctk.CTk):
        def __init__(self):
            super().__init__()

            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")

            self.title(f"{APP_NAME} | v{VERSAO}")
            self.geometry("1180x780")
            self.minsize(1180, 780)

            self.origem_pdf: Optional[Path] = None
            self.base_path: Optional[Path] = None
            self._montar_ui()

        def _montar_ui(self):
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(3, weight=1)

            frame_top = ctk.CTkFrame(self)
            frame_top.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
            frame_top.grid_columnconfigure(0, weight=1)

            lbl_titulo = ctk.CTkLabel(
                frame_top,
                text=f"{APP_NAME} | v{VERSAO}",
                font=ctk.CTkFont(size=22, weight="bold"),
            )
            lbl_titulo.grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")

            lbl_sub = ctk.CTkLabel(
                frame_top,
                text=(
                    "Leitura universal de PDF para encontrar CPF no conteúdo, com suporte a PDF único "
                    "ou pasta inteira, proteção por senha e criação de rascunho no Outlook."
                ),
                font=ctk.CTkFont(size=13),
                justify="left",
            )
            lbl_sub.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

            frame_origem = ctk.CTkFrame(self)
            frame_origem.grid(row=1, column=0, padx=16, pady=8, sticky="ew")
            frame_origem.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(frame_origem, text="Origem PDF").grid(row=0, column=0, padx=12, pady=10, sticky="w")

            self.ent_origem = ctk.CTkEntry(frame_origem)
            self.ent_origem.grid(row=0, column=1, padx=12, pady=10, sticky="ew")
            self._set_entry_readonly(self.ent_origem, "")

            ctk.CTkButton(frame_origem, text="Selecionar Pasta", width=140, command=self._selecionar_pasta).grid(
                row=0, column=2, padx=6, pady=10
            )
            ctk.CTkButton(frame_origem, text="Selecionar PDF", width=140, command=self._selecionar_pdf).grid(
                row=0, column=3, padx=(6, 12), pady=10
            )

            frame_base = ctk.CTkFrame(self)
            frame_base.grid(row=2, column=0, padx=16, pady=8, sticky="ew")
            frame_base.grid_columnconfigure(1, weight=1)
            frame_base.grid_rowconfigure(2, weight=1)

            ctk.CTkLabel(frame_base, text="Base por arquivo").grid(row=0, column=0, padx=12, pady=10, sticky="w")

            self.ent_base = ctk.CTkEntry(frame_base)
            self.ent_base.grid(row=0, column=1, padx=12, pady=10, sticky="ew")
            self._set_entry_readonly(self.ent_base, "")

            ctk.CTkButton(frame_base, text="Selecionar Base", width=140, command=self._selecionar_base).grid(
                row=0, column=2, padx=(6, 12), pady=10
            )

            ctk.CTkLabel(
                frame_base,
                text="Ou cole a base abaixo. Cabeçalhos aceitos: CPF, Matrícula/Matricula, Nome, Email/Email Alternativo",
            ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 6), sticky="w")

            self.txt_base = ctk.CTkTextbox(frame_base, height=145)
            self.txt_base.grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 12), sticky="ew")
            self.txt_base.insert(
                "1.0",
                "CPF;Matrícula;Nome;Email Alternativo\n"
                "12345678900;123456;Nome e Sobrenome;email@exemplo.com\n"
                
            )

            frame_exec = ctk.CTkFrame(self)
            frame_exec.grid(row=3, column=0, padx=16, pady=8, sticky="nsew")
            frame_exec.grid_columnconfigure(0, weight=1)
            frame_exec.grid_rowconfigure(2, weight=1)

            botoes = ctk.CTkFrame(frame_exec)
            botoes.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
            botoes.grid_columnconfigure(5, weight=1)

            self.btn_localizar = ctk.CTkButton(
                botoes,
                text="Encontrar CPF(s)",
                width=180,
                command=self._iniciar_localizacao,
            )
            self.btn_localizar.grid(row=0, column=0, padx=(0, 10), pady=8, sticky="w")

            self.btn_iniciar = ctk.CTkButton(
                botoes,
                text="Proteger + Criar Rascunho",
                width=220,
                command=self._iniciar_rascunho,
            )
            self.btn_iniciar.grid(row=0, column=1, padx=10, pady=8, sticky="w")

            self.btn_validar_base = ctk.CTkButton(
                botoes,
                text="Validar Base Colada",
                width=180,
                command=self._validar_base_colada,
            )
            self.btn_validar_base.grid(row=0, column=2, padx=10, pady=8, sticky="w")

            self.btn_reiniciar = ctk.CTkButton(
                botoes,
                text="Reiniciar Processo",
                width=170,
                command=self._reiniciar,
            )
            self.btn_reiniciar.grid(row=0, column=3, padx=10, pady=8, sticky="w")
#boton para gerar template excel
            self.btn_template = ctk.CTkButton(
                botoes,
                text="Gerar Template Excel",
                width=190,
                command=self._gerar_template_excel
            )
            self.btn_template.grid(row=0, column=4, padx=10, pady=8, sticky="w")

            self.progress = ctk.CTkProgressBar(frame_exec)
            self.progress.grid(row=1, column=0, padx=12, pady=(2, 6), sticky="ew")
            self.progress.set(0)

            self.lbl_prog = ctk.CTkLabel(frame_exec, text="0/0")
            self.lbl_prog.grid(row=1, column=0, padx=12, pady=(2, 6), sticky="e")

            self.txt_log = ctk.CTkTextbox(frame_exec)
            self.txt_log.grid(row=2, column=0, padx=12, pady=(6, 12), sticky="nsew")
            self.txt_log.configure(state="disabled")

            footer = ctk.CTkLabel(self, text=FOOTER_UI, font=ctk.CTkFont(size=11))
            footer.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="e")

        def _set_entry_readonly(self, entry: CTkEntry, value: str):
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
            entry.configure(state="readonly")

        def _selecionar_pasta(self):
            p = filedialog.askdirectory(title="Selecione a pasta com PDFs")
            if p:
                self.origem_pdf = Path(p)
                self._set_entry_readonly(self.ent_origem, str(self.origem_pdf))
                self._log(f"Pasta selecionada: {self.origem_pdf}")

        def _selecionar_pdf(self):
            p = filedialog.askopenfilename(
                title="Selecione um PDF",
                filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
            )
            if p:
                self.origem_pdf = Path(p)
                self._set_entry_readonly(self.ent_origem, str(self.origem_pdf))
                self._log(f"PDF selecionado: {self.origem_pdf}")

        def _selecionar_base(self):
            p = filedialog.askopenfilename(
                title="Selecione a base",
                filetypes=[("Bases suportadas", "*.csv *.xls *.xlsx *.xlsm *.xlsb"), ("Todos", "*.*")],
            )
            if p:
                self.base_path = Path(p)
                self._set_entry_readonly(self.ent_base, str(self.base_path))
                self._log(f"Base selecionada: {self.base_path}")

        def _log(self, msg: str):
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", msg + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")

        def _limpar_log(self):
            self.txt_log.configure(state="normal")
            self.txt_log.delete("1.0", "end")
            self.txt_log.configure(state="disabled")

        def _on_progress(self, atual: int, total: int):
            if total <= 0:
                self.progress.set(0)
                self.lbl_prog.configure(text="0/0")
                return
            self.progress.set(atual / total)
            self.lbl_prog.configure(text=f"{atual}/{total}")
            self.update_idletasks()

        def _texto_base(self) -> str:
            texto = self.txt_base.get("1.0", "end").strip()
            exemplo = (
                "CPF;Matrícula;Nome;Email Alternativo\n"
                "12345678900;123456;Nome e Sobrenome;email@exemplo.com\n"
                
            )
            if texto == exemplo:
                return ""
            return texto

        def _validar_base_colada(self):
            try:
                texto = self._texto_base()
                base = obter_base(self.base_path, texto)
                self._log(f"Base validada com sucesso. Total de CPFs carregados: {len(base)}")
                messagebox.showinfo("Base validada", f"Base validada com sucesso.\n\nTotal de CPFs: {len(base)}")
            except Exception as e:
                self._log(f"Erro ao validar base: {e}")
                messagebox.showerror("Erro na base", str(e))

        def _alternar_botoes(self, habilitar: bool):
            estado = "normal" if habilitar else "disabled"
            self.btn_localizar.configure(state=estado)
            self.btn_iniciar.configure(state=estado)
            self.btn_validar_base.configure(state=estado)
            self.btn_reiniciar.configure(state=estado)

        def _reiniciar(self):
            self.origem_pdf = None
            self.base_path = None
            self._set_entry_readonly(self.ent_origem, "")
            self._set_entry_readonly(self.ent_base, "")
            self.txt_base.delete("1.0", "end")
            self._limpar_log()
            self.progress.set(0)
            self.lbl_prog.configure(text="0/0")
            self._log("Tela reiniciada. Pronto para novo processamento.")

        def _gerar_template_excel(self):
            try:
                caminho = gerar_template_excel()

                self._log(f"Template Excel gerado: {caminho}")

                messagebox.showinfo(
                    "Template criado",
                    f"O template foi criado com sucesso.\n\n{caminho}"
                )

            except Exception as e:
                messagebox.showerror(
                    "Erro ao gerar template",
                    str(e)
                )

        def _executar(self, criar_rascunho: bool):
            if not self.origem_pdf:
                self._log("Erro: selecione uma pasta ou um PDF antes de iniciar.")
                messagebox.showerror("Erro", "Selecione uma pasta ou um PDF antes de iniciar.")
                return

            if criar_rascunho:
                texto = self._texto_base()
                if not self.base_path and not texto:
                    self._log("Erro: informe uma base por arquivo ou cole os dados na tela.")
                    messagebox.showerror(
                        "Erro",
                        "Para criar rascunhos, informe uma base por arquivo ou cole os dados diretamente na tela.",
                    )
                    return
            else:
                texto = self._texto_base()

            self._alternar_botoes(False)
            self.progress.set(0)
            self.lbl_prog.configure(text="0/0")

            modo = "Proteger + Criar Rascunho" if criar_rascunho else "Encontrar CPF(s)"
            self._log("")
            self._log("Iniciando processamento...")
            self._log(f"Modo: {modo}")
            self._log(f"Origem: {self.origem_pdf}")
            if criar_rascunho:
                self._log("Base usada: base colada na tela" if texto else f"Base usada: {self.base_path}")
            self._log("")

            def worker():
                try:
                    resultados, log_path = processar_arquivos(
                        origem_pdf=self.origem_pdf,
                        base_path=self.base_path,
                        base_texto=texto,
                        criar_rascunho=criar_rascunho,
                        on_progress=lambda a, t: self.after(0, self._on_progress, a, t),
                        on_log=lambda m: self.after(0, self._log, m),
                    )

                    resumo = resumir_resultados(resultados, modo)
                    self.after(0, self._log, "")
                    self.after(0, self._log, resumo)
                    self.after(0, self._log, f"Log salvo em: {log_path}")
                    self.after(0, messagebox.showinfo, "Processo concluído", resumo + f"\n\nLog: {log_path}")

                except Exception as e:
                    msg = f"Ocorreu um erro: {e}\n\n{traceback.format_exc()}"
                    self.after(0, self._log, msg)
                    self.after(0, messagebox.showerror, "Erro", msg)
                finally:
                    self.after(0, self._alternar_botoes, True)

            threading.Thread(target=worker, daemon=True).start()

        def _iniciar_localizacao(self):
            self._executar(criar_rascunho=False)

        def _iniciar_rascunho(self):
            self._executar(criar_rascunho=True)

else:

    class App:
        def __init__(self):
            raise RuntimeError(
                "customtkinter não está instalado. Instale com: pip install customtkinter"
            )
# ============================================================
# GERAR TEMPLATE EXCEL DE EXEMPLO
# ============================================================

def gerar_template_excel(destino: Path = None):
    """
    Gera um arquivo Excel modelo para preenchimento da base de colaboradores.
    """

    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("Instale as dependências: pip install pandas openpyxl")

    if destino is None:
        destino = Path.cwd() / "template_base_colaboradores.xlsx"

    dados = {
        "CPF": [
            "12345678900",
            "12345678901",
            "12345678902",
            "12345678903"
        ],
        "Matrícula": [
            "0001",
            "0002",
            "0003",
            "0004"
        ],
        "Nome": [
            "Fulano de Tal Sobrenome1",
            "Fulano de Tal Sobrenome2",
            "Fulano de Tal Sobrenome3",
            "Fulano de Tal Sobrenome4"
        ],
        "Email": [
            "fulano1@email.com",
            "fulano2@email.com",
            "fulano3@email.com",
            "fulano4@email.com"
        ]
    }

    df = pd.DataFrame(dados)

    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="BaseEnvio", index=False)

    return destino

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
