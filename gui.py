import os
import sys
import threading
from datetime import date
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Tenta carregar CustomTkinter para estética moderna premium
USE_CUSTOM_TK = False
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    USE_CUSTOM_TK = True
except ImportError:
    pass

from core.config_loader import ConfigLoader
from core.pdf_extractor import PDFExtractor
from core.payment_calculator import calcular_data_pagamento
from core.outlook_service import OutlookService
from core.logger import AutomationLogger
from main import AutomacaoPagamentos


class AppGUI:
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.config_data

        self.all_table_data = []
        self.tree_item_paths = {}

        if USE_CUSTOM_TK:
            self.root = ctk.CTk()
            self.root.title("Monte Carmo Shopping — Automação de Pagamentos & Outlook")
            self.root.geometry("1060x780")
            self.root.minsize(920, 680)
            self._build_custom_ui()
        else:
            self.root = tk.Tk()
            self.root.title("Monte Carmo Shopping — Automação de Pagamentos")
            self.root.geometry("980x720")
            self._build_standard_ui()

        self._setup_treeview_styles()
        self._create_context_menu()

    def _setup_treeview_styles(self):
        """Configura o estilo escuro elegante para a Treeview do Tkinter."""
        style = ttk.Style()
        style.theme_use("clam")
        
        bg_color = "#1E1E2E"
        fg_color = "#F3F4F6"
        heading_bg = "#111827"
        selected_bg = "#2563EB"

        style.configure(
            "Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            rowheight=30,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background=heading_bg,
            foreground="#9CA3AF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=6
        )
        style.map("Treeview", background=[("selected", selected_bg)], foreground=[("selected", "#FFFFFF")])
        style.map("Treeview.Heading", background=[("active", "#374151")])

    def _create_context_menu(self):
        """Cria o menu de contexto (clique direito) na tabela."""
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#1F2937", fg="#F3F4F6", activebackground="#2563EB")
        self.context_menu.add_command(label="📄 Visualizar PDF", command=self._open_selected_pdf)
        self.context_menu.add_command(label="📁 Abrir Pasta no Windows Explorer", command=self._open_selected_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copiar Linha Digitável / Código de Barras", command=self._copy_linha_digitavel)
        self.context_menu.add_command(label="✉️ Abrir Pasta de Rascunhos no Outlook", command=self._open_outlook_drafts)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _build_custom_ui(self):
        # 1. Header Frame Premium
        header_frame = ctk.CTkFrame(self.root, fg_color="#181825", corner_radius=12, border_width=1, border_color="#313244")
        header_frame.pack(fill="x", padx=15, pady=(12, 6))

        title_label = ctk.CTkLabel(
            header_frame, 
            text="🏢 Monte Carmo Shopping", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#F3F4F6"
        )
        title_label.pack(side="left", padx=18, pady=12)

        title_badge = ctk.CTkLabel(
            header_frame, 
            text="AUTOMAÇÃO FINANCEIRA & OUTLOOK", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#10B981",
            fg_color="#064E3B",
            corner_radius=6,
            padx=10,
            pady=4
        )
        title_badge.pack(side="left", padx=5, pady=12)

        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="v2.5 • Programação de Pagamentos", 
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF"
        )
        subtitle_label.pack(side="right", padx=18, pady=12)

        # 2. Frame de Configurações
        config_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#1E1E2E")
        config_frame.pack(fill="x", padx=15, pady=4)

        lbl_path = ctk.CTkLabel(config_frame, text="📁 Caminho das Pastas (Rede):", font=ctk.CTkFont(weight="bold"))
        lbl_path.grid(row=0, column=0, sticky="w", padx=15, pady=6)

        self.entry_path = ctk.CTkEntry(config_frame, width=480, placeholder_text="Digite ou selecione a pasta de pagamentos...")
        self.entry_path.insert(0, self.config.get("caminho_rede", r"\\SERVIDOR\Pagamentos"))
        self.entry_path.grid(row=0, column=1, padx=10, pady=6, sticky="ew")

        btn_browse = ctk.CTkButton(config_frame, text="Procurar...", width=100, fg_color="#374151", hover_color="#4B5563", command=self._browse_path)
        btn_browse.grid(row=0, column=2, padx=15, pady=6)

        lbl_emails = ctk.CTkLabel(config_frame, text="✉️ E-mail Contas a Pagar:", font=ctk.CTkFont(weight="bold"))
        lbl_emails.grid(row=1, column=0, sticky="w", padx=15, pady=6)

        self.entry_email_to = ctk.CTkEntry(config_frame, width=480)
        self.entry_email_to.insert(0, self.config.get("email_contas_pagar", "contasapagar@montecarmo.com.br"))
        self.entry_email_to.grid(row=1, column=1, padx=10, pady=6, sticky="ew")

        lbl_gpt = ctk.CTkLabel(config_frame, text="🔑 Chave API ChatGPT (Opcional):", font=ctk.CTkFont(weight="bold"))
        lbl_gpt.grid(row=2, column=0, sticky="w", padx=15, pady=6)

        self.entry_gpt_key = ctk.CTkEntry(config_frame, width=480, show="*")
        self.entry_gpt_key.insert(0, self.config.get("openai_api_key", ""))
        self.entry_gpt_key.grid(row=2, column=1, padx=10, pady=6, sticky="ew")

        btn_save_config = ctk.CTkButton(config_frame, text="Salvar Config", width=100, fg_color="#2563EB", hover_color="#1D4ED8", command=self._save_config)
        btn_save_config.grid(row=2, column=2, padx=15, pady=6)

        config_frame.columnconfigure(1, weight=1)

        # 3. Frame de Ações Principais
        action_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#1E1E2E")
        action_frame.pack(fill="x", padx=15, pady=4)

        self.btn_run = ctk.CTkButton(
            action_frame, 
            text="🚀 Executar Automação (Gerar Rascunhos no Outlook)", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10B981", 
            hover_color="#059669",
            height=42,
            command=self._start_automation_thread
        )
        self.btn_run.pack(side="left", padx=15, pady=8, expand=True, fill="x")

        btn_test_pdf = ctk.CTkButton(
            action_frame, 
            text="🔍 Testar 1 PDF", 
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4B5563",
            hover_color="#374151",
            height=42,
            command=self._test_single_pdf
        )
        btn_test_pdf.pack(side="right", padx=15, pady=8)

        # 4. Summary Stats Cards (Cards Indicadores)
        stats_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=4)

        self.card_pastas = self._create_card(stats_frame, "📁 Pastas Lidas", "0", 0, "#3B82F6")
        self.card_pdfs = self._create_card(stats_frame, "📄 PDFs Processados", "0", 1, "#8B5CF6")
        self.card_rascunhos = self._create_card(stats_frame, "✉️ Rascunhos Criados", "0", 2, "#10B981")
        self.card_alertas = self._create_card(stats_frame, "⚠️ Alertas / Erros", "0", 3, "#EF4444")

        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        # 5. Sistema de Abas (Tabview)
        self.tabview = ctk.CTkTabview(self.root, corner_radius=10, fg_color="#1E1E2E")
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(4, 6))

        self.tab_tabela = self.tabview.add("📊 Tabela Interativa de Resultados")
        self.tab_log = self.tabview.add("🖥️ Log de Execução")

        self._build_table_tab(self.tab_tabela)

        # Aba de Log de Execução
        log_top = ctk.CTkFrame(self.tab_log, fg_color="transparent")
        log_top.pack(fill="x", padx=5, pady=(5, 5))

        lbl_log_title = ctk.CTkLabel(log_top, text="Log de Execução em Tempo Real:", font=ctk.CTkFont(weight="bold"))
        lbl_log_title.pack(side="left", padx=5)

        btn_copy_log = ctk.CTkButton(log_top, text="📋 Copiar Log", width=100, fg_color="#374151", command=self._copy_log)
        btn_copy_log.pack(side="right", padx=5)

        btn_clear_log = ctk.CTkButton(log_top, text="🗑️ Limpar", width=80, fg_color="#374151", command=self._clear_log)
        btn_clear_log.pack(side="right", padx=5)

        self.log_textbox = ctk.CTkTextbox(self.tab_log, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#111827")
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Barra de Status na Parte Inferior
        self.status_bar = ctk.CTkLabel(self.root, text="● Pronto para executar", font=ctk.CTkFont(size=11), text_color="#9CA3AF", anchor="w")
        self.status_bar.pack(fill="x", padx=20, pady=(0, 6))

    def _build_table_tab(self, parent):
        """Constrói a Tabela Interativa na Tab 1 com barra de ferramentas e filtros inteligentes."""
        toolbar_frame = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=5, pady=(4, 8))

        lbl_search = ctk.CTkLabel(toolbar_frame, text="🔍 Buscar:", font=ctk.CTkFont(weight="bold"))
        lbl_search.pack(side="left", padx=(5, 5))

        self.entry_search = ctk.CTkEntry(toolbar_frame, placeholder_text="Filtrar fornecedor, arquivo, valor ou data...", width=280)
        self.entry_search.pack(side="left", padx=5)
        self.entry_search.bind("<KeyRelease>", self._filter_table)

        btn_clear_search = ctk.CTkButton(toolbar_frame, text="❌", width=30, fg_color="#374151", hover_color="#4B5563", command=self._clear_search)
        btn_clear_search.pack(side="left", padx=(0, 8))

        self.combo_filter = ctk.CTkOptionMenu(
            toolbar_frame, 
            values=["Todos os Documentos", "Apenas Boletos", "Apenas Notas Fiscais", "Com Alerta / Erro"],
            width=170,
            command=self._filter_table
        )
        self.combo_filter.pack(side="left", padx=5)

        # Botões de Ação na Direita
        btn_open_outlook = ctk.CTkButton(
            toolbar_frame, 
            text="✉️ Rascunhos Outlook", 
            fg_color="#8B5CF6", 
            hover_color="#7C3AED",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=150,
            command=self._open_outlook_drafts
        )
        btn_open_outlook.pack(side="right", padx=5)

        btn_open_folder = ctk.CTkButton(
            toolbar_frame, 
            text="📁 Abrir Pasta", 
            fg_color="#2563EB", 
            hover_color="#1D4ED8",
            width=110,
            command=self._open_selected_folder
        )
        btn_open_folder.pack(side="right", padx=5)

        btn_open_pdf = ctk.CTkButton(
            toolbar_frame, 
            text="📄 Visualizar PDF", 
            fg_color="#4B5563", 
            hover_color="#374151",
            width=110,
            command=self._open_selected_pdf
        )
        btn_open_pdf.pack(side="right", padx=5)

        # Treeview Container
        table_container = ttk.Frame(parent)
        table_container.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("pasta", "arquivo", "tipo", "valor", "vencimento", "pagamento", "status")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("pasta", text="Pasta / Fornecedor ⇕", command=lambda: self._sort_column("pasta", False))
        self.tree.heading("arquivo", text="Arquivo PDF ⇕", command=lambda: self._sort_column("arquivo", False))
        self.tree.heading("tipo", text="Tipo ⇕", command=lambda: self._sort_column("tipo", False))
        self.tree.heading("valor", text="Valor (R$) ⇕", command=lambda: self._sort_column("valor", False))
        self.tree.heading("vencimento", text="Vencimento ⇕", command=lambda: self._sort_column("vencimento", False))
        self.tree.heading("pagamento", text="Data Pagamento ⇕", command=lambda: self._sort_column("pagamento", False))
        self.tree.heading("status", text="Status Outlook ⇕", command=lambda: self._sort_column("status", False))

        self.tree.column("pasta", width=170, anchor="w")
        self.tree.column("arquivo", width=200, anchor="w")
        self.tree.column("tipo", width=95, anchor="center")
        self.tree.column("valor", width=115, anchor="e")
        self.tree.column("vencimento", width=100, anchor="center")
        self.tree.column("pagamento", width=115, anchor="center")
        self.tree.column("status", width=200, anchor="w")

        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_table_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)  # Clique direito no Windows

    def _create_card(self, parent, title: str, initial_val: str, col: int, accent_color: str = "#10B981"):
        card = ctk.CTkFrame(parent, fg_color="#1E1E2E", corner_radius=10, border_width=1, border_color="#313244")
        card.grid(row=0, column=col, padx=6, pady=4, sticky="ew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="#9CA3AF")
        lbl_t.pack(pady=(8, 2))

        lbl_v = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=20, weight="bold"), text_color=accent_color)
        lbl_v.pack(pady=(0, 8))
        return lbl_v

    def _build_standard_ui(self):
        # Fallback de interface Tkinter padrão
        tk.Label(self.root, text="Monte Carmo Shopping — Programação de Pagamentos", font=("Arial", 14, "bold")).pack(pady=10)

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=10, pady=5)

        tk.Label(frame, text="Caminho das Pastas:").pack(side="left")
        self.entry_path = tk.Entry(frame, width=50)
        self.entry_path.insert(0, self.config.get("caminho_rede", r"\\SERVIDOR\Pagamentos"))
        self.entry_path.pack(side="left", padx=5)

        tk.Button(frame, text="Buscar", command=self._browse_path).pack(side="left")

        self.btn_run = tk.Button(self.root, text="Executar Automação", bg="#10B981", fg="white", font=("Arial", 11, "bold"), command=self._start_automation_thread)
        self.btn_run.pack(pady=10)

        self.log_textbox = tk.Text(self.root, font=("Consolas", 10))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

    def _browse_path(self):
        chosen = filedialog.askdirectory(title="Selecione a Pasta Raiz de Pagamentos")
        if chosen:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, chosen)

    def _save_config(self):
        self.config["caminho_rede"] = self.entry_path.get().strip()
        self.config["email_contas_pagar"] = self.entry_email_to.get().strip()
        if hasattr(self, "entry_gpt_key"):
            self.config["openai_api_key"] = self.entry_gpt_key.get().strip()
        self.config_loader.save_config(self.config)
        messagebox.showinfo("Configurações", "Configurações salvas com sucesso!")

    def append_log(self, text: str):
        if USE_CUSTOM_TK:
            self.log_textbox.insert(tk.END, text + "\n")
            self.log_textbox.see(tk.END)
        else:
            self.log_textbox.insert(tk.END, text + "\n")
            self.log_textbox.see(tk.END)

    def _copy_log(self):
        content = self.log_textbox.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Log", "Log copiado para a área de transferência!")

    def _clear_log(self):
        self.log_textbox.delete("1.0", tk.END)

    def _clear_search(self):
        if hasattr(self, "entry_search"):
            self.entry_search.delete(0, tk.END)
            self._filter_table()

    def _update_results_table(self, dados_varredura):
        """Popula a tabela interativa com os dados lidos de cada boleto e nota fiscal."""
        self.all_table_data.clear()
        self.tree_item_paths.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        raiz = self.entry_path.get().strip()

        for pasta_data in dados_varredura:
            nome_pasta = pasta_data.get("pasta", "")
            status_draft = pasta_data.get("status_rascunho", "")
            pasta_completa = os.path.join(raiz, nome_pasta)

            boletos = pasta_data.get("boletos", [])
            for bol in boletos:
                tipo_str = "Boleto" if bol.get("tipo_documento") == "boleto" else "Nota Fiscal"
                
                # Formatador visual de status
                if "criado com sucesso" in status_draft.lower():
                    status_badge = "🟢 Rascunho Criado"
                elif "erro" in status_draft.lower() or "falha" in status_draft.lower():
                    status_badge = f"🔴 {status_draft}"
                else:
                    status_badge = status_draft

                row_item = {
                    "pasta": nome_pasta,
                    "arquivo": bol.get("arquivo", ""),
                    "tipo": tipo_str,
                    "valor": bol.get("valor_formatado", "R$ 0,00"),
                    "vencimento": bol.get("data_vencimento_str", ""),
                    "pagamento": bol.get("data_pagamento_str", ""),
                    "status": status_badge,
                    "folder_path": pasta_completa,
                    "pdf_path": bol.get("caminho_completo", ""),
                    "linha_digitavel": bol.get("linha_digitavel", "")
                }
                self.all_table_data.append(row_item)

        self._populate_tree(self.all_table_data)

        # Seleciona a Tab da Tabela para exibição imediata dos resultados
        if USE_CUSTOM_TK:
            self.tabview.set("📊 Tabela Interativa de Resultados")

    def _populate_tree(self, items):
        """Insere os itens filtrados na Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in items:
            item_id = self.tree.insert(
                "", "end",
                values=(
                    row["pasta"],
                    row["arquivo"],
                    row["tipo"],
                    row["valor"],
                    row["vencimento"],
                    row["pagamento"],
                    row["status"]
                )
            )
            self.tree_item_paths[item_id] = {
                "folder_path": row["folder_path"],
                "pdf_path": row["pdf_path"],
                "linha_digitavel": row.get("linha_digitavel", "")
            }

    def _filter_table(self, *args):
        """Filtra os dados da tabela por texto e categoria de documento."""
        query = self.entry_search.get().strip().lower() if hasattr(self, "entry_search") else ""
        filtro_cat = self.combo_filter.get() if hasattr(self, "combo_filter") else "Todos os Documentos"

        filtered = []
        for row in self.all_table_data:
            # 1. Filtro por Categoria
            if filtro_cat == "Apenas Boletos" and row["tipo"] != "Boleto":
                continue
            elif filtro_cat == "Apenas Notas Fiscais" and row["tipo"] != "Nota Fiscal":
                continue
            elif filtro_cat == "Com Alerta / Erro" and "🔴" not in row["status"] and "⚠️" not in row["status"]:
                continue

            # 2. Busca por texto
            if query:
                text_target = f"{row['pasta']} {row['arquivo']} {row['vencimento']} {row['pagamento']} {row['valor']}".lower()
                if query not in text_target:
                    continue

            filtered.append(row)

        self._populate_tree(filtered)

    def _sort_column(self, col, reverse):
        """Ordena a Treeview ao clicar no cabeçalho da coluna."""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    def _open_selected_folder(self):
        """Abre a pasta da rede selecionada no Windows Explorer com 1 clique."""
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showwarning("Aviso", "Selecione uma linha na tabela primeiro.")
            return
        path_info = self.tree_item_paths.get(item_id, {})
        folder_path = path_info.get("folder_path")
        if folder_path and os.path.exists(folder_path):
            os.startfile(folder_path)
        else:
            messagebox.showwarning("Pasta não encontrada", f"A pasta '{folder_path}' não existe ou não está acessível.")

    def _open_selected_pdf(self):
        """Abre o arquivo PDF selecionado no leitor padrão do Windows."""
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showwarning("Aviso", "Selecione um arquivo PDF na tabela primeiro.")
            return
        path_info = self.tree_item_paths.get(item_id, {})
        pdf_path = path_info.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            os.startfile(pdf_path)
        else:
            messagebox.showwarning("Arquivo não encontrado", f"O arquivo PDF '{pdf_path}' não foi encontrado.")

    def _copy_linha_digitavel(self):
        """Copia a linha digitável do boleto selecionado para a área de transferência."""
        item_id = self.tree.focus()
        if not item_id:
            return
        path_info = self.tree_item_paths.get(item_id, {})
        linha_dig = path_info.get("linha_digitavel")
        if linha_dig:
            self.root.clipboard_clear()
            self.root.clipboard_append(linha_dig)
            messagebox.showinfo("Copiado", f"Linha digitável copiada:\n{linha_dig}")
        else:
            messagebox.showinfo("Informação", "Nenhuma linha digitável encontrada para este item.")

    def _open_outlook_drafts(self):
        """Abre a pasta de Rascunhos do Outlook com 1 clique."""
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            # 16 = olFolderDrafts
            drafts_folder = namespace.GetDefaultFolder(16)
            drafts_folder.Display()
        except Exception as e:
            messagebox.showerror("Erro ao abrir Outlook", f"Não foi possível abrir a pasta de Rascunhos do Outlook:\n{e}")

    def _on_table_double_click(self, event):
        """Ao dar duplo-clique em qualquer linha da tabela, abre o PDF no Windows."""
        self._open_selected_pdf()

    def _test_single_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Selecione um arquivo PDF para testar extração",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not file_path:
            return

        extractor = PDFExtractor(
            api_key=self.config.get("openai_api_key"),
            model=self.config.get("openai_model", "gpt-4o-mini")
        )
        nome_pasta = os.path.basename(os.path.dirname(file_path)) or "Teste"
        res = extractor.parse_boleto_data(file_path, nome_pasta)

        if res["data_vencimento"]:
            pag, vencido = calcular_data_pagamento(res["data_vencimento"])
            res["data_pagamento_str"] = pag.strftime("%d/%m/%Y")
            res["esta_vencido"] = vencido
        else:
            res["data_pagamento_str"] = "N/A"

        info_msg = (
            f"Arquivo: {res['arquivo']}\n"
            f"Fornecedor extraído: {res['fornecedor']}\n"
            f"Valor: {res['valor_formatado']}\n"
            f"Vencimento: {res['data_vencimento_str']}\n"
            f"Data Pagamento Calculada: {res['data_pagamento_str']}\n"
            f"Sucesso: {res['sucesso']}\n"
            f"Erro/Aviso: {res['erro'] or 'Nenhum'}"
        )
        messagebox.showinfo("Resultado da Extração", info_msg)

    def _start_automation_thread(self):
        path = self.entry_path.get().strip()
        if not path:
            messagebox.showwarning("Aviso", "Por favor, especifique o caminho das pastas de pagamentos.")
            return

        self._save_config()

        if USE_CUSTOM_TK:
            self.btn_run.configure(state="disabled", text="⏳ Executando Automação...")
            self.status_bar.configure(text="⏳ Lendo pastas de pagamentos e gerando rascunhos no Outlook...", text_color="#F59E0B")
        else:
            self.btn_run.config(state="disabled", text="Executando...")

        # Executa a automação em thread separada para manter a GUI responsiva
        t = threading.Thread(target=self._run_automation_process, args=(path,), daemon=True)
        t.start()

    def _run_automation_process(self, path: str):
        try:
            self.append_log("Iniciando processo em segundo plano...\n")
            app = AutomacaoPagamentos(caminho_raiz=path)
            stats = app.executar()

            # Atualizar cards de estatística
            if USE_CUSTOM_TK:
                self.card_pastas.configure(text=str(stats.get("total_pastas", 0)))
                self.card_pdfs.configure(text=str(stats.get("total_pdfs", 0)))
                self.card_rascunhos.configure(text=str(stats.get("rascunhos_criados", 0)))
                
                alertas_totais = stats.get("erros_leitura", 0) + stats.get("erros_outlook", 0)
                self.card_alertas.configure(text=str(alertas_totais))
                self.status_bar.configure(text="● Automação concluída com sucesso!", text_color="#10B981")

            # Atualizar a Tabela Interativa de Resultados
            self.root.after(0, lambda: self._update_results_table(stats.get("dados_varredura", [])))

            if "erro_critico" in stats:
                messagebox.showerror("Erro de Execução", stats["erro_critico"])
            else:
                messagebox.showinfo(
                    "Automação Concluída", 
                    f"Processo finalizado com sucesso!\n\n"
                    f"• Pastas analisadas: {stats['total_pastas']}\n"
                    f"• PDFs processados: {stats['total_pdfs']}\n"
                    f"• Rascunhos criados no Outlook: {stats['rascunhos_criados']}\n"
                    f"• Alertas / Erros: {stats['erros_leitura'] + stats['erros_outlook']}"
                )
        except Exception as e:
            self.append_log(f"\n[ERRO CRÍTICO] {e}")
            if USE_CUSTOM_TK:
                self.status_bar.configure(text=f"🔴 Erro: {e}", text_color="#EF4444")
            messagebox.showerror("Erro Fatal", f"Ocorreu uma exceção não tratada:\n{e}")
        finally:
            if USE_CUSTOM_TK:
                self.btn_run.configure(state="normal", text="🚀 Executar Automação (Gerar Rascunhos no Outlook)")
            else:
                self.btn_run.config(state="normal", text="Executar Automação")


def main():
    gui = AppGUI()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
