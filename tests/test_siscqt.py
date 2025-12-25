# tests/test_siscqt.py
import pytest
import pandas as pd
import os
import shutil
from siscqt_engine import ElectricalEngine
from siscqt_utils import SimuladorReadequacao
from siscqt_db import DatabaseManager
from siscqt_constantes import DEFAULT_PARAMS

# --- FIXTURES (DADOS DE EXEMPLO) ---


@pytest.fixture
def config_mock():
    """Cria uma configuração simulada de Cabos e IPs para os testes."""
    # Dicionário SIMPLES (O que o Engine usa para calcular)
    cabos_simple = {"CABO_FINO": 1.0, "CABO_MEDIO": 0.5, "CABO_GROSSO": 0.1}
    # Dicionário COMPLETO (O que vem do Banco de Dados/Interface)
    cabos_full = {
        "CABO_FINO": {"coef": 1.0, "preco": 10},
        "CABO_MEDIO": {"coef": 0.5, "preco": 20},
        "CABO_GROSSO": {"coef": 0.1, "preco": 50},
    }

    ips = {"IP 100W": 100.0, "Sem IP": 0.0}
    perfis = {"Padrão": {"cqt_max": 5.0, "sobrecarga_max": 100.0}}

    return {
        "cabos": cabos_simple,
        "ips": ips,
        "perfis": perfis,
        "cabos_full": cabos_full,
    }


@pytest.fixture
def df_simples():
    """Cria um DataFrame simples: Trafo -> Poste A -> Poste B"""
    data = {
        "PONTO": ["TRAFO", "POSTE_A", "POSTE_B"],
        "MONTANTE": ["", "TRAFO", "POSTE_A"],
        "METROS": [0.0, 100.0, 50.0],
        "CABO": ["", "CABO_MEDIO", "CABO_MEDIO"],
        "MONO": [0, 10, 5],
        "BIFÁSICO": [0, 0, 0],
        "TRIFÁSICO": [0, 0, 0],
        "TRI ESPECIAL": [0, 0, 0],
        "CARGA_ESP_KVA": [0.0, 0.0, 0.0],
        "TIPO_IP": ["Sem IP", "IP 100W", "Sem IP"],
        "QTD_IP": [0, 1, 0],
    }
    return pd.DataFrame(data)


# --- TESTES DE TOPOLOGIA ---


def test_validar_topologia_correta(df_simples):
    ok, erros = ElectricalEngine.validar_topologia(df_simples)
    assert ok is True
    assert len(erros) == 0


def test_validar_topologia_ciclo():
    df_loop = pd.DataFrame({"PONTO": ["TRAFO", "A", "B"], "MONTANTE": ["", "B", "A"]})
    ok, erros = ElectricalEngine.validar_topologia(df_loop)
    assert ok is False
    assert any("Ciclo" in e for e in erros)


def test_validar_ponto_sem_montante():
    df = pd.DataFrame({"PONTO": ["TRAFO", "A"], "MONTANTE": ["", ""]})
    ok, erros = ElectricalEngine.validar_topologia(df)
    assert ok is False
    assert any("sem montante" in e for e in erros)


# --- TESTES DE CÁLCULO ELÉTRICO (ENGINE) ---


def test_calculo_queda_tensao(df_simples, config_mock):
    params = DEFAULT_PARAMS.copy()
    params["trafo_kva"] = 112.5
    params["perfil"] = "Padrão"

    # O Engine precisa do dicionário "achatado" (apenas coeficientes)
    config_context = {
        "cabos": config_mock["cabos"],
        "ips": config_mock["ips"],
        "perfis": config_mock["perfis"],
    }

    df_res, kpis, _ = ElectricalEngine.calcular(df_simples, params, config_context)

    idx_a = df_res[df_res["PONTO"] == "POSTE_A"].index[0]
    idx_b = df_res[df_res["PONTO"] == "POSTE_B"].index[0]

    qt_a = df_res.at[idx_a, "CQT_ACUMULADA"]
    qt_b = df_res.at[idx_b, "CQT_ACUMULADA"]

    assert qt_a > 0
    assert qt_b > qt_a
    assert kpis["demanda"] > 0


def test_fator_demanda():
    fd_1 = ElectricalEngine.get_fator_demanda(1, "A")
    fd_100 = ElectricalEngine.get_fator_demanda(100, "A")
    assert fd_1 > fd_100


# --- TESTES DE SIMULAÇÃO (CORRIGIDO) ---


def test_simulador_recondutoracao(df_simples, config_mock):
    params = DEFAULT_PARAMS.copy()
    params["perfil"] = "Padrão"

    df_ruim = df_simples.copy()
    df_ruim.loc[df_ruim["PONTO"] == "POSTE_B", "METROS"] = 5000

    # [FIX 1] Passamos 'cabos' (dicionário simples com floats) e não 'cabos_full' (dicts complexos)
    # O engine dentro do simulador não sabe lidar com dicionários de preço, apenas floats de coeficiente.
    config_full = {
        "cabos": config_mock["cabos"],
        "ips": config_mock["ips"],
        "perfis": config_mock["perfis"],
    }

    cabos_habilitados = ["CABO_FINO", "CABO_MEDIO", "CABO_GROSSO"]

    resultado = SimuladorReadequacao.executar(
        "Teste", df_ruim, params, config_full, cabos_habilitados
    )

    df_final = resultado["df"]
    cabo_a = df_final[df_final["PONTO"] == "POSTE_A"]["CABO"].values[0]
    cabo_b = df_final[df_final["PONTO"] == "POSTE_B"]["CABO"].values[0]

    assert (cabo_a == "CABO_GROSSO") or (cabo_b == "CABO_GROSSO")
    assert resultado["resolvido"] is True or resultado["iteracoes"] > 0


# --- TESTE DE BANCO DE DADOS (CORRIGIDO) ---


def test_database_crud():
    db_test_file = "test_db.sqlite"

    import siscqt_constantes

    siscqt_constantes.DB_FILE = db_test_file

    DatabaseManager._instance = None
    db = DatabaseManager()

    nome_proj = "PROJETO_TESTE_PYTEST"

    try:
        # [FIX 2] Usar colunas completas para evitar KeyError no DB
        # Criamos manualmente ou usamos o template e preenchemos
        df_save = pd.DataFrame(
            {
                "PONTO": ["TRAFO"],
                "MONTANTE": [""],
                "METROS": [0.0],
                "CABO": [""],
                "MONO": [0],
                "BIFÁSICO": [0],
                "TRIFÁSICO": [0],
                "TRI ESPECIAL": [0],
                "CARGA_ESP_KVA": [0.0],
                "TIPO_IP": ["Sem IP"],
                "QTD_IP": [0],
            }
        )

        cenarios = {"Cen1": df_save}
        params = {"Cen1": DEFAULT_PARAMS}

        ok, msg = db.salvar_projeto(nome_proj, cenarios, params)
        assert ok is True, f"Falha ao salvar: {msg}"

        projs = db.listar_projetos()
        pid = next((p["id"] for p in projs if p["nome"] == nome_proj), None)
        assert pid is not None

        cfgs, trechos, nome_recup = db.carregar_projeto(pid)
        assert nome_recup == nome_proj
        assert len(trechos) == 1

        ok, msg = db.excluir_projeto(pid)
        assert ok is True

    finally:
        if os.path.exists(siscqt_constantes.DB_FILE):
            try:
                os.remove(siscqt_constantes.DB_FILE)
            except:
                pass
