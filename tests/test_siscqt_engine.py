# test_siscqt_engine.py
import pytest
import pandas as pd
import numpy as np
from siscqt_engine import ElectricalEngine


# --- FIXTURES (Dados de Teste) ---
@pytest.fixture
def config_mock():
    return {
        "cabos": {
            "3x150+70mm² Al": {"coef": 0.0005, "r": 0.206, "x": 0.08},
            "3x50+50mm² Al": {"coef": 0.0012, "r": 0.641, "x": 0.09},
        },
        "ips": {"IP 150W": {"pot": 150.0}},
        "perfis": {"Padrão": {"cqt_max": 5.0, "sobrecarga_max": 100.0}},
    }


@pytest.fixture
def params_mock():
    return {"trafo_kva": 45.0, "perfil": "Padrão", "classe_tipo": "Automático"}


@pytest.fixture
def df_rede_valida():
    """
    Rede Radial: TRAFO -> A (50m) -> B (50m)
    Cargas: A (10 Mono), B (5 Mono)
    """
    data = {
        "PONTO": ["TRAFO", "A", "B"],
        "MONTANTE": ["", "TRAFO", "A"],
        "METROS": [0.0, 50.0, 50.0],
        "CABO": ["", "3x150+70mm² Al", "3x50+50mm² Al"],
        "MONO": [0, 10, 5],
        "BIFÁSICO": [0, 0, 0],
        "TRIFÁSICO": [0, 0, 0],
        "TRI ESPECIAL": [0, 0, 0],
        "CARGA_ESP_KVA": [0.0, 0.0, 0.0],
        "TIPO_IP": ["Sem IP", "IP 150W", "Sem IP"],
        "QTD_IP": [0, 1, 0],
    }
    return pd.DataFrame(data)


# --- TESTES DE INTEGRIDADE ---


def test_validacao_topologia_sem_ciclos(df_rede_valida):
    ok, erros = ElectricalEngine.validar_topologia(df_rede_valida)
    assert ok is True
    assert len(erros) == 0


def test_deteccao_de_ciclo():
    df_ciclo = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "A", "B"],
            "MONTANTE": ["", "B", "A"],  # Ciclo A <-> B
            "METROS": [0, 10, 10],
        }
    )
    ok, erros = ElectricalEngine.validar_topologia(df_ciclo)
    assert ok is False
    assert any("Ciclo" in e for e in erros)


def test_deteccao_duplicidade():
    df_dup = pd.DataFrame(
        {
            "PONTO": ["TRAFO", "A", "A"],  # Ponto A duplicado
            "MONTANTE": ["", "TRAFO", "TRAFO"],
        }
    )
    ok, erros = ElectricalEngine.validar_topologia(df_dup)
    assert ok is False
    assert any("duplicados" in e for e in erros)


# --- TESTES DE CÁLCULO ELÉTRICO ---


def test_calculo_fluxo_completo(df_rede_valida, params_mock, config_mock):
    """Verifica se o método calcular preenche as colunas críticas e KPIs."""
    df_res, kpis, avisos = ElectricalEngine.calcular(
        df_rede_valida, params_mock, config_mock
    )

    # 1. Verifica geração de colunas
    cols_esperadas = [
        "TOTAL_LOCAL_KVA",
        "CQT_ACUMULADA",
        "ICC_KA",
        "SUGESTAO_BALANCEAMENTO",
    ]
    for col in cols_esperadas:
        assert col in df_res.columns

    # 2. Verifica coerência física (Queda de Tensão)
    # Tensão deve cair conforme se afasta do trafo (B > A)
    idx_a = df_res[df_res["PONTO"] == "A"].index[0]
    idx_b = df_res[df_res["PONTO"] == "B"].index[0]

    assert df_res.at[idx_b, "CQT_ACUMULADA"] > df_res.at[idx_a, "CQT_ACUMULADA"]
    assert df_res.at[idx_b, "CQT_ACUMULADA"] > 0

    # 3. Verifica coerência física (ICC)
    # Curto-circuito deve ser maior perto do trafo (A > B)
    assert df_res.at[idx_a, "ICC_KA"] > df_res.at[idx_b, "ICC_KA"]
    assert df_res.at[idx_a, "ICC_KA"] > 0

    # 4. Verifica Baricentro integrado
    assert "baricentro" in kpis
    assert kpis["baricentro"]["ponto_proximo"] != "N/A"


def test_balanceamento_fases_logica(df_rede_valida):
    """Testa se a função de balanceamento popula a coluna corretamente."""
    # Prepara ambiente
    df_rede_valida["SUGESTAO_BALANCEAMENTO"] = ""
    ordem = ["TRAFO", "A", "B"]
    pmap = {"TRAFO": 0, "A": 1, "B": 2}

    # Executa Balanceamento
    ElectricalEngine.balancear_fases(df_rede_valida, ordem, pmap)

    # Verifica resultado no ponto A (10 clientes Mono)
    res_a = df_rede_valida.loc[
        df_rede_valida["PONTO"] == "A", "SUGESTAO_BALANCEAMENTO"
    ].values[0]

    # Deve conter sugestão de fase (Ex: "Mono: A")
    assert "Mono:" in res_a
    # Como são 10 clientes, deve haver distribuição (uso de pipe '|')
    assert "|" in res_a


def test_baricentro_logica(df_rede_valida):
    """Testa se o baricentro identifica corretamente o centro de massa."""
    # Aumenta drasticamente a carga em A para forçar o baricentro nele
    df_rede_valida.loc[df_rede_valida["PONTO"] == "A", "TOTAL_LOCAL_KVA"] = 1000.0
    df_rede_valida.loc[df_rede_valida["PONTO"] == "B", "TOTAL_LOCAL_KVA"] = 1.0

    res = ElectricalEngine.sugerir_centro_carga(df_rede_valida)

    # O baricentro deve ser o ponto A ou muito próximo (distância ~50m)
    assert res["ponto_proximo"] == "A"
    assert 49.0 < res["distancia_ideal"] < 51.0
