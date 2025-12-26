import pytest
import pandas as pd
from backend.engine import ElectricalEngine


def mock_config_perfis():
    """Configuração de perfis baseada em constantes.py"""
    return {
        "cabos": {"CABO_TESTE": {"coef": 1.0, "preco": 0}},
        "ips": {"Sem IP": 0.0},
        "perfis": {
            "Massivos": {"cqt_max": 6.0, "sobrecarga_max": 120.0},
            "RNT": {"cqt_max": 3.0, "sobrecarga_max": 100.0},
        },
    }


def test_reprovacao_por_queda_tensao():
    """Deve reprovar se a QT acumulada exceder o limite do perfil."""
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
            {
                "PONTO": "A",
                "MONTANTE": "TRAFO",
                "METROS": 700,
                "CABO": "CABO_TESTE",
                "MONO": 0,
                "BI": 0,
                "TRI": 0,
                "TRI_ESP": 0,
                "CARGA_ESP_KVA": 1.0,
            },
        ]
    )

    config = mock_config_perfis()
    params = {
        "trafo_kva": 45.0,
        "classe_tipo": "Manual",
        "classe_manual": "B",
        "perfil": "Massivos",
    }

    df_res, kpis, avisos = ElectricalEngine.calcular(df, params, config)

    # Validação: Agora sem as tags de citação que causaram o erro
    assert kpis["max_cqt"] > 6.0
    assert any("CRÍTICO" in a and "QT" in a for a in avisos)


def test_reprovacao_por_sobrecarga_trafo():
    """Deve reprovar se o carregamento do trafo exceder a sobrecarga máxima."""
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
            {
                "PONTO": "A",
                "MONTANTE": "TRAFO",
                "METROS": 10,
                "CABO": "CABO_TESTE",
                "MONO": 0,
                "BI": 0,
                "TRI": 0,
                "TRI_ESP": 0,
                "CARGA_ESP_KVA": 30.0,
            },
        ]
    )

    config = mock_config_perfis()
    params = {
        "trafo_kva": 15.0,
        "classe_tipo": "Manual",
        "classe_manual": "B",
        "perfil": "RNT",
    }

    df_res, kpis, avisos = ElectricalEngine.calcular(df, params, config)

    # Validação corrigida
    assert kpis["ocupacao"] > 100.0
    assert any("CRÍTICO" in a and "Trafo" in a for a in avisos)


def test_aprovacao_dentro_dos_limites():
    """Deve passar se estiver dentro dos limites."""
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
            {
                "PONTO": "A",
                "MONTANTE": "TRAFO",
                "METROS": 100,
                "CABO": "CABO_TESTE",
                "CARGA_ESP_KVA": 1.0,
            },
        ]
    )
    config = mock_config_perfis()
    params = {
        "trafo_kva": 75.0,
        "classe_tipo": "Manual",
        "classe_manual": "B",
        "perfil": "Massivos",
    }

    _, kpis, avisos = ElectricalEngine.calcular(df, params, config)
    criticos = [a for a in avisos if "CRÍTICO" in a]
    assert len(criticos) == 0
