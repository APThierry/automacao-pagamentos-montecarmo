from datetime import date, timedelta
from typing import Tuple

MESES_PT_BR = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro"
}

def obter_mes_extenso(dt: date) -> str:
    """Retorna o mês em extenso em português minúsculo."""
    return MESES_PT_BR.get(dt.month, "")

def calcular_data_pagamento(data_vencimento: date, data_atual: date = None) -> Tuple[date, bool]:
    """
    Calcula a data ideal de pagamento respeitando as regras do Monte Carmo Shopping:
    - Pagamentos ocorrem apenas em Segunda (0), Terça (1) ou Quarta (2).
    - Vencimento em Seg/Ter/Qua -> Próprio dia
    - Vencimento em Quinta/Sexta/Sábado -> Quarta-feira anterior
    - Vencimento em Domingo -> Segunda-feira seguinte (caso não esteja vencido)
    - Se a data calculada já passou da data atual, ajusta para o próximo dia válido (Seg/Ter/Qua).
    
    Retorna (data_pagamento, esta_vencido)
    """
    if data_atual is None:
        data_atual = date.today()

    dias_validos = [0, 1, 2]  # 0=segunda, 1=terça, 2=quarta
    esta_vencido = data_vencimento < data_atual

    # Caso especial Domingo (weekday 6)
    if data_vencimento.weekday() == 6:
        segunda_seguinte = data_vencimento + timedelta(days=1)
        if not esta_vencido and segunda_seguinte >= data_atual:
            candidato = segunda_seguinte
        else:
            # Se já passou ou está vencido, recua para quarta anterior ao domingo
            candidato = data_vencimento - timedelta(days=4)
    else:
        candidato = data_vencimento
        while candidato.weekday() not in dias_validos:
            candidato -= timedelta(days=1)

    # Se a data candidata for no passado em relação a hoje, ajusta para hoje ou próximo dia válido
    if candidato < data_atual:
        candidato = data_atual
        while candidato.weekday() not in dias_validos:
            candidato += timedelta(days=1)

    return candidato, esta_vencido

def obter_saudacao(hora_atual: int) -> str:
    """
    Determina a saudação apropriada baseada no horário do dia:
    - 05:00 - 11:59: "Bom dia"
    - 12:00 - 17:59: "Boa tarde"
    - 18:00 - 04:59: "Boa noite"
    """
    if 5 <= hora_atual < 12:
        return "Bom dia"
    elif 12 <= hora_atual < 18:
        return "Boa tarde"
    else:
        return "Boa noite"
