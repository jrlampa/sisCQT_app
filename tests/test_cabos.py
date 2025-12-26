import pytest
from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_CABOS


def test_busca_cabo_exato():
    """O básico: nome igual ao catálogo deve funcionar."""
    nome_oficial = list(DEFAULT_CABOS.keys())[0]  # Pega um cabo real
    coef = ElectricalEngine._buscar_cabo_flexivel(nome_oficial, DEFAULT_CABOS)
    assert coef > 0, "Não encontrou cabo com nome exato!"


def test_busca_cabo_sujo_csv():
    """O cenário real: Inputs do teu CSV vs Chaves do Sistema."""

    # Dicionário simulando o catalogo do constantes.py
    # Chaves "limpas" que esperamos ter no sistema
    catalogo = {
        "3x35+54.6mm² Al": 0.5,
        "3x50+50mm² Al": 0.4,
        "2#16(25)mm² Al": 0.8,
        "Multiplex 1#35 (35) CA": 0.3,
    }

    scenarios = [
        # (Input do CSV, Chave esperada no Catálogo)
        ("3x35+54,6 - Al", "3x35+54.6mm² Al"),  # Virgula vs Ponto, hífens
        ("3x50+1x50 - Al", "3x50+50mm² Al"),  # "1x" extra no neutro
        ("2# 16(25)", "2#16(25)mm² Al"),  # Espaços e falta de unidade
        ("CABO 3x35+54.6", "3x35+54.6mm² Al"),  # Prefixo lixo
        ("3 x 35 + 54.6", "3x35+54.6mm² Al"),  # Espaços excessivos
    ]

    for input_csv, expected_key in scenarios:
        coef = ElectricalEngine._buscar_cabo_flexivel(input_csv, catalogo)
        assert (
            coef == catalogo[expected_key]
        ), f"Falhou ao mapear '{input_csv}' para '{expected_key}'"


def test_cabo_inexistente():
    """Deve retornar 0.0 sem estourar erro."""
    coef = ElectricalEngine._buscar_cabo_flexivel("Cabo De Aço Inox", DEFAULT_CABOS)
    assert coef == 0.0
