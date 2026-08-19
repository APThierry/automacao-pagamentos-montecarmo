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

        # Separa boletos de notas fiscais
        boletos = [b for b in boletos_info if b.get("tipo_documento") == "boleto" or b.get("linha_digitavel")]
        notas_fiscais = [b for b in boletos_info if b not in boletos]

        # Caso 1: Pasta possui exatamente 1 boleto (com ou sem notas fiscais associadas)
        if len(boletos) == 1:
            b = boletos[0]
            venc_str = b.get("data_vencimento_str", "A verificar")
            pag_str = b.get("data_pagamento_str", "A verificar")
            forn_str = b.get("fornecedor", nome_pasta)
            val_str = b.get("valor_formatado", "R$ 0,00")
            linha_dig = b.get("linha_digitavel")

            corpo += f"Data de vencimento: {venc_str}\n"
            corpo += f"Data para pagamento: {pag_str}\n"
            corpo += f"Fornecedor: {forn_str}\n"
            corpo += f"Valor: {val_str}\n"
            corpo += "Forma de pagamento: Boleto\n"
            if linha_dig:
                corpo += f"Linha Digitável: {linha_dig}\n"

            if notas_fiscais:
                corpo += f"\nNotas Fiscais anexadas ({len(notas_fiscais)} item/itens):\n"
                for nf in notas_fiscais:
                    val_nf = nf.get("valor_formatado", "R$ 0,00")
                    corpo += f"• {nf['arquivo']} - {val_nf}\n"
                corpo += "(Valor total consolidado no boleto em anexo)\n"

            if b.get("esta_vencido"):
                corpo += "\n⚠️ Atenção: data de vencimento já passou. Verificar urgência.\n"

        # Caso 2: Apensas 1 documento genérico ou sem tipo boleto explícito
        elif len(boletos_info) == 1:
            b = boletos_info[0]
            venc_str = b.get("data_vencimento_str", "A verificar")
            pag_str = b.get("data_pagamento_str", "A verificar")
            forn_str = b.get("fornecedor", nome_pasta)
            val_str = b.get("valor_formatado", "R$ 0,00")
            linha_dig = b.get("linha_digitavel")

            corpo += f"Data de vencimento: {venc_str}\n"
            corpo += f"Data para pagamento: {pag_str}\n"
            corpo += f"Fornecedor: {forn_str}\n"
            corpo += f"Valor: {val_str}\n"
            corpo += "Forma de pagamento: Boleto\n"
            if linha_dig:
                corpo += f"Linha Digitável: {linha_dig}\n"

            if b.get("esta_vencido"):
                corpo += "\n⚠️ Atenção: data de vencimento já passou. Verificar urgência.\n"

        # Caso 3: Múltiplos boletos na mesma pasta
        else:
            corpo += f"Documentos/Boletos identificados na pasta ({len(boletos_info)} itens):\n\n"
            tem_vencido = False
            for idx, b in enumerate(boletos_info, 1):
                venc_str = b.get("data_vencimento_str", "A verificar")
                pag_str = b.get("data_pagamento_str", "A verificar")
                forn_str = b.get("fornecedor", nome_pasta)
                val_str = b.get("valor_formatado", "R$ 0,00")
                arquivo_str = b.get("arquivo", "")
                linha_dig = b.get("linha_digitavel")
                tipo_str = "Boleto" if b.get("tipo_documento") == "boleto" else "Nota Fiscal"

                corpo += f"--- Documento {idx}: {tipo_str} ({arquivo_str}) ---\n"
                corpo += f"Data de vencimento: {venc_str}\n"
                corpo += f"Data para pagamento: {pag_str}\n"
                corpo += f"Fornecedor: {forn_str}\n"
                corpo += f"Valor: {val_str}\n"
                corpo += "Forma de pagamento: Boleto\n"
                if linha_dig:
                    corpo += f"Linha Digitável: {linha_dig}\n"
                corpo += "\n"

                if b.get("esta_vencido"):
                    tem_vencido = True

            if tem_vencido:
                corpo += "⚠️ Atenção: Há documento(s) com data de vencimento já ultrapassada. Verificar urgência.\n\n"

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
