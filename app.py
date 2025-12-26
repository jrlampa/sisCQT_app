# app.py
import streamlit as st
import logging
import copy
import time
from io import BytesIO
import pandas as pd
from siscqt_constantes import DEFAULT_PARAMS, COL_MAPPING
from siscqt_db import DatabaseManager
from siscqt_engine import ElectricalEngine
from siscqt_gui import render_aba, render_config_page

# 1. Configuração e Logging
st.set_page_config(page_title="SisCQT - Enterprise V24", page_icon="⚡", layout="wide")
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SisCQT")

# Inicializa Banco de Dados
db = DatabaseManager()


def main():
    if "init" not in st.session_state:
        st.session_state.lista_abas = ["ATUAL", "ATUAL+NC", "PROJ 01", "PROJ 02"]
        st.session_state.cenarios = {
            k: ElectricalEngine.get_template_dataframe()
            for k in st.session_state.lista_abas
        }
        st.session_state.params = {
            k: copy.deepcopy(DEFAULT_PARAMS) for k in st.session_state.lista_abas
        }
        st.session_state.resultados = {}
        st.session_state.hashes = {}

        c, i, t, p = db.load_configs()
        st.session_state.config_cabos = c
        st.session_state.config_ips = i
        st.session_state.config_trafos = t
        st.session_state.config_perfis = p

        st.session_state.view_mode = "main"
        st.session_state.init = True

    if "delete_tab" in st.session_state:
        target = st.session_state.delete_tab
        if target in st.session_state.lista_abas:
            st.session_state.cenarios.pop(target, None)
            st.session_state.params.pop(target, None)
            st.session_state.resultados.pop(target, None)
            st.session_state.hashes.pop(target, None)
            st.session_state.lista_abas.remove(target)
        del st.session_state.delete_tab
        st.rerun()

    # --- SIDEBAR: IDENTIDADE VISUAL ---
    try:
        st.sidebar.image("logoim3.png", use_container_width=True)
    except:
        st.sidebar.warning("logoim3.png não encontrado")

    st.sidebar.title("🗄️ Menu")

    if st.sidebar.button("🏠 Projetos", use_container_width=True):
        st.session_state.view_mode = "main"
        st.rerun()

    if st.sidebar.button("⚙️ Configurações", use_container_width=True):
        st.session_state.view_mode = "config"
        st.rerun()

    st.sidebar.divider()

    # --- ROTEAMENTO DE PÁGINAS ---
    if st.session_state.view_mode == "config":
        render_config_page(db)
        # Créditos no rodapé da sidebar mesmo na config
        _render_creditos()
        return

    # MODO PROJETOS (MAIN)
    projs = db.listar_projetos()

    if projs:
        with st.sidebar.expander("Gerenciar Banco de Dados"):
            opts = {f"{p['id']}: {p['nome']}": p["id"] for p in projs}
            sel = st.selectbox("Projeto Selecionado:", list(opts.keys()))
            c1, c2 = st.columns(2)
            if c1.button("📂 Abrir"):
                cfgs, trechos, nome = db.carregar_projeto(opts[sel])
                if cfgs:
                    new_abas, new_cens, new_pars = [], {}, {}
                    for c in cfgs:
                        nm = c["nome_cenario"]
                        new_abas.append(nm)
                        p_merged = copy.deepcopy(DEFAULT_PARAMS)
                        try:
                            perf_saved = (
                                c["perfil"] if c["perfil"] else "Padrão (Urbano)"
                            )
                        except:
                            perf_saved = "Padrão (Urbano)"
                        p_merged.update(
                            {
                                "trafo_kva": c["trafo_kva"],
                                "classe_tipo": c["classe_tipo"],
                                "classe_manual": c["classe_manual"],
                                "fp_ip": c["fp_ip"],
                                "perfil": perf_saved,
                            }
                        )
                        new_pars[nm] = p_merged
                        new_cens[nm] = []
                    for t in trechos:
                        new_cens[t["nome_cenario"]].append(
                            {
                                "PONTO": t["ponto"],
                                "MONTANTE": t["montante"],
                                "METROS": t["metros"],
                                "CABO": t["cabo"],
                                "MONO": t["mono"],
                                "BIFÁSICO": t["bi"],
                                "TRIFÁSICO": t["tri"],
                                "TRI ESPECIAL": t["tri_esp"],
                                "CARGA_ESP_KVA": t["carga_esp"],
                                "TIPO_IP": t["tipo_ip"],
                                "QTD_IP": t["qtd_ip"],
                            }
                        )
                    st.session_state.lista_abas = new_abas
                    st.session_state.cenarios = {
                        k: (
                            pd.DataFrame(v)
                            if v
                            else ElectricalEngine.get_template_dataframe()
                        )
                        for k, v in new_cens.items()
                    }
                    st.session_state.params = new_pars
                    st.session_state.resultados = {}
                    st.success(f"Carregado: {nome}")
                    time.sleep(0.5)
                    st.rerun()

            del_key = f"del_confirm_{opts[sel]}"
            if c2.button("Apagar"):
                st.session_state[del_key] = True

            if st.session_state.get(del_key, False):
                st.warning("Confirma exclusão permanente?")
                if st.button("Sim, Excluir", key=f"yes_{del_key}"):
                    ok, msg = db.excluir_projeto(opts[sel])
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    del st.session_state[del_key]
                    time.sleep(0.5)
                    st.rerun()
                if st.button("Cancelar", key=f"no_{del_key}"):
                    del st.session_state[del_key]
                    st.rerun()

    with st.sidebar.expander("Salvar Projeto Atual", expanded=False):
        ns = st.text_input("Nome do Arquivo (DB)")
        if st.button("Gravar no Banco", use_container_width=True):
            if ns:
                pid = db.check_nome(ns)
                if pid:
                    if st.checkbox("Sobrescrever existente?"):
                        ok, msg = db.salvar_projeto(
                            ns, st.session_state.cenarios, st.session_state.params, pid
                        )
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                else:
                    ok, msg = db.salvar_projeto(
                        ns, st.session_state.cenarios, st.session_state.params
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.sidebar.divider()

    # --- NOVO CENÁRIO (OTIMIZADO) ---
    with st.sidebar.expander("➕ Novo Cenário / Aba", expanded=True):
        next_idx = len(st.session_state.lista_abas) + 1
        sug_name = f"PROJ {next_idx:02d}"
        new_tab_name = st.text_input(
            "Nome da Nova Aba:", value=sug_name, key="new_tab_name_input"
        )

        st.markdown("**Origem dos Dados:**")
        create_mode = st.radio(
            "Origem",
            [
                "Em Branco",
                "Importar Existente",
                "Importar Excel (Concessionária)",
            ],  # Adicionada opção
            label_visibility="collapsed",
            key="create_tab_mode",
        )

        # Variáveis de controle para importação
        uploaded_file = None

        if create_mode == "Importar Existente":
            # ... (código existente de cópia de aba) ...
            pass

        elif create_mode == "Importar Excel (Concessionária)":
            uploaded_file = st.file_uploader(
                "Selecione a planilha (.xls/.xlsx)", type=["xls", "xlsx"]
            )
            if uploaded_file:
                st.info("Arquivo carregado. Clique em 'Criar Cenário' para processar.")

        if st.button("Criar Cenário", type="primary", use_container_width=True):
            if not new_tab_name.strip():
                st.error("O nome da aba não pode estar vazio.")
            elif new_tab_name in st.session_state.lista_abas:
                st.error(f"Já existe uma aba chamada '{new_tab_name}'.")
            else:
                # Lógica de Criação
                new_df = None
                new_params = copy.deepcopy(DEFAULT_PARAMS)

                try:
                    if create_mode == "Em Branco":
                        new_df = ElectricalEngine.get_template_dataframe()

                    elif create_mode == "Importar Existente" and source_tab:
                        new_df = st.session_state.cenarios[source_tab].copy()
                        new_params = copy.deepcopy(st.session_state.params[source_tab])

                    elif create_mode == "Importar Excel (Concessionária)":
                        if not uploaded_file:
                            st.error("Faça o upload do arquivo primeiro.")
                            st.stop()

                        from siscqt_utils import importar_planilha_concessionaria

                        # Chama o importador blindado
                        df_imp, trafo_imp, cabos_imp, cls_imp, errs = (
                            importar_planilha_concessionaria(uploaded_file)
                        )

                        if df_imp.empty:
                            st.error(
                                "Falha na importação: Nenhum dado válido encontrado."
                            )
                            if errs:
                                st.error(f"Detalhes: {errs}")
                            st.stop()

                        new_df = df_imp
                        new_params["trafo_kva"] = trafo_imp
                        new_params["classe_manual"] = cls_imp

                        # Atualiza cabos globais se encontrar novos
                        if cabos_imp:
                            st.session_state.config_cabos.update(cabos_imp)
                            st.toast(
                                f"{len(cabos_imp)} condutores atualizados da planilha."
                            )

                        if errs:
                            st.warning("Avisos na importação:")
                            for e in errs:
                                st.write(f"- {e}")

                    # Finalização
                    if new_df is not None:
                        st.session_state.lista_abas.append(new_tab_name)
                        st.session_state.cenarios[new_tab_name] = new_df
                        st.session_state.params[new_tab_name] = new_params
                        st.success(f"Cenário '{new_tab_name}' criado com sucesso!")
                        time.sleep(0.5)
                        st.rerun()

                except Exception as e:
                    st.error(f"Erro ao criar cenário: {str(e)}")

    # --- RENDERIZAÇÃO DAS ABAS ---
    tabs = st.tabs(st.session_state.lista_abas)
    for i, t in enumerate(tabs):
        with t:
            render_aba(st.session_state.lista_abas[i], i)

    # --- RODAPÉ: EXPORTAÇÃO ---
    st.sidebar.divider()
    if st.sidebar.button("Exportar Excel Geral", use_container_width=True):
        data_exp = {}
        for aba in st.session_state.lista_abas:
            if aba in st.session_state.resultados:
                data_exp[aba] = {
                    "df": st.session_state.resultados[aba]["df"],
                    "trafo": st.session_state.params[aba]["trafo_kva"],
                }
            else:
                df_raw = st.session_state.cenarios[aba].copy()
                for c in COL_MAPPING.values():
                    if c not in df_raw.columns:
                        df_raw[c] = 0.0
                df_raw["CQT_TRECHO"] = 0.0
                df_raw["CQT_ACUMULADA"] = 0.0
                data_exp[aba] = {
                    "df": df_raw,
                    "trafo": st.session_state.params[aba]["trafo_kva"],
                }
        try:
            o = BytesIO()
            try:
                import xlsxwriter

                engine = "xlsxwriter"
            except:
                engine = "openpyxl"
            with pd.ExcelWriter(o, engine=engine) as w:
                for n, d in data_exp.items():
                    d["df"].to_excel(w, sheet_name=n, index=False)
            st.sidebar.download_button(
                "📥 Baixar .xlsx",
                o.getvalue(),
                "Relatorio_Geral.xlsx",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Erro Export: {e}")

    # CRÉDITOS
    _render_creditos()


def _render_creditos():
    st.sidebar.markdown("---")
    st.sidebar.caption("**Desenvolvido por:** Jonatas Lampa")
    st.sidebar.caption("jonatas.lampa@im3brasil.com.br")


if __name__ == "__main__":
    main()
