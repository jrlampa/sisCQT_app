# tests/test_importacao.py
import pytest
import pandas as pd
import os
from backend.utils import importar_planilha_concessionaria

TEMP_FILE = "temp_teste_caos.xlsx"


def criar_excel_caotico(offset_linhas=0, nomes_sujos=False, colunas_fora_ordem=False):
    data = []
    # Lixo inicial
    for i in range(offset_linhas):
        data.append(["Relatório Geral", "Emitido em:", "2024", "", ""])

    if nomes_sujos:
        headers = ["  PONTO  ", " MONTANTE", "METROS", " CABO ", "CQT_ESP"]
    else:
        headers = ["PONTO", "MONTANTE", "METROS", "CABO", "EXPECTED_CQT"]

    if colunas_fora_ordem:
        headers = [headers[0], headers[1], headers[3], headers[2], headers[4]]

    data.append(headers)

    # Dados de teste
    if colunas_fora_ordem:
        # B1 metros 10, B2 metros 20
        row1 = ["B1", "TRAFO", "3x35", "10", "0.5"]
        row2 = ["B2", "B1", "3x35+50 ", "20", "1.0"]
    else:
        row1 = ["B1", "TRAFO", "10", "3x35", "0.5"]
        row2 = ["B2", "B1", "20", "3x35+50 ", "1.0"]

    data.append(row1)
    data.append(row2)

    df = pd.DataFrame(data)
    with pd.ExcelWriter(TEMP_FILE) as writer:
        df.to_excel(writer, sheet_name="CQT ATUAL", index=False, header=False)
    return TEMP_FILE


def teardown_module(module):
    if os.path.exists(TEMP_FILE):
        try:
            os.remove(TEMP_FILE)
        except PermissionError:
            pass  # Ignora se o Windows ainda estiver bloqueando, mas o código novo resolve isso


def test_importacao_cabecalho_deslocado():
    """Teste 1.1: O cabeçalho está deslocado."""
    arquivo = criar_excel_caotico(offset_linhas=10)
    df, _, _, _ = importar_planilha_concessionaria(arquivo)

    assert not df.empty

    # CORREÇÃO: Busca pelo PONTO específico, não pelo índice 0 (que é TRAFO)
    linha_b1 = df[df["PONTO"] == "B1"]
    assert not linha_b1.empty, "Ponto B1 não encontrado"
    assert float(linha_b1.iloc[0]["METROS"]) == 10.0


def test_importacao_colunas_sujas():
    """Teste 1.2: Colunas com espaços e nomes sujos."""
    arquivo = criar_excel_caotico(offset_linhas=2, nomes_sujos=True)
    df, _, _, _ = importar_planilha_concessionaria(arquivo)

    assert "PONTO" in df.columns
    assert "CABO" in df.columns

    # CORREÇÃO: Busca pelo PONTO B2 para validar a limpeza do cabo
    linha_b2 = df[df["PONTO"] == "B2"]
    assert not linha_b2.empty, "Ponto B2 não encontrado"
    # O valor original era "3x35+50 " (com espaço), esperamos "3x35+50" (sem espaço)
    assert linha_b2.iloc[0]["CABO"] == "3x35+50"


def test_importacao_ordem_colunas_diferente():
    """Teste 1.3: Colunas fora de ordem."""
    arquivo = criar_excel_caotico(offset_linhas=1, colunas_fora_ordem=True)
    df, _, _, _ = importar_planilha_concessionaria(arquivo)

    linha_b1 = df[df["PONTO"] == "B1"].iloc[0]
    assert float(linha_b1["METROS"]) == 10.0
    assert "3x35" in str(linha_b1["CABO"])
