import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import pyautogui
import pyperclip
import time
import re
import json
from pathlib import Path

try:
    from pynput import keyboard as pk
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = True


class PreenchedorSSAF8Simples:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("CustomerThink | Preenchedor SSA F8 Simples")
        self.app.geometry("1500x920")
        self.app.minsize(1180, 760)

        self.COR_HEADER = "#121C4E"
        self.COR_AZUL_1 = "#163A70"
        self.COR_AZUL_2 = "#245A9A"
        self.COR_AZUL_3 = "#3E7CC3"
        self.COR_AZUL_4 = "#DCE6F2"
        self.COR_AZUL_5 = "#EEF4FA"
        self.COR_SUCESSO = "#2F7D32"
        self.COR_ALERTA = "#C62828"
        self.COR_NEUTRA = "#6B7280"
        self.COR_INFO = "#406A9A"
        self.COR_CARD = "#FFFFFF"
        self.COR_FUNDO = "#F4F7FB"
        self.COR_BORDA = "#D7E0EA"
        self.COR_TEXTO = "#1F2937"
        self.COR_TEXTO_SUAVE = "#5F6B7A"
        self.COR_AMBAR = "#A97C00"

        self.df = pd.DataFrame(columns=["CDC", "DADO", "TIPO", "STATUS", "OBS"])
        self.last_f8_time = 0.0
        self._debounce_secs = 0.30
        self._sending = False
        self.global_on = False
        self.hk_listener = None
        self._local_f8_bound = False

        self.criar_interface()
        self._bind_local_keys()
        self.app.protocol("WM_DELETE_WINDOW", self.fechar_app)

        self.log("Aplicação inicializada.")
        if HAS_PYNPUT:
            self.log("pynput disponível para hotkey global.")
        else:
            self.log("pynput não encontrado. F8 funcionará localmente na janela do app.")

    # =========================================================
    # BASE VISUAL CUSTOMERTHINK
    # =========================================================
    def criar_card(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=self.COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.COR_BORDA
        )

    def criar_botao(self, parent, texto, comando, cor, hover, width=140):
        return ctk.CTkButton(
            parent,
            text=texto,
            command=comando,
            fg_color=cor,
            hover_color=hover,
            text_color="white",
            width=width,
            height=40,
            corner_radius=10,
            font=("Segoe UI", 12, "bold")
        )

    def criar_entry(self, parent, width=None):
        kwargs = {
            "height": 40,
            "fg_color": "white",
            "border_color": "#AEBFD3",
            "text_color": self.COR_TEXTO,
            "font": ("Segoe UI", 12),
        }
        if width is not None:
            kwargs["width"] = width
        return ctk.CTkEntry(parent, **kwargs)

    def criar_combo(self, parent, values, command=None, width=None):
        kwargs = {
            "values": values,
            "command": command,
            "state": "readonly",
            "height": 40,
            "fg_color": "white",
            "border_color": "#AEBFD3",
            "button_color": "#DCE6F2",
            "button_hover_color": "#C8D8EA",
            "text_color": self.COR_TEXTO,
            "dropdown_fg_color": "white",
            "dropdown_text_color": self.COR_TEXTO,
            "font": ("Segoe UI", 12),
        }
        if width is not None:
            kwargs["width"] = width
        return ctk.CTkComboBox(parent, **kwargs)

    def criar_interface(self):
        self.app.configure(fg_color=self.COR_FUNDO)

        header = ctk.CTkFrame(self.app, fg_color=self.COR_HEADER, corner_radius=0, height=84)
        header.pack(fill="x")
        header.pack_propagate(False)

        esquerda = ctk.CTkFrame(header, fg_color="transparent")
        esquerda.pack(side="left", fill="both", expand=True, padx=20, pady=14)

        ctk.CTkLabel(
            esquerda,
            text="Preenchedor SSA | F8 Simples",
            font=("Segoe UI", 28, "bold"),
            text_color="white"
        ).pack(anchor="w")

        ctk.CTkLabel(
            esquerda,
            text="CustomerThinker | fluxo para 1 tela: o usuário posiciona o cursor no SSA e o F8 preenche a linha atual",
            font=("Segoe UI", 13),
            text_color="#D9E7F5"
        ).pack(anchor="w", pady=(4, 0))

        direita = ctk.CTkFrame(header, fg_color="transparent")
        direita.pack(side="right", padx=20, pady=14)

        self.lbl_hotkey_mode = ctk.CTkLabel(
            direita,
            text="Hotkey: Local",
            font=("Segoe UI", 12, "bold"),
            text_color="white"
        )
        self.lbl_hotkey_mode.pack(anchor="e")

        self.lbl_modo_execucao = ctk.CTkLabel(
            direita,
            text="Modo: F8 preenche e avança",
            font=("Segoe UI", 12),
            text_color="#D9E7F5"
        )
        self.lbl_modo_execucao.pack(anchor="e", pady=(4, 0))

        body = ctk.CTkFrame(self.app, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self.criar_bloco_entrada(body)
        self.criar_bloco_config(body)
        self.criar_bloco_preview(body)
        self.criar_bloco_execucao(body)

        self.atualizar_resumo()
        self.atualizar_linha_atual()

    # =========================================================
    # BLOCO ENTRADA
    # =========================================================
    def criar_bloco_entrada(self, parent):
        frame = self.criar_card(parent)
        frame.grid(row=0, column=0, padx=(0, 6), pady=(0, 8), sticky="nsew")

        ctk.CTkLabel(
            frame,
            text="1. Entrada rápida",
            font=("Segoe UI", 18, "bold"),
            text_color=self.COR_TEXTO
        ).pack(anchor="w", padx=16, pady=(14, 8))

        botoes = ctk.CTkFrame(frame, fg_color="transparent")
        botoes.pack(fill="x", padx=16, pady=(0, 8))

        self.criar_botao(botoes, "Ler dados colados", self.ler_dados_colados, self.COR_HEADER, "#1B2C63", 165).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes, "Modelo valor", self.inserir_modelo_valor, self.COR_AZUL_2, "#1E4F8A", 130).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes, "Modelo percentual", self.inserir_modelo_percentual, self.COR_AZUL_3, "#2D68A8", 160).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes, "Limpar texto", self.limpar_texto, self.COR_NEUTRA, "#5D6671", 120).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes, "Limpar base", self.limpar_base, "#A83E4A", "#933540", 120).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes, "Validar base", self.validar_base_visual, self.COR_INFO, "#355D87", 125).pack(side="left")

        ctk.CTkLabel(
            frame,
            text="Aceita TAB, ponto e vírgula ou múltiplos espaços. Pode colar com ou sem cabeçalho.",
            font=("Segoe UI", 12),
            text_color=self.COR_TEXTO_SUAVE
        ).pack(anchor="w", padx=16, pady=(0, 6))

        texto_frame = ctk.CTkFrame(frame, fg_color="transparent")
        texto_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.txt_entrada = ctk.CTkTextbox(
            texto_frame,
            height=260,
            font=("Consolas", 12),
            fg_color="#FBFCFE",
            text_color=self.COR_TEXTO,
            border_width=1,
            border_color=self.COR_BORDA
        )
        self.txt_entrada.pack(side="left", fill="both", expand=True)

        self.scroll_txt = ctk.CTkScrollbar(texto_frame, command=self.txt_entrada.yview)
        self.scroll_txt.pack(side="right", fill="y")
        self.txt_entrada.configure(yscrollcommand=self.scroll_txt.set)

    # =========================================================
    # BLOCO CONFIG
    # =========================================================
    def criar_bloco_config(self, parent):
        frame = self.criar_card(parent)
        frame.grid(row=0, column=1, padx=(6, 0), pady=(0, 8), sticky="nsew")

        ctk.CTkLabel(
            frame,
            text="2. Configuração operacional",
            font=("Segoe UI", 18, "bold"),
            text_color=self.COR_TEXTO
        ).pack(anchor="w", padx=16, pady=(14, 8))

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 10))
        for i in range(5):
            grid.grid_columnconfigure(i, weight=1)

        labels_1 = ["Usar campo", "Navegação", "Delay entre ações", "Delay inicial", "Qtd. a executar"]
        for i, txt in enumerate(labels_1):
            ctk.CTkLabel(grid, text=txt, font=("Segoe UI", 12, "bold"), text_color=self.COR_TEXTO).grid(row=0, column=i, sticky="w", padx=6, pady=(0, 4))

        self.cmb_usar = self.criar_combo(grid, ["VALOR", "PERCENTUAL"])
        self.cmb_usar.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 8))
        self.cmb_usar.set("VALOR")

        self.cmb_modo = self.criar_combo(grid, ["TAB"])
        self.cmb_modo.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 8))
        self.cmb_modo.set("TAB")

        self.entry_delay = self.criar_entry(grid)
        self.entry_delay.grid(row=1, column=2, sticky="ew", padx=6, pady=(0, 8))
        self.entry_delay.insert(0, "0,15")

        self.entry_delay_inicial = self.criar_entry(grid)
        self.entry_delay_inicial.grid(row=1, column=3, sticky="ew", padx=6, pady=(0, 8))
        self.entry_delay_inicial.insert(0, "3")

        self.entry_qtd = self.criar_entry(grid)
        self.entry_qtd.grid(row=1, column=4, sticky="ew", padx=6, pady=(0, 8))
        self.entry_qtd.insert(0, "TODOS")

        labels_2 = ["TAB após CDC", "TAB após dado", "Limpar campo atual", "Ação final", "Linha inicial"]
        for i, txt in enumerate(labels_2):
            ctk.CTkLabel(grid, text=txt, font=("Segoe UI", 12, "bold"), text_color=self.COR_TEXTO).grid(row=2, column=i, sticky="w", padx=6, pady=(8, 4))

        self.entry_tabs_cdc = self.criar_entry(grid)
        self.entry_tabs_cdc.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 8))
        self.entry_tabs_cdc.insert(0, "3")

        self.entry_tabs_final = self.criar_entry(grid)
        self.entry_tabs_final.grid(row=3, column=1, sticky="ew", padx=6, pady=(0, 8))
        self.entry_tabs_final.insert(0, "0")

        self.cmb_limpar = self.criar_combo(grid, ["SIM", "NAO"])
        self.cmb_limpar.grid(row=3, column=2, sticky="ew", padx=6, pady=(0, 8))
        self.cmb_limpar.set("SIM")

        self.cmb_acao_final = self.criar_combo(grid, ["ENTER", "TAB", "NENHUMA"])
        self.cmb_acao_final.grid(row=3, column=3, sticky="ew", padx=6, pady=(0, 8))
        self.cmb_acao_final.set("ENTER")

        self.entry_linha_inicial = self.criar_entry(grid)
        self.entry_linha_inicial.grid(row=3, column=4, sticky="ew", padx=6, pady=(0, 8))
        self.entry_linha_inicial.insert(0, "1")

        linha2 = ctk.CTkFrame(frame, fg_color="transparent")
        linha2.pack(fill="x", padx=16, pady=(0, 10))

        self.criar_botao(linha2, "Salvar layout", self.salvar_layout_json, self.COR_AZUL_2, "#1E4F8A", 130).pack(side="left", padx=(0, 8))
        self.criar_botao(linha2, "Carregar layout", self.carregar_layout_json, self.COR_AZUL_3, "#2D68A8", 145).pack(side="left", padx=(0, 8))
        self.criar_botao(linha2, "Exportar log", self.exportar_log_txt, self.COR_INFO, "#355D87", 130).pack(side="left", padx=(0, 8))
        self.criar_botao(linha2, "Ignorar selecionada", self.marcar_linha_ignorada, self.COR_NEUTRA, "#59616D", 165).pack(side="left")

        box = ctk.CTkFrame(frame, fg_color=self.COR_AZUL_5, corner_radius=10, border_width=1, border_color=self.COR_BORDA)
        box.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(box, text="Lógica simplificada para 1 tela", font=("Segoe UI", 14, "bold"), text_color=self.COR_TEXTO).pack(anchor="w", padx=12, pady=(12, 6))
        ctk.CTkLabel(
            box,
            text=(
                "1. O usuário deixa o cursor no primeiro campo do SSA.\n"
                "2. Pressiona F8.\n"
                "3. O app escreve CDC, navega por TAB e escreve o valor ou percentual.\n"
                "4. Depois marca a linha como OK e avança automaticamente.\n"
                "6. Não depende de capturar posição na tela."
            ),
            justify="left",
            font=("Segoe UI", 12),
            text_color=self.COR_TEXTO_SUAVE
        ).pack(anchor="w", padx=12, pady=(0, 12))

    # =========================================================
    # BLOCO PREVIEW
    # =========================================================
    def criar_bloco_preview(self, parent):
        frame = self.criar_card(parent)
        frame.grid(row=1, column=0, padx=(0, 6), pady=(0, 0), sticky="nsew")

        ctk.CTkLabel(frame, text="3. Preview da base", font=("Segoe UI", 18, "bold"), text_color=self.COR_TEXTO).pack(anchor="w", padx=16, pady=(14, 8))

        resumo = ctk.CTkFrame(frame, fg_color="transparent")
        resumo.pack(fill="x", padx=16, pady=(0, 8))

        self.lbl_resumo = ctk.CTkLabel(
            resumo,
            text="Total: 0 | Pendentes: 0 | OK: 0 | Erro: 0 | Ignorados: 0",
            font=("Segoe UI", 12, "bold"),
            text_color=self.COR_TEXTO_SUAVE
        )
        self.lbl_resumo.pack(anchor="w")

        tree_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.tree = ttk.Treeview(tree_frame, columns=("LINHA", "CDC", "DADO", "TIPO", "STATUS", "OBS"), show="headings")

        for col, txt in [("LINHA", "Linha"), ("CDC", "CDC"), ("DADO", "Dado"), ("TIPO", "Tipo"), ("STATUS", "Status"), ("OBS", "Observação")]:
            self.tree.heading(col, text=txt)

        self.tree.column("LINHA", width=70, anchor="center")
        self.tree.column("CDC", width=120, anchor="center")
        self.tree.column("DADO", width=140, anchor="e")
        self.tree.column("TIPO", width=110, anchor="center")
        self.tree.column("STATUS", width=120, anchor="center")
        self.tree.column("OBS", width=330, anchor="w")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black", rowheight=30, fieldbackground="white", font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background=self.COR_AZUL_4, foreground="black", font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", "#D9E7F5")], foreground=[("selected", "black")])

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    # =========================================================
    # BLOCO EXECUÇÃO
    # =========================================================
    def criar_bloco_execucao(self, parent):
        frame = self.criar_card(parent)
        frame.grid(row=1, column=1, padx=(6, 0), pady=(0, 0), sticky="nsew")

        ctk.CTkLabel(frame, text="4. Execução por hotkey", font=("Segoe UI", 18, "bold"), text_color=self.COR_TEXTO).pack(anchor="w", padx=16, pady=(14, 8))

        txt = (
            "Fluxo operacional:\n"
            "1. Cole os dados.\n"
            "2. Leia e valide a base.\n"
            "3. Ajuste os TABs conforme o SSA.\n"
            "4. Clique no primeiro campo do SSA.\n"
            "5. Pressione F8 para preencher a linha atual.\n"
            "6. Use F6 para pular e F9 para voltar."
        )
        ctk.CTkLabel(frame, text=txt, justify="left", font=("Segoe UI", 12), text_color=self.COR_TEXTO_SUAVE).pack(anchor="w", padx=16, pady=(0, 10))

        botoes1 = ctk.CTkFrame(frame, fg_color="transparent")
        botoes1.pack(fill="x", padx=16, pady=(0, 8))

        self.criar_botao(botoes1, "Iniciar da linha", self.iniciar_da_linha_configurada, self.COR_AZUL_2, "#1E4F8A", 135).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes1, "Executar 1 linha", self.executar_proxima_linha_manual, self.COR_AZUL_3, "#2D68A8", 135).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes1, "Pular linha", self.pular_linha_manual, self.COR_AMBAR, "#916B00", 120).pack(side="left", padx=(0, 8))
        self.criar_botao(botoes1, "Voltar linha", self.voltar_linha, self.COR_NEUTRA, "#5D6671", 125).pack(side="left", padx=(0, 8))

        botoes2 = ctk.CTkFrame(frame, fg_color="transparent")
        botoes2.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_hotkey = self.criar_botao(
            botoes2,
            "Ativar hotkey global",
            self.toggle_global,
            self.COR_HEADER,
            "#1B2C63",
            180
        )
        self.btn_hotkey.pack(side="left", padx=(0, 8))

        self.criar_botao(botoes2, "Marcar erro", self.marcar_erro_manual, self.COR_ALERTA, "#AE2323", 120).pack(side="left", padx=(0, 8))

        self.lbl_status = ctk.CTkLabel(frame, text="Status: aguardando dados.", font=("Segoe UI", 12, "bold"), text_color=self.COR_HEADER)
        self.lbl_status.pack(anchor="w", padx=16, pady=(0, 8))

        self.lbl_linha = ctk.CTkLabel(frame, text="Linha atual: 0", font=("Segoe UI", 12), text_color=self.COR_TEXTO_SUAVE)
        self.lbl_linha.pack(anchor="w", padx=16, pady=(0, 4))

        self.lbl_progresso = ctk.CTkLabel(frame, text="Progresso: 0/0", font=("Segoe UI", 12, "bold"), text_color=self.COR_INFO)
        self.lbl_progresso.pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(frame, text="Log operacional", font=("Segoe UI", 13, "bold"), text_color=self.COR_TEXTO).pack(anchor="w", padx=16, pady=(0, 6))

        log_frame = ctk.CTkFrame(frame, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.txt_log = ctk.CTkTextbox(
            log_frame,
            height=440,
            font=("Consolas", 11),
            fg_color="#FBFCFE",
            text_color=self.COR_TEXTO,
            border_width=1,
            border_color=self.COR_BORDA
        )
        self.txt_log.pack(side="left", fill="both", expand=True)

        self.scroll_log = ctk.CTkScrollbar(log_frame, command=self.txt_log.yview)
        self.scroll_log.pack(side="right", fill="y")
        self.txt_log.configure(yscrollcommand=self.scroll_log.set)

    # =========================================================
    # LOG E STATUS
    # =========================================================
    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        linha = f"[{timestamp}] {msg}\n"
        if hasattr(self, "txt_log"):
            self.txt_log.insert("end", linha)
            self.txt_log.see("end")
            self.app.update_idletasks()
        else:
            print(linha)

    def set_status(self, msg, cor=None):
        self.lbl_status.configure(text=f"Status: {msg}", text_color=cor or self.COR_HEADER)
        self.app.update_idletasks()

    # =========================================================
    # HOTKEYS
    # =========================================================
    def _bind_local_keys(self):
        self.app.bind("<F8>", self._on_f8_local)
        self.app.bind("<F6>", lambda e: self.on_pular_hotkey())
        self.app.bind("<F9>", lambda e: self.on_voltar_hotkey())
        self._local_f8_bound = True

    def _unbind_local_f8(self):
        if self._local_f8_bound:
            try:
                self.app.unbind("<F8>")
            except Exception:
                pass
            self._local_f8_bound = False

    def _has_modifiers(self, event) -> bool:
        st = getattr(event, "state", 0)
        return bool(st & 0x0001 or st & 0x0004 or st & 0x0008)

    def _on_f8_local(self, event):
        if self._has_modifiers(event):
            return
        self.executar_proxima_linha_manual()

    def toggle_global(self):
        if not HAS_PYNPUT:
            messagebox.showerror("Hotkey global", "Instale o pacote 'pynput' para usar F8 global.")
            return

        if not self.global_on:
            try:
                self._unbind_local_f8()
                mapping = {
                    "<f8>": lambda: self.app.after(0, self.executar_proxima_linha_manual),
                    "<f6>": lambda: self.app.after(0, self.on_pular_hotkey),
                    "<f9>": lambda: self.app.after(0, self.on_voltar_hotkey),
                }
                self.hk_listener = pk.GlobalHotKeys(mapping)
                self.hk_listener.start()
                self.global_on = True
                self.btn_hotkey.configure(text="Desativar hotkey global", fg_color="#6c757d", hover_color="#5c636a")
                self.lbl_hotkey_mode.configure(text="Hotkey: Global")
                self.log("Hotkey global ativada: F8 preenche, F6 pula, F9 volta.")
                self.set_status("hotkey global ativada", self.COR_SUCESSO)
            except Exception as e:
                messagebox.showerror("Hotkey global", f"Falha ao ativar hotkey global.\n\nDetalhe: {e}")
        else:
            try:
                if self.hk_listener:
                    self.hk_listener.stop()
            except Exception:
                pass
            self.hk_listener = None
            self.global_on = False
            self.app.bind("<F8>", self._on_f8_local)
            self._local_f8_bound = True
            self.btn_hotkey.configure(text="Ativar hotkey global", fg_color=self.COR_HEADER, hover_color="#1B2C63")
            self.lbl_hotkey_mode.configure(text="Hotkey: Local")
            self.log("Hotkey global desativada. F8 local reativado.")
            self.set_status("hotkey global desativada", self.COR_INFO)

    # =========================================================
    # ENTRADA / PARSER
    # =========================================================
    def inserir_modelo_valor(self):
        self.txt_entrada.delete("1.0", "end")
        self.txt_entrada.insert("1.0", "CDC\tVALOR\n300000\t843,60\n301000\t3532,00\n303000\t2000,00")
        self.cmb_usar.set("VALOR")

    def inserir_modelo_percentual(self):
        self.txt_entrada.delete("1.0", "end")
        self.txt_entrada.insert("1.0", "CDC\tPERCENTUAL\n300000\t25\n301000\t35\n303000\t40")
        self.cmb_usar.set("PERCENTUAL")

    def limpar_texto(self):
        self.txt_entrada.delete("1.0", "end")

    def limpar_base(self):
        self.df = pd.DataFrame(columns=["CDC", "DADO", "TIPO", "STATUS", "OBS"])
        self.renderizar_base()
        self.atualizar_resumo()
        self.atualizar_linha_atual()
        self.log("Base limpa.")
        self.set_status("base limpa", self.COR_INFO)

    def detectar_cabecalho(self, primeira_linha):
        p1 = str(primeira_linha[0]).strip().lower()
        p2 = str(primeira_linha[1]).strip().lower()
        palavras = ["cdc", "valor", "percentual", "percent", "%", "dado"]
        return any(p in p1 for p in palavras) or any(p in p2 for p in palavras)

    def separar_linha(self, linha):
        linha = linha.strip()
        if not linha:
            return None

        if "\t" in linha:
            partes = [p.strip() for p in linha.split("\t") if p.strip() != ""]
            if len(partes) >= 2:
                return partes[0], partes[1]

        if ";" in linha:
            partes = [p.strip() for p in linha.split(";") if p.strip() != ""]
            if len(partes) >= 2:
                return partes[0], partes[1]

        partes = re.split(r"\s{2,}", linha)
        partes = [p.strip() for p in partes if p.strip()]
        if len(partes) >= 2:
            return partes[0], partes[1]

        return None

    def ler_dados_colados(self):
        texto = self.txt_entrada.get("1.0", "end").strip()
        if not texto:
            messagebox.showwarning("Atenção", "Cole os dados antes de ler.")
            return

        linhas = [l for l in texto.splitlines() if l.strip()]
        if not linhas:
            messagebox.showwarning("Atenção", "Não há linhas válidas para leitura.")
            return

        registros = []
        primeira_parse = self.separar_linha(linhas[0])
        inicio = 0
        if primeira_parse and self.detectar_cabecalho(primeira_parse):
            inicio = 1

        tipo = self.cmb_usar.get()
        for i in range(inicio, len(linhas)):
            resultado = self.separar_linha(linhas[i])
            if not resultado:
                self.log(f"Linha ignorada por formato inválido: {linhas[i]}")
                continue

            cdc, dado = resultado
            registros.append({
                "CDC": str(cdc).strip(),
                "DADO": str(dado).strip(),
                "TIPO": tipo,
                "STATUS": "PENDENTE",
                "OBS": ""
            })

        if not registros:
            messagebox.showwarning("Atenção", "Nenhum dado válido foi identificado.")
            return

        self.df = pd.DataFrame(registros)
        self.pre_validar_dataframe()
        self.iniciar_da_linha_configurada(silencioso=True)
        self.renderizar_base()
        self.atualizar_resumo()
        self.atualizar_linha_atual()
        self.log(f"{len(self.df)} linha(s) carregada(s) por cola.")
        self.set_status(f"{len(self.df)} linha(s) carregada(s)", self.COR_SUCESSO)

    # =========================================================
    # PRÉ-VALIDAÇÃO
    # =========================================================
    def pre_validar_dataframe(self):
        if self.df.empty:
            return

        for idx, row in self.df.iterrows():
            cdc = str(row["CDC"]).strip()
            dado = str(row["DADO"]).strip()

            if not cdc:
                self.df.at[idx, "STATUS"] = "IGNORADO"
                self.df.at[idx, "OBS"] = "CDC vazio"
                continue

            if not dado:
                self.df.at[idx, "STATUS"] = "IGNORADO"
                self.df.at[idx, "OBS"] = "Dado vazio"
                continue

            if self.df.at[idx, "STATUS"] not in ["OK", "IGNORADO"]:
                self.df.at[idx, "STATUS"] = "PENDENTE"
                self.df.at[idx, "OBS"] = ""

    def validar_base_visual(self):
        if self.df.empty:
            messagebox.showwarning("Validação", "Não há base carregada.")
            return
        self.pre_validar_dataframe()
        self.renderizar_base()
        self.atualizar_resumo()
        self.atualizar_linha_atual()
        self.log("Base validada visualmente.")
        self.set_status("base validada", self.COR_INFO)

    # =========================================================
    # RESUMO E GRID
    # =========================================================
    def renderizar_base(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.df.empty:
            return

        for idx, row in self.df.iterrows():
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(idx + 1, row["CDC"], row["DADO"], row["TIPO"], row["STATUS"], row["OBS"])
            )

    def atualizar_status_linha(self, idx, status, obs=None):
        if idx < 0 or idx >= len(self.df):
            return

        self.df.at[idx, "STATUS"] = status
        if obs is not None:
            self.df.at[idx, "OBS"] = obs

        self.tree.item(
            str(idx),
            values=(
                idx + 1,
                self.df.at[idx, "CDC"],
                self.df.at[idx, "DADO"],
                self.df.at[idx, "TIPO"],
                self.df.at[idx, "STATUS"],
                self.df.at[idx, "OBS"]
            )
        )
        self.atualizar_resumo()

    def atualizar_resumo(self):
        if self.df.empty:
            self.lbl_resumo.configure(text="Total: 0 | Pendentes: 0 | OK: 0 | Erro: 0 | Ignorados: 0")
            self.lbl_progresso.configure(text="Progresso: 0/0")
            return

        total = len(self.df)
        pend = int((self.df["STATUS"] == "PENDENTE").sum())
        ok = int((self.df["STATUS"] == "OK").sum())
        erro = int((self.df["STATUS"] == "ERRO").sum())
        ign = int((self.df["STATUS"] == "IGNORADO").sum())

        self.lbl_resumo.configure(text=f"Total: {total} | Pendentes: {pend} | OK: {ok} | Erro: {erro} | Ignorados: {ign}")
        self.lbl_progresso.configure(text=f"Progresso: {ok + ign}/{total}")

    def obter_proxima_linha_pendente(self):
        if self.df.empty:
            return None
        pendentes = self.df.index[self.df["STATUS"].isin(["PENDENTE", "ERRO"])]
        if len(pendentes) == 0:
            return None
        return int(pendentes[0])

    def atualizar_linha_atual(self):
        idx = self.obter_proxima_linha_pendente()
        if idx is None:
            self.lbl_linha.configure(text="Linha atual: concluído")
        else:
            self.lbl_linha.configure(text=f"Linha atual: {idx + 1} de {len(self.df)}")
            try:
                self.tree.selection_set(str(idx))
                self.tree.focus(str(idx))
                self.tree.see(str(idx))
            except Exception:
                pass

    # =========================================================
    # PARÂMETROS
    # =========================================================
    def obter_delay(self):
        try:
            return float(str(self.entry_delay.get()).replace(",", "."))
        except Exception:
            return 0.10

    def obter_delay_inicial(self):
        try:
            return int(float(str(self.entry_delay_inicial.get()).replace(",", ".")))
        except Exception:
            return 2

    def obter_qtd(self):
        txt = str(self.entry_qtd.get()).strip().upper()
        if txt == "" or txt == "TODOS":
            return len(self.df)
        try:
            return max(1, min(int(txt), len(self.df)))
        except Exception:
            return len(self.df)

    def obter_tabs_cdc(self):
        try:
            return max(0, int(float(str(self.entry_tabs_cdc.get()).replace(",", "."))))
        except Exception:
            return 1

    def obter_tabs_final(self):
        try:
            return max(0, int(float(str(self.entry_tabs_final.get()).replace(",", "."))))
        except Exception:
            return 0

    def obter_linha_inicial(self):
        try:
            linha = int(float(str(self.entry_linha_inicial.get()).replace(",", ".")))
            if linha < 1:
                linha = 1
            if self.df.empty:
                return 1
            return min(linha, len(self.df))
        except Exception:
            return 1

    # =========================================================
    # EXECUÇÃO
    # =========================================================
    def validar_execucao(self):
        if self.df.empty:
            messagebox.showwarning("Validação", "Leia os dados antes de executar.")
            return False
        return True

    def colar_texto(self, texto, limpar=False):
        pyperclip.copy(str(texto))
        if limpar:
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.08)
        pyautogui.hotkey("ctrl", "v")

    def digitar_texto(self, texto, intervalo=0.02, limpar=False):
        if limpar:
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.08)
        pyautogui.write(str(texto), interval=intervalo)

    def limpar_campo_atual(self, delay=0.08):
        pyautogui.hotkey("ctrl", "a")
        time.sleep(delay)
        pyautogui.press("backspace")
        time.sleep(delay)

    def preparar_dado_para_digitacao(self, dado, usar):
        valor = str(dado).strip()
        if usar == "VALOR":
            valor = valor.replace(" ", "")
        elif usar == "PERCENTUAL":
            valor = valor.replace("%", "").strip()
        return valor

    def escrever_cdc(self, cdc):
        self.colar_texto(cdc, limpar=False)

    def escrever_dado_no_campo(self, dado, usar, delay):
        valor = self.preparar_dado_para_digitacao(dado, usar)
        if self.cmb_limpar.get() == "SIM":
            self.limpar_campo_atual(delay=max(0.05, delay))
            self.digitar_texto(valor, intervalo=max(0.01, delay / 5), limpar=False)
        else:
            self.digitar_texto(valor, intervalo=max(0.01, delay / 5), limpar=False)
        return valor

    def executar_tabs(self, quantidade, delay):
        for _ in range(quantidade):
            pyautogui.press("tab")
            time.sleep(delay)

    def executar_acao_final(self, delay):
        acao = self.cmb_acao_final.get()
        if acao == "ENTER":
            pyautogui.press("enter")
            time.sleep(delay)
        elif acao == "TAB":
            pyautogui.press("tab")
            time.sleep(delay)

    def iniciar_da_linha_configurada(self, silencioso=False):
        if self.df.empty:
            if not silencioso:
                messagebox.showwarning("Início", "Carregue a base primeiro.")
            return

        linha = self.obter_linha_inicial() - 1
        for idx in range(len(self.df)):
            if idx < linha and self.df.at[idx, "STATUS"] in ["PENDENTE", "ERRO"]:
                self.df.at[idx, "STATUS"] = "IGNORADO"
                self.df.at[idx, "OBS"] = "Ignorado por linha inicial"

        for idx in range(linha, len(self.df)):
            if self.df.at[idx, "STATUS"] not in ["OK", "IGNORADO"]:
                self.df.at[idx, "STATUS"] = "PENDENTE"
                if self.df.at[idx, "OBS"] == "Ignorado por linha inicial":
                    self.df.at[idx, "OBS"] = ""

        self.renderizar_base()
        self.atualizar_resumo()
        self.atualizar_linha_atual()
        self.log(f"Execução posicionada a partir da linha {linha + 1}.")
        self.set_status(f"linha inicial ajustada para {linha + 1}", self.COR_INFO)

    def executar_linha(self, idx):
        if idx is None or idx >= len(self.df):
            return False

        if self._sending:
            return False

        agora = time.time()
        if agora - self.last_f8_time < self._debounce_secs:
            return False
        self.last_f8_time = agora
        self._sending = True

        try:
            cdc = str(self.df.at[idx, "CDC"]).strip()
            dado = str(self.df.at[idx, "DADO"]).strip()
            usar = self.cmb_usar.get()
            delay = self.obter_delay()
            tabs_cdc = self.obter_tabs_cdc()
            tabs_final = self.obter_tabs_final()

            if not cdc:
                self.atualizar_status_linha(idx, "IGNORADO", "CDC vazio")
                self.log(f"Linha {idx + 1}: CDC vazio, ignorada.")
                self.atualizar_linha_atual()
                return True

            if not dado:
                self.atualizar_status_linha(idx, "IGNORADO", "Dado vazio")
                self.log(f"Linha {idx + 1}: dado vazio, ignorada.")
                self.atualizar_linha_atual()
                return True

            delay_inicial = self.obter_delay_inicial()

            self.atualizar_status_linha(idx, "PROCESSANDO", "")
            self.set_status(f"processando linha {idx + 1}", self.COR_INFO)
            self.log(f"Linha {idx + 1}: CDC={cdc} | {usar}={dado} | tabs_cdc={tabs_cdc} | tabs_final={tabs_final} | limpar_dado={self.cmb_limpar.get()}")

            if delay_inicial > 0:
                self.log(f"Linha {idx + 1}: aguardando delay inicial de {delay_inicial}s.")
                time.sleep(delay_inicial)

            self.escrever_cdc(cdc)
            time.sleep(delay)

            if tabs_cdc > 0:
                self.executar_tabs(tabs_cdc, delay)

            dado_digitado = self.escrever_dado_no_campo(dado, usar, delay)
            self.log(f"Linha {idx + 1}: dado enviado ao campo após Ctrl+A/limpeza -> {dado_digitado}")
            time.sleep(delay)

            if tabs_final > 0:
                self.executar_tabs(tabs_final, delay)

            self.executar_acao_final(delay)

            self.atualizar_status_linha(idx, "OK", "Preenchido com F8")
            self.log(f"Linha {idx + 1}: preenchida com sucesso.")
            self.set_status(f"linha {idx + 1} preenchida", self.COR_SUCESSO)
            self.atualizar_linha_atual()
            return True

        except Exception as e:
            self.atualizar_status_linha(idx, "ERRO", str(e))
            self.log(f"Linha {idx + 1}: erro ao preencher - {e}")
            self.set_status(f"erro na linha {idx + 1}", self.COR_ALERTA)
            self.atualizar_linha_atual()
            return False
        finally:
            time.sleep(0.02)
            self._sending = False

    def executar_proxima_linha_manual(self):
        if not self.validar_execucao():
            return

        idx = self.obter_proxima_linha_pendente()
        if idx is None:
            self.set_status("não há linhas pendentes", self.COR_INFO)
            return

        self.executar_linha(idx)

    def pular_linha_manual(self):
        idx = self.obter_proxima_linha_pendente()
        if idx is None:
            self.set_status("não há linhas pendentes", self.COR_INFO)
            return
        self.atualizar_status_linha(idx, "IGNORADO", "Pulado manualmente")
        self.log(f"Linha {idx + 1} pulada manualmente.")
        self.set_status(f"linha {idx + 1} pulada", self.COR_AMBAR)
        self.atualizar_linha_atual()

    def marcar_erro_manual(self):
        idx = self.obter_proxima_linha_pendente()
        if idx is None:
            self.set_status("não há linhas pendentes", self.COR_INFO)
            return
        self.atualizar_status_linha(idx, "ERRO", "Marcado manualmente")
        self.log(f"Linha {idx + 1} marcada como erro manualmente.")
        self.set_status(f"linha {idx + 1} marcada com erro", self.COR_ALERTA)
        self.atualizar_linha_atual()

    def on_pular_hotkey(self):
        self.pular_linha_manual()

    def on_voltar_hotkey(self):
        self.voltar_linha()

    def voltar_linha(self):
        if self.df.empty:
            return

        linhas_ok = self.df.index[self.df["STATUS"].isin(["OK", "IGNORADO", "ERRO"])] .tolist()
        if not linhas_ok:
            self.set_status("não há linha concluída para retornar", self.COR_INFO)
            return

        idx = linhas_ok[-1]
        self.atualizar_status_linha(idx, "PENDENTE", "Retornada manualmente")
        self.log(f"Linha {idx + 1} retornada para PENDENTE.")
        self.set_status(f"linha {idx + 1} voltou para pendente", self.COR_INFO)
        self.atualizar_linha_atual()

    # =========================================================
    # UTILITÁRIOS
    # =========================================================
    def marcar_linha_ignorada(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Ignorar", "Selecione uma linha na grade.")
            return

        idx = int(selecionado[0])
        self.atualizar_status_linha(idx, "IGNORADO", "Ignorada manualmente")
        self.log(f"Linha {idx + 1} marcada como ignorada manualmente.")
        self.set_status(f"linha {idx + 1} ignorada", self.COR_INFO)
        self.atualizar_linha_atual()

    def exportar_log_txt(self):
        try:
            conteudo = self.txt_log.get("1.0", "end").strip()
            if not conteudo:
                messagebox.showwarning("Exportar", "O log está vazio.")
                return

            caminho = filedialog.asksaveasfilename(
                title="Salvar log",
                defaultextension=".txt",
                filetypes=[("Arquivo texto", "*.txt")],
                initialfile="log_preenchedor_ssa_f8.txt"
            )
            if not caminho:
                return

            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)

            self.log(f"Log exportado para: {caminho}")
            self.set_status("log exportado", self.COR_SUCESSO)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível exportar o log.\n\nDetalhe: {e}")

    def salvar_layout_json(self):
        try:
            dados = {
                "usar_campo": self.cmb_usar.get(),
                "modo": self.cmb_modo.get(),
                "delay": self.entry_delay.get(),
                "delay_inicial": self.entry_delay_inicial.get(),
                "quantidade": self.entry_qtd.get(),
                "tabs_cdc": self.entry_tabs_cdc.get(),
                "tabs_final": self.entry_tabs_final.get(),
                "limpar_campo": self.cmb_limpar.get(),
                "acao_final": self.cmb_acao_final.get(),
                "linha_inicial": self.entry_linha_inicial.get(),
            }

            caminho = filedialog.asksaveasfilename(
                title="Salvar layout",
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
                initialfile="layout_preenchedor_ssa_f8.json"
            )
            if not caminho:
                return

            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=4)

            self.log(f"Layout salvo em: {caminho}")
            self.set_status("layout salvo", self.COR_SUCESSO)

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o layout.\n\nDetalhe: {e}")

    def carregar_layout_json(self):
        try:
            caminho = filedialog.askopenfilename(title="Carregar layout", filetypes=[("JSON", "*.json")])
            if not caminho:
                return

            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)

            self.cmb_usar.set(dados.get("usar_campo", "VALOR"))
            self.cmb_modo.set(dados.get("modo", "TAB"))

            self.entry_delay.delete(0, "end")
            self.entry_delay.insert(0, dados.get("delay", "0,15"))

            self.entry_delay_inicial.delete(0, "end")
            self.entry_delay_inicial.insert(0, dados.get("delay_inicial", "3"))

            self.entry_qtd.delete(0, "end")
            self.entry_qtd.insert(0, dados.get("quantidade", "TODOS"))

            self.entry_tabs_cdc.delete(0, "end")
            self.entry_tabs_cdc.insert(0, dados.get("tabs_cdc", "3"))

            self.entry_tabs_final.delete(0, "end")
            self.entry_tabs_final.insert(0, dados.get("tabs_final", "0"))

            self.cmb_limpar.set(dados.get("limpar_campo", "SIM"))
            self.cmb_acao_final.set(dados.get("acao_final", "ENTER"))

            self.entry_linha_inicial.delete(0, "end")
            self.entry_linha_inicial.insert(0, dados.get("linha_inicial", "1"))

            self.log(f"Layout carregado de: {caminho}")
            self.set_status("layout carregado", self.COR_SUCESSO)

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar o layout.\n\nDetalhe: {e}")

    # =========================================================
    # FECHAMENTO
    # =========================================================
    def fechar_app(self):
        try:
            if self.hk_listener:
                self.hk_listener.stop()
        except Exception:
            pass
        self.app.destroy()

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    app = PreenchedorSSAF8Simples()
    app.run()
