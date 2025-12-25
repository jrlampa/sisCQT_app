import pytest
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_PARAMS
from backend.utils import importar_planilha_concessionaria

FILE_EXCEL = "other\\MC_A052616848_CQT.xlsx"


@pytest.fixture
def dados_reais():
    if not os.path.exists(FILE_EXCEL):
        pytest.skip("Arquivo Excel não encontrado.")

    print(f"\nCarregando e Sanitizando: {FILE_EXCEL}...")
    df_final, trafo_kva, config_cabos, classe_detectada = (
        importar_planilha_concessionaria(FILE_EXCEL)
    )
    df_expected = df_final[["PONTO", "EXPECTED_CQT"]].copy()
    return df_final, df_expected, trafo_kva, config_cabos, classe_detectada


def test_validacao_real(dados_reais):
    df_input, df_expected, trafo_kva, config_cabos, classe_detectada = dados_reais

    params = DEFAULT_PARAMS.copy()
    params["trafo_kva"] = trafo_kva
    params["classe_tipo"] = "Manual"
    params["classe_manual"] = classe_detectada

    config_context = {
        "cabos": config_cabos,
        "ips": {"Sem IP": 0.0},
        "perfis": {"Padrão (Urbano)": {"cqt_max": 10.0, "sobrecarga_max": 200.0}},
    }

    df_res, kpis, avisos = ElectricalEngine.calcular(df_input, params, config_context)

    if "CQT_ACUMULADA" not in df_res.columns:
        pytest.fail(f"Cálculo abortado. Erros: {avisos}")

    df_compare = pd.merge(
        df_res[["PONTO", "CQT_ACUMULADA"]], df_expected, on="PONTO", how="inner"
    )
    df_compare["DIF"] = (df_compare["CQT_ACUMULADA"] - df_compare["EXPECTED_CQT"]).abs()

    perc = ((df_compare["DIF"] < 0.5).sum() / len(df_compare)) * 100
    print(f"\n>> Aderência (Diferença < 0.5%): {perc:.1f}%")
    assert perc > 90.0
