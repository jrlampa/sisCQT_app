# tests/test_balanceamento.py
import pytest
import pandas as pd
from backend.engine import ElectricalEngine


def test_sugestao_balanceamento_monofasico():
    """Deve sugerir a distribuição de 3 cargas monofásicas entre as fases A, B e C."""
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
            {
                "PONTO": "P1",
                "MONTANTE": "TRAFO",
                "METROS": 50,
                "CABO": "3x35+54.6mm² Al",
                "MONO": 3,
                "BIFÁSICO": 0,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 0,
                "TIPO_IP": "Sem IP",
                "QTD_IP": 0,
            },
        ]
    )

    config = {
        "cabos": {"3x35+54.6mm² Al": {"coef": 0.2416}},
        "ips": {"Sem IP": 0.0},
        "perfis": {"Massivos": {"cqt_max": 6.0, "sobrecarga_max": 120.0}},
    }
    params = {
        "trafo_kva": 45.0,
        "classe_tipo": "Manual",
        "classe_manual": "A",
        "perfil": "Massivos",
    }

    df_res, _, _ = ElectricalEngine.calcular(df, params, config)

    sugestao = df_res[df_res["PONTO"] == "P1"]["SUGESTAO_BALANCEAMENTO"].iloc[0]

    assert sugestao != "-"
    assert "1M->A" in sugestao
    assert "1M->B" in sugestao
    assert "1M->C" in sugestao


def test_sugestao_balanceamento_bifasico():
    """Deve sugerir a distribuição de cargas bifásicas nos pares de fases."""
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
            {
                "PONTO": "P1",
                "MONTANTE": "TRAFO",
                "METROS": 20,
                "CABO": "3x35+54.6mm² Al",
                "MONO": 0,
                "BIFÁSICO": 2,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 0,
                "TIPO_IP": "Sem IP",
                "QTD_IP": 0,
            },
        ]
    )

    # CORREÇÃO: Adicionada a chave 'sobrecarga_max' para evitar o KeyError
    config = {
        "cabos": {"3x35+54.6mm² Al": {"coef": 0.2416}},
        "ips": {"Sem IP": 0.0},
        "perfis": {"Massivos": {"cqt_max": 6.0, "sobrecarga_max": 120.0}},
    }
    params = {
        "trafo_kva": 45.0,
        "classe_tipo": "Manual",
        "classe_manual": "A",
        "perfil": "Massivos",
    }

    df_res, _, _ = ElectricalEngine.calcular(df, params, config)
    sugestao = df_res[df_res["PONTO"] == "P1"]["SUGESTAO_BALANCEAMENTO"].iloc[0]

    assert "1B->" in sugestao
    # Para 2 cargas bifásicas, esperamos 2 sugestões separadas por vírgula
    assert len(sugestao.split(",")) == 2
