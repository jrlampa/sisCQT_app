import pytest
import pandas as pd
import random
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_PARAMS, DEFAULT_CABOS_DATA


def gerar_rede_caotica(num_nos_min=10, num_nos_max=100):
    num_nos = random.randint(num_nos_min, num_nos_max)
    cabos_disponiveis = list(DEFAULT_CABOS_DATA.keys())

    data = []
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

    nos_existentes = ["TRAFO"]

    for i in range(1, num_nos):
        nome = f"P{i}"
        pai = random.choice(nos_existentes)
        comp = random.uniform(1.0, 300.0)
        cabo = random.choice(cabos_disponiveis)
        mono = random.choice([0, 0, 1, 5, 15])
        bi = random.choice([0, 0, 1, 5])
        tri = random.choice([0, 0, 1])
        ip_qtd = random.choice([0, 0, 0, 1, 5])
        tipo_ip = "IP 150W" if ip_qtd > 0 else "Sem IP"
        carga_esp = random.choice([0.0, 0.0, 5.0, 15.5])

        data.append(
            {
                "PONTO": nome,
                "MONTANTE": pai,
                "METROS": round(comp, 2),
                "CABO": cabo,
                "MONO": mono,
                "BIFÁSICO": bi,
                "TRIFÁSICO": tri,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": carga_esp,
                "TIPO_IP": tipo_ip,
                "QTD_IP": ip_qtd,
            }
        )
        nos_existentes.append(nome)

    return pd.DataFrame(data)


@pytest.fixture
def config_full():
    cabos_simple = {k: v[0] for k, v in DEFAULT_CABOS_DATA.items()}
    ips = {"IP 150W": 150.0, "Sem IP": 0.0}
    return {
        "cabos": cabos_simple,
        "ips": ips,
        "perfis": {"Teste": {"cqt_max": 999.0, "sobrecarga_max": 9999.0}},
    }


def test_simulacao_monte_carlo(config_full):
    ITERATIONS = 50  # Reduzido para teste rápido
    print(f"\n🎲 Iniciando Monte Carlo ({ITERATIONS} iterações)...")
    sucessos = 0

    for i in range(ITERATIONS):
        df_caos = gerar_rede_caotica(num_nos_min=20, num_nos_max=150)
        params = DEFAULT_PARAMS.copy()
        params["trafo_kva"] = float(random.choice([45, 75, 112.5, 150, 300]))
        params["perfil"] = "Teste"

        try:
            df_res, kpis, _ = ElectricalEngine.calcular(df_caos, params, config_full)

            col_local = (
                "TOTAL_TRECHO_LOCAL"
                if "TOTAL_TRECHO_LOCAL" in df_res.columns
                else "TOTAL_LOCAL_KVA"
            )
            soma_pontas = df_res[col_local].sum()
            carga_trafo = kpis["demanda"]

            if abs(soma_pontas - carga_trafo) > 0.01:
                pytest.fail(
                    f"🚨 ERRO FÍSICA (Iter {i}): Trafo({carga_trafo:.2f}) != Soma({soma_pontas:.2f})"
                )

            if (df_res["CQT_ACUMULADA"] < -0.001).any():
                pytest.fail(f"🚨 ERRO CQT NEGATIVA (Iter {i})")

            if df_res.isnull().values.any():
                pytest.fail(f"🚨 ERRO NaN DETECTADO (Iter {i})")

            sucessos += 1

        except Exception as e:
            pytest.fail(f"💥 CRASH na iteração {i}! Erro: {str(e)}")

    print(f"\n✅ SUCESSO: {sucessos} redes aleatórias validadas.")
