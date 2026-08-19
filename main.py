import os
import sys
import argparse
from datetime import date
from typing import Dict, Any, List

from core.config_loader import ConfigLoader
from core.pdf_extractor import PDFExtractor
from core.payment_calculator import calcular_data_pagamento
from core.outlook_service import OutlookService
from core.logger import AutomationLogger


class AutomacaoPagamentos:
    def __init__(self, caminho_raiz: str = None, config_path: str = "config.json"):
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.config_data
        
        if caminho_raiz:
            self.caminho_raiz = caminho_raiz
        else:
            self.caminho_raiz = self.config.get("caminho_rede", r"\\SERVIDOR\Pagamentos")

        self.extractor = PDFExtractor()
        self.outlook = OutlookService(self.config)
        self.logger = AutomationLogger(self.config.get("log_folder", "logs"))

    def executar(self) -> Dict[str, Any]:
        """
        Executa a automação completa de agendamento de pagamentos.
        Retorna o resumo das estatísticas.
        """
        self.logger.log("==================================================================")
        self.logger.log(" INICIANDO AUTOMAÇÃO DE PROGRAMAÇÃO DE PAGAMENTOS - MONTE CARMO ")
        self.logger.log("==================================================================")
        self.logger.log(f"Caminho das pastas: {self.caminho_raiz}")

        stats = {
            "caminho_raiz": self.caminho_raiz,
            "total_pastas": 0,
            "total_pdfs": 0,
            "rascunhos_criados": 0,
            "erros_leitura": 0,
            "erros_outlook": 0,
            "pastas_ignoradas": 0
        }

        if not os.path.exists(self.caminho_raiz):
            self.logger.log(f"ERRO: Caminho de rede ou pasta raiz não encontrada: '{self.caminho_raiz}'", nivel="ERRO")
            stats["erro_critico"] = f"Caminho não encontrado: {self.caminho_raiz}"
            return stats

        subpastas = [
            f for f in os.listdir(self.caminho_raiz)
            if os.path.isdir(os.path.join(self.caminho_raiz, f))
        ]

        stats["total_pastas"] = len(subpastas)
        self.logger.log(f"Encontradas {len(subpastas)} subpastas para processamento.")

        dados_varredura = []
        data_hoje = date.today()

        for nome_pasta in subpastas:
            pasta_path = os.path.join(self.caminho_raiz, nome_pasta)
            arquivos = os.listdir(pasta_path)
            pdfs = [
                os.path.join(pasta_path, f)
                for f in arquivos
                if f.lower().endswith(".pdf")
            ]

            if not pdfs:
                self.logger.log(f"Pasta '{nome_pasta}' sem arquivos PDF. Ignorada.", nivel="AVISO")
                stats["pastas_ignoradas"] += 1
                continue

            self.logger.log(f"--- Processando pasta '{nome_pasta}' ({len(pdfs)} PDFs) ---")
            stats["total_pdfs"] += len(pdfs)

            boletos_info = []
            for pdf_path in pdfs:
                info = self.extractor.parse_boleto_data(pdf_path, nome_pasta)
                
                # Se obtivemos data de vencimento, calculamos a data de pagamento
                if info.get("data_vencimento"):
                    dt_venc = info["data_vencimento"]
                    dt_pag, esta_vencido = calcular_data_pagamento(dt_venc, data_hoje)
                    info["data_pagamento"] = dt_pag
                    info["data_pagamento_str"] = dt_pag.strftime("%d/%m/%Y")
                    info["esta_vencido"] = esta_vencido
                else:
                    info["data_pagamento"] = None
                    info["data_pagamento_str"] = "Mão de obra / Revisar"
                    info["esta_vencido"] = False

                if not info["sucesso"]:
                    self.logger.log(f"  [ATENÇÃO] {info['arquivo']}: {info['erro']}", nivel="AVISO")
                    stats["erros_leitura"] += 1
                else:
                    self.logger.log(
                        f"  [OK] {info['arquivo']} | Venc: {info['data_vencimento_str']} | "
                        f"Pag: {info['data_pagamento_str']} | Valor: {info['valor_formatado']}"
                    )

                boletos_info.append(info)

            # Criar Rascunho no Outlook para a pasta
            sucesso_draft, msg_draft = self.outlook.criar_rascunho(
                nome_pasta=nome_pasta,
                boletos_info=boletos_info,
                anexos=pdfs,
                dt_referencia=data_hoje
            )

            if sucesso_draft:
                self.logger.log(f"  --> {msg_draft}")
                stats["rascunhos_criados"] += 1
            else:
                self.logger.log(f"  --> ERRO AO CRIAR RASCUNHO: {msg_draft}", nivel="ERRO")
                stats["erros_outlook"] += 1

            dados_varredura.append({
                "pasta": nome_pasta,
                "anexos": pdfs,
                "boletos": boletos_info,
                "status_rascunho": msg_draft
            })

        # Salva o log resumido
        self.logger.registrar_resultado(dados_varredura, stats)

        self.logger.log("\n==================================================================")
        self.logger.log("                   RESUMO FINAL DA EXECUÇÃO                       ")
        self.logger.log("==================================================================")
        self.logger.log(f" Subpastas analisadas : {stats['total_pastas']}")
        self.logger.log(f" Arquivos PDF lidos   : {stats['total_pdfs']}")
        self.logger.log(f" Rascunhos criados    : {stats['rascunhos_criados']}")
        self.logger.log(f" Alertas de leitura   : {stats['erros_leitura']}")
        self.logger.log(f" Erros de Outlook     : {stats['erros_outlook']}")
        self.logger.log(f" Pastas sem PDFs      : {stats['pastas_ignoradas']}")
        self.logger.log("==================================================================\n")

        return stats


def main():
    parser = argparse.ArgumentParser(description="Automação de Programação de Pagamentos - Monte Carmo Shopping")
    parser.add_argument("--path", type=str, help="Caminho raiz alternativo para as pastas de pagamentos")
    args = parser.parse_args()

    app = AutomacaoPagamentos(caminho_raiz=args.path)
    app.executar()


if __name__ == "__main__":
    main()
