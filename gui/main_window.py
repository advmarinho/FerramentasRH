import customtkinter as ctk
from tkinter import messagebox
from funcoes import main as proteger_automatico, proteger_documento_personalizado

class MainWindow(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()

    def create_widgets(self):
        # Título e descrição
        logo = ctk.CTkLabel(self, text="🔐 PDF Protect Tool", font=("Segoe UI", 28, "bold"))
        logo.pack(pady=20)

        desc = ctk.CTkLabel(self, text="Selecione a operação desejada:", font=("Segoe UI", 16))
        desc.pack(pady=10)

        # Botão para proteção automática
        auto_btn = ctk.CTkButton(self, text="Proteger PDF Automático", width=200, command=self.auto_protect)
        auto_btn.pack(pady=10)

        # Botão para proteção personalizada
        custom_btn = ctk.CTkButton(self, text="Proteger PDF Manualmente", width=200, command=self.custom_protect)
        custom_btn.pack(pady=10)

        # Botão para visualizar logs (se houver implementação)
        # logs_btn = ctk.CTkButton(self, text="Visualizar Logs", width=200, command=self.view_logs)
        # logs_btn.pack(pady=10)

        # Botão para sair
        exit_btn = ctk.CTkButton(self, text="Sair", fg_color="red", width=200, command=self.master.destroy)
        exit_btn.pack(pady=10)

    def auto_protect(self):
        # Chama a função que realiza o fluxo automático de proteção do PDF
        try:
            resultado = proteger_automatico()
            if resultado:
                messagebox.showinfo("Sucesso", "PDF protegido com sucesso!")
            else:
                messagebox.showerror("Erro", "Ocorreu um erro no processamento automático.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

    def custom_protect(self):
        # Chama a função que realiza a proteção personalizada (definindo senha)
        try:
            proteger_documento_personalizado()
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

    # Se você tiver uma função para visualizar logs, poderá adicioná-la aqui
    # def view_logs(self):
    #     pass
