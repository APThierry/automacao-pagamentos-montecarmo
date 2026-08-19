import os
from datetime import datetime, date
from typing import List, Dict, Any
from core.payment_calculator import obter_saudacao, obter_mes_extenso

class OutlookService:
    """
    Serviço de comunicação com o Microsoft Outlook via PyWin32 COM.
    Cria e salva rascunhos de e-mail sem envio automático.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._win32 = None
        self._load_win32()

    def _load_win32(self):
        try:
            import win32com.client as win32
            self._win32 = win32
        except ImportError:
            print("Aviso: módulo 'pywin32' não instalado. Teste de Outlook executará em modo simulação.")

    def criar_rascunho(self, 
                       nome_pasta: str, 
                       boletos_info: List[Dict[str, Any]], 
                       anexos: List[str],
                       dt_referencia: date = None) -> tuple[bool, str]:
        """
        Cria um e-mail rascunho no Outlook para a pasta especificada.
        Retorna (sucesso, mensagem_ou_assunto).
        """
        if dt_referencia is None:
            dt_referencia = date.today()

        hora_atual = datetime.now().hour
        saudacao = obter_saudacao(hora_atual)

        # Determina o mês principal para o assunto (mês do 1º boleto com vencimento ou mês atual)
        primeiro_vencimento = None
        for b in boletos_info:
            if b.get("data_vencimento"):
                primeiro_vencimento = b["data_vencimento"]
                break

        mes_extenso = obter_mes_extenso(primeiro_vencimento) if primeiro_vencimento else obter_mes_extenso(dt_referencia)
        assunto = f"Boleto {nome_pasta} - {mes_extenso.capitalize()}"

        para = self.config.get("email_contas_pagar", "contasapagar@montecarmo.com.br")
        
        # CC formatado
        cc_list = [
            self.config.get("email_michel", "michel@montecarmo.com.br"),
            self.config.get("email_marcus", "marcus@montecarmo.com.br"),
            self.config.get("email_harley", "harley@montecarmo.com.br")
        ]
        cc = "; ".join([e for e in cc_list if e])

        # Montagem do corpo do e-mail
        corpo = "Status: Aprovado por Marcus/Harley\n\n"
        corpo += f"{saudacao},\n\n"

        fornecedor_principal = boletos_info[0].get("fornecedor", nome_pasta) if boletos_info else nome_pasta
        corpo += f"Solicito programação de pagamento referente ao boleto do mês de {mes_extenso} da {fornecedor_principal}.\n\n"

        if len(boletos_info) == 1:
            b = boletos_info[0]
            venc_str = b.get("data_vencimento_str", "A verificar")
            pag_str = b.get("data_pagamento_str", "A verificar")
            forn_str = b.get("fornecedor", nome_pasta)
            val_str = b.get("valor_formatado", "R$ 0,00")

            corpo += f"Data de vencimento: {venc_str}\n"
            corpo += f"Data para pagamento: {pag_str}\n"
            corpo += f"Fornecedor: {forn_str}\n"
            corpo += f"Valor: {val_str}\n"
            corpo += "Forma de pagamento: Boleto\n"

            if b.get("esta_vencido"):
                corpo += "\n⚠️ Atenção: data de vencimento já passou. Verificar urgência.\n"

        else:
            corpo += f"Boletos identificados na pasta ({len(boletos_info)} itens):\n\n"
            tem_vencido = False
            for idx, b in enumerate(boletos_info, 1):
                venc_str = b.get("data_vencimento_str", "A verificar")
                pag_str = b.get("data_pagamento_str", "A verificar")
                forn_str = b.get("fornecedor", nome_pasta)
                val_str = b.get("valor_formatado", "R$ 0,00")
                arquivo_str = b.get("arquivo", "")

                corpo += f"--- Boleto {idx} ({arquivo_str}) ---\n"
                corpo += f"Data de vencimento: {venc_str}\n"
                corpo += f"Data para pagamento: {pag_str}\n"
                corpo += f"Fornecedor: {forn_str}\n"
                corpo += f"Valor: {val_str}\n"
                corpo += "Forma de pagamento: Boleto\n\n"

                if b.get("esta_vencido"):
                    tem_vencido = True

            if tem_vencido:
                corpo += "⚠️ Atenção: Há boleto(s) com data de vencimento já ultrapassada. Verificar urgência.\n\n"

        corpo += "\nQualquer dúvida estou à disposição."

        # Tenta criar o rascunho no Outlook via Win32 COM
        if self._win32:
            try:
                outlook = self._win32.Dispatch('outlook.application')
                mail = outlook.CreateItem(0)  # 0 = olMailItem

                mail.Subject = assunto
                mail.Body = corpo
                mail.To = para
                mail.CC = cc

                for anexo_path in anexos:
                    if os.path.exists(anexo_path):
                        mail.Attachments.Add(os.path.abspath(anexo_path))

                mail.Save()  # Salva como RASCUNHO (NUNCA envia)
                return True, f"Rascunho criado com sucesso: '{assunto}'"
            except Exception as e:
                return False, f"Falha ao integrar com Outlook COM: {e}"
        else:
            # Modo Simulação (caso Outlook não esteja presente ou em ambiente sem COM)
            return True, f"[SIMULAÇÃO] Rascunho seria criado para: '{assunto}' (Para: {para})"
