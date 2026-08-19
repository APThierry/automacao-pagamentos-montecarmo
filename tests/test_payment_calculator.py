from datetime import date
import pytest
from core.payment_calculator import calcular_data_pagamento, obter_mes_extenso, obter_saudacao

def test_vencimento_segunda():
    # Vencimento 17/08/2026 (segunda-feira)
    vencimento = date(2026, 8, 17)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 17)
    assert not vencido

def test_vencimento_terca():
    # Vencimento 18/08/2026 (terça-feira)
    vencimento = date(2026, 8, 18)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 18)
    assert not vencido

def test_vencimento_quarta():
    # Vencimento 19/08/2026 (quarta-feira)
    vencimento = date(2026, 8, 19)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 19)
    assert not vencido

def test_vencimento_quinta():
    # Vencimento 20/08/2026 (quinta-feira) -> Quarta-feira anterior (19/08)
    vencimento = date(2026, 8, 20)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 19)
    assert not vencido

def test_vencimento_sexta():
    # Vencimento 21/08/2026 (sexta-feira) -> Quarta-feira anterior (19/08)
    vencimento = date(2026, 8, 21)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 19)
    assert not vencido

def test_vencimento_sabado():
    # Vencimento 15/08/2026 (sábado) -> Quarta-feira anterior (12/08)
    vencimento = date(2026, 8, 15)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 12)
    assert not vencido

def test_vencimento_domingo_nao_vencido():
    # Vencimento 16/08/2026 (domingo) -> Segunda-feira seguinte (17/08/2026)
    vencimento = date(2026, 8, 16)
    hoje = date(2026, 8, 12)
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert pagamento == date(2026, 8, 17)
    assert not vencido

def test_vencimento_no_passado():
    # Vencimento no passado (ex: 01/08/2026, hoje e 19/08/2026)
    vencimento = date(2026, 8, 1)
    hoje = date(2026, 8, 19) # quarta-feira
    pagamento, vencido = calcular_data_pagamento(vencimento, hoje)
    assert vencido is True
    # Ajusta para a data atual ou próxima válida (19/08/2026 e quarta-feira)
    assert pagamento == date(2026, 8, 19)

def test_obter_mes_extenso():
    assert obter_mes_extenso(date(2026, 8, 15)) == "agosto"
    assert obter_mes_extenso(date(2026, 9, 1)) == "setembro"

def test_obter_saudacao():
    assert obter_saudacao(8) == "Bom dia"
    assert obter_saudacao(14) == "Boa tarde"
    assert obter_saudacao(20) == "Boa noite"
    assert obter_saudacao(3) == "Boa noite"
