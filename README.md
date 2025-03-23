# PDF Protect Tool

O **PDF Protect Tool** é uma ferramenta desenvolvida para auxiliar profissionais de RH e DP na proteção de arquivos PDF. Com ela, você pode:
- Selecionar um PDF através de uma interface gráfica intuitiva.
- Extrair automaticamente o CPF contido no PDF (no formato 999.999.999-99).
- Proteger o PDF com uma senha gerada a partir do CPF ou com uma senha personalizada definida pelo usuário.
- Gerar um rascunho de e-mail no Outlook com o PDF protegido anexado, facilitando a comunicação com o destinatário.

## Funcionalidades

- **Proteção Automática:** Usa o CPF extraído para proteger o PDF.
- **Proteção Personalizada:** Permite definir manualmente uma senha para proteger o PDF.
- **Integração com Outlook:** Cria automaticamente um rascunho de e-mail com o PDF protegido anexado.
- **Interface Moderna:** Desenvolvida com CustomTkinter para uma experiência de usuário aprimorada.

## Download

Para baixar o executável ou os arquivos do projeto, clique no link abaixo:

[**Download PDF Protect Tool**](https://drive.google.com/file/d/1FgWPq7p1ShX5k9WXnTP-oZbHzE05kWyS/view?usp=sharing)

## Instalação

### Requisitos

- **Python 3.7+**
- **Dependências Python:**
  - `customtkinter`
  - `tkinter` (geralmente incluso com o Python)
  - `PyPDF2`
  - `pikepdf`
  - `pywin32` (necessário para integração com o Outlook)
  - `pandas` (para funcionalidades de log, se necessário)
  - `pyfiglet` (opcional, para exibir um banner)

### Instalando as Dependências

Abra o terminal e execute:

```bash
pip install customtkinter PyPDF2 pikepdf pywin32 pandas pyfiglet
