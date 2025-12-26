import pytest
import pandas as pd
from backend.engine import ElectricalEngine


def criar_rede_com_loop():
    # TRAFO -> A -> B -> C -> A (Loop)
    data = [
        {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
        {"PONTO": "A", "MONTANTE": "TRAFO", "METROS": 10, "CABO": "3x35"},
        {"PONTO": "B", "MONTANTE": "A", "METROS": 10, "CABO": "3x35"},
        {"PONTO": "C", "MONTANTE": "B", "METROS": 10, "CABO": "3x35"},
        # O ERRO ESTÁ AQUI: C aponta de volta para A, criando loop A-B-C-A
        {"PONTO": "A", "MONTANTE": "C", "METROS": 10, "CABO": "3x35"},
        # Nota: Pandas não permite duplicar PONTO no index facilmente se usarmos set_index,
        # mas aqui estamos simulando erro de cadastro onde o usuário editou o montante errado.
        # Vamos fazer um loop mais simples para não ter IDs duplicados: B aponta para A
    ]
    return pd.DataFrame(data)


def criar_rede_loop_simples():
    # TRAFO -> A -> B -> A
    data = [
        {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""},
        {"PONTO": "A", "MONTANTE": "TRAFO", "METROS": 10, "CABO": "3x35"},
        {"PONTO": "B", "MONTANTE": "A", "METROS": 10, "CABO": "3x35"},
        # Alteramos a topologia para simular que o "Pai" de A virou B (impossível fisicamente, mas possível no Excel)
    ]
    # Representação mais fiel de como o engine lê: Adjacência
    # Vamos criar um DF onde a lógica de montante cria o ciclo
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0},
            {"PONTO": "A", "MONTANTE": "B", "METROS": 10},  # A depende de B
            {
                "PONTO": "B",
                "MONTANTE": "A",
                "METROS": 10,
            },  # B depende de A (Loop isolado do Trafo)
        ]
    )
    return df


def test_detecao_ciclo():
    """Teste 2.1: Deve detetar ciclo direto A <-> B"""
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0},
            {"PONTO": "A", "MONTANTE": "B", "METROS": 10},
            {"PONTO": "B", "MONTANTE": "A", "METROS": 10},
        ]
    )

    # O Engine deve retornar False e uma lista de erros
    ok, erros = ElectricalEngine.validar_topologia(df)

    assert ok is False, "O sistema aceitou uma rede com loop!"
    assert any(
        "Ciclo" in e for e in erros
    ), f"Esperava erro de 'Ciclo', recebeu: {erros}"


def test_ciclo_complexo():
    """Teste 2.2: Ciclo indireto TRAFO -> A -> B -> C -> A"""
    # Neste caso, C aponta para A, mas A aponta para Trafo.
    # Isso tecnicamente cria dois pais para A se não cuidarmos, ou um redirecionamento.
    # Vamos simular um erro onde o usuário mudou o montante de A para C.
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0},
            {"PONTO": "A", "MONTANTE": "C", "METROS": 10},  # Mudou de TRAFO para C
            {"PONTO": "B", "MONTANTE": "A", "METROS": 10},
            {"PONTO": "C", "MONTANTE": "B", "METROS": 10},
        ]
    )

    ok, erros = ElectricalEngine.validar_topologia(df)
    assert ok is False
    assert any("Ciclo" in e for e in erros)


def test_pontos_isolados():
    """Teste 2.3: Ilhas (Nós que não chegam no TRAFO)"""
    # TRAFO (sozinho)
    # A -> B (Desconectados do TRAFO)
    df = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0},
            {"PONTO": "A", "MONTANTE": "TRAFO", "METROS": 10},
            {"PONTO": "B", "MONTANTE": "C", "METROS": 10},  # C não existe
        ]
    )

    # No engine atual, apontar para inexistente é erro.
    ok, erros = ElectricalEngine.validar_topologia(df)
    assert ok is False
    assert any("inexistente" in e or "Isolados" in e for e in erros)
