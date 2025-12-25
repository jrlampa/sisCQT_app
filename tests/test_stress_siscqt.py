import pytest
import pandas as pd
import time
import random
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.engine import ElectricalEngine
from backend.utils import SimuladorReadequacao
from backend.constantes import DEFAULT_PARAMS


# --- GERADOR DE REDES SINTÉTICAS ---
def gerar_rede_sintetica(num_nos=100, ramificacao=2):
    data = []
    # Nó Raiz
    data.append(
        {
            "PONTO": "TRAFO",
            "MONTANTE": "",
            "METROS": 0.0,
            "CABO": "",
            "MONO": 0,
            "BIFÁSICO": 0,
            "TRIFÁSICO": 0,
            "TRI ESPECIAL": 0,
            "CARGA_ESP_KVA": 0.0,
            "TIPO_IP": "Sem IP",
            "QTD_IP": 0,
        }
    )

    fila = ["TRAFO"]
    criados = 1

    while criados < num_nos and fila:
        pai = fila.pop(0)
        for i in range(ramificacao):
            if criados >= num_nos:
                break
            nome = f"P{criados}"
            data.append(
                {
                    "PONTO": nome,
                    "MONTANTE": pai,
                    "METROS": float(random.randint(30, 60)),
                    "CABO": "3#70+1x70 - Al - F.P 1",
                    "MONO": random.randint(0, 3),
                    "BIFÁSICO": 0,
                    "TRIFÁSICO": 0,
                    "TRI ESPECIAL": 0,
                    "CARGA_ESP_KVA": 0.0,
                    "TIPO_IP": "IP 100W" if criados % 3 == 0 else "Sem IP",
                    "QTD_IP": 1 if criados % 3 == 0 else 0,
                }
            )
            fila.append(nome)
            criados += 1

    return pd.DataFrame(data)


@pytest.fixture
def config_padrao():
    return {
        "cabos": {"3#70+1x70 - Al - F.P 1": 0.1296, "3#150+70 - Al - F.P 1": 0.0573},
        "ips": {"IP 100W": 100.0, "Sem IP": 0.0},
        "perfis": {"Padrão (Urbano)": {"cqt_max": 6.0, "sobrecarga_max": 100.0}},
    }


def test_performance_rede_grande(config_padrao):
    df_big = gerar_rede_sintetica(num_nos=1000, ramificacao=3)
    params = DEFAULT_PARAMS.copy()
    params["trafo_kva"] = 300.0

    start_time = time.time()
    df_res, kpis, avisos = ElectricalEngine.calcular(df_big, params, config_padrao)
    elapsed = time.time() - start_time

    print(f"\n⚡ Performance (1000 nós): {elapsed:.4f}s")
    assert elapsed < 1.0, "Engine lento!"
    assert not df_res.empty


def test_consistencia_fisica_balanco_carga(config_padrao):
    df_rede = gerar_rede_sintetica(num_nos=50, ramificacao=2)
    params = DEFAULT_PARAMS.copy()

    df_res, kpis, _ = ElectricalEngine.calcular(df_rede, params, config_padrao)
    carga_trafo_engine = kpis["demanda"]

    col_total = "TOTAL_TRECHO_LOCAL"
    if col_total not in df_res.columns:
        col_total = "TOTAL_LOCAL_KVA"

    soma_manual = df_res[col_total].sum()
    diferenca = abs(carga_trafo_engine - soma_manual)

    print(
        f"\n⚖️ Balanço: Trafo({carga_trafo_engine:.2f}) vs Soma({soma_manual:.2f}) | Dif: {diferenca:.4f}"
    )
    assert diferenca < 0.01


def test_simulador_rede_impossivel(config_padrao):
    df_longa = pd.DataFrame(
        [
            {
                "PONTO": "TRAFO",
                "MONTANTE": "",
                "METROS": 0.0,
                "CABO": "",
                "MONO": 0,
                "BIFÁSICO": 0,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 0.0,
                "QTD_IP": 0,
            },
            {
                "PONTO": "P1",
                "MONTANTE": "TRAFO",
                "METROS": 5000.0,
                "CABO": "3#70+1x70 - Al - F.P 1",
                "MONO": 50,
                "BIFÁSICO": 0,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 0.0,
                "QTD_IP": 0,
            },
        ]
    )
    df_longa["TIPO_IP"] = "Sem IP"

    params = DEFAULT_PARAMS.copy()
    config_full = {
        "cabos": config_padrao["cabos"],
        "ips": config_padrao["ips"],
        "perfis": config_padrao["perfis"],
    }
    cabos_hab = ["3#70+1x70 - Al - F.P 1", "3#150+70 - Al - F.P 1"]

    resultado = SimuladorReadequacao.executar(
        "Teste Impossível", df_longa, params, config_full, cabos_hab
    )

    print(f"\n🛡️ Simulador Msg: {resultado['msg']}")
    assert resultado["resolvido"] is False
    assert resultado["iteracoes"] > 0


def test_validacao_dados_sujos(config_padrao):
    df_sujo = pd.DataFrame(
        [
            {"PONTO": "TRAFO", "MONTANTE": None, "METROS": "zero", "CABO": None},
            {
                "PONTO": " P1 ",
                "MONTANTE": "trafo",
                "METROS": "100,5",
                "CABO": "3#70+1x70 - Al - F.P 1",
                "MONO": "10",
            },
        ]
    )
    params = DEFAULT_PARAMS.copy()
    df_res, kpis, avisos = ElectricalEngine.calcular(df_sujo, params, config_padrao)

    assert not df_res.empty
    val_metros = df_res.iloc[1]["METROS"]
    assert abs(val_metros - 100.5) < 0.001
    assert df_res.iloc[1]["MONO"] == 10
