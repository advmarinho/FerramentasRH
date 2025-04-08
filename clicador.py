import pyautogui
import time
import customtkinter as ctk
from tkinter import messagebox
import threading
import os
from PIL import Image, ImageDraw

class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Clicador - By Anderson Marinho")
        self.geometry("500x400")
        ctk.set_appearance_mode("Dark")  # Pode ser "Light", "Dark" ou "System"
        ctk.set_default_color_theme("blue")
        
        # Define o ícone da aplicação
        icon_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "icone.ico")
        if not os.path.exists(icon_path):
            # Cria uma imagem de ícone com uma seta circular contínua
            icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon)
            draw.ellipse((8, 8, 56, 56), outline="blue", width=4)  # Círculo externo
            draw.polygon([(32, 8), (36, 16), (28, 16)], fill="blue")  # Cabeça da seta
            draw.arc((12, 12, 52, 52), start=0, end=270, fill="blue", width=4)  # Arco da seta
            icon.save(icon_path)
        try:
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Erro ao definir o ícone: {e}")
        
        # Permitir redimensionar a janela
        self.resizable(True, True)
        
        # Variáveis de controle
        self.posicao = None
        self.contador = 0
        self.executando = False
        self.pausado = False
        
        # Criação de um frame principal para organizar os widgets
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Campo de entrada para definir o intervalo
        self.intervalo_label = ctk.CTkLabel(self.main_frame, text="Intervalo entre cliques (segundos):")
        self.intervalo_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.intervalo_entry = ctk.CTkEntry(self.main_frame)
        self.intervalo_entry.insert(0, "60")  # Valor padrão
        self.intervalo_entry.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # Seção para selecionar a posição do clique
        self.posicao_info = ctk.CTkLabel(self.main_frame, text="Posição selecionada: Nenhuma")
        self.posicao_info.grid(row=1, column=0, columnspan=2, padx=10, pady=5)
        self.selecionar_btn = ctk.CTkButton(self.main_frame, text="Selecionar Posição", command=self.selecionar_posicao)
        self.selecionar_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        # Label para exibir a quantidade de cliques realizados
        self.contador_label = ctk.CTkLabel(self.main_frame, text="Cliques realizados: 0")
        self.contador_label.grid(row=3, column=0, columnspan=2, padx=10, pady=5)
        
        # Frame para os botões de controle: Pausar, Retomar e Parar
        self.btn_frame = ctk.CTkFrame(self.main_frame)
        self.btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Botões de controle (o clique é iniciado automaticamente após a seleção)
        self.pausar_btn = ctk.CTkButton(self.btn_frame, text="Pausar", command=self.pausar, state="disabled")
        self.pausar_btn.grid(row=0, column=0, padx=5)
        
        self.retornar_btn = ctk.CTkButton(self.btn_frame, text="Retomar", command=self.retomar, state="disabled")
        self.retornar_btn.grid(row=0, column=1, padx=5)
        
        self.parar_btn = ctk.CTkButton(self.btn_frame, text="Parar", command=self.parar, state="disabled")
        self.parar_btn.grid(row=0, column=2, padx=5)
        
    def selecionar_posicao(self):
        messagebox.showinfo("Instrução", 
                            "Mova o mouse para a posição desejada e aguarde 3 segundos para iniciar o clique automaticamente.")
        # Oculta a janela para facilitar a seleção da posição
        self.withdraw()
        time.sleep(3)
        self.posicao = pyautogui.position()
        self.deiconify()
        self.posicao_info.configure(text=f"Posição selecionada: {self.posicao}")
        # Após a seleção, inicia automaticamente o clique
        self.iniciar()
    
    def click_loop(self, intervalo):
        self.contador = 0
        while self.executando:
            if not self.pausado:
                pyautogui.click(self.posicao)
                self.contador += 1
                self.contador_label.configure(text=f"Cliques realizados: {self.contador}")
                print(f"Clique {self.contador} realizado na posição {self.posicao}.")
            # Aguarda o tempo de intervalo, verificando a cada segundo se o processo foi pausado ou parado
            for _ in range(intervalo):
                if not self.executando:
                    break
                time.sleep(1)
        messagebox.showinfo("Parado", f"Execução interrompida. Total de cliques realizados: {self.contador}")
        
    def iniciar(self):
        if self.posicao is None:
            messagebox.showerror("Erro", "Selecione uma posição antes de iniciar.")
            return
        try:
            intervalo = int(self.intervalo_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "O intervalo deve ser um número inteiro.")
            return
        
        self.executando = True
        self.pausado = False
        self.pausar_btn.configure(state="normal")
        self.parar_btn.configure(state="normal")
        self.retornar_btn.configure(state="disabled")
        # Inicia a thread responsável pelo clique automático
        thread = threading.Thread(target=self.click_loop, args=(intervalo,))
        thread.daemon = True
        thread.start()
        
    def pausar(self):
        if self.executando and not self.pausado:
            self.pausado = True
            self.pausar_btn.configure(state="disabled")
            self.retornar_btn.configure(state="normal")
            print("Execução pausada.")
            
    def retomar(self):
        if self.executando and self.pausado:
            self.pausado = False
            self.retornar_btn.configure(state="disabled")
            self.pausar_btn.configure(state="normal")
            print("Execução retomada.")
            
    def parar(self):
        if self.executando:
            self.executando = False
            self.pausar_btn.configure(state="disabled")
            self.retornar_btn.configure(state="disabled")
            self.parar_btn.configure(state="disabled")
            print("Execução parada.")

if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()
