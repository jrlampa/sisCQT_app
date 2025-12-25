# siscqt_utils.py
import pandas as pd
import copy
from typing import List, Dict, Tuple
from siscqt_engine import ElectricalEngine


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


# --- IMPORTADOR DE PLANILHA CONCESSIONÁRIA FUNÇÃO AUXILIAR ---
def importar_planilha_concessionaria(
    arquivo_excel,
) -> Tuple[pd.DataFrame, float, Dict, str]:
    """
    Importador Blindado:
    Retorna: (DataFrame, Trafo_kVA, Config_Cabos, Classe_Detectada)
    """
    SHEET_BASE = "BASE DE DADOS"
    SHEET_CQT = "CQT ATUAL"
    SHEET_ATUAL = "ATUAL"

    def safe_float(val):
        try:
            if pd.isna(val):
                return 0.0
            s = str(val).replace(",", ".").strip()
            return float(s) if s else 0.0
        except:
            return 0.0

    def normalize_id(val):
        if pd.isna(val):
            return ""
        s = str(val).strip().upper()
        return s[:-2] if s.endswith(".0") else s

    # --- 1. CABOS ---
    config_cabos = {}
    try:
        df_base = pd.read_excel(arquivo_excel, sheet_name=SHEET_BASE, header=1)
        for _, row in df_base.iterrows():
            try:
                nome = str(row.iloc[0]).strip()
                coef = safe_float(row.iloc[1])
                if nome and nome != "nan" and coef > 0:
                    config_cabos[nome] = coef
            except:
                continue
    except:
        pass

    # --- FIM FUNÇÃO AUXILIAR ---

    # --- 2. TOPOLOGIA ---
    # Tenta ler trafo kVA antes do header real
    trafo_kva = 45.0
    try:
        df_raw_cqt = pd.read_excel(arquivo_excel, sheet_name=SHEET_CQT, header=None)
        trafo_kva = safe_float(df_raw_cqt.iloc[2, 5])
    except:
        pass

    # Localiza cabeçalho
    header_idx = 7
    try:
        df_raw_cqt = pd.read_excel(arquivo_excel, sheet_name=SHEET_CQT, header=None)
        idx_found = df_raw_cqt[
            df_raw_cqt[0].astype(str).str.upper().str.strip() == "TRECHO"
        ].index[0]
        header_idx = idx_found
    except:
        pass

    df_cqt = pd.read_excel(arquivo_excel, sheet_name=SHEET_CQT, header=header_idx)
    # Colunas esperadas: A(0)=TRECHO, B(1)=MONTANTE, C(2)=COMPRIMENTO, I(8)=CABO, L(11)=EXPECTED
    df_topology = df_cqt.iloc[:, [0, 1, 2, 8, 11]].copy()
    df_topology.columns = ["PONTO", "MONTANTE", "METROS", "CABO", "EXPECTED_CQT"]

    df_topology["PONTO"] = df_topology["PONTO"].apply(normalize_id)
    df_topology["MONTANTE"] = (
        df_topology["MONTANTE"]
        .apply(normalize_id)
        .replace({"NAN": "", "NONE": "", "0": ""})
    )

    def ajustar_metros(val):
        v = safe_float(val)
        return v * 100.0 if (v < 10.0 and v > 0) else v

    df_topology["METROS"] = df_topology["METROS"].apply(ajustar_metros)
    df_topology["CABO"] = df_topology["CABO"].astype(str).str.strip()
    df_topology["EXPECTED_CQT"] = df_topology["EXPECTED_CQT"].apply(safe_float)

    df_topology = df_topology[df_topology["PONTO"] != ""]
    # Garante que TRAFO é mantido ou criado
    mask_real = (df_topology["PONTO"] == "TRAFO") | (df_topology["METROS"] > 0.1)
    df_topology = df_topology[mask_real]

    if not df_topology[df_topology["PONTO"] == "TRAFO"].empty:
        # Se já existe, limpa montante
        df_topology.loc[
            df_topology["PONTO"] == "TRAFO", ["MONTANTE", "METROS", "CABO"]
        ] = ["", 0.0, ""]
    else:
        # Cria se não existe
        row_trafo = pd.DataFrame(
            [
                {
                    "PONTO": "TRAFO",
                    "MONTANTE": "",
                    "METROS": 0.0,
                    "CABO": "",
                    "EXPECTED_CQT": 0.0,
                }
            ]
        )
        df_topology = pd.concat([row_trafo, df_topology], ignore_index=True)

    # Corrige primeiro ponto pós-trafo se estiver orfão
    if len(df_topology) > 1:
        # Assume que a segunda linha (index 1, pois Trafo é 0 ou foi inserido) conecta no Trafo se estiver vazia
        # Lógica simplificada: pontos sem pai que não são trafo viram filhos do trafo
        for idx in df_topology.index:
            p = df_topology.at[idx, "PONTO"]
            m = df_topology.at[idx, "MONTANTE"]
            if p != "TRAFO" and m == "":
                df_topology.at[idx, "MONTANTE"] = "TRAFO"

    # --- 3. CARGAS E CLASSE ---
    df_raw_atual = pd.read_excel(arquivo_excel, sheet_name=SHEET_ATUAL, header=None)

    classe_encontrada = "A"
    try:
        # Procura "CLASSE X" nas primeiras 10 linhas/colunas
        subset = df_raw_atual.iloc[:10, :10].astype(str).values.flatten()
        for cell in subset:
            cell_u = cell.upper()
            if "CLASSE" in cell_u:
                for letra in ["A", "B", "C", "D", "E"]:
                    if (
                        f'"{letra}"' in cell_u
                        or f"'{letra}'" in cell_u
                        or f" {letra} " in cell_u
                        or cell_u.endswith(f" {letra}")
                    ):
                        classe_encontrada = letra
                        break
    except:
        pass

    header_atual_idx = 0
    try:
        for r in range(15):
            vals = df_raw_atual.iloc[r].astype(str).values
            if "TRECHO" in vals or "PONTO" in vals:
                header_atual_idx = r
                break
    except:
        pass

    df_atual = pd.read_excel(
        arquivo_excel, sheet_name=SHEET_ATUAL, header=header_atual_idx
    )
    try:
        # Colunas: J(9)=PONTO, L(11)=MONO, M(12)=BI, N(13)=TRI, O(14)=TRI_ESP
        # IPs: S(18)..W(22)
        data_loads = df_atual.iloc[:, [9, 11, 12, 13, 14]].copy()
        data_loads.columns = ["PONTO", "MONO", "BI", "TRI", "TRI_ESP"]
        data_loads["IP70"] = df_atual.iloc[:, 18]
        data_loads["IP80"] = df_atual.iloc[:, 19]
        data_loads["IP150"] = df_atual.iloc[:, 20]
        data_loads["IP250"] = df_atual.iloc[:, 21]
        data_loads["IP400"] = df_atual.iloc[:, 22]
    except:
        return df_topology, trafo_kva, config_cabos, classe_encontrada

    data_loads["PONTO"] = data_loads["PONTO"].apply(normalize_id)
    data_loads = data_loads[data_loads["PONTO"] != ""]

    cols_num = [
        "MONO",
        "BI",
        "TRI",
        "TRI_ESP",
        "IP70",
        "IP80",
        "IP150",
        "IP250",
        "IP400",
    ]
    for c in cols_num:
        data_loads[c] = data_loads[c].apply(safe_float)

    data_loads["SOMA"] = data_loads[cols_num].sum(axis=1)
    data_loads = data_loads[data_loads["SOMA"] > 0]

    pontos_validos = set(df_topology["PONTO"].unique())
    data_loads = data_loads[data_loads["PONTO"].isin(pontos_validos)]

    pot_ips = {"IP70": 0.07, "IP80": 0.08, "IP150": 0.15, "IP250": 0.25, "IP400": 0.40}

    def calc_ip_kva(row):
        t = 0.0
        for k, v in pot_ips.items():
            t += row.get(k, 0) * v
        return t

    data_loads["CARGA_ESP_KVA"] = data_loads.apply(calc_ip_kva, axis=1)

    # 4. MERGE
    df_final = pd.merge(df_topology, data_loads, on="PONTO", how="left")
    cols_fill = ["MONO", "BI", "TRI", "TRI_ESP", "CARGA_ESP_KVA"]
    df_final[cols_fill] = df_final[cols_fill].fillna(0)

    df_final = df_final.rename(
        columns={"TRI_ESP": "TRI ESPECIAL", "BI": "BIFÁSICO", "TRI": "TRIFÁSICO"}
    )
    df_final["TIPO_IP"] = "Sem IP"
    df_final["QTD_IP"] = 0

    # 5. DEDUPLICAÇÃO FINAL (Segurança contra merges duplicados)
    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

    return df_final, trafo_kva, config_cabos, classe_encontrada
