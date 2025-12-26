# frontend/api_client.py
import requests
import pandas as pd
import os
from typing import Tuple, Dict, List
from dotenv import load_dotenv

load_dotenv()

# [CORREÇÃO] Pega URL do ambiente ou usa localhost como fallback
# No Docker, você definirá API_URL="http://backend:8000/api/v1/calcular"
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/calcular")


class APIClient:
    @staticmethod
    def calcular_via_api(
        df: pd.DataFrame, params: dict
    ) -> Tuple[pd.DataFrame, Dict, List[str]]:
        rede_list = []
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
            cargas = {
                "mono": int(row.get("MONO", 0)),
                "bi": int(row.get("BIFÁSICO", 0)),
                "tri": int(row.get("TRIFÁSICO", 0)),
                "tri_esp": int(row.get("TRI ESPECIAL", 0)),
                "carga_esp_kva": float(row.get("CARGA_ESP_KVA", 0)),
                "tipo_ip": str(row.get("TIPO_IP", "Sem IP")),
                "qtd_ip": int(row.get("QTD_IP", 0)),
            }
            rede_list.append(
                {
                    "id": str(row.get("PONTO", "")),
                    "pai_id": str(row.get("MONTANTE", "")),
                    "metros": float(row.get("METROS", 0.0)),
                    "cabo": str(row.get("CABO", "")),
                    "cargas": cargas,
                }
            )

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

        try:
            response = requests.post(
                BASE_URL, json=payload, timeout=15
            )  # Timeout aumentado para segurança
            if response.status_code == 200:
                data = response.json()
                resultados_api = pd.DataFrame(data["resultados_detalhados"])
                kpis = data["kpis"]
                avisos = data["avisos_tecnicos"]
                df_final = df.copy()

                # Merge seguro dos resultados
                df_final["_key"] = df_final["PONTO"].astype(str).str.upper().str.strip()
                resultados_api["_key"] = (
                    resultados_api["PONTO"].astype(str).str.upper().str.strip()
                )
                resultados_api = resultados_api.set_index("_key")

                cols_to_update = [
                    "CQT_ACUMULADA",
                    "CARGA_ACUMULADA_G",
                    "CQT_TRECHO",
                    "ICC_KA",
                    "SUGESTAO_BALANCEAMENTO",
                ]
                for idx, row in df_final.iterrows():
                    key = row["_key"]
                    if key in resultados_api.index:
                        for col in cols_to_update:
                            if col in resultados_api.columns:
                                df_final.at[idx, col] = resultados_api.at[key, col]

                df_final.drop(columns=["_key"], inplace=True)
                return df_final, kpis, avisos
            else:
                try:
                    erro_msg = response.json().get("detail", response.text)
                except:
                    erro_msg = response.text
                return df, {}, [f"Erro da API ({response.status_code}): {erro_msg}"]
        except requests.exceptions.ConnectionError:
            return (
                df,
                {},
                [f"ERRO CONEXÃO: Não foi possível contatar o servidor em {BASE_URL}"],
            )
        except Exception as e:
            return df, {}, [f"Erro Cliente: {str(e)}"]
