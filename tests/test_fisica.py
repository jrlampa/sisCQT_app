import pytest
import pandas as pd
from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_CABOS, DEFAULT_PARAMS


def criar_rede_linear_simples():
    """
    Topologia: TRAFO -> A (100m) -> B (100m)
    Carga: Apenas no ponto B (10 kVA) para simplificar o momento.
    Cabo: Vamos usar um cabo fictício com Coeficiente = 1.0 para facilitar a conta.
    """
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
            # Trecho 1: Trafo -> A
            # Passa toda a carga de B (10kVA) por aqui.
            {
                "PONTO": "A",
                "MONTANTE": "TRAFO",
                "METROS": 100,
                "CABO": "CABO_TESTE",
                "MONO": 0,
                "BIFÁSICO": 0,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 0,
            },
            # Trecho 2: A -> B
            # Carga local de 10kVA
            {
                "PONTO": "B",
                "MONTANTE": "A",
                "METROS": 100,
                "CABO": "CABO_TESTE",
                "MONO": 0,
                "BIFÁSICO": 0,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 10.0,
            },
        ]
    )
    return df


def mock_config():
    """Configuração controlada para o teste"""
    return {
        "cabos": {
            "CABO_TESTE": {
                "coef": 1.0,
                "preco": 0,
            }  # Coeficiente 1.0 facilita a conta mental
        },
        "ips": {"Sem IP": 0.0},
        "perfis": {"Teste": {"cqt_max": 10.0, "sobrecarga_max": 100.0}},
    }


def mock_params():
    return {
        "trafo_kva": 100.0,
        "classe_tipo": "Manual",
        "classe_manual": "A",  # Fator de demanda simples
        "perfil": "Teste",
    }


def test_monotonicidade_tensao():
    """A queda de tensão deve crescer ou manter-se à medida que nos afastamos da fonte."""
    df = criar_rede_linear_simples()
    config = mock_config()
    params = mock_params()

    # Executa o cálculo
    df_res, kpis, _ = ElectricalEngine.calcular(df, params, config)

    # Extrai resultados
    qt_trafo = df_res[df_res["PONTO"] == "TRAFO"]["CQT_ACUMULADA"].iloc[0]
    qt_a = df_res[df_res["PONTO"] == "A"]["CQT_ACUMULADA"].iloc[0]
    qt_b = df_res[df_res["PONTO"] == "B"]["CQT_ACUMULADA"].iloc[0]

    # Validações
    assert qt_trafo == 0.0, "A queda de tensão na fonte deve ser 0"
    assert qt_a > qt_trafo, "A tensão deve cair do Trafo para A"
    assert qt_b > qt_a, "A tensão deve cair de A para B"


def test_calculo_exato_qt():
    """
    Valida a fórmula exata usada no engine.
    Fórmula Engine: QT = Momento * (Metros / 100) * Coef

    Cenário:
    - Ponto B tem carga 10kVA.
    - Fator Demanda (Classe A, 1 cliente) = aprox 1.0 ou tabulado.
    - Vamos forçar CARGA_ESP_KVA que não sofre Fator de Demanda para ser exato.
    """
    df = criar_rede_linear_simples()
    config = mock_config()
    params = mock_params()

    # Forçar Fator de Demanda não influenciar: Usar Carga Especial (fator 1.0)
    # A carga é 10 kVA em B.
    # O momento em A (passagem) é 10 kVA.
    # O momento em B (ponta) é 10 kVA (pontual).

    df_res, kpis, _ = ElectricalEngine.calcular(df, params, config)

    row_a = df_res[df_res["PONTO"] == "A"].iloc[0]
    row_b = df_res[df_res["PONTO"] == "B"].iloc[0]

    # Validar Carga Acumulada
    # Em A, deve passar a carga de B (10) + carga de A (0) = 10
    assert row_a["CARGA_ACUMULADA_G"] == 10.0

    # Validar QT no Trecho A (Trafo -> A)
    # Distancia = 100m. Divisor = 100. => 1.0 unidade de distância (hm)
    # Momento = 10 kVA
    # Coef = 1.0
    # Esperado: 10 * 1.0 * 1.0 = 10.0

    # Nota: O engine usa UNIT_DIVISOR = 100.0 (constantes.py)
    qt_trecho_a = row_a["CQT_TRECHO"]
    assert (
        abs(qt_trecho_a - 10.0) < 0.1
    ), f"Erro no cálculo do Trecho A. Deu {qt_trecho_a}, esperava 10.0"

    # Validar QT Total em B
    # Trecho B (A -> B):
    # Distancia = 100m => 1.0
    # Momento em B = 10 kVA (carga pontual)
    # Coef = 1.0
    # QT Trecho B = 10.0
    # QT Acumulada B = QT(A) + QT(Trecho B) = 10 + 10 = 20
    qt_total_b = row_b["CQT_ACUMULADA"]
    assert (
        abs(qt_total_b - 20.0) < 0.1
    ), f"Erro no cálculo acumulado em B. Deu {qt_total_b}, esperava 20.0"
