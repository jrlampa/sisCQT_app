# normalizacao_dados.py
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple


def sanitizar(
    df_input: pd.DataFrame,
    valid_cabos: Optional[List[str]] = None,
    valid_ips: Optional[List[str]] = None,
    limites: Optional[Dict[str, float]] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Padroniza tipos de dados, preenche valores nulos e valida consistência básica
    dos dados de entrada para o sistema SisCQT.

    Esta função é a **FONTE ÚNICA DE NORMALIZAÇÃO** do sistema.

    Ações realizadas:
    1. Garante existência de todas as colunas do schema padrão.
    2. Converte IDs (PONTO/MONTANTE) para string, maiúsculas e remove sufixos '.0'.
    3. Normaliza numéricos (vírgula -> ponto, preenche NaNs com 0).
    4. Valida a existência e formatação do ponto 'TRAFO'.
    5. Remove linhas vazias/inválidas.

    Args:
        df_input (pd.DataFrame): DataFrame bruto contendo os dados da rede.
        valid_cabos (List[str], opcional): Lista de cabos cadastrados (para validação futura).
        valid_ips (List[str], opcional): Lista de tipos de IP cadastrados.
        limites (Dict[str, float], opcional): Limites operacionais.

    Returns:
        Tuple[pd.DataFrame, List[str]]:
            1. DataFrame normalizado, tipado e limpo.
            2. Lista de mensagens de erro ou alertas encontrados.
    """
    # Trabalha em uma cópia para não alterar o objeto original
    df = df_input.copy()
    erros: List[str] = []

    # 1. Definição de Schema e Valores Default
    cols_default = {
        "PONTO": "",
        "MONTANTE": "",
        "CABO": "",
        "TIPO_IP": "Sem IP",
        "METROS": 0.0,
        "MONO": 0,
        "BIFÁSICO": 0,
        "TRIFÁSICO": 0,
        "TRI ESPECIAL": 0,
        "CARGA_ESP_KVA": 0.0,
        "QTD_IP": 0,
    }

    # 2. Garantia de Existência de Colunas
    for col, default_val in cols_default.items():
        if col not in df.columns:
            df[col] = default_val

    # 3. Sanitização de Colunas de Texto (String)
    # IDs devem ser UPPERCASE, sem espaços e sem sufixo decimal de importação (.0)
    cols_str = ["PONTO", "MONTANTE", "CABO", "TIPO_IP"]
    for c in cols_str:
        # Garante string e remove espaços
        df[c] = df[c].fillna("").astype(str).str.strip()

        # Converte "nan", "none", "null" literais para vazio
        df.loc[df[c].str.lower().isin(["nan", "none", "null"]), c] = ""

        # Normalização específica para IDs (PONTO/MONTANTE)
        if c in ["PONTO", "MONTANTE"]:
            df[c] = df[c].str.upper().str.replace(r"\.0$", "", regex=True)

    # 4. Sanitização de Colunas Numéricas
    cols_num = [
        "METROS",
        "MONO",
        "BIFÁSICO",
        "TRIFÁSICO",
        "TRI ESPECIAL",
        "CARGA_ESP_KVA",
        "QTD_IP",
    ]

    for c in cols_num:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(",", ".", regex=False)

        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        if (df[c] < 0).any():
            erros.append(
                f"Coluna '{c}' contém valores negativos (mantidos, mas verifique)."
            )

    # Tipagem fina para contagens (Inteiros)
    cols_int = ["MONO", "BIFÁSICO", "TRIFÁSICO", "TRI ESPECIAL", "QTD_IP"]
    for c in cols_int:
        df[c] = df[c].astype(int)

    # 5. Normalização do Ponto de Referência (TRAFO)
    trafo_mask = df["PONTO"] == "TRAFO"

    if not trafo_mask.any():
        erros.append("Ponto de origem 'TRAFO' não encontrado na coluna PONTO.")
    else:
        # Garante atributos raiz do Trafo (Sem montante, Distância 0)
        df.loc[trafo_mask, ["MONTANTE", "METROS", "CABO"]] = ["", 0.0, ""]

    # 6. Remoção de Linhas Vazias/Lixo (Onde PONTO é vazio após limpeza)
    df = df[df["PONTO"] != ""].reset_index(drop=True)

    if df.empty:
        erros.append("A tabela de dados está vazia após a limpeza.")

    return df, erros
