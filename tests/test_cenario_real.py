import pytest
import pandas as pd
import os
from pathlib import Path

# Configuração de caminhos robusta
BASE_DIR = Path(__file__).resolve().parent.parent
FILE_EXCEL = BASE_DIR / "other" / "MC_A052616848_CQT.xlsx"

# Se o caminho acima falhar (ex: rodando de outra pasta), tenta a raiz
if not FILE_EXCEL.exists():
    FILE_EXCEL = Path("MC_A052616848_CQT.xlsx")

from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_PARAMS
from backend.utils import importar_planilha_concessionaria


@pytest.fixture
def dados_reais():
    if not os.path.exists(FILE_EXCEL):
        pytest.skip(f"Arquivo não encontrado em: {FILE_EXCEL}")

    # IMPORTANTE: A função importar_planilha_concessionaria precisa
    # ter o alias "EXPECTED_CQT" adicionado no backend/utils.py
    # para não descartar essa coluna!

    df_final, trafo_kva, config_cabos, classe_detectada = (
        importar_planilha_concessionaria(FILE_EXCEL)
    )

    # Verificação amigável para o desenvolvedor
    if "EXPECTED_CQT" not in df_final.columns:
        pytest.fail(
            f"A coluna 'EXPECTED_CQT' não foi encontrada. "
            f"Colunas disponíveis: {list(df_final.columns)}. "
            "Verifique se adicionou o alias no 'known_aliases' do backend/utils.py"
        )

    df_expected = df_final[["PONTO", "EXPECTED_CQT"]].copy()
    return df_final, df_expected, trafo_kva, config_cabos, classe_detectada


def test_validacao_real(dados_reais):
    df_input, df_expected, trafo_kva, config_cabos, classe_detectada = dados_reais

    params = DEFAULT_PARAMS.copy()
    params["trafo_kva"] = trafo_kva
    params["classe_tipo"] = "Manual"
    params["classe_manual"] = classe_detectada
    params["perfil"] = "Padrão (Urbano)"

    config_context = {
        "cabos": config_cabos,
        "ips": {"Sem IP": 0.0},
        "perfis": {"Padrão (Urbano)": {"cqt_max": 10.0, "sobrecarga_max": 200.0}},
    }

    df_res, kpis, avisos = ElectricalEngine.calcular(df_input, params, config_context)

    # Verifica se o cálculo não retornou erro crítico
    assert "CQT_ACUMULADA" in df_res.columns, f"Erro no motor: {avisos}"

    # Merge para comparar apenas pontos que existem em ambos
    df_compare = pd.merge(
        df_res[["PONTO", "CQT_ACUMULADA"]], df_expected, on="PONTO", how="inner"
    )

    # Cálculo da Aderência
    df_compare["DIF"] = (df_compare["CQT_ACUMULADA"] - df_compare["EXPECTED_CQT"]).abs()

    # Tolerância de 0.5% (comum em engenharia devido a arredondamentos)
    acertos = (df_compare["DIF"] < 0.5).sum()
    total = len(df_compare)
    perc = (acertos / total) * 100 if total > 0 else 0

    print(f"\n>> Comparação de {total} pontos.")
    print(f">> Aderência (Erro < 0.5%): {perc:.1f}%")

    assert perc > 90.0, f"Aderência muito baixa: {perc:.1f}%"
