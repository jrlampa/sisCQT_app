# test_importacao.py
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from normalizacao_dados import sanitizar
from siscqt_utils import importar_planilha_concessionaria

# --- TESTES DE NORMALIZAÇÃO CENTRALIZADA ---


def test_sanitizar_estrutura_basica():
    """Testa se colunas faltantes são criadas e tipos corrigidos."""
    df_in = pd.DataFrame(
        {
            "PONTO": ["A", "B"],
            "METROS": ["10,5", 20],  # Vírgula e Inteiro misturados
            "MONO": [1, "NaN"],  # NaN como string
        }
    )

    df_out, erros = sanitizar(df_in)

    # Validações
    assert "MONTANTE" in df_out.columns  # Coluna criada
    assert df_out["METROS"].dtype == float
    assert df_out.at[0, "METROS"] == 10.5
    assert df_out.at[1, "MONO"] == 0  # NaN tratado
    assert "TRAFO" not in df_out["PONTO"].values  # Não tinha trafo na entrada
    assert any("TRAFO" in e for e in erros)  # Erro reportado


def test_sanitizar_trafo_e_ids():
    """Testa normalização de IDs e ponto TRAFO."""
    df_in = pd.DataFrame(
        {
            "PONTO": ["trafo", "a.0 ", "b"],  # Lowercase, sufixo float, espaço
            "MONTANTE": ["", "TRAFO", "A.0"],
            "METROS": [100, 10, 10],  # Trafo com metros incorretos
        }
    )

    df_out, _ = sanitizar(df_in)

    # Valida TRAFO
    idx_trafo = df_out[df_out["PONTO"] == "TRAFO"].index[0]
    assert df_out.at[idx_trafo, "METROS"] == 0.0  # Forçado a 0

    # Valida IDs
    assert "A" in df_out["PONTO"].values
    assert "B" in df_out["PONTO"].values
    assert "TRAFO" in df_out["MONTANTE"].values


# --- TESTES DE IMPORTAÇÃO (MOCK) ---


@pytest.fixture
def mock_excel_data():
    """Simula dados brutos lidos do Excel."""
    # Sheet CQT (Topologia)
    df_cqt = pd.DataFrame(
        [
            ["TRAFO", "", 0, "", "", "", "", "", "Cabo Trafo", "", "", 0],
            ["1", "TRAFO", 0.5, "", "", "", "", "", "3x35", "", "", 0],  # 0.5 HM = 50m
            ["2", "1", 40, "", "", "", "", "", "3x35", "", "", 0],
        ]
    )

    # Sheet ATUAL (Cargas)
    # Cols relevantes mapeadas: J(9)=PONTO, L(11)=MONO...
    raw_data = [[""] * 30 for _ in range(5)]
    # Linha 0 (Header simulado)
    raw_data[0][9] = "PONTO"
    raw_data[0][11] = "MONO"
    raw_data[0][12] = "BI"

    # Linha 1 (Dado 1)
    raw_data[1][9] = "1"
    raw_data[1][11] = 10

    # Linha 2 (Dado 2)
    raw_data[2][9] = "2"
    raw_data[2][12] = 5

    df_atual = pd.DataFrame(raw_data)

    return df_cqt, df_atual


@patch("pandas.read_excel")
def test_importador_fluxo_completo(mock_read_excel, mock_excel_data):
    """
    Testa se o importador chama o pandas, processa e sanitiza o resultado.
    """
    df_cqt, df_atual = mock_excel_data

    # Configura o mock para retornar diferentes DFs dependendo da sheet_name
    def side_effect(io, sheet_name, **kwargs):
        if sheet_name == "CQT ATUAL":
            return df_cqt
        if sheet_name == "ATUAL":
            return df_atual
        return pd.DataFrame()  # Default empty

    mock_read_excel.side_effect = side_effect

    # Executa
    df_res, trafo, _, cls, erros = importar_planilha_concessionaria("dummy.xlsx")

    # Validações
    assert not df_res.empty
    assert (
        "TOTAL_LOCAL_KVA" not in df_res.columns
    )  # Colunas calculadas não devem vir daqui
    assert "CARGA_ESP_KVA" in df_res.columns

    # Verifica conversão de HM para M no ponto 1 (0.5 -> 50.0)
    # Nota: A sanitização converte PONTO '1' para string '1'
    row_1 = df_res[df_res["PONTO"] == "1"].iloc[0]
    assert row_1["METROS"] == 50.0

    # Verifica merge de cargas
    assert row_1["MONO"] == 10

    # Verifica TRAFO
    assert "TRAFO" in df_res["PONTO"].values
