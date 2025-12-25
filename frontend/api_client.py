# siscqt_api_client.py
import requests
import pandas as pd
import json
from typing import Tuple, Dict, List

# Endereço da API (local por enquanto)
API_URL = "http://127.0.0.1:8000/api/v1/calcular"


class APIClient:
    @staticmethod
    def calcular_via_api(
        df: pd.DataFrame, params: dict
    ) -> Tuple[pd.DataFrame, Dict, List[str]]:
        """
        Envia os dados para o Backend FastAPI e reconstrói o DataFrame de resposta.
        """
        # 1. Converter DataFrame para o formato JSON exigido pela API
        rede_list = []

        # Garante que colunas numéricas não sejam NaN antes de converter
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
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        for _, row in df.iterrows():
            # Monta o objeto de Cargas
            cargas = {
                "mono": int(row.get("MONO", 0)),
                "bi": int(row.get("BIFÁSICO", 0)),
                "tri": int(row.get("TRIFÁSICO", 0)),
                "tri_esp": int(row.get("TRI ESPECIAL", 0)),
                "carga_esp_kva": float(row.get("CARGA_ESP_KVA", 0)),
                "tipo_ip": str(row.get("TIPO_IP", "Sem IP")),
                "qtd_ip": int(row.get("QTD_IP", 0)),
            }

            # Monta o nó da rede
            no = {
                "id": str(row.get("PONTO", "")),
                "pai_id": str(row.get("MONTANTE", "")),
                "metros": float(row.get("METROS", 0.0)),
                "cabo": str(row.get("CABO", "")),
                "cargas": cargas,
            }
            rede_list.append(no)

        # Monta o Payload completo
        payload = {
            "config": {
                "trafo_kva": float(params.get("trafo_kva", 45)),
                "classe_tipo": str(params.get("classe_tipo", "Automático")),
                "classe_manual": str(params.get("classe_manual", "B")),
                "fp_ip": float(params.get("fp_ip", 1.0)),
                "perfil": str(params.get("perfil", "Massivos")),
            },
            "rede": rede_list,
        }

        # 2. Enviar Requisição POST
        try:
            # Timeout curto para teste local (2s), pode aumentar em produção
            response = requests.post(API_URL, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # 3. Processar Sucesso
                # A API retorna apenas os resultados calculados. Precisamos mesclar com o original.
                resultados_api = pd.DataFrame(data["resultados_detalhados"])
                kpis = data["kpis"]
                avisos = data["avisos_tecnicos"]

                # Merge inteligente: Pega o DF original e atualiza as colunas de resultado
                df_final = df.copy()

                # Prepara chaves para merge (Case Insensitive)
                df_final["_key"] = df_final["PONTO"].astype(str).str.upper().str.strip()
                resultados_api["_key"] = (
                    resultados_api["PONTO"].astype(str).str.upper().str.strip()
                )
                resultados_api = resultados_api.set_index("_key")

                # Colunas que queremos trazer da API
                cols_to_update = [
                    "CQT_ACUMULADA",
                    "CARGA_ACUMULADA_G",
                    "CQT_TRECHO",
                    "ICC_KA",
                ]

                for idx, row in df_final.iterrows():
                    key = row["_key"]
                    if key in resultados_api.index:
                        for col in cols_to_update:
                            if col in resultados_api.columns:
                                df_final.at[idx, col] = resultados_api.at[key, col]

                # Limpa coluna auxiliar
                df_final.drop(columns=["_key"], inplace=True)

                return df_final, kpis, avisos

            else:
                # Erro da API (400, 500, etc)
                try:
                    erro_msg = response.json().get("detail", response.text)
                except:
                    erro_msg = response.text
                return df, {}, [f"Erro da API ({response.status_code}): {erro_msg}"]

        except requests.exceptions.ConnectionError:
            return (
                df,
                {},
                [
                    "ERRO DE CONEXÃO: O servidor API não está rodando ou está inacessível."
                ],
            )
        except Exception as e:
            return df, {}, [f"Erro Inesperado no Cliente: {str(e)}"]
