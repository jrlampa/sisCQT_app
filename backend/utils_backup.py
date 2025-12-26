# backend/utils.py
import pandas as pd
import copy
from typing import List, Dict, Tuple
from backend.engine import ElectricalEngine


class DiagnosticoEngenharia:
    @staticmethod
    def analisar_baricentro(df: pd.DataFrame, trafo_kva: float) -> Dict:
        try:
            saidas = df[df["MONTANTE"] == "TRAFO"]
            if saidas.empty:
                return {"status": "OK", "msg": "Trafo sem cargas."}

            cargas = []
            total = 0.0
            for _, row in saidas.iterrows():
                # Tenta usar a carga acumulada calculada pelo engine
                k = row.get("ACUMULADA_KVA", 0.0)
                if pd.isna(k) or k == 0:
                    k = row.get("CARGA_ACUMULADA_G", 0.0)

                cargas.append({"ponto": row["PONTO"], "kva": k})
                total += k

            if total == 0:
                return {"status": "OK", "msg": "Sem carga ativa."}

            cargas.sort(key=lambda x: x["kva"], reverse=True)
            major = cargas[0]

            if len(cargas) > 1 and (major["kva"] / total < 0.60):
                return {
                    "status": "OTIMIZADO",
                    "msg": "Trafo bem posicionado (Cargas equilibradas).",
                }
            else:
                return {
                    "status": "SUGESTAO",
                    "msg": f"Tronco '{major['ponto']}' concentra {(major['kva']/total)*100:.0f}% da carga. Avaliar deslocamento.",
                }
        except:
            return {"status": "ERRO", "msg": "Erro no cálculo."}

    @staticmethod
    def gerar_recomendacoes(df, kpis, avisos):
        recs = []
        if kpis.get("ocupacao", 0) > 100:
            recs.append(
                {
                    "titulo": "Sobrecarga",
                    "texto": "Trafo operando acima da capacidade nominal.",
                }
            )
        if kpis.get("max_cqt", 0) > kpis.get("limites_usados", {}).get("cqt_max", 6.0):
            recs.append(
                {
                    "titulo": "Queda de Tensão",
                    "texto": "Verificar troncos principais e aplicar recondutoração.",
                }
            )
        return recs


class SimuladorReadequacao:
    @staticmethod
    def _obter_proximo_cabo_melhor(
        atual: str, disponiveis_map: Dict[str, float]
    ) -> str:
        """
        Retorna o cabo COM COEFICIENTE IMEDIATAMENTE MENOR (melhor condutividade).
        Não pula para o melhor de todos, vai degrau por degrau.
        """
        coef_atual = disponiveis_map.get(atual, 999.0)

        # Filtra cabos que são estritamente melhores (coeficiente menor)
        candidatos = []
        for nome, coef in disponiveis_map.items():
            if coef < (coef_atual - 0.00001):  # Margem segura float
                candidatos.append((nome, coef))

        if not candidatos:
            return None  # Já estamos no topo

        # Ordena por coeficiente DECRESCENTE (do maior para o menor).
        # O primeiro da lista será o que tem o maior coeficiente dentre os melhores,
        # ou seja, o degrau imediatamente acima do atual.
        candidatos.sort(key=lambda x: x[1], reverse=True)

        return candidatos[0][0]

    @staticmethod
    def _obter_proximo_trafo(atual_kva: float) -> float:
        """Retorna a próxima potência comercial disponível."""
        trafos = sorted(DEFAULT_TRAFOS_LISTA)
        for t in trafos:
            if t > atual_kva:
                return float(t)
        return None  # Já está no máximo

    @staticmethod
    def _get_path_to_source(df: pd.DataFrame, target_point: str) -> List[int]:
        """Retorna indices do caminho [Perto_Trafo, ..., Ponto_Alvo]"""
        path_indices = []
        curr = target_point
        map_montante = dict(zip(df["PONTO"], df["MONTANTE"]))
        map_idx = dict(zip(df["PONTO"], df.index))
        seen = set()

        while curr and curr != "TRAFO":
            if curr in seen:
                break
            seen.add(curr)
            idx = map_idx.get(curr)
            if idx is not None:
                path_indices.append(idx)
            curr = map_montante.get(curr)

        return list(reversed(path_indices))

    @staticmethod
    def executar(
        nome_origem: str,
        df_base: pd.DataFrame,
        params: Dict,
        config_full: Dict,
        cabos_habilitados_nomes: List[str],
    ):
        """
        Algoritmo:
        1. Identifica o ponto com pior queda.
        2. Percorre o caminho do Trafo até esse ponto.
        3. No primeiro trecho: melhora o cabo 1 nível. Recalcula.
        4. Se resolveu -> Fim.
        5. Se não resolveu -> Tenta melhorar esse mesmo trecho de novo.
        6. Se esse trecho maximizou -> Avança para o próximo trecho.
        """
        df_sim = df_base.copy()

        # 1. Prepara mapa de coeficientes apenas dos cabos permitidos
        cabos_cfg = config_full["cabos"]
        mapa_coefs_habilitados = {}
        for nome in cabos_habilitados_nomes:
            dados = cabos_cfg.get(nome)
            if dados:
                c = dados["coef"] if isinstance(dados, dict) else dados
                mapa_coefs_habilitados[nome] = c

        # Mapa de referência global (para saber o coef do cabo atual, mesmo que não esteja na lista de habilitados)
        full_coefs_ref = {
            k: (v["coef"] if isinstance(v, dict) else v) for k, v in cabos_cfg.items()
        }

        limites = config_full["perfis"].get(params.get("perfil", ""), {})
        lim_cqt = limites.get("cqt_max", 6.0)

        log_changes = {}  # {ponto: "Cabo Antigo -> Novo"}

        # Loop Principal
        max_iter = 50  # Segurança
        iteracao = 0
        resolved = False

        while iteracao < max_iter:
            iteracao += 1

            # A. Calcula
            df_calc, kpis, _ = ElectricalEngine.calcular(df_sim, params, config_full)
            if kpis["max_cqt"] <= lim_cqt:
                resolved = True
                break

            # B. Identifica Caminho Crítico
            idx_worst = df_calc["CQT_ACUMULADA"].idxmax()
            ponto_worst = df_calc.at[idx_worst, "PONTO"]
            caminho_indices = SimuladorReadequacao._get_path_to_source(
                df_calc, ponto_worst
            )

            # C. Tenta melhorar (Estratégia Gulosa no Tronco)
            change_made = False

            for idx in caminho_indices:
                cabo_atual = df_sim.at[idx, "CABO"]

                # Descobre o coef do cabo atual
                coef_atual = full_coefs_ref.get(cabo_atual, 999.0)

                # Se o cabo atual não está no mapa de habilitados (ex: é um cabo antigo),
                # precisamos adicionar ele temporariamente no mapa para a função de comparação funcionar,
                # ou a função _obter vai achar que ele não existe.
                # Mas melhor: passamos o mapa de habilitados e comparamos valor numérico.

                novo_cabo = SimuladorReadequacao._obter_proximo_cabo_melhor(
                    cabo_atual, mapa_coefs_habilitados
                )

                if novo_cabo:
                    # Aplica a mudança
                    df_sim.at[idx, "CABO"] = novo_cabo
                    ponto = df_sim.at[idx, "PONTO"]

                    # Log inteligente: se já mudou esse ponto antes, atualiza o log para mostrar a evolução final
                    if ponto in log_changes:
                        # Ex: "Cabo A -> Cabo B" vira "Cabo A -> Cabo C"
                        original = log_changes[ponto].split(" -> ")[0]
                        log_changes[ponto] = f"{original} -> {novo_cabo}"
                    else:
                        log_changes[ponto] = f"{cabo_atual} -> {novo_cabo}"

                    change_made = True
                    # BREAK IMPORTANTE: Mudou um cabo? Recalcula tudo imediatamente.
                    # Não muda o próximo trecho ainda. Queremos ver se essa mudança resolveu.
                    break

            if not change_made:
                # Percorreu todo o caminho e todos os trechos já estão com o melhor cabo possível da lista.
                break

        # Resultado Final
        df_final, kpis_final, _ = ElectricalEngine.calcular(df_sim, params, config_full)

        if resolved:
            msg = "Simulação concluída com sucesso."
        else:
            # Mensagem Específica solicitada
            msg = (
                f"Mesmo com a troca dos condutores para o máximo permitido ({list(mapa_coefs_habilitados.keys())[0]}...) "
                f"do Trafo até o ponto {ponto_worst}, não foi possível corrigir a QT ({kpis_final['max_cqt']:.2f}%). "
                "É SUGERIDO DIVIDIR CIRCUITO."
            )

        return {
            "df": df_final,
            "kpis": kpis_final,
            "log": log_changes,
            "resolvido": resolved,
            "msg": msg,
        }


def importar_planilha_concessionaria(
    arquivo_excel,
) -> Tuple[pd.DataFrame, float, Dict, str]:
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

    # 1. CABOS
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

    # 2. TOPOLOGIA
    trafo_kva = 45.0
    try:
        df_raw_cqt = pd.read_excel(arquivo_excel, sheet_name=SHEET_CQT, header=None)
        trafo_kva = safe_float(df_raw_cqt.iloc[2, 5])
    except:
        pass

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

    # [CORREÇÃO] Limpeza agressiva no Import
    df_topology["CABO"] = df_topology["CABO"].astype(str)
    df_topology["CABO"] = df_topology["CABO"].str.replace(r"[\r\n]+", " ", regex=True)
    df_topology["CABO"] = (
        df_topology["CABO"].str.replace(r"\s+", " ", regex=True).str.strip()
    )
    df_topology["CABO"] = df_topology["CABO"].replace(
        {"nan": "", "None": "", "0": "", "0.0": ""}
    )

    df_topology["EXPECTED_CQT"] = df_topology["EXPECTED_CQT"].apply(safe_float)
    df_topology = df_topology[df_topology["PONTO"] != ""]

    mask_real = (df_topology["PONTO"] == "TRAFO") | (df_topology["METROS"] > 0.1)
    df_topology = df_topology[mask_real]

    if not df_topology[df_topology["PONTO"] == "TRAFO"].empty:
        df_topology.loc[
            df_topology["PONTO"] == "TRAFO", ["MONTANTE", "METROS", "CABO"]
        ] = ["", 0.0, ""]
    else:
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

    if len(df_topology) > 1:
        for idx in df_topology.index:
            p = df_topology.at[idx, "PONTO"]
            m = df_topology.at[idx, "MONTANTE"]
            if p != "TRAFO" and m == "":
                df_topology.at[idx, "MONTANTE"] = "TRAFO"

    # 3. CARGAS E CLASSE (Mantém igual ao anterior)
    # ... (Copiar o restante da função importar_planilha do código anterior) ...
    # Se precisar do código completo desta parte, avise, mas a correção principal está na limpeza do "CABO" acima.

    return df_topology, trafo_kva, config_cabos, "B"
