# siscqt_utils.py
import pandas as pd
import copy
from typing import List, Dict, Tuple
from siscqt_engine import ElectricalEngine

# IMPORTAÇÃO DA NORMALIZAÇÃO CENTRALIZADA
from normalizacao_dados import sanitizar


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
) -> Tuple[pd.DataFrame, float, Dict, str, List[str]]:
    """
    Importador Blindado com Normalização Centralizada.
    Lê planilhas padrão da concessionária, extrai topologia e cargas,
    e aplica sanitização rigorosa.

    Retorna: (DataFrame_Normalizado, Trafo_kVA, Config_Cabos, Classe, Lista_Erros)
    """
    SHEET_BASE = "BASE DE DADOS"
    SHEET_CQT = "CQT ATUAL"
    SHEET_ATUAL = "ATUAL"

    erros_importacao = []

    # --- 1. CABOS (Extração de Metadados) ---
    config_cabos = {}
    try:
        df_base = pd.read_excel(arquivo_excel, sheet_name=SHEET_BASE, header=1)
        # Normalização leve apenas para extrair configs (não afeta o DF principal ainda)
        for _, row in df_base.iterrows():
            try:
                nome = str(row.iloc[0]).strip()
                # Conversão segura local apenas para config
                coef_str = str(row.iloc[1]).replace(",", ".")
                coef = float(coef_str) if coef_str and coef_str != "nan" else 0.0

                if nome and nome.lower() != "nan" and coef > 0:
                    config_cabos[nome] = coef
            except:
                continue
    except Exception as e:
        erros_importacao.append(
            f"Aviso: Não foi possível ler a aba '{SHEET_BASE}'. Usando cabos padrão. ({str(e)})"
        )

    # --- 2. TOPOLOGIA (Extração Estrutural) ---
    trafo_kva = 45.0

    # Tentativa de ler KVA do cabeçalho
    try:
        df_head = pd.read_excel(
            arquivo_excel, sheet_name=SHEET_CQT, header=None, nrows=10
        )
        # Procura célula com valor numérico compatível com trafo na região superior
        val = str(df_head.iloc[2, 5]).replace(",", ".")
        trafo_kva = float(val)
    except:
        pass  # Mantém default 45.0

    # Localização dinâmica do cabeçalho
    header_idx = 7
    try:
        df_raw_scan = pd.read_excel(
            arquivo_excel, sheet_name=SHEET_CQT, header=None, nrows=20
        )
        # Procura linha que contenha "TRECHO"
        for idx, row in df_raw_scan.iterrows():
            if "TRECHO" in [str(v).upper().strip() for v in row.values]:
                header_idx = idx
                break
    except:
        pass

    try:
        df_cqt = pd.read_excel(arquivo_excel, sheet_name=SHEET_CQT, header=header_idx)
        # Mapeamento de colunas por índice (Layout Padrão Concessionária)
        # A(0)=PONTO, B(1)=MONTANTE, C(2)=METROS, I(8)=CABO
        df_topology = df_cqt.iloc[:, [0, 1, 2, 8]].copy()
        df_topology.columns = ["PONTO", "MONTANTE", "METROS", "CABO"]

        # Ajuste específico de unidade (m -> hm) antes da sanitização
        # A sanitização trata tipos, mas não regras de negócio como conversão de unidade específica desta planilha
        def _ajustar_unidade_metros(val):
            try:
                s = str(val).replace(",", ".")
                v = float(s)
                # Se vier em hectômetros (ex: 0.4) converte para metros (40.0)
                # Heurística: Trechos < 10m costumam ser HM nesta planilha
                return v * 100.0 if (v < 10.0 and v > 0) else v
            except:
                return 0.0

        df_topology["METROS"] = df_topology["METROS"].apply(_ajustar_unidade_metros)

    except Exception as e:
        return (
            pd.DataFrame(),
            trafo_kva,
            config_cabos,
            "A",
            [f"Erro crítico ao ler topologia: {str(e)}"],
        )

    # --- 3. CARGAS E CLASSE (Extração de Demanda) ---
    try:
        # Leitura para buscar Classe
        df_raw_atual = pd.read_excel(
            arquivo_excel, sheet_name=SHEET_ATUAL, header=None, nrows=15
        )
        classe_encontrada = "A"

        # Varredura por string de classe
        texto_dump = df_raw_atual.to_string().upper()
        for cls in ["A", "B", "C", "D", "E"]:
            if f"CLASSE {cls}" in texto_dump or f'CLASSE "{cls}"' in texto_dump:
                classe_encontrada = cls
                break

        # Localiza header da tabela de cargas
        header_atual_idx = 0
        for r in range(len(df_raw_atual)):
            vals = [str(v).upper() for v in df_raw_atual.iloc[r].values]
            if "TRECHO" in vals or "PONTO" in vals:
                header_atual_idx = r
                break

        df_atual = pd.read_excel(
            arquivo_excel, sheet_name=SHEET_ATUAL, header=header_atual_idx
        )

        # Mapeamento de colunas de carga (Índices fixos do modelo)
        # J(9)=PONTO, L(11)=MONO, M(12)=BI, N(13)=TRI, O(14)=TRI_ESP
        # IPs: S(18)..W(22)
        cols_indices = [9, 11, 12, 13, 14, 18, 19, 20, 21, 22]
        data_loads = df_atual.iloc[:, cols_indices].copy()
        data_loads.columns = [
            "PONTO",
            "MONO",
            "BIFÁSICO",
            "TRIFÁSICO",
            "TRI ESPECIAL",
            "IP70",
            "IP80",
            "IP150",
            "IP250",
            "IP400",
        ]

        # Cálculo de Carga Especial (IPs)
        pot_ips = {
            "IP70": 0.07,
            "IP80": 0.08,
            "IP150": 0.15,
            "IP250": 0.25,
            "IP400": 0.40,
        }

        # Função auxiliar temporária para cálculo de IP (antes da sanitização final)
        def _calc_ip(row):
            t = 0.0
            qtd = 0
            for k, v in pot_ips.items():
                try:
                    val = float(str(row.get(k, 0)).replace(",", "."))
                    if val > 0:
                        t += val * v
                        qtd += int(val)
                except:
                    pass
            return pd.Series([t, qtd])

        data_loads[["CARGA_ESP_KVA", "QTD_IP"]] = data_loads.apply(_calc_ip, axis=1)

        # Limpeza pré-merge: Remove cargas sem Ponto definido
        data_loads = data_loads[data_loads["PONTO"].notna()]
        # Normaliza PONTO para string upper para garantir o merge
        data_loads["PONTO"] = (
            data_loads["PONTO"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\.0$", "", regex=True)
        )
        df_topology["PONTO"] = (
            df_topology["PONTO"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\.0$", "", regex=True)
        )

        # Merge (Left Join na Topologia)
        df_merged = pd.merge(
            df_topology,
            data_loads[
                [
                    "PONTO",
                    "MONO",
                    "BIFÁSICO",
                    "TRIFÁSICO",
                    "TRI ESPECIAL",
                    "CARGA_ESP_KVA",
                    "QTD_IP",
                ]
            ],
            on="PONTO",
            how="left",
        )

        # Preenche tipo de IP genérico se houver quantidade
        df_merged["TIPO_IP"] = "Sem IP"
        df_merged.loc[df_merged["QTD_IP"] > 0, "TIPO_IP"] = "IP Misto"

    except Exception as e:
        erros_importacao.append(
            f"Erro ao ler cargas: {str(e)}. Usando apenas topologia."
        )
        df_merged = df_topology.copy()

    # --- 4. CENTRALIZAÇÃO DA NORMALIZAÇÃO (BLINDAGEM FINAL) ---
    # Aqui ocorre a mágica: Tipagem, Preenchimento de Nulos, Validação de TRAFO, Remoção de Lixo
    df_norm, erros_sanitizacao = sanitizar(df_merged)

    erros_finais = erros_importacao + erros_sanitizacao

    return df_norm, trafo_kva, config_cabos, classe_encontrada, erros_finais
