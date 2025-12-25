import pytest
from fastapi.testclient import TestClient
from backend_api import app

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


def test_calculo_sucesso_fluxo_normal():
    payload = payload_valido()
    response = client.post("/api/v1/calcular", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "status_geral" in data
    assert len(data["resultados_detalhados"]) == 2
    assert data["resultados_detalhados"][1]["CQT_ACUMULADA"] > 0


def test_validacao_cabo_inexistente():
    payload = payload_valido()
    # Injeta nome de cabo inválido
    payload["rede"][1]["cabo"] = "CABO_INEXISTENTE_XYZ"

    response = client.post("/api/v1/calcular", json=payload)

    assert response.status_code == 200
    data = response.json()
    avisos = data["avisos_tecnicos"]
    # Agora vai passar porque o Engine inclui o nome do cabo na mensagem!
    assert any("CABO_INEXISTENTE_XYZ" in aviso for aviso in avisos)


def test_validacao_topologia_ciclo():
    """Testa um ciclo que o Engine não consegue 'consertar'."""
    payload = payload_valido()

    # Cria ciclo P1 -> P2 -> P1 (longe do trafo)
    # Adiciona P2
    payload["rede"].append(
        {
            "id": "P2",
            "pai_id": "P1",
            "metros": 40.0,
            "cabo": "3x70+54.6mm² Al",
            "cargas": {"mono": 0, "bi": 0, "tri": 0, "tipo_ip": "Sem IP"},
        }
    )

    # Faz P1 apontar para P2 (Ciclo Mortal)
    # Originalmente P1 apontava para TRAFO.
    payload["rede"][1]["pai_id"] = "P2"

    # Rede: TRAFO (orfão de filhos), P1->P2->P1 (Ciclo isolado)

    response = client.post("/api/v1/calcular", json=payload)

    assert response.status_code == 400
    detail = response.json()["detail"]
    # Pode ser erro de Ciclo ou Ilha, ambos são fatais
    assert "Ciclo" in detail or "Pontos isolados" in detail


def test_payload_incompleto_pydantic():
    payload = {"config": {"trafo_kva": 75}}
    response = client.post("/api/v1/calcular", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", "rede"] for error in errors)
