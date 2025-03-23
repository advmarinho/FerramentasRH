import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
import customtkinter as ctk

class PDFProtectApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF Protect Tool by Anderson Marinho")
        self.geometry("600x400")
        ctk.set_appearance_mode("dark")  # ou "light"
        ctk.set_default_color_theme("blue")
        MainWindow(self).pack(expand=True, fill="both")

if __name__ == "__main__":
    app = PDFProtectApp()
    app.mainloop()
