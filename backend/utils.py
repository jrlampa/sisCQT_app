# backend/utils.py
import pandas as pd
import copy
from typing import List, Dict, Tuple
from backend.engine import ElectricalEngine
from backend.constantes import DEFAULT_TRAFOS_LISTA


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
                return {"status": "OTIMIZADO", "msg": "Trafo bem posicionado."}
            else:
                return {
                    "status": "SUGESTAO",
                    "msg": f"Tronco '{major['ponto']}' concentra {(major['kva']/total)*100:.0f}% da carga.",
                }
        except:
            return {"status": "ERRO", "msg": "Erro no cálculo."}

    @staticmethod
    def gerar_recomendacoes(df, kpis, avisos):
        recs = []
        if kpis.get("ocupacao", 0) > 100:
            recs.append({"titulo": "Sobrecarga", "texto": "Trafo > 100%."})
        if kpis.get("max_cqt", 0) > kpis.get("limites_usados", {}).get("cqt_max", 6.0):
            recs.append({"titulo": "Queda Tensão", "texto": "Revisar troncos."})
        return recs


class SimuladorReadequacao:
    @staticmethod
    def _obter_proximo_cabo_melhor(
        atual: str, disponiveis_map: Dict[str, float]
    ) -> str:
        coef_atual = ElectricalEngine._buscar_cabo_flexivel(atual, disponiveis_map)
        if coef_atual == 0.0:
            coef_atual = 999.0

        candidatos = []
        for nome, coef in disponiveis_map.items():
            val = coef["coef"] if isinstance(coef, dict) else coef
            if val < (coef_atual - 0.00001):
                candidatos.append((nome, val))
        if not candidatos:
            return None
        candidatos.sort(key=lambda x: x[1], reverse=True)
        return candidatos[0][0]

    @staticmethod
    def _obter_proximo_trafo(atual_kva: float) -> float:
        trafos = sorted(DEFAULT_TRAFOS_LISTA)
        for t in trafos:
            if t > atual_kva:
                return float(t)
        return None

    @staticmethod
    def _get_path_to_source(df: pd.DataFrame, target_point: str) -> List[int]:
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
        df_sim = df_base.copy()
        params_sim = copy.deepcopy(params)
        cabos_cfg = config_full["cabos"]

        mapa_coefs_habilitados = {}
        for nome in cabos_habilitados_nomes:
            dados = cabos_cfg.get(nome)
            if dados:
                c = dados["coef"] if isinstance(dados, dict) else dados
                mapa_coefs_habilitados[nome] = c

        limites = config_full["perfis"].get(params.get("perfil", ""), {})
        lim_cqt = limites.get("cqt_max", 6.0)
        lim_oc = limites.get("sobrecarga_max", 100.0)
        log_changes = {}

        # [CORREÇÃO] Inicializa df_final para evitar NameError
        df_final = df_sim.copy()

        # 1. UPGRADE TRAFO
        df_calc, kpis, _ = ElectricalEngine.calcular(df_sim, params_sim, config_full)
        iter_trafo = 0
        while kpis["ocupacao"] > lim_oc and iter_trafo < 5:
            novo_kva = SimuladorReadequacao._obter_proximo_trafo(
                params_sim["trafo_kva"]
            )
            if novo_kva:
                old = params_sim["trafo_kva"]
                params_sim["trafo_kva"] = novo_kva
                log_changes["TRAFO"] = f"{old} kVA -> {novo_kva} kVA"
                df_calc, kpis, _ = ElectricalEngine.calcular(
                    df_sim, params_sim, config_full
                )
                iter_trafo += 1
            else:
                break

        # 2. RECONDUTORAÇÃO
        iteration = 0
        resolved = False
        while iteration < 50:
            iteration += 1
            if kpis["max_cqt"] <= lim_cqt:
                resolved = True
                break

            idx_worst = df_calc["CQT_ACUMULADA"].idxmax()
            ponto_worst = df_calc.at[idx_worst, "PONTO"]
            caminho = SimuladorReadequacao._get_path_to_source(df_calc, ponto_worst)

            change_made = False
            for idx in caminho:
                cabo_atual = df_sim.at[idx, "CABO"]
                novo_cabo = SimuladorReadequacao._obter_proximo_cabo_melhor(
                    cabo_atual, mapa_coefs_habilitados
                )
                if novo_cabo:
                    df_sim.at[idx, "CABO"] = novo_cabo
                    ponto = df_sim.at[idx, "PONTO"]
                    if ponto in log_changes:
                        orig = log_changes[ponto].split(" -> ")[0]
                        log_changes[ponto] = f"{orig} -> {novo_cabo}"
                    else:
                        log_changes[ponto] = f"{cabo_atual} -> {novo_cabo}"
                    change_made = True
                    break

            if not change_made:
                break
            df_calc, kpis, _ = ElectricalEngine.calcular(
                df_sim, params_sim, config_full
            )

        # [CORREÇÃO] Recalcula final fora do loop para garantir df_final atualizado
        df_final, kpis_final, _ = ElectricalEngine.calcular(
            df_sim, params_sim, config_full
        )

        is_cqt_ok = kpis_final["max_cqt"] <= lim_cqt
        is_ocup_ok = kpis_final["ocupacao"] <= lim_oc

        if is_cqt_ok and is_ocup_ok:
            msg = "Solução Técnica Encontrada."
            final_status = True
        else:
            final_status = False
            try:
                ponto_critico = df_final.at[df_final["CQT_ACUMULADA"].idxmax(), "PONTO"]
            except:
                ponto_critico = "N/A"
            melhor_cabo = (
                list(mapa_coefs_habilitados.keys())[0]
                if mapa_coefs_habilitados
                else "N/A"
            )
            msg = (
                f"Mesmo com a troca para ({melhor_cabo}...) até {ponto_critico}, "
                f"QT ({kpis_final['max_cqt']:.2f}%) ainda alta. É SUGERIDO DIVIDIR CIRCUITO."
            )

        return {
            "df": df_final,
            "kpis": kpis_final,
            "log": log_changes,
            "params_opt": params_sim,
            "msg": msg,
            "resolvido": final_status,
            "iteracoes": iteration,
        }


def importar_planilha_concessionaria(arquivo_excel):
    SHEET_CQT = "CQT ATUAL"

    def clean_string(val):
        if pd.isna(val):
            return ""
        return str(val).strip()

    try:
        # 1. Leitura bruta sem assumir cabeçalho
        df_raw = pd.read_excel(
            arquivo_excel, sheet_name=SHEET_CQT, header=None, nrows=50
        )

        header_idx = -1
        col_map = {}
        targets = {
        "PONTO": ["PONTO", "PT", "TRECHO", "NÓ"],
        "MONTANTE": ["MONTANTE", "PAI", "DE", "FROM"],
        "METROS": ["METROS", "DIST", "COMPRIMENTO", "M ", "M."], # Adicionado "M." e "M "
        "CABO": ["CABO", "CONDUTOR", "FIO"],
        "EXPECTED_CQT": ["EXPECTED_CQT", "CQT_ESP", "CQT%", "QUEDA", "EXPECTED"]
    }

    # Busca robusta: verifica se o termo alvo está contido em qualquer parte da célula
    for idx, row in df_raw.iterrows():
        row_clean = [str(x).upper().strip() for x in row.values]
        matches = {}
        for key, synonyms in targets.items():
            for i, cell in enumerate(row_clean):
                # [MELHORIA] Checagem parcial para nomes como "METROS (M)"
                if any(s in cell for s in synonyms):
                    matches[key] = i
                    break
                
                if "PONTO" in matches and "MONTANTE" in matches and "METROS" in matches:
                    header_idx = idx
                    col_map = matches
                    break

        if header_idx == -1:
            return pd.DataFrame(), 45.0, {}, "B"

        # 2. Re-lê o arquivo pulando o lixo (header_idx é a linha das labels)
        df_data = pd.read_excel(
            arquivo_excel, sheet_name=SHEET_CQT, skiprows=header_idx + 1, header=None
        )

        # 3. Mapeamento por índice
        final_data = {}
        for std_name, col_index in col_map.items():
            series = df_data.iloc[:, col_index]
            if std_name in ["PONTO", "MONTANTE", "CABO"]:
                final_data[std_name] = series.astype(str).str.strip().replace("nan", "")
            else:
                final_data[std_name] = pd.to_numeric(series, errors="coerce").fillna(0)

        df_final = pd.DataFrame(final_data)

        # Filtro 1: O PONTO deve ser algo que pareça um ID (normalmente não é um número float longo)
        # Vamos converter para string e remover o que não é dado de rede
        df_final = df_final[df_final["PONTO"].apply(lambda x: len(str(x)) < 20)].copy()

        # Filtro 2: Remover linhas que contenham palavras de cabeçalho nos dados
        blacklist = ["TRECHO", "MONTANTE", "CARGAS", "TOTAL", "CLIENTES", "ILUMINAÇÃO"]
        df_final = df_final[~df_final["PONTO"].str.upper().isin(blacklist)]

        # Filtro 3: Validar que METROS é numérico e maior que zero (exceto TRAFO)
        df_final["METROS"] = pd.to_numeric(df_final["METROS"], errors="coerce").fillna(
            0
        )
        # Remove linhas onde metros e ponto são lixo
        df_final = df_final[(df_final["PONTO"] == "TRAFO") | (df_final["METROS"] > 0)]

        # 1. REMOVER LINHAS ONDE O PONTO É INVÁLIDO OU NULO
        # Isso remove as linhas de lixo que causaram os duplicados "0" e "3.2"
        df_final = df_final[
            df_final["PONTO"].notna()
            & (df_final["PONTO"].astype(str).str.strip() != "")
            & (df_final["PONTO"].astype(str).str.strip() != "0")
            & (df_final["PONTO"].astype(str).str.strip() != "0.0")
        ].copy()

        # 2. LIMPEZA ADICIONAL: Ignorar cabeçalhos repetidos que podem ter sido lidos
        strings_ignorar = ["PONTO", "TRECHO", "NÓ", "CLIENTES", "TOTAL", "CARGAS"]
        df_final = df_final[~df_final["PONTO"].str.upper().isin(strings_ignorar)]

        # 3. GARANTIR UNICIDADE (Caso ainda existam duplicatas reais por erro de cadastro)
        # Se houver duplicados, o motor vai reclamar, mas aqui limpamos o lixo óbvio
        df_final = df_final.drop_duplicates(subset=["PONTO"]).reset_index(drop=True)

        # 4. GARANTIA DO NÓ TRAFO (Fundamental para o Engine)
        if not df_final["PONTO"].str.contains("TRAFO").any():
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
            df_final = pd.concat([row_trafo, df_final], ignore_index=True)

        return df_final, 45.0, {}, "B"

    except Exception as e:
        print(f"Erro na importação: {e}")
        return pd.DataFrame(), 45.0, {}, "B"
