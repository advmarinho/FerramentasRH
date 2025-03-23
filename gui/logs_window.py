import pandas as pd
import customtkinter as ctk
from tkinter import ttk

class LogsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Logs de Execuções")
        self.geometry("600x400")
        self.load_logs()

    def load_logs(self):
        try:
            logs = pd.read_csv('logs/logInforme.csv')
        except Exception as e:
            logs = pd.DataFrame({"Mensagem": ["Nenhum log encontrado."]})

        cols = logs.columns.tolist()
        tree = ttk.Treeview(self, columns=cols, show='headings')
        tree.pack(expand=True, fill='both')

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, anchor='center')

        for _, row in logs.iterrows():
            tree.insert("", "end", values=row.tolist())
