import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from yt_dlp import YoutubeDL

# ---------------------- Função de download ----------------------

def progresso(d):
    if d['status'] == 'finished':
        app.log(f"✅ Finalizado: {os.path.basename(d['filename'])}")
    elif d['status'] == 'downloading':
        pct = d.get('_percent_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        app.log(f"⚙️ Baixando... {pct} (ETA {eta})")


def baixar_playlist(url: str, pasta_destino: str) -> None:
    if not url.strip():
        messagebox.showerror("Erro", "Informe a URL da playlist.")
        return
    os.makedirs(pasta_destino, exist_ok=True)
    opcoes = {
        'outtmpl': os.path.join(pasta_destino, '%(playlist_index)03d - %(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'merge_output_format': 'mp4',
        'ignoreerrors': True,
        'restrictfilenames': True,
        'progress_hooks': [progresso],
        'quiet': True,
        'newline': True,
    }
    try:
        with YoutubeDL(opcoes) as ydl:
            ydl.download([url])
    except Exception as e:
        messagebox.showerror("Erro", f"Falha no download: {e}")
    else:
        messagebox.showinfo("Concluído", "Download da playlist concluído!")

# ---------------------- Interface GUI ----------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Downloader de Playlist YouTube")
        self.geometry("600x300")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # URL da playlist
        self.label_url = ctk.CTkLabel(self, text="URL da Playlist:")
        self.label_url.pack(pady=(20,5))
        self.entry_url = ctk.CTkEntry(self, width=500)
        self.entry_url.pack(pady=(0,15))

        # Pasta de destino
        self.label_out = ctk.CTkLabel(self, text="Pasta de Destino:")
        self.label_out.pack(pady=(0,5))
        frame_out = ctk.CTkFrame(self)
        frame_out.pack(pady=(0,15))
        self.entry_out = ctk.CTkEntry(frame_out, width=400)
        self.entry_out.pack(side="left", padx=(0,5))
        self.btn_browse = ctk.CTkButton(frame_out, text="Selecionar", command=self.browse_folder)
        self.btn_browse.pack(side="left")

        # Botão de download
        self.btn_download = ctk.CTkButton(self, text="Baixar Playlist", command=self.start_download)
        self.btn_download.pack(pady=(0,20))

        # Área de log
        self.text_log = ctk.CTkTextbox(self, width=550, height=80, state="disabled")
        self.text_log.pack(padx=10)

    def browse_folder(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de saída")
        if pasta:
            self.entry_out.delete(0, ctk.END)
            self.entry_out.insert(0, pasta)

    def log(self, msg: str):
        self.text_log.configure(state="normal")
        self.text_log.insert(ctk.END, msg + "\n")
        self.text_log.see(ctk.END)
        self.text_log.configure(state="disabled")

    def start_download(self):
        url = self.entry_url.get()
        pasta = self.entry_out.get() or "videos"
        # Executa em thread para não travar a GUI
        t = threading.Thread(target=baixar_playlist, args=(url, pasta), daemon=True)
        t.start()

# Retém a referência para hooks
app = App()

if __name__ == '__main__':
    app.mainloop()
