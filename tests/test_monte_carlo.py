import pytest
import pandas as pd
import random
import numpy as np
import math
from siscqt_engine import ElectricalEngine
from siscqt_constantes import DEFAULT_PARAMS, DEFAULT_CABOS_DATA


# --- GERADOR DE CAOS (FUZZER) ---
def gerar_rede_caotica(num_nos_min=10, num_nos_max=100):
    """
    Gera uma rede completamente aleatória e imprevisível.
    """
    num_nos = random.randint(num_nos_min, num_nos_max)

    # Lista de Cabos disponíveis no sistema
    cabos_disponiveis = list(DEFAULT_CABOS_DATA.keys())

    data = []
    # Nó Raiz (Trafo)
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
        # Escolhe um pai aleatório já existente (cria ramificações aleatórias)
        pai = random.choice(nos_existentes)

        # Caos nos parâmetros
        comp = random.uniform(1.0, 300.0)  # De 1m a 300m
        cabo = random.choice(cabos_disponiveis)

        # Cargas aleatórias (alguns nós zerados, outros pesados)
        mono = random.choice([0, 0, 1, 5, 15])
        bi = random.choice([0, 0, 1, 5])
        tri = random.choice([0, 0, 1])
        ip_qtd = random.choice([0, 0, 0, 1, 5])
        tipo_ip = "IP 150W" if ip_qtd > 0 else "Sem IP"

        # Carga Especial (aleatória)
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


# --- FIXTURE ---
@pytest.fixture
def config_full():
    cabos_simple = {k: v[0] for k, v in DEFAULT_CABOS_DATA.items()}
    ips = {"IP 150W": 150.0, "Sem IP": 0.0}
    return {
        "cabos": cabos_simple,
        "ips": ips,
        # Limites altos para não poluir o log com avisos, queremos testar a matemática
        "perfis": {"Teste": {"cqt_max": 999.0, "sobrecarga_max": 9999.0}},
    }


# --- O TESTE DE FOGO COMPLETO ---
def test_simulacao_monte_carlo(config_full):
    """
    Roda 100 simulações com redes aleatórias.
    Verifica:
    1. Lei de Kirchhoff (Balanço de Carga)
    2. Consistência de Queda de Tensão (CQT)
    3. Cálculo de Carregamento (Ocupação)
    4. Ausência de NaNs/Infs (Estabilidade Numérica)
    """
    ITERATIONS = 100
    print(f"\n🎲 Iniciando Monte Carlo Estendido ({ITERATIONS} iterações)...")

    sucessos = 0

    for i in range(ITERATIONS):
        # 1. Gera cenário único
        df_caos = gerar_rede_caotica(num_nos_min=20, num_nos_max=150)
        params = DEFAULT_PARAMS.copy()
        params["trafo_kva"] = float(random.choice([45, 75, 112.5, 150, 300]))
        params["perfil"] = "Teste"

        try:
            # 2. Executa Engine
            df_res, kpis, _ = ElectricalEngine.calcular(df_caos, params, config_full)

            # --- VALIDAÇÃO A: FÍSICA (BALANÇO DE CARGA) ---
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

            # --- VALIDAÇÃO B: QUEDA DE TENSÃO (CQT) ---
            # CQT não pode ser negativa em rede passiva (exceto erros de arredondamento ínfimos)
            if (df_res["CQT_ACUMULADA"] < -0.001).any():
                pior = df_res["CQT_ACUMULADA"].min()
                pytest.fail(f"🚨 ERRO CQT NEGATIVA (Iter {i}): Valor encontrado {pior}")

            # Max CQT no KPI deve bater com Max CQT no DataFrame
            max_df = df_res["CQT_ACUMULADA"].max()
            max_kpi = kpis["max_cqt"]
            if abs(max_df - max_kpi) > 0.001:
                pytest.fail(
                    f"🚨 ERRO KPI CQT (Iter {i}): DF({max_df}) != KPI({max_kpi})"
                )

            # --- VALIDAÇÃO C: CARREGAMENTO (OCUPAÇÃO) ---
            # Ocupação = (Demanda / Trafo) * 100
            ocup_calc = (carga_trafo / params["trafo_kva"]) * 100.0
            ocup_engine = kpis["ocupacao"]

            if abs(ocup_calc - ocup_engine) > 0.01:
                pytest.fail(
                    f"🚨 ERRO OCUPAÇÃO (Iter {i}): Calc({ocup_calc:.2f}) != Engine({ocup_engine:.2f})"
                )

            # --- VALIDAÇÃO D: ESTABILIDADE NUMÉRICA ---
            # Não pode haver NaN (Not a Number) ou Inf (Infinito)
            if df_res.isnull().values.any():
                pytest.fail(
                    f"🚨 ERRO NaN DETECTADO (Iter {i}): O DataFrame contém valores nulos!"
                )

            # Verifica se algum valor explodiu (Overflow)
            # Ex: CQT > 1000% (fisicamente impossível, mas matematicamente possível se R for gigante)
            # Vamos tolerar valores altos, mas não Infinito.
            cols_check = ["CQT_ACUMULADA", "CARGA_ACUMULADA_G"]
            if "CARGA_ACUMULADA_G" in df_res.columns:
                for c in cols_check:
                    if np.isinf(df_res[c]).any():
                        pytest.fail(
                            f"🚨 ERRO INFINITO (Iter {i}): Coluna {c} tem valor Infinito."
                        )

            sucessos += 1

        except Exception as e:
            pytest.fail(
                f"💥 CRASH na iteração {i}!\nParams: Trafo {params['trafo_kva']}\nErro: {str(e)}"
            )

    print(
        f"\n✅ SUCESSO ABSOLUTO: {sucessos} redes aleatórias validadas em Carga, CQT e Ocupação."
    )
