import json
import os
from typing import Dict, Any

DEFAULT_CONFIG = {
    "caminho_rede": r"\\SERVIDOR\Pagamentos",
    "email_contas_pagar": "contasapagar@montecarmo.com.br",
    "email_michel": "michel@montecarmo.com.br",
    "email_marcus": "marcus@montecarmo.com.br",
    "email_harley": "harley@montecarmo.com.br",
    "assinante": "Thierry Silva | Tecnologia da Informação",
    "dias_pagamento_validos": [0, 1, 2],
    "log_folder": "logs"
}

class ConfigLoader:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config_data = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Mesclar com padrão caso faltem chaves
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"Erro ao carregar {self.config_path}, utilizando configuração padrão. Detalhe: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    def save_config(self, data: Dict[str, Any]) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.config_data = data
        except Exception as e:
            print(f"Erro ao salvar configurações em {self.config_path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config_data.get(key, default)
