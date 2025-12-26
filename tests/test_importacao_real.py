import os
import pandas as pd
import pytest
from siscqt_utils import importar_planilha_concessionaria


def test_importacao_arquivo_real_existente():
    """
    Teste de Integração (Arquivo Real):
    1. Verifica se o arquivo alvo existe na raiz.
    2. Executa o importador 'importar_planilha_concessionaria'.
    3. Valida se a normalização (siscqt_utils + normalizacao_dados) ocorreu corretamente.
    """
    # Nome do arquivo que JÁ EXISTE na raiz
    nome_arquivo = "CP_A052750522_CQT.xlsx"

    # 1. Validação de Pré-condição (O arquivo deve existir)
    if not os.path.exists(nome_arquivo):
        pytest.fail(
            f"O arquivo '{nome_arquivo}' não foi encontrado na raiz do diretório. Adicione o arquivo antes de rodar o teste."
        )

    # 2. Execução do Importador
    # Chama a função que lê o arquivo, processa abas e chama normalizacao_dados.sanitizar
    df_res, trafo, cabos, classe, erros = importar_planilha_concessionaria(nome_arquivo)

    # 3. Asserções e Validações de Integridade

    # a) Validação Estrutural
    assert not df_res.empty, "Falha Crítica: O DataFrame importado está vazio."
    assert (
        "TRAFO" in df_res["PONTO"].values
    ), "O ponto 'TRAFO' é obrigatório e não foi encontrado/gerado."

    # b) Validação de Colunas Esperadas (Padrão SisCQT)
    colunas_obrigatorias = [
        "PONTO",
        "MONTANTE",
        "METROS",
        "CABO",
        "MONO",
        "BIFÁSICO",
        "TRIFÁSICO",
        "TRI ESPECIAL",
        "CARGA_ESP_KVA",
        "TIPO_IP",
        "QTD_IP",
    ]
    for col in colunas_obrigatorias:
        assert (
            col in df_res.columns
        ), f"Coluna obrigatória '{col}' ausente no DataFrame final."

    # c) Validação de Sanitização de Tipos (Via normalizacao_dados)
    # Garante que números são números e não strings
    assert pd.api.types.is_numeric_dtype(
        df_res["METROS"]
    ), "Coluna METROS não foi convertida para numérico."
    assert pd.api.types.is_numeric_dtype(
        df_res["MONO"]
    ), "Coluna MONO não foi convertida para numérico."

    # d) Validação de Lógica de Negócio Específica (Conversão m/hm)
    # Verifica se algum valor foi convertido corretamente (ex: se na planilha tiver 0,35 e virou 35.0)
    # Pega um ponto de exemplo (ex: ponto '2' se existir)
    if "2" in df_res["PONTO"].values:
        row_2 = df_res[df_res["PONTO"] == "2"].iloc[0]
        # Assumindo que o arquivo real tem o cenário do teste anterior (0,35 hm -> 35.0 m)
        # Se o arquivo for diferente, ajuste ou remova esta asserção específica
        assert (
            row_2["METROS"] > 1.0
        ), f"Alerta: Valor de metros ({row_2['METROS']}) parece muito baixo (possível falha na conversão hm->m)."

    # e) Validação de Metadados Extraídos
    print(f"\n--- Relatório de Importação ---")
    print(f"Trafo Identificado: {trafo} kVA")
    print(f"Classe Identificada: {classe}")
    print(f"Cabos Carregados: {len(cabos)} tipos")
    if erros:
        print("Avisos de Importação:", erros)

    assert (
        trafo > 0
    ), "A potência do trafo não foi lida corretamente (veio 0 ou negativo)."
