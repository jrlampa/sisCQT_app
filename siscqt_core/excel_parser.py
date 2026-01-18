# siscqt_core/excel_parser.py
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from io import BytesIO

# IMPORTAÇÃO DA NORMALIZAÇÃO CENTRALIZADA
from .normalizacao_dados import sanitizar # Adjusted import


def importar_planilha_concessionaria(
    arquivo_excel_bytes: BytesIO,
) -> Tuple[pd.DataFrame, float, Dict, str, List[str]]:
    """
    Importador Blindado com Normalização Centralizada.
    Lê planilhas padrão da concessionária, extrai topologia e cargas,
    e aplica sanitização rigorosa.

    Retorna: (DataFrame_Normalizado, Trafo_kVA, Config_Cabos, Classe, Lista_Erros)
    """
    SHEET_BASE = "BASE DE DADOS"
    SHEET_CQT = "CQT ATUAL"
    SHEET_ATUAL = "ATUAL"

    erros_importacao = []

    # --- 1. CABOS (Extração de Metadados) ---
    config_cabos = {}
    try:
        df_base = pd.read_excel(arquivo_excel_bytes, sheet_name=SHEET_BASE, header=1)
        # Normalização leve apenas para extrair configs (não afeta o DF principal ainda)
        for _, row in df_base.iterrows():
            try:
                nome = str(row.iloc[0]).strip()
                # Conversão segura local apenas para config
                coef_str = str(row.iloc[1]).replace(",", ".")
                coef = float(coef_str) if coef_str and coef_str != "nan" else 0.0

                if nome and nome.lower() != "nan" and coef > 0:
                    config_cabos[nome] = coef
            except:
                continue
    except Exception as e:
        erros_importacao.append(
            f"Aviso: Não foi possível ler a aba '{SHEET_BASE}'. Usando cabos padrão. ({str(e)})"
        )
    
    arquivo_excel_bytes.seek(0) # Reset stream for next read

    # --- 2. TOPOLOGIA (Extração Estrutural) ---
    trafo_kva = 45.0

    # Tentativa de ler KVA do cabeçalho
    try:
        df_head = pd.read_excel(
            arquivo_excel_bytes, sheet_name=SHEET_CQT, header=None, nrows=10
        )
        # Procura célula com valor numérico compatível com trafo na região superior
        val = str(df_head.iloc[2, 5]).replace(",", ".")
        trafo_kva = float(val)
    except:
        pass  # Mantém default 45.0
    
    arquivo_excel_bytes.seek(0) # Reset stream for next read

    # Localização dinâmica do cabeçalho
    header_idx = 7
    try:
        df_raw_scan = pd.read_excel(
            arquivo_excel_bytes, sheet_name=SHEET_CQT, header=None, nrows=20
        )
        # Procura linha que contenha "TRECHO"
        for idx, row in df_raw_scan.iterrows():
            if "TRECHO" in [str(v).upper().strip() for v in row.values]:
                header_idx = idx
                break
    except:
        pass

    arquivo_excel_bytes.seek(0) # Reset stream for next read
    
    try:
        df_cqt = pd.read_excel(arquivo_excel_bytes, sheet_name=SHEET_CQT, header=header_idx)
        # Mapeamento de colunas por índice (Layout Padrão Concessionária)
        # A(0)=PONTO, B(1)=MONTANTE, C(2)=METROS, I(8)=CABO
        df_topology = df_cqt.iloc[:, [0, 1, 2, 8]].copy()
        df_topology.columns = ["PONTO", "MONTANTE", "METROS", "CABO"]

        # Ajuste específico de unidade (m -> hm) antes da sanitização
        # A sanitização trata tipos, mas não regras de negócio como conversão de unidade específica desta planilha
        def _ajustar_unidade_metros(val):
            try:
                s = str(val).replace(",", ".")
                v = float(s)
                # Se vier em hectômetros (ex: 0.4) converte para metros (40.0)
                # Heurística: Trechos < 10m costumam ser HM nesta planilha
                return v * 100.0 if (v < 10.0 and v > 0) else v
            except:
                return 0.0

        df_topology["METROS"] = df_topology["METROS"].apply(_ajustar_unidade_metros)

    except Exception as e:
        return (
            pd.DataFrame(),
            trafo_kva,
            config_cabos,
            "A",
            [f"Erro crítico ao ler topologia: {str(e)}"],
        )
    
    arquivo_excel_bytes.seek(0) # Reset stream for next read

    # --- 3. CARGAS E CLASSE (Extração de Demanda) ---
    try:
        # Leitura para buscar Classe
        df_raw_atual = pd.read_excel(
            arquivo_excel_bytes, sheet_name=SHEET_ATUAL, header=None, nrows=15
        )
        classe_encontrada = "A"

        # Varredura por string de classe
        texto_dump = df_raw_atual.to_string().upper()
        for cls in ["A", "B", "C", "D", "E"]:
            if f"CLASSE {cls}" in texto_dump or f'CLASSE "{cls}"' in texto_dump:
                classe_encontrada = cls
                break

        # Localiza header da tabela de cargas
        header_atual_idx = 0
        for r in range(len(df_raw_atual)):
            vals = [str(v).upper() for v in df_raw_atual.iloc[r].values]
            if "TRECHO" in vals or "PONTO" in vals:
                header_atual_idx = r
                break
        
        arquivo_excel_bytes.seek(0) # Reset stream for next read

        df_atual = pd.read_excel(
            arquivo_excel_bytes, sheet_name=SHEET_ATUAL, header=header_atual_idx
        )

        # Mapeamento de colunas de carga (Índices fixos do modelo)
        # J(9)=PONTO, L(11)=MONO, M(12)=BI, N(13)=TRI, O(14)=TRI_ESP
        # IPs: S(18)..W(22)
        cols_indices = [9, 11, 12, 13, 14, 18, 19, 20, 21, 22]
        data_loads = df_atual.iloc[:, cols_indices].copy()
        data_loads.columns = [
            "PONTO",
            "MONO",
            "BIFÁSICO",
            "TRIFÁSICO",
            "TRI ESPECIAL",
            "IP70",
            "IP80",
            "IP150",
            "IP250",
            "IP400",
        ]

        # Cálculo de Carga Especial (IPs)
        pot_ips = {
            "IP70": 0.07,
            "IP80": 0.08,
            "IP150": 0.15,
            "IP250": 0.25,
            "IP400": 0.40,
        }

        # Função auxiliar temporária para cálculo de IP (antes da sanitização final)
        def _calc_ip(row):
            t = 0.0
            qtd = 0
            for k, v in pot_ips.items():
                try:
                    val = float(str(row.get(k, 0)).replace(",", "."))
                    if val > 0:
                        t += val * v
                        qtd += int(val)
                except:
                    pass
            return pd.Series([t, qtd])

        data_loads[["CARGA_ESP_KVA", "QTD_IP"]] = data_loads.apply(_calc_ip, axis=1)

        # Limpeza pré-merge: Remove cargas sem Ponto definido
        data_loads = data_loads[data_loads["PONTO"].notna()]
        # Normaliza PONTO para string upper para garantir o merge
        data_loads["PONTO"] = (
            data_loads["PONTO"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\.0$", "", regex=True)
        )
        df_topology["PONTO"] = (
            df_topology["PONTO"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\.0$", "", regex=True)
        )

        # Merge (Left Join na Topologia)
        df_merged = pd.merge(
            df_topology,
            data_loads[
                [
                    "PONTO",
                    "MONO",
                    "BIFÁSICO",
                    "TRIFÁSICO",
                    "TRI ESPECIAL",
                    "CARGA_ESP_KVA",
                    "QTD_IP",
                ]
            ],
            on="PONTO",
            how="left",
        )

        # Preenche tipo de IP genérico se houver quantidade
        df_merged["TIPO_IP"] = "Sem IP"
        df_merged.loc[df_merged["QTD_IP"] > 0, "TIPO_IP"] = "IP Misto"

    except Exception as e:
        erros_importacao.append(
            f"Erro ao ler cargas: {str(e)}. Usando apenas topologia."
        )
        df_merged = df_topology.copy()

    # --- 4. CENTRALIZAÇÃO DA NORMALIZAÇÃO (BLINDAGEM FINAL) ---
    # Aqui ocorre a mágica: Tipagem, Preenchimento de Nulos, Validação de TRAFO, Remoção de Lixo
    df_norm, erros_sanitizacao = sanitizar(df_merged)

    erros_finais = erros_importacao + erros_sanitizacao

    return df_norm, trafo_kva, config_cabos, classe_encontrada, erros_finais
