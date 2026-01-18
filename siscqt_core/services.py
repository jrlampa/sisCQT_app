# siscqt_core/services.py
import math
from collections import deque, defaultdict
from typing import Tuple, Dict, List, Optional, Any
import pandas as pd

from .siscqt_constantes import ( # Adjusted import
    UNIT_DIVISOR,
    COL_MAPPING,
    TABELA_DEMANDA,
    CABOS_IMPEDANCIA,
)
from .normalizacao_dados import sanitizar # Adjusted import


class ElectricalEngine:
    """Motor de cálculo elétrico para sistemas de distribuição em baixa tensão."""

    @staticmethod
    def get_template_dataframe() -> pd.DataFrame:
        """Retorna DataFrame com estrutura padrão para entrada de dados."""
        return pd.DataFrame(
            {
                "PONTO": ["TRAFO"],
                "MONTANTE": [""],
                "METROS": [0.0],
                "CABO": [""],
                "MONO": [0],
                "BIFÁSICO": [0],
                "TRIFÁSICO": [0],
                "TRI ESPECIAL": [0],
                "CARGA_ESP_KVA": [0.0],
                "TIPO_IP": ["Sem IP"],
                "QTD_IP": [0],
            }
        )

    @staticmethod
    def validar_preenchimento(df: pd.DataFrame, config_ips: Dict = None) -> List[str]:
        """
        Valida a integridade topológica dos dados.
        Nota: A sanitização de tipos já deve ter sido feita via normalizacao_dados.sanitizar.
        """
        erros = []
        if df.empty:
            return ["A tabela está vazia. Insira dados para calcular."]

        # 1. Verifica Pontos Duplicados
        pontos_series = df["PONTO"]  # Já normalizado (string/upper)
        if pontos_series.duplicated().any():
            dups = pontos_series[pontos_series.duplicated()].unique()
            erros.append(f"Existem pontos com nomes duplicados: {', '.join(dups)}")

        # 2. Verifica Existência do TRAFO
        if "TRAFO" not in pontos_series.values:
            erros.append(
                "O ponto de origem 'TRAFO' não foi encontrado na coluna PONTO."
            )

        # 3. Verifica Conectividade (Montantes Orfãos)
        set_pontos = set(pontos_series.values)

        for idx, row in df.iterrows():
            p = row["PONTO"]
            m = row["MONTANTE"]

            if p == "TRAFO":
                continue

            if m not in set_pontos:
                erros.append(
                    f"O ponto '{p}' tem um montante inválido ou inexistente: '{m}'"
                )

        return erros

    @staticmethod
    def sugerir_centro_carga(df: pd.DataFrame) -> dict:
        """Calcula o Baricentro Elétrico da rede."""
        if df.empty:
            return {"ponto_proximo": "N/A", "msg": "Tabela de dados vazia."}

        # Garante normalização caso chamado externamente sem passar pelo calcular
        df_calc, _ = sanitizar(df)
        col_carga_final = "CARGA_CALCULADA_TEMP"

        # Lógica de Prioridade de Carga
        if "TOTAL_LOCAL_KVA" in df_calc.columns:
            df_calc[col_carga_final] = df_calc["TOTAL_LOCAL_KVA"]
        elif (
            "CARGA_DIST_KVA" in df_calc.columns
            and "CARGA_PONTUAL_KVA" in df_calc.columns
        ):
            df_calc[col_carga_final] = (
                df_calc["CARGA_DIST_KVA"] + df_calc["CARGA_PONTUAL_KVA"]
            )
        elif "CARGA_ESP_KVA" in df_calc.columns:
            df_calc[col_carga_final] = df_calc["CARGA_ESP_KVA"]
        else:
            return {
                "ponto_proximo": "N/A",
                "msg": "Colunas de carga (TOTAL_LOCAL_KVA ou componentes) não encontradas.",
            }

        try:
            topologia = {}
            for _, row in df_calc.iterrows():
                p = row["PONTO"]
                if not p:
                    continue
                m = row["MONTANTE"]
                d_trecho = row["METROS"]  # Já numérico
                c_no = row[col_carga_final]
                topologia[p] = {"pai": m, "d_seg": d_trecho, "carga": c_no}

            # ... (Lógica de cálculo do baricentro mantida inalterada) ...
            dist_cache = {}

            def _get_dist_acumulada(no, visitados):
                if no == "TRAFO" or not no:
                    return 0.0
                if no in dist_cache:
                    return dist_cache[no]
                if no in visitados:
                    return 0.0
                dados = topologia.get(no)
                if not dados:
                    return 0.0
                visitados.add(no)
                dist_pai = _get_dist_acumulada(dados["pai"], visitados)
                dist_total = dist_pai + dados["d_seg"]
                dist_cache[no] = dist_total
                visitados.remove(no)
                return dist_total

            soma_momento = 0.0
            soma_carga = 0.0
            mapa_analise = []
            nos_validos = [p for p in topologia.keys() if p != "TRAFO"]

            for p in nos_validos:
                dist_real = _get_dist_acumulada(p, set())
                carga = topologia[p]["carga"]
                mapa_analise.append((p, dist_real))
                if carga > 0:
                    soma_carga += carga
                    soma_momento += carga * dist_real

            if soma_carga <= 0:
                return {
                    "ponto_proximo": "TRAFO",
                    "distancia_ideal": 0.0,
                    "msg": "Rede sem carga ativa.",
                }

            dist_ideal = soma_momento / soma_carga
            melhor_ponto = min(mapa_analise, key=lambda x: abs(x[1] - dist_ideal))[0]

            return {
                "ponto_proximo": melhor_ponto,
                "distancia_ideal": dist_ideal,
                "msg": f"Baricentro (D={dist_ideal:.1f}m do Trafo) -> Ponto sugerido: {melhor_ponto}",
            }

        except Exception as e:
            return {
                "ponto_proximo": "ERRO",
                "distancia_ideal": 0.0,
                "msg": f"Falha no cálculo: {str(e)}",
            }

    @staticmethod
    def validar_topologia(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Verifica integridade da rede (ciclos, nós isolados, conectividade)."""
        # (Lógica original de validar_topologia mantida)
        erros: List[str] = []
        if df["PONTO"].duplicated().any():
            dups = df[df["PONTO"].duplicated()]["PONTO"].unique().tolist()
            return False, [f"Pontos duplicados: {dups}"]

        nodes = set(df["PONTO"])
        adj = defaultdict(list)
        for _, r in df.iterrows():
            p, m = r["PONTO"], r["MONTANTE"]
            if p == "TRAFO":
                continue
            if not m:
                erros.append(f"Ponto '{p}' sem montante.")
            elif m not in nodes:
                erros.append(f"Ponto '{p}' aponta para montante inexistente '{m}'.")
            else:
                adj[m].append(p)

        if erros:
            return False, erros

        vis, stack = set(), set()

        def _has_cycle(u):
            vis.add(u)
            stack.add(u)
            for v in adj[u]:
                if v not in vis:
                    if _has_cycle(v):
                        return True
                elif v in stack:
                    return True
            stack.remove(u)
            return False

        for n in nodes:
            if n not in vis:
                if _has_cycle(n):
                    return False, [f"Ciclo detectado na rede (loop em '{n}')."]

        q = deque(["TRAFO"])
        reached = {"TRAFO"}
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in reached:
                    reached.add(v)
                    q.append(v)

        orphans = nodes - reached
        if orphans:
            return False, [f"Pontos isolados do Trafo: {list(orphans)}"]
        return True, []

    @staticmethod
    def calcular_ordem_topologica(df: pd.DataFrame) -> List[str]:
        # (Mantém implementação original de ordenação)
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
    def get_fator_demanda(tc: int, cls: str) -> float:
        idx = {"A": 0, "B": 1, "C": 2, "D": 3}.get(cls, 0)
        for mn, mx, *v in TABELA_DEMANDA:
            if mn <= tc <= mx:
                return v[idx]
        return [0.5, 0.8, 1.3, 2.0][idx]

    @staticmethod
    def calcular_icc(
        df: pd.DataFrame, ordem: List[str], pmap: Dict[str, int], trafo_kva: float
    ) -> None:
        v_fase = 220.0 / math.sqrt(3)
        z_base = (0.22**2 * 1000) / trafo_kva if trafo_kva > 0 else 1.0
        z_trafo_ohm = 0.04 * z_base
        imp = {"TRAFO": complex(0, z_trafo_ohm)}
        for n in ordem:
            if n == "TRAFO":
                continue
            i = pmap[n]
            pai = df.at[i, "MONTANTE"]
            if pai not in imp:
                continue
            cabo = df.at[i, "CABO"]
            km = df.at[i, "METROS"] / 1000.0
            dados_z = CABOS_IMPEDANCIA.get(cabo, {"r": 1.0, "x": 0.1})
            z_trecho = complex(dados_z["r"] * km, dados_z["x"] * km)
            imp[n] = imp[pai] + z_trecho
            z_mod = abs(imp[n])
            df.at[i, "ICC_KA"] = (v_fase / z_mod) / 1000.0 if z_mod > 0 else 0

    @staticmethod
    def _obter_fase_monofasica_ideal(acumuladores: Dict[str, float]) -> str:
        return min(acumuladores, key=acumuladores.get)

    @staticmethod
    def _obter_fases_bifasicas_ideais(acumuladores: Dict[str, float]) -> str:
        combinacoes = {
            "AB": acumuladores["A"] + acumuladores["B"],
            "BC": acumuladores["B"] + acumuladores["C"],
            "CA": acumuladores["C"] + acumuladores["A"],
        }
        return min(combinacoes, key=combinacoes.get)

    @staticmethod
    def balancear_fases(
        df: pd.DataFrame, ordem: List[str], pmap: Dict[str, int]
    ) -> None:
        # (Lógica original de balanceamento mantida, garantindo execução sobre df já sanitizado)
        acumuladores = {"A": 0.0, "B": 0.0, "C": 0.0}
        PESO_MONO, PESO_BI, PESO_TRI, PESO_TRI_ESP = 1.5, 2.5, 4.0, 6.0
        if "SUGESTAO_BALANCEAMENTO" not in df.columns:
            df["SUGESTAO_BALANCEAMENTO"] = ""
        for n in ordem:
            if n == "TRAFO":
                continue
            idx = pmap.get(n)
            if idx is None:
                continue
            try:
                qtd_mono = float(df.at[idx, "MONO"] or 0)
                qtd_bi = float(df.at[idx, "BIFÁSICO"] or 0)
                qtd_tri = float(df.at[idx, "TRIFÁSICO"] or 0)
                qtd_tri_esp = float(df.at[idx, "TRI ESPECIAL"] or 0)
            except:
                continue

            sugestao_no = []
            total_tri = (qtd_tri * PESO_TRI) + (qtd_tri_esp * PESO_TRI_ESP)
            if total_tri > 0:
                p = total_tri / 3.0
                acumuladores["A"] += p
                acumuladores["B"] += p
                acumuladores["C"] += p
                if qtd_mono == 0 and qtd_bi == 0:
                    sugestao_no.append("Tri: ABC")

            for _ in range(int(qtd_bi)):
                f = ElectricalEngine._obter_fases_bifasicas_ideais(acumuladores)
                p = PESO_BI / 2.0
                for ph in f:
                    acumuladores[ph] += p
                sugestao_no.append(f"Bi: {f}")

            for _ in range(int(qtd_mono)):
                f = ElectricalEngine._obter_fase_monofasica_ideal(acumuladores)
                acumuladores[f] += PESO_MONO
                sugestao_no.append(f"Mono: {f}")

            df.at[idx, "SUGESTAO_BALANCEAMENTO"] = (
                " | ".join(sugestao_no) if sugestao_no else "OK"
            )

    @staticmethod
    def calcular(
        df: pd.DataFrame, params: Dict, config_context: Dict
    ) -> Tuple[pd.DataFrame, Dict, List[str]]:
        """
        Executa cálculo elétrico.
        Utiliza `normalizacao_dados.sanitizar` para garantir integridade inicial.
        """
        coef_cabos = config_context.get("cabos", {})
        mapa_ips = config_context.get("ips", {})
        perfis = config_context.get("perfis", {})
        nome_perfil = params.get("perfil", "Padrão (Urbano)")
        limites = perfis.get(nome_perfil, {"cqt_max": 6.0, "sobrecarga_max": 100.0})

        if params.get("trafo_kva", 0) <= 0:
            return df, {}, ["Trafo deve ser > 0."]

        # Remove colunas calculadas anteriores
        cols_to_clean = list(COL_MAPPING.values()) + [
            "QTD_CLI",
            "POT_IP_KVA",
            "TOTAL_LOCAL_KVA",
            "CQT_TRECHO",
            "CQT_ACUMULADA",
            "ICC_KA",
            "SUGESTAO_BALANCEAMENTO",
            "CARGA_DIST_KVA",
            "CARGA_PONTUAL_KVA",
            "ACUMULADA_KVA",
        ]
        df = df.drop(
            columns=[c for c in cols_to_clean if c in df.columns], errors="ignore"
        )

        # --- CENTRALIZAÇÃO DA NORMALIZAÇÃO ---
        df, err_sanit = sanitizar(
            df, list(coef_cabos.keys()), list(mapa_ips.keys()), limites
        )
        df = df.reset_index(drop=True)

        if err_sanit:
            return df, {}, err_sanit

        # Validação Topológica (Lógica de Grafo)
        ok, err_topo = ElectricalEngine.validar_topologia(df)
        if not ok:
            return df, {}, err_topo

        # Inicializa colunas de cálculo
        new_cols = [
            "QTD_CLI",
            "POT_IP_KVA",
            "TOTAL_LOCAL_KVA",
            "CQT_TRECHO",
            "CQT_ACUMULADA",
            "ICC_KA",
            "SUGESTAO_BALANCEAMENTO",
            "CARGA_DIST_KVA",
            "CARGA_PONTUAL_KVA",
            "ACUMULADA_KVA",
        ]
        for c in new_cols:
            df[c] = 0.0 if c != "SUGESTAO_BALANCEAMENTO" else ""

        avisos_diagnostico = []
        ordem = ElectricalEngine.calcular_ordem_topologica(df)
        if len(ordem) != len(df):
            return df, {}, ["Erro desconhecido na topologia."]

        # --- Lógica de Cálculo (Mantida) ---
        m = df["MONO"].sum()
        b = df["BIFÁSICO"].sum()
        t = df["TRIFÁSICO"].sum()
        te = df["TRI ESPECIAL"].sum()
        tc = int(m + b + t + te)

        cls = "A"
        if params.get("classe_tipo") == "Automático":
            if tc == 0:
                cls = "A"
            elif (te > 0 and te / tc > 0.1) or te >= 3:
                cls = "D"
            elif t > 0 or (tc > 0 and t / tc >= 0.2):
                cls = "C"
            elif (tc > 0 and (b + t) / tc >= 0.4) or b > m:
                cls = "B"
        else:
            cls = params.get("classe_manual", "A")

        fd = ElectricalEngine.get_fator_demanda(tc, cls)
        df["QTD_CLI"] = (
            df["MONO"] + df["BIFÁSICO"] + df["TRIFÁSICO"] + df["TRI ESPECIAL"]
        )
        df["CARGA_DIST_KVA"] = df["QTD_CLI"] * fd

        fp = params.get("fp_ip", 0.92)
        fp = 0.92 if fp <= 0 else fp
        df["POT_IP_KVA"] = df["TIPO_IP"].map(mapa_ips).fillna(0.0) / 1000.0
        df["CARGA_PONTUAL_KVA"] = df["CARGA_ESP_KVA"] + (
            df["POT_IP_KVA"] * df["QTD_IP"]
        )
        df["TOTAL_LOCAL_KVA"] = df["CARGA_DIST_KVA"] + df["CARGA_PONTUAL_KVA"]

        pmap = {p: i for i, p in enumerate(df["PONTO"])}
        accum = defaultdict(float)
        for n in reversed(ordem):
            i = pmap[n]
            accum[n] += df.at[i, "TOTAL_LOCAL_KVA"]
            pai = df.at[i, "MONTANTE"]
            if pai:
                accum[pai] += accum[n]
            df.at[i, "ACUMULADA_KVA"] = accum[n]

        cqt_acumulada_dict = {"TRAFO": 0.0}
        for n in ordem:
            if n == "TRAFO":
                continue
            i = pmap[n]
            pai = df.at[i, "MONTANTE"]

            carga_jusante = accum[n] - df.at[i, "TOTAL_LOCAL_KVA"]
            momento = (
                (df.at[i, "CARGA_DIST_KVA"] / 2)
                + df.at[i, "CARGA_PONTUAL_KVA"]
                + carga_jusante
            )

            cabo = df.at[i, "CABO"]
            coef = coef_cabos.get(cabo, 0.0)
            if cabo and cabo not in coef_cabos and df.at[i, "METROS"] > 0:
                avisos_diagnostico.append(
                    f"ALERTA: Ponto '{n}' tem cabo desconhecido '{cabo}'."
                )

            km = df.at[i, "METROS"] / UNIT_DIVISOR
            q_trecho = momento * km * coef
            tot = cqt_acumulada_dict.get(pai, 0.0) + q_trecho
            cqt_acumulada_dict[n] = tot
            df.at[i, "CQT_TRECHO"] = q_trecho
            df.at[i, "CQT_ACUMULADA"] = tot

            if tot > limites["cqt_max"]:
                avisos_diagnostico.append(
                    f"CRÍTICO: Ponto '{n}' QT {tot:.2f}% > {limites['cqt_max']}%"
                )

        ElectricalEngine.calcular_icc(df, ordem, pmap, params.get("trafo_kva", 75))
        df.rename(columns=COL_MAPPING, inplace=True)

        trafo_idx = pmap.get("TRAFO")
        dem = (
            df.at[trafo_idx, "CARGA_ACUMULADA_G"]
            if trafo_idx is not None and "CARGA_ACUMULADA_G" in df.columns
            else 0.0
        )
        ocupacao = (dem / float(params.get("trafo_kva", 75))) * 100
        if ocupacao > limites["sobrecarga_max"]:
            avisos_diagnostico.append(
                f"CRÍTICO: Trafo {ocupacao:.1f}% > {limites['sobrecarga_max']}%"
            )

        dados_baricentro = ElectricalEngine.sugerir_centro_carga(df)

        kpis = {
            "classe": cls,
            "fator": fd,
            "demanda": dem,
            "max_cqt": df["CQT_ACUMULADA"].max() if "CQT_ACUMULADA" in df else 0.0,
            "clientes": tc,
            "ocupacao": ocupacao,
            "limites_usados": limites,
            "baricentro": dados_baricentro,
        }
        return df, kpis, avisos_diagnostico


class DiagnosticoEngenharia:
    """
    Gera recomendações técnicas baseadas na leitura estática do circuito.
    Não realiza simulações, apenas interpretação de engenharia.
    """

    @staticmethod
    def analisar_baricentro(df: pd.DataFrame, trafo_kva: float) -> Dict:
        """
        Analisa se o Trafo está bem posicionado eletricalmente.
        Lógica Conservadora: Se houver equilíbrio entre troncos, sugere manter.
        """
        try:
            # Identifica saídas imediatas do Trafo
            saidas = df[df["MONTANTE"] == "TRAFO"]
            if saidas.empty:
                return {"status": "OK", "msg": "Trafo sem cargas conectadas."}

            # Analisa o balanço de carga (Momentos elétricos imediatos)
            # Usa 'ACUMULADA_KVA' que representa o peso de todo o ramo jusante
            cargas_troncos = []
            total_sistema = 0.0

            for _, row in saidas.iterrows():
                k = row.get("ACUMULADA_KVA", 0.0)
                ponto = row.get("PONTO", "?")
                cargas_troncos.append({"ponto": ponto, "kva": k})
                total_sistema += k

            if total_sistema == 0:
                return {"status": "OK", "msg": "Sem carga ativa."}

            # Ordena troncos por carga
            cargas_troncos.sort(key=lambda x: x["kva"], reverse=True)
            maior_tronco = cargas_troncos[0]

            # Critério de "Já no Baricentro":
            # 1. Se tem mais de 1 saída
            # 2. E o maior tronco não detém mais que 60% da carga total (indica certo equilíbrio)
            is_balanced = (len(cargas_troncos) > 1) and (
                maior_tronco["kva"] / total_sistema < 0.60
            )

            if is_balanced:
                msg = (
                    "O Transformador encontra-se posicionado próximo ao baricentro elétrico ideal. "
                    "Os troncos de saída apresentam distribuição de carga equilibrada, não justificando "
                    "deslocamento físico do equipamento."
                )
                return {"status": "OTIMIZADO", "msg": msg}
            else:
                # Sugere deslocamento na direção do tronco mais pesado
                msg = (
                    f"Sugestão de Reposicionamento: O tronco '{maior_tronco['ponto']}' concentra "
                    f"aprox. {(maior_tronco['kva']/total_sistema)*100:.0f}% da carga total. "
                    f"Avaliar deslocamento do Trafo na direção deste ponto para reduzir momentos elétricos."
                )
                return {"status": "SUGESTAO", "msg": msg}

        except Exception as e:
            return {
                "status": "ERRO",
                "msg": f"Não foi possível calcular baricentro: {str(e)}",
            }

    @staticmethod
    def gerar_recomendacoes(
        df: pd.DataFrame, kpis: Dict, avisos: List[str]
    ) -> List[Dict]:
        """Gera lista de alternativas de engenharia (Texto)."""
        recs = []

        ocupacao = kpis.get("ocupacao", 0)
        max_cqt = kpis.get("max_cqt", 0)

        # 1. Análise de Sobrecarga
        if ocupacao > 100:
            recs.append(
                {
                    "titulo": "Substituição de Transformador",
                    "texto": f"O trafo opera com {ocupacao:.1f}% de ocupação. Avaliar substituição por potência comercial imediatamente superior ou alívio de carga para outro circuito.",
                }
            )
            recs.append(
                {
                    "titulo": "Divisão de Circuito",
                    "texto": "Considerar dividir a Área de Atuação (AA) e inserir novo posto de transformação para reduzir o raio de atendimento.",
                }
            )

        # 2. Análise de Queda de Tensão
        if max_cqt > kpis.get("limites_usados", {}).get("cqt_max", 6.0):
            recs.append(
                {
                    "titulo": "Recondutoração (Troncos Principais)",
                    "texto": "Identificar trechos com maior 'Momento Elétrico' (Carga x Distância) partindo do Trafo e aplicar cabos de maior seção. (Utilize a aba 'Simulação' para testar).",
                }
            )
            recs.append(
                {
                    "titulo": "Redistribuição de Cargas (Balanceamento)",
                    "texto": "Verificar se há desequilíbrio severo entre fases que esteja agravando a queda de tensão em uma fase específica.",
                }
            )

        # 3. Baricentro
        # (Adicionado dinamicamente na UI, mas a lógica está acima)

        return recs


class SimuladorReadequacao:
    """
    Simulador de Recondutoração Top-Down Estrito.
    Princípio: Trafo -> Ponta.
    Nunca melhora a ponta se o montante não estiver resolvido/adequado.
    """

    @staticmethod
    def _obter_cabo_melhor(atual: str, disponiveis: Dict[str, float]) -> str:
        """Retorna o nome do cabo imediatamente melhor (menor coef) que o atual, se houver."""
        coef_atual = disponiveis.get(atual, 999.0)

        # Lista de candidatos melhores (coef menor)
        candidatos = [
            (nome, coef)
            for nome, coef in disponiveis.items()
            if coef < (coef_atual - 0.0001)
        ]

        if not candidatos:
            return None  # Já é o melhor cabo ou não tem opção

        # Ordena por coeficiente decrescente (do mais próximo do atual para o melhor absoluto)
        # Queremos o "next best", ou seja, o maior coeficiente que ainda seja menor que o atual
        candidatos.sort(key=lambda x: x[1], reverse=True)

        return candidatos[0][0]  # Nome do cabo

    @staticmethod
    def _get_path_to_source(df: pd.DataFrame, target_point: str) -> List[int]:
        """Retorna lista de INDICES do dataframe do Trafo até o ponto alvo."""
        path_indices = []
        curr = target_point

        # Cria mapa seguro
        map_montante = dict(zip(df["PONTO"], df["MONTANTE"]))
        map_idx = dict(zip(df["PONTO"], df.index))

        seen = set()
        while curr and curr != "TRAFO":
            if curr in seen:
                break  # Loop prevention
            seen.add(curr)

            idx = map_idx.get(curr)
            if idx is not None:
                path_indices.append(idx)

            curr = map_montante.get(curr)

        return list(reversed(path_indices))  # [Idx_prox_trafo, ..., Idx_target]

    @staticmethod
    def executar(
        nome_origem: str,
        df_base: pd.DataFrame,
        params: Dict,
        config_full: Dict,
        cabos_habilitados_nomes: List[str],
    ):
        """
        Executa simulação iterativa Top-Down.
        """
        # 1. Preparação
        df_sim = df_base.copy()

        # Filtra cabos disponíveis e seus coeficientes
        cabos_cfg = config_full["cabos"]  # {nome: {'coef': x, ...}}
        mapa_coefs_habilitados = {}
        for nome in cabos_habilitados_nomes:
            dados = cabos_cfg.get(nome)
            if dados:
                c = dados["coef"] if isinstance(dados, dict) else dados
                mapa_coefs_habilitados[nome] = c

        limites = config_full["perfis"].get(params.get("perfil", ""), {})
        lim_cqt = limites.get("cqt_max", 6.0)

        log_changes = {}  # {ponto: "Cabo A -> Cabo B"}
        iteration = 0
        max_iter = 20  # Evitar loop infinito

        resolved = False

        # 2. Loop de Correção
        while iteration < max_iter:
            iteration += 1

            # A. Calcula estado atual
            df_calc, kpis, _ = ElectricalEngine.calcular(df_sim, params, config_full)
            max_q = kpis["max_cqt"]

            if max_q <= lim_cqt:
                resolved = True
                break

            # B. Identifica o "Pior Ponto" (Gargalo do sistema)
            idx_worst = df_calc["CQT_ACUMULADA"].idxmax()
            ponto_worst = df_calc.at[idx_worst, "PONTO"]

            # C. Traça rota Trafo -> Pior Ponto
            # Retorna índices na ordem topológica correta
            caminho_indices = SimuladorReadequacao._get_path_to_source(
                df_calc, ponto_worst
            )

            change_made_in_this_pass = False

            # D. Tenta melhorar o PRIMEIRO trecho da rota que ainda pode ser melhorado
            # (Estratégia Gulosa Top-Down)
            for idx in caminho_indices:
                cabo_atual = df_sim.at[idx, "CABO"]

                # Tenta pegar o próximo cabo melhor
                novo_cabo = SimuladorReadequacao._obter_cabo_melhor(
                    cabo_atual, mapa_coefs_habilitados
                )

                if novo_cabo:
                    # Aplica mudança
                    df_sim.at[idx, "CABO"] = novo_cabo
                    ponto = df_sim.at[idx, "PONTO"]
                    log_changes[ponto] = f"{cabo_atual} -> {novo_cabo}"
                    change_made_in_this_pass = True

                    # PARA AQUI. Recalcula tudo.
                    # Motivo: Melhorar um trecho tronco pode resolver todos os problemas jusante.
                    # Não queremos superdimensionar a ponta se o tronco resolver.
                    break

            if not change_made_in_this_pass:
                # Se percorreu todo o caminho crítico e não conseguiu melhorar nada
                # (ex: tudo já está no melhor cabo disponível), aborta.
                break

        # 3. Resultado Final
        df_final, kpis_final, _ = ElectricalEngine.calcular(df_sim, params, config_full)

        msg_resultado = (
            "Simulação concluída com sucesso."
            if resolved
            else "Limite físico dos cabos atingido (Critérios não atendidos)."
        )

        return {
            "df": df_final,
            "kpis": kpis_final,
            "log": log_changes,
            "iteracoes": iteration,
            "msg": msg_resultado,
            "resolvido": resolved,
        }