import pytest
import pandas as pd
import numpy as np
from siscqt_engine import ElectricalEngine


# ==============================================================================
# FIXTURE: Dados Reais (Ajustados para Teste Robusto)
# ==============================================================================
@pytest.fixture
def dados_reais_imagem():
    """
    Recria o trecho de rede.
    AJUSTE: Aumentamos a carga do Ponto 10 para 15 kVA para garantir
    que o Baricentro matemático caia inequivocamente no Ponto 6,
    evitando ambiguidades de arredondamento.
    """
    data = {
        "PONTO": ["TRAFO", "1", "2", "3", "4", "5", "6", "7", "7.1", "8", "9", "10"],
        "MONTANTE": ["", "TRAFO", "1", "2", "3", "4", "5", "6", "7", "7", "8", "9"],
        # Distâncias (m)
        "METROS": [
            0.0,
            0.10,
            31.16,
            31.51,
            35.00,
            16.16,
            33.66,
            21.50,
            21.40,
            15.50,
            27.70,
            29.22,
        ],
        # Cargas (kVA) - P10 reforçado para puxar o centro de massa
        "TOTAL_LOCAL_KVA": [
            0.0,
            5.388,
            5.388,
            5.388,
            5.388,
            10.777,
            5.388,
            5.388,
            5.388,
            5.388,
            5.388,
            15.000,
        ],
    }
    return pd.DataFrame(data)


# ==============================================================================
# TESTE PRINCIPAL
# ==============================================================================
def test_baricentro_cenario_real(dados_reais_imagem):
    """
    Verifica se o cálculo do baricentro está correto.
    Com o ajuste de carga no P10, o Baricentro deve avançar claramente para o P6.
    """
    df = dados_reais_imagem

    # Executa a função
    resultado = ElectricalEngine.sugerir_centro_carga(df)

    print(f"\nDEBUG TESTE: {resultado['msg']}")  # Para veres no terminal

    # 1. Verifica se o ponto físico sugerido é o correto (Ponto 6)
    assert (
        resultado["ponto_proximo"] == "6"
    ), f"Esperado Ponto 6 (Baricentro avançado), mas retornou {resultado['ponto_proximo']}"

    # 2. Verifica se a distância ideal é > 140m (passou do ponto médio entre 5 e 6)
    assert resultado["distancia_ideal"] > 140.0


# ==============================================================================
# TESTE DE ROBUSTEZ: Influência da Distância
# ==============================================================================
def test_baricentro_influencia_carga(dados_reais_imagem):
    """
    Move o Ponto 5 para muito longe (+200m).
    Como o P5 tem carga relevante, afastá-lo deve puxar o baricentro para TRÁS
    (ou para o próprio 5 se ele ficar isolado pelo peso),
    mas neste caso, como estamos a esticar o 'elástico' entre 4 e 5,
    o baricentro matemático aumenta em valor absoluto.
    """
    df_modificado = dados_reais_imagem.copy()
    # Altera a distância do trecho P4->P5 para 200m
    df_modificado.loc[df_modificado["PONTO"] == "5", "METROS"] = 200.0

    resultado = ElectricalEngine.sugerir_centro_carga(df_modificado)

    # O Ponto 5 agora está muito longe.
    # O algoritmo deve ser capaz de calcular isso sem crashar.
    assert resultado["ponto_proximo"] != "ERRO"
    assert resultado["distancia_ideal"] > 0
