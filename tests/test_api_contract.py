import pytest
import sys
import os
from fastapi.testclient import TestClient

# Garante path para backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api import app

client = TestClient(app)


def payload_valido():
    return {
        "config": {
            "trafo_kva": 112.5,
            "classe_tipo": "Automático",
            "perfil": "Massivos",
        },
        "rede": [
            {
                "id": "TRAFO",
                "pai_id": "",
                "metros": 0.0,
                "cabo": "",
                "cargas": {"mono": 0, "bi": 0, "tri": 0, "tipo_ip": "Sem IP"},
            },
            {
                "id": "P1",
                "pai_id": "TRAFO",
                "metros": 45.0,
                "cabo": "3x70+54.6mm² Al",
                "cargas": {"mono": 2, "bi": 1, "tri": 0, "tipo_ip": "IP 100W"},
            },
        ],
    }


def test_api_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_calculo_sucesso():
    payload = payload_valido()
    response = client.post("/api/v1/calcular", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "status_geral" in data
    assert len(data["resultados_detalhados"]) == 2


def test_validacao_cabo_inexistente():
    payload = payload_valido()
    payload["rede"][1]["cabo"] = "CABO_DOIDO_XYZ"
    response = client.post("/api/v1/calcular", json=payload)
    assert response.status_code == 200
    # O sistema deve aceitar mas gerar um aviso técnico
    assert any("CABO_DOIDO_XYZ" in av for av in response.json()["avisos_tecnicos"])


def test_validacao_topologia_ciclo():
    """Cria um ciclo P1 -> P2 -> P1 que o sanitizador não pode remover."""
    payload = payload_valido()

    # Adiciona P2 conectado a P1
    payload["rede"].append(
        {
            "id": "P2",
            "pai_id": "P1",
            "metros": 40.0,
            "cabo": "3x70+54.6mm² Al",
            "cargas": {"mono": 0, "bi": 0, "tri": 0, "tipo_ip": "Sem IP"},
        }
    )

    # Faz P1 apontar para P2 (Criando o Loop P1->P2->P1)
    payload["rede"][1]["pai_id"] = "P2"

    response = client.post("/api/v1/calcular", json=payload)

    # Agora sim deve dar 400 Bad Request
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Ciclo" in detail or "Pontos isolados" in detail
