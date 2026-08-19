import os
import json
from datetime import datetime
from typing import List, Dict, Any

class AutomationLogger:
    """
    Gerenciador de logs para registrar as atividades da automação de agendamento de pagamentos.
    Salva relatórios em formato TXT e JSON no diretório de logs.
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.txt_log_path = os.path.join(self.log_dir, f"execucao_{timestamp}.log")
        self.json_log_path = os.path.join(self.log_dir, f"execucao_{timestamp}.json")
        self.entries = []

    def log(self, mensagem: str, nivel: str = "INFO"):
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linha = f"[{data_hora}] [{nivel}] {mensagem}"
        print(linha)
        try:
            with open(self.txt_log_path, "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except Exception as e:
            print(f"Erro ao salvar log em texto: {e}")

    def registrar_resultado(self, dados_varredura: List[Dict[str, Any]], estatisticas: Dict[str, Any]):
        relatorio = {
            "data_execucao": datetime.now().isoformat(),
            "estatisticas": estatisticas,
            "detalhes_pastas": dados_varredura
        }
        try:
            with open(self.json_log_path, "w", encoding="utf-8") as f:
                json.dump(relatorio, f, indent=4, ensure_ascii=False, default=str)
            self.log(f"Relatório JSON salvo com sucesso em: {self.json_log_path}")
        except Exception as e:
            self.log(f"Erro ao salvar relatório JSON: {e}", nivel="ERRO")
