# backend_api.py
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

# Importa o Motor Validado
from siscqt_engine import ElectricalEngine
from siscqt_constantes import DEFAULT_CABOS, DEFAULT_IPS, DEFAULT_PERFIS

# --- CONFIGURAÇÃO DA API ---
app = FastAPI(
    title="SisCQT Enterprise API",
    description="Motor de Cálculo de Redes de Distribuição BT (Norma ENEL/NBR)",
    version="2.0.0",
)

# --- 1. MODELOS DE DADOS (O Contrato Rigoroso) ---
# O Pydantic garante que ninguém mande texto onde deve ser número.


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

    @validator("id", "pai_id")
    def uppercase_ids(cls, v):
        return v.strip().upper() if v else ""


class ConfigSimulacao(BaseModel):
    trafo_kva: float = Field(..., gt=0, description="Potência do Transformador")
    classe_tipo: str = "Automático"
    classe_manual: str = "B"
    fp_ip: float = 1.0
    perfil: str = "Padrão (Urbano)"


class RequestCalculo(BaseModel):
    config: ConfigSimulacao
    rede: List[NoRede]


# --- 2. ENDPOINTS ---


@app.get("/")
def health_check():
    """Verifica se o motor está online."""
    return {"status": "online", "engine": "SisCQT v2.0", "license": "Enterprise"}


@app.get("/catalogos")
def obter_catalogos():
    """Retorna os cabos e perfis disponíveis no sistema."""
    return {
        "cabos": list(DEFAULT_CABOS.keys()),
        "ips": list(DEFAULT_IPS.keys()),
        "perfis": list(
            DEFAULT_PERFIS.keys()
        ),  # Ajuste conforme estrutura do constantes
    }


@app.post("/api/v1/calcular")
def calcular_rede(payload: RequestCalculo):
    """
    Recebe a topologia JSON, processa no Engine Python e retorna o Laudo Técnico.
    """
    try:
        # 1. Converter JSON (Pydantic) -> DataFrame (Pandas)
        # O Engine espera colunas específicas ("PONTO", "MONTANTE", etc)
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

        # 2. Preparar Contexto (Mockado do DB ou Constantes)
        # Numa versão futura, isso viria de `siscqt_db.py`
        config_context = {
            "cabos": DEFAULT_CABOS,
            "ips": DEFAULT_IPS,
            # Se DEFAULT_PERFIS for lista de tuplas, converte para dict
            "perfis": {
                "Padrão (Urbano)": {"cqt_max": 6.0, "sobrecarga_max": 100.0},
                "Rural": {"cqt_max": 10.0, "sobrecarga_max": 100.0},
            },
        }

        # 3. Executar o Motor (A Mágica)
        params = payload.config.dict()
        df_res, kpis, avisos = ElectricalEngine.calcular(
            df_input, params, config_context
        )

        # 4. Verificar falha crítica
        if df_res.empty:
            raise HTTPException(status_code=400, detail=f"Erro de Cálculo: {avisos}")

        # 5. Serializar Resposta
        # Filtra apenas colunas relevantes para o JSON
        cols_output = [
            "PONTO",
            "CQT_ACUMULADA",
            "CARGA_ACUMULADA_G",
            "CQT_TRECHO",
            "MOMENTO_KVA_M",
            "ICC_KA",
        ]
        # Garante que colunas existem antes de filtrar
        cols_presentes = [c for c in cols_output if c in df_res.columns]

        resultados_nos = df_res[cols_presentes].to_dict(orient="records")

        # Status Global
        aprovado = (
            (len(avisos) == 0)
            and (kpis["max_cqt"] <= 6.0)
            and (kpis["ocupacao"] <= 100)
        )

        return {
            "status_geral": "APROVADO" if aprovado else "REPROVADO",
            "kpis": kpis,
            "avisos_tecnicos": avisos,
            "resultados_detalhados": resultados_nos,
        }

    except Exception as e:
        # Loga o erro no servidor e retorna 500 para o cliente
        print(f"Erro Interno: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Roda o servidor localmente na porta 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
