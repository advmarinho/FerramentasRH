import win32com.client as win32
import os

def create_outlook_draft(pdf_path, cpf):
    outlook = win32.Dispatch('Outlook.Application')
    mail = outlook.CreateItem(0)
    mail.Subject = "📎 Informe de Rendimentos Protegido 2024/2025"
    mail.Body = f"""
    Prezado(a),

    Segue anexo o informe de rendimentos protegido.
    Senha: CPF somente números ({cpf})

    Atenciosamente,
    Anderson Marinho
    """
    mail.Attachments.Add(os.path.abspath(pdf_path))
    mail.Save()
    mail.Display()
