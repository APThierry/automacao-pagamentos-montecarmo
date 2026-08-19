import os
import sys
import threading
from datetime import date
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Tenta carregar CustomTkinter para estética moderna premium, fallback para Tkinter padrão se necessário
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

        if USE_CUSTOM_TK:
            self.root = ctk.CTk()
            self.root.title("Monte Carmo Shopping — Programação de Pagamentos")
            self.root.geometry("900x680")
            self.root.minsize(800, 600)
            self._build_custom_ui()
        else:
            self.root = tk.Tk()
            self.root.title("Monte Carmo Shopping — Programação de Pagamentos")
            self.root.geometry("850x650")
            self._build_standard_ui()

    def _build_custom_ui(self):
        # Frame de Cabeçalho
        header_frame = ctk.CTkFrame(self.root, fg_color="#1F2937", corner_radius=10)
        header_frame.pack(fill="x", padx=15, pady=10)

        title_label = ctk.CTkLabel(
            header_frame, 
            text="🏢 Monte Carmo Shopping — Automação Financeira", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#F3F4F6"
        )
        title_label.pack(side="left", padx=15, pady=15)

        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="Programação de Pagamentos & Outlook", 
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF"
        )
        subtitle_label.pack(side="right", padx=15, pady=15)

        # Frame de Configurações
        config_frame = ctk.CTkFrame(self.root, corner_radius=10)
        config_frame.pack(fill="x", padx=15, pady=5)

        # Linha 1: Caminho da Rede
        lbl_path = ctk.CTkLabel(config_frame, text="Caminho das Pastas (Rede):", font=ctk.CTkFont(weight="bold"))
        lbl_path.grid(row=0, column=0, sticky="w", padx=15, pady=8)

        self.entry_path = ctk.CTkEntry(config_frame, width=500)
        self.entry_path.insert(0, self.config.get("caminho_rede", r"\\SERVIDOR\Pagamentos"))
        self.entry_path.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        btn_browse = ctk.CTkButton(config_frame, text="Selecionar...", width=100, command=self._browse_path)
        btn_browse.grid(row=0, column=2, padx=15, pady=8)

        # Linha 2: E-mails Destinatários
        lbl_emails = ctk.CTkLabel(config_frame, text="E-mail Contas a Pagar:", font=ctk.CTkFont(weight="bold"))
        lbl_emails.grid(row=1, column=0, sticky="w", padx=15, pady=8)

        self.entry_email_to = ctk.CTkEntry(config_frame, width=500)
        self.entry_email_to.insert(0, self.config.get("email_contas_pagar", "contasapagar@montecarmo.com.br"))
        self.entry_email_to.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        btn_save_config = ctk.CTkButton(config_frame, text="Salvar Config", width=100, fg_color="#3B82F6", command=self._save_config)
        btn_save_config.grid(row=1, column=2, padx=15, pady=8)

        config_frame.columnconfigure(1, weight=1)

        # Frame de Botões de Ação
        action_frame = ctk.CTkFrame(self.root, corner_radius=10)
        action_frame.pack(fill="x", padx=15, pady=5)

        self.btn_run = ctk.CTkButton(
            action_frame, 
            text="🚀 Executar Automação (Salvar Rascunhos)", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10B981", 
            hover_color="#059669",
            height=40,
            command=self._start_automation_thread
        )
        self.btn_run.pack(side="left", padx=15, pady=10, expand=True, fill="x")

        btn_test_pdf = ctk.CTkButton(
            action_frame, 
            text="📄 Testar PDF Individual", 
            font=ctk.CTkFont(size=12),
            fg_color="#6B7280",
            height=40,
            command=self._test_single_pdf
        )
        btn_test_pdf.pack(side="right", padx=15, pady=10)

        # Frame de Estatísticas / Cards
        stats_frame = ctk.CTkFrame(self.root, corner_radius=10)
        stats_frame.pack(fill="x", padx=15, pady=5)

        self.card_pastas = self._create_card(stats_frame, "Pastas Lidas", "0", 0)
        self.card_pdfs = self._create_card(stats_frame, "PDFs Processados", "0", 1)
        self.card_rascunhos = self._create_card(stats_frame, "Rascunhos Criados", "0", 2)
        self.card_alertas = self._create_card(stats_frame, "Alertas / Erros", "0", 3)

        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        # Console de Log Live
        log_frame = ctk.CTkFrame(self.root, corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        lbl_log = ctk.CTkLabel(log_frame, text="Log de Execução em Tempo Real:", font=ctk.CTkFont(weight="bold"))
        lbl_log.pack(anchor="w", padx=15, pady=(10, 5))

        self.log_textbox = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    def _create_card(self, parent, title: str, initial_val: str, col: int):
        card = ctk.CTkFrame(parent, fg_color="#374151", corner_radius=8)
        card.grid(row=0, column=col, padx=8, pady=8, sticky="ew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="#D1D5DB")
        lbl_t.pack(pady=(8, 2))

        lbl_v = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=18, weight="bold"), text_color="#10B981")
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
        self.config_loader.save_config(self.config)
        messagebox.showinfo("Configurações", "Configurações salvas com sucesso!")

    def append_log(self, text: str):
        if USE_CUSTOM_TK:
            self.log_textbox.insert(tk.END, text + "\n")
            self.log_textbox.see(tk.END)
        else:
            self.log_textbox.insert(tk.END, text + "\n")
            self.log_textbox.see(tk.END)

    def _test_single_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Selecione um arquivo PDF para testar extração",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not file_path:
            return

        extractor = PDFExtractor()
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
            messagebox.showerror("Erro Fatal", f"Ocorreu uma exceção não tratada:\n{e}")
        finally:
            if USE_CUSTOM_TK:
                self.btn_run.configure(state="normal", text="🚀 Executar Automação (Salvar Rascunhos)")
            else:
                self.btn_run.config(state="normal", text="Executar Automação")


def main():
    gui = AppGUI()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
