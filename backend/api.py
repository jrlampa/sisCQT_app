# backend/api.py
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_CABOS, DEFAULT_IPS, DEFAULT_PERFIS

app = FastAPI(
    title="SisCQT Enterprise API",
    description="Motor de Cálculo de Redes de Distribuição BT",
    version="2.2.0",
)


class CargaInput(BaseModel):
    mono: int = Field(0, ge=0)
    bi: int = Field(0, ge=0)
    tri: int = Field(0, ge=0)
    tri_esp: int = Field(0, ge=0)
    carga_esp_kva: float = Field(0.0, ge=0.0)
    tipo_ip: str = Field("Sem IP")
    qtd_ip: int = Field(0, ge=0)


class NoRede(BaseModel):
    id: str = Field(...)
    pai_id: str = Field(...)
    metros: float = Field(..., ge=0.0)
    cabo: str = Field(...)
    cargas: CargaInput

    @field_validator("id", "pai_id")
    @classmethod
    def uppercase_ids(cls, v: str) -> str:
        return v.strip().upper() if v else ""


class ConfigSimulacao(BaseModel):
    trafo_kva: float = Field(..., gt=0)
    classe_tipo: str = "Automático"
    classe_manual: str = "B"
    fp_ip: float = 1.0
    perfil: str = "Massivos"


class RequestCalculo(BaseModel):
    config: ConfigSimulacao
    rede: List[NoRede]


def _converter_perfis_para_dict():
    perfis_dict = {}
    for p in DEFAULT_PERFIS:
        perfis_dict[p[0]] = {
            "cqt_max": p[1],
            "sobrecarga_max": p[2],
            "metros_max": p[3] if len(p) > 3 else 3000.0,
            "clientes_max": p[4] if len(p) > 4 else 2000,
        }
    return perfis_dict


@app.get("/")
def health_check():
    return {"status": "online", "engine": "SisCQT v2.2", "license": "Enterprise"}


@app.get("/catalogos")
def obter_catalogos():
    return {
        "cabos": list(DEFAULT_CABOS.keys()),
        "ips": list(DEFAULT_IPS.keys()),
        "perfis": [p[0] for p in DEFAULT_PERFIS],
    }


@app.post("/api/v1/calcular")
def calcular_rede(payload: RequestCalculo):
    try:
        dados_lista = []
        for no in payload.rede:
            row = {
                "PONTO": no.id,
                "MONTANTE": no.pai_id,
                "METROS": no.metros,
                "CABO": no.cabo,
                "MONO": no.cargas.mono,
                "BIFÁSICO": no.cargas.bi,
                "TRIFÁSICO": no.cargas.tri,
                "TRI ESPECIAL": no.cargas.tri_esp,
                "CARGA_ESP_KVA": no.cargas.carga_esp_kva,
                "TIPO_IP": no.cargas.tipo_ip,
                "QTD_IP": no.cargas.qtd_ip,
            }
            dados_lista.append(row)

        df_input = pd.DataFrame(dados_lista)
        config_context = {
            "cabos": DEFAULT_CABOS,
            "ips": DEFAULT_IPS,
            "perfis": _converter_perfis_para_dict(),
        }

        params = payload.config.model_dump()
        df_res, kpis, avisos = ElectricalEngine.calcular(
            df_input, params, config_context
        )

        if not kpis:
            raise HTTPException(status_code=400, detail=f"Erro Crítico: {avisos}")
        if df_res.empty:
            raise HTTPException(status_code=400, detail=f"Erro desconhecido: {avisos}")

        # [CRUCIAL] Adicionado SUGESTAO_BALANCEAMENTO na lista de colunas para devolver
        cols_output = [
            "PONTO",
            "CQT_ACUMULADA",
            "CARGA_ACUMULADA_G",
            "CQT_TRECHO",
            "MOMENTO_KVA_M",
            "ICC_KA",
            "SUGESTAO_BALANCEAMENTO",
        ]
        cols_presentes = [c for c in cols_output if c in df_res.columns]
        resultados_nos = df_res[cols_presentes].to_dict(orient="records")

        limite_cqt = kpis.get("limites_usados", {}).get("cqt_max", 6.0)
        limite_oc = kpis.get("limites_usados", {}).get("sobrecarga_max", 100.0)

        # Aprovado apenas se:
        # 1. Não houver avisos de erro (topologia, etc)
        # 2. Max QT estiver dentro do limite do perfil
        # 3. Ocupação do Trafo estiver dentro do limite de sobrecarga
        aprovado = (
            (len([a for a in avisos if "ERRO" in a]) == 0)
            and (kpis["max_cqt"] <= limite_cqt)
            and (kpis["ocupacao"] <= limite_oc)
        )

        return {
            "status_geral": "APROVADO" if aprovado else "REPROVADO",
            "kpis": kpis,
            "avisos_tecnicos": avisos,
            "resultados_detalhados": resultados_nos,
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
