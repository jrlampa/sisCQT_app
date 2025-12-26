import pandas as pd
import numpy as np
import math
import re
from collections import deque, defaultdict
from typing import Tuple, Dict, List

from backend.constantes import (
    UNIT_DIVISOR,
    TABELA_DEMANDA,
    FP_GERAL,
    FP_IP,
    ENGINE_VERSION,
    CABOS_IMPEDANCIA,
    COL_MAPPING,
)


class ElectricalEngine:
    @staticmethod
    def get_version():
        return ENGINE_VERSION

    @staticmethod
    def validar_estritamente(df: pd.DataFrame, params: Dict) -> List[str]:
        erros = []
        trafos = df[df["PONTO"] == "TRAFO"]
        if len(trafos) != 1:
            erros.append("ERRO: A rede deve conter exatamente um nó 'TRAFO'.")
        c_tipo = params.get("classe_tipo")
        if c_tipo not in ["Automático", "Manual"]:
            erros.append(f"ERRO: classe_tipo '{c_tipo}' inválido.")
        if c_tipo == "Manual" and params.get("classe_manual") not in [
            "A",
            "B",
            "C",
            "D",
        ]:
            erros.append(
                f"ERRO: Classe manual '{params.get('classe_manual')}' inválida."
            )
        if UNIT_DIVISOR != 100.0:
            erros.append("ERRO: UNIT_DIVISOR inconsistente para norma QTOS.")
        return erros

    @staticmethod
    def _normalizar_chave(texto: str) -> str:
        if not isinstance(texto, str) or not texto.strip():
            return ""
        s = texto.lower().strip()
        s = (
            s.replace(",", ".")
            .replace(" x ", "#")
            .replace("x", "#")
            .replace("+1#", "+")
        )
        ruidos = [
            "mm2",
            "mm²",
            "mm",
            "al",
            "cu",
            "ca",
            "multiplex",
            "conc",
            "cabo",
            "f.p",
            "1",
        ]
        for r in ruidos:
            s = s.replace(r, "")
        return re.sub(r"[^0-9+#.]", "", s)

    @staticmethod
    def _buscar_cabo_flexivel(nome_cabo: str, catalogo: Dict) -> Tuple[float, str]:
        if not nome_cabo:
            return 0.0, ""
        if nome_cabo in catalogo:
            return catalogo[nome_cabo], nome_cabo
        assinatura_input = ElectricalEngine._normalizar_chave(nome_cabo)
        if assinatura_input:
            for key_cat in catalogo.keys():
                if ElectricalEngine._normalizar_chave(key_cat) == assinatura_input:
                    return catalogo[key_cat], key_cat
        return 0.0, ""

    @staticmethod
    def validar_topologia(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        nodes = set(df["PONTO"])
        if df["PONTO"].duplicated().any():
            return False, ["ERRO: Pontos duplicados detectados."]
        adj = defaultdict(list)
        for _, r in df.iterrows():
            p, m = str(r["PONTO"]), str(r["MONTANTE"])
            if p == "TRAFO":
                continue
            if m not in nodes:
                return False, [
                    f"ERRO: Ponto '{p}' aponta para montante inexistente '{m}'."
                ]
            adj[m].append(p)
        visitados, pilha = set(), set()

        def tem_ciclo(u):
            visitados.add(u)
            pilha.add(u)
            for v in adj[u]:
                if v not in visitados:
                    if tem_ciclo(v):
                        return True
                elif v in pilha:
                    return True
            pilha.remove(u)
            return False

        if any(tem_ciclo(n) for n in nodes if n not in visitados):
            return False, ["ERRO: Ciclo (loop) detectado. A rede deve ser radial."]
        fila, alcancaveis = deque(["TRAFO"]), {"TRAFO"}
        while fila:
            u = fila.popleft()
            for v in adj[u]:
                if v not in alcancaveis:
                    alcancaveis.add(v)
                    fila.append(v)
        isolados = nodes - alcancaveis
        if isolados:
            return False, [f"ERRO: Pontos isolados do Trafo: {list(isolados)[:3]}"]
        return True, []

    @staticmethod
    def get_fator_demanda(tc, cls, tabela_demanda=None):
        tabela = tabela_demanda if tabela_demanda else TABELA_DEMANDA
        idx = {"A": 2, "B": 3, "C": 4, "D": 5}.get(cls, 3)
        for row in tabela:
            if row[0] <= tc <= row[1]:
                return row[idx]
        return [1.5, 2.5, 4.0, 6.0][idx - 2]

    @staticmethod
    def calcular_ordem_topologica(df):
        adj = defaultdict(list)
        in_degree = {n: 0 for n in df["PONTO"]}
        for _, r in df.iterrows():
            if r["PONTO"] != "TRAFO":
                adj[r["MONTANTE"]].append(r["PONTO"])
                in_degree[r["PONTO"]] += 1
        q = deque(["TRAFO"])
        topo = []
        while q:
            u = q.popleft()
            topo.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    q.append(v)
        return topo

    @staticmethod
    def balancear_fases(df: pd.DataFrame, ordem: List[str], pmap: Dict):
        fases = {"A": 0, "B": 0, "C": 0}
        df["SUGESTAO_BALANCEAMENTO"] = "-"
        for n in ordem:
            i = pmap[n]
            m, b = int(df.at[i, "MONO"]), int(df.at[i, "BIFÁSICO"])
            sug = []
            for _ in range(m):
                f = min(fases, key=fases.get)
                fases[f] += 1
                sug.append(f"1M->{f}")
            for _ in range(b):
                p = min(
                    [("A", "B"), ("B", "C"), ("C", "A")],
                    key=lambda x: fases[x[0]] + fases[x[1]],
                )
                fases[p[0]] += 1
                fases[p[1]] += 1
                sug.append(f"1B->{p[0]}{p[1]}")
            if sug:
                df.at[i, "SUGESTAO_BALANCEAMENTO"] = ", ".join(sug)

    @staticmethod
    def calcular_icc(df, ordem, pmap, trafo_kva):
        v_fase = 127.0
        z_base = (0.22**2 * 1000 / trafo_kva) if trafo_kva > 0 else 1.0
        z_trafo = complex(0, 0.04 * z_base)
        imp = {"TRAFO": z_trafo}
        for n in ordem:
            i = pmap[n]
            if n == "TRAFO":
                df.at[i, "ICC_KA"] = v_fase / abs(z_trafo) / 1000.0
                continue
            pai = df.at[i, "MONTANTE"]
            cabo = df.at[i, "CABO"]
            km = df.at[i, "METROS"] / 1000.0
            z_cabo = CABOS_IMPEDANCIA.get(cabo, {"r": 99, "x": 99})
            imp[n] = imp[pai] + complex(z_cabo["r"] * km, z_cabo["x"] * km)
            mod = abs(imp[n])
            df.at[i, "ICC_KA"] = (v_fase / mod / 1000.0) if mod > 0 else 0

    @staticmethod
    def calcular(
        df: pd.DataFrame, params: Dict, config_context: Dict
    ) -> Tuple[pd.DataFrame, Dict, List[str]]:
        coef_cabos = config_context.get("cabos", {})
        if not coef_cabos:
            return df, {}, ["ERRO: Catálogo de cabos vazio."]
        cols_num = [
            "METROS",
            "MONO",
            "BIFÁSICO",
            "TRIFÁSICO",
            "TRI ESPECIAL",
            "CARGA_ESP_KVA",
            "QTD_IP",
        ]
        for c in cols_num:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
            if (df[c] < 0).any():
                return df, {}, [f"ERRO: Valores negativos em '{c}'."]
        df.loc[df["PONTO"] == "TRAFO", ["METROS", "CABO"]] = [0, ""]
        erros_pre = ElectricalEngine.validar_estritamente(df, params)
        if erros_pre:
            return df, {}, erros_pre
        ok_topo, erros_topo = ElectricalEngine.validar_topologia(df)
        if not ok_topo:
            return df, {}, erros_topo
        ordem = ElectricalEngine.calcular_ordem_topologica(df)
        if len(ordem) != len(df):
            return df, {}, ["ERRO: Falha na integridade topológica."]
        pmap = {p: i for i, p in enumerate(df["PONTO"])}
        m, b, t, te = (
            df["MONO"].sum(),
            df["BIFÁSICO"].sum(),
            df["TRIFÁSICO"].sum(),
            df["TRI ESPECIAL"].sum(),
        )
        tc = int(m + b + t + te)
        if params.get("classe_tipo") == "Automático":
            if tc == 0:
                cls = "A"
            elif (te / tc > 0.1) or te >= 3:
                cls = "D"
            elif t / tc >= 0.2:
                cls = "C"
            elif (b + t) / tc >= 0.4:
                cls = "B"
            else:
                cls = "A"
        else:
            cls = params.get("classe_manual", "B")
        fd = ElectricalEngine.get_fator_demanda(tc, cls, config_context.get("demandas"))

        # Correção 1: CARGA_DIST_KVA agora armazena carga INSTALADA (Sem FD)
        df["CARGA_DIST_KVA"] = df["MONO"] + df["BIFÁSICO"] + df["TRIFÁSICO"]

        pot_ip_kva = (
            df["TIPO_IP"].map(config_context.get("ips", {})).fillna(0.0) / 1000.0
        )
        df["CARGA_PONTUAL_KVA"] = (
            df["CARGA_ESP_KVA"] + (pot_ip_kva * df["QTD_IP"]) + df["TRI ESPECIAL"]
        )
        df["TOTAL_LOCAL_KVA"] = df["CARGA_DIST_KVA"] + df["CARGA_PONTUAL_KVA"]

        accum = defaultdict(float)
        for n in reversed(ordem):
            idx = pmap[n]
            accum[n] += df.at[idx, "TOTAL_LOCAL_KVA"]
            pai = df.at[idx, "MONTANTE"]
            if pai:
                accum[pai] += accum[n]
            df.at[idx, "ACUMULADA_KVA"] = accum[n]

        avisos = []
        cqt_acum = {"TRAFO": 0.0}
        for n in ordem:
            idx = pmap[n]
            if n == "TRAFO":
                df.at[idx, "CQT_TRECHO"] = 0.0
                df.at[idx, "CQT_ACUMULADA"] = 0.0
                continue
            pai = df.at[idx, "MONTANTE"]
            momento = (
                (df.at[idx, "CARGA_DIST_KVA"] / 2)
                + df.at[idx, "CARGA_PONTUAL_KVA"]
                + (accum[n] - df.at[idx, "TOTAL_LOCAL_KVA"])
            )
            coef, cabo_real = ElectricalEngine._buscar_cabo_flexivel(
                df.at[idx, "CABO"], coef_cabos
            )
            df.at[idx, "CABO"] = cabo_real if cabo_real else df.at[idx, "CABO"]
            if coef == 0 and df.at[idx, "METROS"] > 0:
                avisos.append(f"ALERTA: Ponto '{n}' com cabo desconhecido.")
            km = df.at[idx, "METROS"] / UNIT_DIVISOR
            q_trecho = momento * km * coef
            cqt_acum[n] = cqt_acum[pai] + q_trecho
            df.at[idx, "CQT_TRECHO"], df.at[idx, "CQT_ACUMULADA"] = (
                q_trecho,
                cqt_acum[n],
            )
            limites = config_context.get("perfis", {}).get(
                params.get("perfil"), {"cqt_max": 6.0}
            )
            if cqt_acum[n] > limites["cqt_max"]:
                avisos.append(
                    f"ALERTA CRÍTICO: Ponto '{n}' QT {cqt_acum[n]:.2f}% excedida."
                )

        ElectricalEngine.calcular_icc(df, ordem, pmap, params.get("trafo_kva", 75))
        ElectricalEngine.balancear_fases(df, ordem, pmap)
        df.rename(columns=COL_MAPPING, inplace=True)

        # Correção 2: Cálculo de Demanda no Trafo separado (FD global aplicado uma única vez)
        total_distribuida_rede = df["CARGA_DISTRIBUIDA"].sum()
        total_pontual_rede = df["CARGA_PONTUAL_LOCAL"].sum()
        demanda_trafo = (total_distribuida_rede * fd) + total_pontual_rede

        kpis = {
            "classe": cls,
            "fator": fd,
            "demanda": demanda_trafo,
            "ocupacao": (demanda_trafo / params.get("trafo_kva", 75)) * 100,
            "max_cqt": df["CQT_ACUMULADA"].max(),
            "engine_version": ENGINE_VERSION,
            "unit_divisor": UNIT_DIVISOR,
            "snapshot_params": params,
        }
        return df, kpis, avisos
