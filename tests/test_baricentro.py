import pytest
import pandas as pd
from siscqt_engine import ElectricalEngine


# ==============================================================================
# CENÁRIO 1: Rede Linear Simples
# ==============================================================================
def test_baricentro_linear_carga_pesada_perto():
    """
    Cenário:
    TRAFO --(100m)--> P1 (50 kVA) --(100m)--> P2 (10 kVA)

    Matemática:
    - P1: Dist=100m, Carga=50. Momento = 5000.
    - P2: Dist=200m, Carga=10. Momento = 2000.
    - Total Momento = 7000. Total Carga = 60.
    - Distância Ideal = 7000 / 60 = 116.66m

    Vencedor:
    - P1 está a 100m (Delta = 16.6m)
    - P2 está a 200m (Delta = 83.3m)
    -> O Baricentro deve ser P1.
    """
    df = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "P1", "P2"],
            "MONTANTE": ["", "TRAFO", "P1"],
            "METROS": [0, 100, 100],
            "TOTAL_LOCAL_KVA": [0, 50, 10],
        }
    )

    resultado = ElectricalEngine.sugerir_centro_carga(df)

    assert resultado["ponto_proximo"] == "P1"
    assert 116.0 < resultado["distancia_ideal"] < 117.0


# ==============================================================================
# CENÁRIO 2: Rede Linear com Carga na Ponta
# ==============================================================================
def test_baricentro_linear_carga_pesada_longe():
    """
    Cenário:
    TRAFO --(100m)--> P1 (10 kVA) --(100m)--> P2 (50 kVA)

    Matemática:
    - P1: Dist=100m, Carga=10. Momento = 1000.
    - P2: Dist=200m, Carga=50. Momento = 10000.
    - Total Momento = 11000. Total Carga = 60.
    - Distância Ideal = 11000 / 60 = 183.33m

    Vencedor:
    - P1 (100m) -> Delta 83.3
    - P2 (200m) -> Delta 16.6
    -> O Baricentro deve ser P2.
    """
    df = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "P1", "P2"],
            "MONTANTE": ["", "TRAFO", "P1"],
            "METROS": [0, 100, 100],
            "TOTAL_LOCAL_KVA": [0, 10, 50],
        }
    )

    resultado = ElectricalEngine.sugerir_centro_carga(df)
    assert resultado["ponto_proximo"] == "P2"


# ==============================================================================
# CENÁRIO 3: Rede Ramificada (Teste de Recursão de Distância)
# ==============================================================================
def test_baricentro_ramificado():
    """
    Cenário em 'T':
    TRAFO --(10m)--> P1 (Sem Carga) --(100m)--> P2 (10 kVA) [Longe e Leve]
                       |
                       +--(10m)--> P3 (100 kVA) [Perto e Pesado]

    Distâncias Reais:
    - P1: 10m
    - P2: 10+100 = 110m
    - P3: 10+10 = 20m

    Matemática:
    - Momento P2: 10 * 110 = 1100
    - Momento P3: 100 * 20 = 2000
    - Total: 3100 / 110 = 28.18m (Distância Ideal)

    Vencedor:
    - P1 (10m) -> Delta 18.18
    - P3 (20m) -> Delta 8.18  <-- VENCEDOR
    - P2 (110m) -> Delta 81.82
    """
    df = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "P1", "P2", "P3"],
            "MONTANTE": ["", "TRAFO", "P1", "P1"],
            "METROS": [0, 10, 100, 10],
            "TOTAL_LOCAL_KVA": [0, 0, 10, 100],
        }
    )

    resultado = ElectricalEngine.sugerir_centro_carga(df)

    assert resultado["ponto_proximo"] == "P3"
    assert 28.0 < resultado["distancia_ideal"] < 28.5


# ==============================================================================
# CENÁRIO 4: Robustez (Dados Sujos e Strings)
# ==============================================================================
def test_baricentro_dados_sujos():
    """
    Simula dados vindos do CSV com vírgulas e strings.
    """
    df = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "P1"],
            "MONTANTE": ["", "TRAFO"],
            "METROS": [0, "100,5"],  # Vírgula
            "TOTAL_LOCAL_KVA": [0, "10,0"],  # String com vírgula
        }
    )

    resultado = ElectricalEngine.sugerir_centro_carga(df)

    # Se funcionar, deve calcular dist 100.5
    assert resultado["ponto_proximo"] == "P1"
    assert abs(resultado["distancia_ideal"] - 100.5) < 0.1


# ==============================================================================
# CENÁRIO 5: Casos de Borda (Sem Carga ou Sem Coluna)
# ==============================================================================
def test_baricentro_sem_carga():
    df = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "P1"],
            "MONTANTE": ["", "TRAFO"],
            "METROS": [0, 100],
            "TOTAL_LOCAL_KVA": [0, 0],  # Ninguém tem carga
        }
    )
    resultado = ElectricalEngine.sugerir_centro_carga(df)
    assert resultado["distancia_ideal"] == 0
    assert resultado["ponto_proximo"] == "TRAFO"


def test_baricentro_coluna_faltante():
    df = pd.DataFrame(
        {
            "PONTO": ["TRAFO"],
            "MONTANTE": [""],
            "METROS": [0],
            # Falta TOTAL_LOCAL_KVA
        }
    )
    resultado = ElectricalEngine.sugerir_centro_carga(df)
    assert resultado["ponto_proximo"] == "N/A"
    assert "Erro" in resultado["msg"] or "não encontrada" in resultado["msg"]
