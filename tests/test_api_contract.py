import pytest
from fastapi.testclient import TestClient
from backend_api import app  # Importa a sua API recém-criada

client = TestClient(app)


# --- DADOS MOCK (Payloads de Exemplo) ---
def payload_valido():
    return {
        "config": {
            "trafo_kva": 112.5,
            "classe_tipo": "Automático",
            "perfil": "Padrão (Urbano)",
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
                "cabo": "3#70+1x70 - Al - F.P 1",  # Cabo válido do constantes
                "cargas": {"mono": 2, "bi": 1, "tri": 0, "tipo_ip": "IP 100W"},
            },
        ],
    }


def test_api_health_check():
    """O servidor está vivo?"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_calculo_sucesso_fluxo_normal():
    """Envia uma rede válida e espera 200 OK + Resultados."""
    payload = payload_valido()
    response = client.post("/api/v1/calcular", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verifica a estrutura da resposta (O Contrato)
    assert "status_geral" in data
    assert "kpis" in data
    assert "resultados_detalhados" in data
    assert len(data["resultados_detalhados"]) == 2  # Trafo + P1

    # Verifica um valor calculado
    res_p1 = data["resultados_detalhados"][1]
    assert res_p1["PONTO"] == "P1"
    assert res_p1["CQT_ACUMULADA"] > 0  # Tem que ter queda de tensão


def test_validacao_cabo_inexistente():
    """Se o cliente inventar um cabo, a API deve rejeitar (não explodir)."""
    payload = payload_valido()
    # Injeta erro
    payload["rede"][1]["cabo"] = "CABO_DE_ACO_DA_NASA"

    response = client.post("/api/v1/calcular", json=payload)

    # O Engine vai gerar um aviso, mas a API deve processar e retornar o aviso
    # OU se você colocou validator no Pydantic, retorna 422.
    # No nosso código atual, o Engine aceita e devolve aviso nos logs.
    assert response.status_code == 200
    data = response.json()

    # Deve conter avisos técnicos
    avisos = data["avisos_tecnicos"]
    assert any("sem coeficiente" in aviso for aviso in avisos)


def test_validacao_topologia_ciclo():
    """A API deve pegar o erro de topologia antes de travar o servidor."""
    payload = payload_valido()
    # Cria um loop: P1 aponta pra TRAFO, TRAFO aponta pra P1 (Montante inválido)
    payload["rede"][0]["pai_id"] = "P1"

    response = client.post("/api/v1/calcular", json=payload)

    # Esperamos erro 400 (Bad Request) tratado
    assert response.status_code == 400
    assert "Ciclo detetado" in response.json()["detail"]


def test_payload_incompleto_pydantic():
    """Testa se o Pydantic está barrando dados faltando."""
    payload = {
        "config": {"trafo_kva": 75}
        # Falta a lista "rede"!
    }
    response = client.post("/api/v1/calcular", json=payload)

    # 422 Unprocessable Entity (Padrão FastAPI para erro de validação)
    assert response.status_code == 422
