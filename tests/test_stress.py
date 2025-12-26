import pytest
import pandas as pd
import time
from backend.engine import ElectricalEngine


def test_stress_rede_longa_linear():
    """Teste de Stress: 500 nós em linha reta (profundidade máxima)."""
    num_nos = 500
    data = [{"PONTO": "TRAFO", "MONTANTE": "", "METROS": 0, "CABO": ""}]

    # Cria uma linha reta: TRAFO -> P1 -> P2 -> ... -> P500
    for i in range(1, num_nos + 1):
        pai = "TRAFO" if i == 1 else f"P{i-1}"
        data.append(
            {
                "PONTO": f"P{i}",
                "MONTANTE": pai,
                "METROS": 20,  # 20 metros cada vão
                "CABO": "3x35+54.6mm² Al",
                "MONO": 1,
                "BIFÁSICO": 0,
                "TRIFÁSICO": 0,
                "TRI ESPECIAL": 0,
                "CARGA_ESP_KVA": 0,
            }
        )

    df_stress = pd.DataFrame(data)

    config = {
        "cabos": {"3x35+54.6mm² Al": {"coef": 0.2416}},
        "ips": {"Sem IP": 0.0},
        "perfis": {"Massivos": {"cqt_max": 20.0, "sobrecarga_max": 200.0}},
    }
    params = {
        "trafo_kva": 150.0,
        "classe_tipo": "Manual",
        "classe_manual": "A",
        "perfil": "Massivos",
    }

    start_time = time.time()
    # Se o motor usar recursão profunda sem proteção, isto vai dar RecursionError aqui
    df_res, kpis, _ = ElectricalEngine.calcular(df_stress, params, config)
    end_time = time.time()

    duracao = end_time - start_time

    assert not df_res.empty
    assert len(df_res) == num_nos + 1
    # Um cálculo de 500 nós deve demorar menos de 1 segundo em hardware moderno
    assert duracao < 1.0, f"Performance baixa: {duracao:.2f}s para {num_nos} nós"
    print(f"\n✅ Stress Test: {num_nos} nós processados em {duracao:.4f}s")
