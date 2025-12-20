# siscqt_engine.py
import pandas as pd
import numpy as np
import hashlib
import math
from collections import deque, defaultdict
from typing import Tuple, Dict, List
from siscqt_constantes import UNIT_DIVISOR, COL_MAPPING, TABELA_DEMANDA, CABOS_IMPEDANCIA

class ElectricalEngine:
    @staticmethod
    def get_template_dataframe():
        return pd.DataFrame({
            "PONTO": ["TRAFO"], "MONTANTE": [""], "METROS": [0.0], 
            "CABO": [""], 
            "MONO": [0], "BIFÁSICO": [0], "TRIFÁSICO": [0], "TRI ESPECIAL": [0],
            "CARGA_ESP_KVA": [0.0], "TIPO_IP": ["Sem IP"], "QTD_IP": [0]
        })

    @staticmethod
    def limpar_linhas_vazias(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return df
        def tem_dados(row):
            if str(row.get('PONTO', '')).strip(): return True
            cabo = str(row.get('CABO', '')).strip()
            try: mts = float(row.get('METROS', 0))
            except: mts = 0.0
            try: ip_qtd = int(row.get('QTD_IP', 0))
            except: ip_qtd = 0
            carga = 0
            for c in ['MONO', 'BIFÁSICO', 'TRIFÁSICO', 'TRI ESPECIAL', 'CARGA_ESP_KVA']:
                try: carga += float(row.get(c, 0))
                except: pass
            return bool(cabo or mts > 0 or ip_qtd > 0 or carga > 0)
        df_limpo = df[df.apply(tem_dados, axis=1) | (df['PONTO'] == 'TRAFO')].copy()
        return df_limpo.reset_index(drop=True)

    @staticmethod
    def validar_preenchimento(df: pd.DataFrame, mapa_ips: Dict) -> List[str]:
        erros = []
        for idx, row in df.iterrows():
            p = str(row.get('PONTO', '')).strip()
            if p == 'TRAFO': continue
            if not p:
                erros.append(f"Linha {idx+1}: Falta o nome do Ponto.")
                continue
            m = str(row.get('MONTANTE', '')).strip()
            if not m:
                erros.append(f"Ponto '{p}': Falta definir o Montante.")
        return erros

    @staticmethod
    def sanitizar(df_input: pd.DataFrame, valid_cabos: List[str] = None, valid_ips: List[str] = None, limites: Dict = None) -> Tuple[pd.DataFrame, List[str]]:
        df = df_input.copy()
        erros = []
        cols_str = ["PONTO", "MONTANTE", "CABO", "TIPO_IP"]
        for c in cols_str: 
            if c in df.columns: df[c] = df[c].fillna("").astype(str).str.strip()
        trafo_mask = df['PONTO'] == 'TRAFO'
        if not trafo_mask.any(): return df, ["Falta o ponto 'TRAFO'."]
        else: df.loc[trafo_mask, ['MONTANTE', 'METROS', 'CABO']] = ["", 0.0, ""]
        cols_num = ["METROS", "MONO", "BIFÁSICO", "TRIFÁSICO", "TRI ESPECIAL", "CARGA_ESP_KVA", "QTD_IP"]
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                if (df[c] < 0).any(): erros.append(f"Valores negativos em {c}.")
        return df, erros

    @staticmethod
    def validar_topologia(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        erros = []
        if df['PONTO'].duplicated().any(): 
            dups = df[df['PONTO'].duplicated()]['PONTO'].unique().tolist()
            return False, [f"Pontos duplicados: {dups}"]
        nodes = set(df['PONTO']); adj = defaultdict(list)
        for _, r in df.iterrows():
            p, m = r['PONTO'], r['MONTANTE']
            if p == "TRAFO": continue
            if not m: erros.append(f"Ponto '{p}' sem montante.")
            elif m not in nodes: erros.append(f"Ponto '{p}' aponta para montante inexistente '{m}'.")
            else: adj[m].append(p)
        if erros: return False, erros
        vis, stack = set(), set()
        def has_cycle(u):
            vis.add(u); stack.add(u)
            for v in adj[u]:
                if v not in vis:
                    if has_cycle(v): return True
                elif v in stack: return True
            stack.remove(u); return False
        for n in nodes:
            if n not in vis:
                if has_cycle(n): return False, [f"Ciclo detectado na rede (loop em '{n}')."]
        q = deque(["TRAFO"]); reached = {"TRAFO"}
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in reached: reached.add(v); q.append(v)
        orphans = nodes - reached
        if orphans: return False, [f"Pontos isolados do Trafo: {list(orphans)}"]
        return True, []

    @staticmethod
    def calcular_ordem_topologica(df):
        adj = defaultdict(list); in_degree = {n: 0 for n in df['PONTO']}
        for _, r in df.iterrows():
            if r['PONTO'] != 'TRAFO': 
                adj[r['MONTANTE']].append(r['PONTO']); in_degree[r['PONTO']] += 1
        q = deque(["TRAFO"]); topo = []
        while q:
            u = q.popleft(); topo.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0: q.append(v)
        return topo

    @staticmethod
    def get_fator_demanda(tc, cls):
        idx = {"A":0, "B":1, "C":2, "D":3}.get(cls, 0)
        for mn, mx, *v in TABELA_DEMANDA:
            if mn <= tc <= mx: return v[idx]
        return [0.5, 0.8, 1.3, 2.0][idx] 

    @staticmethod
    def sugerir_centro_carga(df: pd.DataFrame) -> str:
        if df.empty: return "N/A"
        col_accum = "CARGA_ACUMULADA_G"
        try:
            df_net = df[df['PONTO'] != 'TRAFO']
            if df_net.empty: return "TRAFO"
            if col_accum in df_net.columns:
                # Garante ordenação escalar evitando Series ambiguas
                return df_net.sort_values(by=col_accum, ascending=False).iloc[0]['PONTO']
            return "TRAFO"
        except: return "TRAFO"

    @staticmethod
    def calcular_icc(df: pd.DataFrame, ordem: List[str], pmap: Dict, trafo_kva: float):
        v_fase = 220.0 / math.sqrt(3)
        z_base = (0.22**2 * 1000) / trafo_kva
        z_trafo_ohm = 0.04 * z_base
        imp = {"TRAFO": complex(0, z_trafo_ohm)}
        for n in ordem:
            if n == "TRAFO": continue
            i = pmap[n]; pai = df.at[i, "MONTANTE"]
            cabo = df.at[i, "CABO"]
            km = df.at[i, "METROS"] / 1000.0
            dados_z = CABOS_IMPEDANCIA.get(cabo, {'r': 1.0, 'x': 0.1})
            z_trecho = complex(dados_z['r'] * km, dados_z['x'] * km)
            imp[n] = imp.get(pai, complex(0,0)) + z_trecho
            z_mod = abs(imp[n])
            df.at[i, "ICC_KA"] = (v_fase / z_mod) / 1000.0 if z_mod > 0 else 0

    @staticmethod
    def balancear_fases(df: pd.DataFrame, ordem: List[str], pmap: Dict):
        fases = {'A': 0.0, 'B': 0.0, 'C': 0.0}
        for n in ordem:
            if n == "TRAFO": continue
            i = pmap[n]
            m = df.at[i, "MONO"]; b = df.at[i, "BIFÁSICO"]
            sugestao = []
            for _ in range(int(m)):
                fl = min(fases, key=fases.get); fases[fl] += 1; sugestao.append(f"1M->{fl}")
            for _ in range(int(b)):
                ps = [('A','B'), ('B','C'), ('C','A')]
                s = {p: fases[p[0]]+fases[p[1]] for p in ps}
                pl = min(s, key=s.get); fases[pl[0]]+=1; fases[pl[1]]+=1; sugestao.append(f"1B->{pl[0]}{pl[1]}")
            df.at[i, "SUGESTAO_BALANCEAMENTO"] = ", ".join(sugestao) if sugestao else "-"

    @staticmethod
    def calcular(df: pd.DataFrame, params: Dict, config_context: Dict) -> Tuple[pd.DataFrame, Dict, List[str]]:
        coef_cabos = config_context['cabos']; mapa_ips = config_context['ips']; perfis = config_context['perfis']
        nome_perfil = params.get("perfil", "Padrão (Urbano)")
        limites = perfis.get(nome_perfil, {"cqt_max": 6.0, "sobrecarga_max": 100.0, "metros_max": 3000.0, "clientes_max": 2000})

        if params.get("trafo_kva", 0) <= 0: return df, {}, ["Trafo deve ser > 0."]
        
        # --- 1. LIMPEZA CRÍTICA (Evita duplicação de colunas em re-calculos) ---
        # Remove colunas calculadas antigas para garantir que .at e .iloc retornem escalares
        cols_to_clean = list(COL_MAPPING.values()) + ["QTD_CLI", "POT_IP_KVA", "TOTAL_LOCAL_KVA", "CQT_TRECHO", "CQT_ACUMULADA", "ICC_KA", "SUGESTAO_BALANCEAMENTO", "CARGA_DIST_KVA", "CARGA_PONTUAL_KVA", "ACUMULADA_KVA"]
        df = df.drop(columns=[c for c in cols_to_clean if c in df.columns], errors='ignore')

        # --- 2. SANITIZAÇÃO E ÍNDICE ---
        df, err_sanit = ElectricalEngine.sanitizar(df, list(coef_cabos.keys()), list(mapa_ips.keys()), limites)
        df = df.reset_index(drop=True) # Reseta índice para garantir alinhamento posicional (0, 1, 2...)
        
        if err_sanit: return df, {}, err_sanit
        ok, err_topo = ElectricalEngine.validar_topologia(df)
        if not ok: return df, {}, err_topo

        # Inicializa colunas limpas
        cols = list(COL_MAPPING.keys()) + ["QTD_CLI", "POT_IP_KVA", "TOTAL_LOCAL_KVA", "CQT_TRECHO", "CQT_ACUMULADA", "ICC_KA", "SUGESTAO_BALANCEAMENTO"]
        for c in cols: df[c] = 0.0 if c != "SUGESTAO_BALANCEAMENTO" else ""
        avisos_diagnostico = []

        ordem = ElectricalEngine.calcular_ordem_topologica(df)
        if len(ordem) != len(df): return df, {}, ["Erro desconhecido na topologia."]

        m=df["MONO"].sum(); b=df["BIFÁSICO"].sum(); t=df["TRIFÁSICO"].sum(); te=df["TRI ESPECIAL"].sum()
        tc = int(m+b+t+te)
        if params["classe_tipo"] == "Automático":
            if tc == 0: cls = "A"
            elif (te>0 and te/tc > 0.1) or te >= 3: cls = "D"
            elif t>0 or (tc>0 and t/tc >= 0.2): cls = "C"
            elif (tc>0 and (b+t)/tc >= 0.4) or b>m: cls = "B"
            else: cls = "A"
        else: cls = params["classe_manual"]
        fd = ElectricalEngine.get_fator_demanda(tc, cls)

        df["QTD_CLI"] = df["MONO"] + df["BIFÁSICO"] + df["TRIFÁSICO"] + df["TRI ESPECIAL"]
        df["CARGA_DIST_KVA"] = df["QTD_CLI"] * fd
        
        fp = params.get("fp_ip", 0.92); fp = 0.92 if fp <= 0 else fp
        df["POT_IP_KVA"] = (df["TIPO_IP"].map(mapa_ips).fillna(0.0) / 1000.0)
        df["CARGA_PONTUAL_KVA"] = df["CARGA_ESP_KVA"] + (df["POT_IP_KVA"] * df["QTD_IP"])
        df["TOTAL_LOCAL_KVA"] = df["CARGA_DIST_KVA"] + df["CARGA_PONTUAL_KVA"]

        pmap = {p: i for i, p in enumerate(df['PONTO'])}
        accum = defaultdict(float)
        for n in reversed(ordem):
            i = pmap[n]; accum[n] += df.at[i, "TOTAL_LOCAL_KVA"]
            pai = df.at[i, "MONTANTE"]
            if pai: accum[pai] += accum[n]
            df.at[i, "ACUMULADA_KVA"] = accum[n]

        cqt_acumulada_dict = {"TRAFO": 0.0}
        for n in ordem:
            if n == "TRAFO": continue
            i = pmap[n]; pai = df.at[i, "MONTANTE"]
            
            # Cálculo de Queda
            carga_jusante_pura = accum[n] - df.at[i, "TOTAL_LOCAL_KVA"]
            carga_local_dist = df.at[i, "CARGA_DIST_KVA"]
            carga_local_pontual = df.at[i, "CARGA_PONTUAL_KVA"] 
            
            momento = (carga_local_dist / 2) + carga_local_pontual + carga_jusante_pura
            
            cabo = df.at[i, "CABO"]
            coef = coef_cabos.get(cabo, 0.0)
            if cabo not in coef_cabos and df.at[i, "METROS"] > 0:
                 avisos_diagnostico.append(f"ALERTA: Ponto '{n}' tem cabo sem coeficiente.")

            km = df.at[i, "METROS"] / UNIT_DIVISOR
            q_trecho = momento * km * coef
            
            tot_acumulado = cqt_acumulada_dict.get(pai, 0.0) + q_trecho
            cqt_acumulada_dict[n] = tot_acumulado
            
            df.at[i, "CQT_TRECHO"] = q_trecho
            df.at[i, "CQT_ACUMULADA"] = tot_acumulado
            
            if tot_acumulado > limites['cqt_max']:
                avisos_diagnostico.append(f"CRÍTICO: Ponto '{n}' QT {tot_acumulado:.2f}% > {limites['cqt_max']}%")

        ElectricalEngine.calcular_icc(df, ordem, pmap, params["trafo_kva"])
        ElectricalEngine.balancear_fases(df, ordem, pmap)

        df.rename(columns=COL_MAPPING, inplace=True)
        
        # --- 3. EXTRAÇÃO BLINDADA DA DEMANDA (SCALAR SAFE) ---
        trafo_idx = pmap.get("TRAFO")
        dem = 0.0
        if trafo_idx is not None:
            # Usa iloc para garantir acesso posicional, evitando problemas de label
            dem_raw = df.iloc[trafo_idx]["CARGA_ACUMULADA_G"]
            
            # Tratamento robusto para Series/Arrays (Evita ValueError: size > 1)
            try:
                if hasattr(dem_raw, 'item'):
                    if hasattr(dem_raw, 'size') and dem_raw.size > 1:
                        # Se por acaso houver duplicidade, pega o primeiro
                         dem = float(dem_raw.iloc[0])
                    else:
                        dem = float(dem_raw.item())
                else:
                    dem = float(dem_raw)
            except:
                dem = 0.0
        
        ocupacao = (dem / float(params["trafo_kva"])) * 100
        
        if ocupacao > limites['sobrecarga_max']:
            avisos_diagnostico.append(f"CRÍTICO: Trafo {ocupacao:.1f}% > {limites['sobrecarga_max']}%")

        kpis = {
            "classe": cls, "fator": fd, "demanda": dem, 
            "max_cqt": df["CQT_ACUMULADA"].max(), "clientes": tc,
            "ocupacao": ocupacao,
            "limites_usados": limites, 
            "cli_mono": int(m), "cli_bi": int(b), "cli_tri": int(t), "cli_esp": int(te)
        }
        return df, kpis, avisos_diagnostico