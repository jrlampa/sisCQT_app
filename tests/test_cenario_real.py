# tests/test_cenario_real.py
import pytest
import pandas as pd
import os
from siscqt_engine import ElectricalEngine
from siscqt_constantes import DEFAULT_PARAMS
from siscqt_utils import importar_planilha_concessionaria

FILE_EXCEL = "MC_A052616848_CQT.xlsx"


@pytest.fixture
def dados_reais():
    if not os.path.exists(FILE_EXCEL):
        pytest.skip("Arquivo Excel não encontrado.")

    print(f"\nCarregando e Sanitizando: {FILE_EXCEL}...")

    # Recebemos a classe detectada também!
    df_final, trafo_kva, config_cabos, classe_detectada = (
        importar_planilha_concessionaria(FILE_EXCEL)
    )

    df_expected = df_final[["PONTO", "EXPECTED_CQT"]].copy()

    return df_final, df_expected, trafo_kva, config_cabos, classe_detectada


def test_validacao_real(dados_reais):
    df_input, df_expected, trafo_kva, config_cabos, classe_detectada = dados_reais

    params = DEFAULT_PARAMS.copy()
    params["trafo_kva"] = trafo_kva

    # --- AQUI ESTÁ A CORREÇÃO MÁGICA ---
    # Usamos a classe que veio da planilha (ex: "B")
    params["classe_tipo"] = "Manual"
    params["classe_manual"] = classe_detectada

    print(f" -> Usando Classe de Demanda: {classe_detectada}")

    config_context = {
        "cabos": config_cabos,
        "ips": {"Sem IP": 0.0},
        "perfis": {"Padrão (Urbano)": {"cqt_max": 10.0, "sobrecarga_max": 200.0}},
    }

    df_res, kpis, avisos = ElectricalEngine.calcular(df_input, params, config_context)

    if "CQT_ACUMULADA" not in df_res.columns:
        print("\n⛔ FALHA CRÍTICA NO ENGINE:")
        for a in avisos:
            print(f" -> {a}")
        pytest.fail(f"Cálculo abortado. Erros: {avisos}")

    df_res_clean = df_res[["PONTO", "CQT_ACUMULADA"]].copy()
    df_compare = pd.merge(df_res_clean, df_expected, on="PONTO", how="inner")

    df_compare["DIF"] = (df_compare["CQT_ACUMULADA"] - df_compare["EXPECTED_CQT"]).abs()

    print("\n\n--- RESULTADO FINAL (Sanitizado + Classe Correta) ---")
    print(f"Trafo: {trafo_kva} kVA")

    print("\nTop 5 Divergências:")
    df_show = df_compare[["PONTO", "CQT_ACUMULADA", "EXPECTED_CQT", "DIF"]]
    print(df_show.sort_values(by="DIF", ascending=False).head(5).to_string(index=False))

    erro_medio = df_compare["DIF"].mean()
    pontos_ok = (df_compare["DIF"] < 0.5).sum()
    perc = (pontos_ok / len(df_compare)) * 100

    print(f"\n>> Erro Médio Global: {erro_medio:.4f}%")
    print(f">> Aderência (Diferença < 0.5%): {perc:.1f}%")

    assert perc > 90.0, f"Aderência de {perc:.1f}% é insuficiente."
