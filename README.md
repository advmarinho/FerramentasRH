# PDF Protect Tool

O **PDF Protect Tool** é uma ferramenta desenvolvida para auxiliar profissionais de RH, DP e demais interessados na proteção de arquivos PDF. Através desta aplicação, você pode:

- **Selecionar um arquivo PDF** através de uma interface gráfica intuitiva.
- **Extrair automaticamente o CPF** presente no PDF (no formato 999.999.999-99).
- **Proteger o PDF** com uma senha gerada a partir do CPF extraído ou uma senha personalizada definida pelo usuário.
- **Gerar um rascunho de e-mail** no Outlook com o PDF protegido anexado, facilitando a comunicação com o destinatário.

## Funcionalidades

- **Proteção Automática:** Extrai o CPF do PDF e protege o arquivo utilizando o CPF como senha.
- **Proteção Personalizada:** Permite que o usuário defina uma senha manualmente para proteger o PDF.
- **Integração com Outlook:** Cria um rascunho de e-mail com o PDF protegido anexado.
- **Interface Gráfica Moderna:** Desenvolvida com CustomTkinter para uma melhor experiência de uso.

## Instalação

### Requisitos

- **Python 3.7+**
- **Dependências Python:**
  - `customtkinter`
  - `tkinter` (já incluso na maioria das instalações do Python)
  - `PyPDF2`
  - `pikepdf`
  - `pywin32` (para integração com o Outlook)
  - `pandas` (para funcionalidades de log, se necessário)
  - `pyfiglet` (opcional, para geração do banner)

### Instalando as Dependências

Abra o terminal e execute:

```bash
pip install customtkinter PyPDF2 pikepdf pywin32 pandas pyfiglet
