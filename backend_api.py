# backend_api.py
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

# Importa o Motor Validado
from siscqt_engine import ElectricalEngine
from siscqt_constantes import DEFAULT_CABOS, DEFAULT_IPS, DEFAULT_PERFIS

# --- CONFIGURAÇÃO DA API ---
app = FastAPI(
    title="SisCQT Enterprise API",
    description="Motor de Cálculo de Redes de Distribuição BT (Norma ENEL/NBR)",
    version="2.1.0",
)

# --- 1. MODELOS DE DADOS (Pydantic V2) ---


class CargaInput(BaseModel):
    mono: int = Field(0, ge=0, description="Qtd consumidores monofásicos")
    bi: int = Field(0, ge=0, description="Qtd consumidores bifásicos")
    tri: int = Field(0, ge=0, description="Qtd consumidores trifásicos")
    tri_esp: int = Field(0, ge=0, description="Qtd trifásicos especiais")
    carga_esp_kva: float = Field(0.0, ge=0.0, description="Carga dedicada (kVA)")
    tipo_ip: str = Field("Sem IP", description="Tipo de Iluminação Pública")
    qtd_ip: int = Field(0, ge=0)


class NoRede(BaseModel):
    id: str = Field(..., description="Identificador único do poste/nó")
    pai_id: str = Field(..., description="ID do nó montante (vazio se for Trafo)")
    metros: float = Field(..., ge=0.0, description="Distância do trecho em metros")
    cabo: str = Field(..., description="Tipo de cabo do trecho")
    cargas: CargaInput

    @field_validator("id", "pai_id")
    @classmethod
    def uppercase_ids(cls, v: str) -> str:
        return v.strip().upper() if v else ""


class ConfigSimulacao(BaseModel):
    trafo_kva: float = Field(..., gt=0, description="Potência do Transformador")
    classe_tipo: str = "Automático"
    classe_manual: str = "B"
    fp_ip: float = 1.0
    perfil: str = "Massivos"  # Ajustado para bater com constantes


class RequestCalculo(BaseModel):
    config: ConfigSimulacao
    rede: List[NoRede]


# --- 2. HELPERS ---
def _converter_perfis_para_dict():
    """Converte a lista de tuplas do constantes.py para dicionário."""
    perfis_dict = {}
    # Estrutura esperada em constantes: (Nome, CQT_Max, Sobrecarga, Metros_Max, Clientes_Max)
    for p in DEFAULT_PERFIS:
        nome = p[0]
        perfis_dict[nome] = {
            "cqt_max": p[1],
            "sobrecarga_max": p[2],
            # Garante fallback se a tupla for menor
            "metros_max": p[3] if len(p) > 3 else 3000.0,
            "clientes_max": p[4] if len(p) > 4 else 2000,
        }
    return perfis_dict


# --- 3. ENDPOINTS ---


@app.get("/")
def health_check():
    """Verifica se o motor está online."""
    return {"status": "online", "engine": "SisCQT v2.1", "license": "Enterprise"}


@app.get("/catalogos")
def obter_catalogos():
    """Retorna os cabos e perfis disponíveis no sistema."""
    # [FIX] Extrai apenas os nomes da lista de perfis
    nomes_perfis = [p[0] for p in DEFAULT_PERFIS]

    return {
        "cabos": list(DEFAULT_CABOS.keys()),
        "ips": list(DEFAULT_IPS.keys()),
        "perfis": nomes_perfis,
    }


@app.post("/api/v1/calcular")
def calcular_rede(payload: RequestCalculo):
    """
    Recebe a topologia JSON, processa no Engine Python e retorna o Laudo Técnico.
    """
    try:
        # 1. Converter JSON (Pydantic) -> DataFrame (Pandas)
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

        # 2. Preparar Contexto
        # [FIX] Converte perfis corretamente
        config_context = {
            "cabos": DEFAULT_CABOS,
            "ips": DEFAULT_IPS,
            "perfis": _converter_perfis_para_dict(),
        }

        # 3. Executar o Motor
        params = payload.config.model_dump()
        df_res, kpis, avisos = ElectricalEngine.calcular(
            df_input, params, config_context
        )

        # [CORREÇÃO] Verifica se KPIs voltaram vazios (indica falha fatal de topologia)
        if not kpis:
            raise HTTPException(
                status_code=400, detail=f"Erro Crítico de Cálculo/Topologia: {avisos}"
            )

        # 4. Verificar falha crítica (DataFrame vazio)
        if df_res.empty:
            raise HTTPException(status_code=400, detail=f"Erro desconhecido: {avisos}")

        # 5. Serializar Resposta
        cols_output = [
            "PONTO",
            "CQT_ACUMULADA",
            "CARGA_ACUMULADA_G",
            "CQT_TRECHO",
            "MOMENTO_KVA_M",
            "ICC_KA",
        ]
        cols_presentes = [c for c in cols_output if c in df_res.columns]

        # Converte para dict orientado a records para JSON limpo
        resultados_nos = df_res[cols_presentes].to_dict(orient="records")

        # Status Global
        # Usa limite do KPI ou default 6.0
        limite_cqt = 6.0
        if "limites_usados" in kpis:
            limite_cqt = kpis["limites_usados"].get("cqt_max", 6.0)

        aprovado = (
            (len(avisos) == 0)
            and (kpis["max_cqt"] <= limite_cqt)
            and (kpis["ocupacao"] <= 100)
        )

        return {
            "status_geral": "APROVADO" if aprovado else "REPROVADO",
            "kpis": kpis,
            "avisos_tecnicos": avisos,
            "resultados_detalhados": resultados_nos,
        }

    except HTTPException as he:
        raise he  # Deixa passar o erro 400 que nós criamos
    except Exception as e:
        print(f"Erro Interno API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
