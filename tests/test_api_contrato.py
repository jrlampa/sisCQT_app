import pytest
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)


def test_api_valida_entrada_correta():
    """Teste 8.1: Payload perfeito deve retornar 200 OK."""
    payload = {
        "config": {"trafo_kva": 75.0, "classe_tipo": "Manual", "perfil": "Massivos"},
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
                "metros": 45.5,
                "cabo": "3x70+54.6mm² Al",
                "cargas": {"mono": 5, "bi": 0, "tri": 0, "tipo_ip": "Sem IP"},
            },
        ],
    }
    response = client.post("/api/v1/calcular", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "resultados_detalhados" in data
    assert data["status_geral"] in ["Calculado", "APROVADO"]


def test_api_rejeita_tipo_dados_errado():
    """Teste 8.2: Enviar string onde deve ser número deve retornar 422 Unprocessable Entity."""
    payload = {"config": {"trafo_kva": "SETENTA E CINCO"}, "rede": []}  # ERRO AQUI
    response = client.post("/api/v1/calcular", json=payload)
    assert response.status_code == 422
    assert "trafo_kva" in response.text


def test_api_rejeita_valores_negativos():
    """Teste 8.3: Metros negativos ou clientes negativos devem ser barrados pelo Pydantic."""
    payload = {
        "config": {"trafo_kva": 75.0, "perfil": "Massivos"},
        "rede": [
            {
                "id": "P1",
                "pai_id": "TRAFO",
                "metros": -10.0,  # ERRO AQUI: Metros negativos
                "cabo": "3x70",
                "cargas": {"mono": 0, "bi": 0, "tri": 0},
            }
        ],
    }
    response = client.post("/api/v1/calcular", json=payload)
    # Se o teu api.py usar Field(ge=0), isto retorna 422.
    assert response.status_code == 422
