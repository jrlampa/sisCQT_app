# frontend/views/dashboard.py
import streamlit as st
import pandas as pd
import time
from backend.constantes import DEFAULT_COL_ORDER, DEFAULT_PARAMS
from backend.engine import ElectricalEngine


def render_dashboard_projetos():
    st.title("📊 Dashboard de Projetos")

    # --- ALERTA DE CADASTRO ---
    if "db" in st.session_state:
        if st.session_state.db.check_needs_setup():
            st.warning(
                "⚠️ **Atenção:** O sistema está operando com condutores genéricos. Vá em 'Configurações' para cadastrar os padrões da concessionária."
            )

    # --- ÁREA DE BANCO DE DADOS (CARREGAR / EXCLUIR) ---
    st.markdown("### 📂 Projetos Salvos (Banco de Dados)")

    projetos = []
    if "db" in st.session_state:
        projetos = st.session_state.db.listar_projetos()

    if projetos:
        # Dicionário reverso para pegar o ID pelo nome
        opcoes = {
            f"{p['nome']} (Criado em: {p['data_criacao']})": p["id"] for p in projetos
        }

        # Layout em 3 colunas: Selectbox (maior) | Carregar | Excluir
        c_sel, c_load, c_del = st.columns([3, 1, 1])

        with c_sel:
            selecionado = st.selectbox(
                "Selecione um projeto:",
                list(opcoes.keys()),
                label_visibility="collapsed",
            )
            pid = opcoes[selecionado]

        with c_load:
            if st.button("📂 Carregar", type="primary", use_container_width=True):
                with st.spinner("Carregando..."):
                    try:
                        cfgs, trechos, nome = st.session_state.db.carregar_projeto(pid)

                        # Limpa memória atual antes de carregar
                        st.session_state.cenarios = {}
                        st.session_state.params = {}
                        st.session_state.resultados = {}
                        st.session_state.lista_abas = (
                            []
                        )  # Se você usa lista_abas, limpe-a também

                        novos_cenarios = {}
                        novos_params = {}

                        # 1. Reconstrói DataFrames
                        df_raw = pd.DataFrame(trechos)
                        if not df_raw.empty:
                            for n_cen, grupo in df_raw.groupby("nome_cenario"):
                                df_c = grupo.drop(
                                    columns=["nome_cenario", "projeto_id", "id"],
                                    errors="ignore",
                                )
                                # Normaliza colunas para maiúsculas (Engine exige)
                                df_c.columns = [c.upper() for c in df_c.columns]

                                # Garante tipos numéricos críticos
                                for col in [
                                    "METROS",
                                    "CARGA_ESP_KVA",
                                    "MONO",
                                    "BIFÁSICO",
                                    "TRIFÁSICO",
                                ]:
                                    if col in df_c.columns:
                                        df_c[col] = pd.to_numeric(
                                            df_c[col], errors="coerce"
                                        ).fillna(0)

                                novos_cenarios[n_cen] = df_c

                        # 2. Reconstrói Parâmetros
                        for cfg in cfgs:
                            n_c = cfg["nome_cenario"]
                            novos_params[n_c] = {
                                "trafo_kva": cfg["trafo_kva"],
                                "classe_tipo": cfg["classe_tipo"],
                                "classe_manual": cfg["classe_manual"],
                                "fp_ip": cfg["fp_ip"],
                                "perfil": cfg["perfil"],
                            }
                            # Se o cenário existir nos params mas não teve trechos (vazio), cria DF vazio com template
                            if n_c not in novos_cenarios:
                                novos_cenarios[n_c] = (
                                    ElectricalEngine.get_template_dataframe()
                                )

                        # 3. Atualiza Sessão
                        st.session_state.cenarios = novos_cenarios
                        st.session_state.params = novos_params

                        # Se usar lista_abas no app.py, atualize-a aqui
                        if "lista_abas" in st.session_state:
                            st.session_state.lista_abas = list(novos_cenarios.keys())

                        st.session_state.current_project_name = nome
                        st.session_state.current_project_db_id = pid

                        if list(novos_cenarios.keys()):
                            st.session_state.active_project_id = list(
                                novos_cenarios.keys()
                            )[0]
                            st.session_state.current_view = "Editor"
                            st.toast(f"Projeto '{nome}' carregado!", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning("O projeto carregado está vazio.")

                    except Exception as e:
                        st.error(f"Erro ao carregar: {e}")

        with c_del:
            # Botão de Exclusão Definitiva
            if st.button("🗑️ Excluir", type="secondary", use_container_width=True):
                confirm = (
                    True  # Em apps reais, ideal usar st.popover, mas aqui simplificamos
                )
                if confirm:
                    ok, msg = st.session_state.db.excluir_projeto(pid)
                    if ok:
                        st.toast(f"Projeto excluído com sucesso!", icon="🗑️")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro ao excluir: {msg}")
    else:
        st.info("Nenhum projeto salvo no banco de dados.")

    st.divider()

    # --- NOVO PROJETO ---
    st.markdown("### 🌱 Criar Novo")
    if st.button("➕ Iniciar Novo Projeto", use_container_width=True):
        new_id = "ATUAL"  # Nome padrão sugerido para 1º cenário

        # Limpa memória para começar limpo
        st.session_state.cenarios = {}
        st.session_state.params = {}
        st.session_state.resultados = {}
        if "lista_abas" in st.session_state:
            st.session_state.lista_abas = []

        # Cria Template com TRAFO
        st.session_state.cenarios[new_id] = ElectricalEngine.get_template_dataframe()
        st.session_state.params[new_id] = DEFAULT_PARAMS.copy()

        if "lista_abas" in st.session_state:
            st.session_state.lista_abas.append(new_id)

        st.session_state.active_project_id = new_id
        st.session_state.current_project_name = "Novo Projeto"
        st.session_state.current_project_db_id = None
        st.session_state.current_view = "Editor"
        st.rerun()

    # --- EM EDIÇÃO (MEMÓRIA) ---
    if st.session_state.cenarios:
        st.divider()
        st.subheader(
            f"Em Edição: {st.session_state.get('current_project_name', 'Sem Nome')}"
        )

        cols = st.columns(3)
        for i, (nome, df) in enumerate(st.session_state.cenarios.items()):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**📄 {nome}**")
                    n_pontos = len(df[df["PONTO"] != "TRAFO"])
                    st.caption(f"{n_pontos} postes/vãos")

                    b1, b2 = st.columns([3, 1])
                    if b1.button("Editar", key=f"ed_{nome}", use_container_width=True):
                        st.session_state.active_project_id = nome
                        st.session_state.current_view = "Editor"
                        st.rerun()

                    # Botão para apagar cenário da memória
                    if b2.button(
                        "✖️", key=f"del_mem_{nome}", help="Fechar este cenário"
                    ):
                        del st.session_state.cenarios[nome]
                        if nome in st.session_state.params:
                            del st.session_state.params[nome]
                        if nome in st.session_state.resultados:
                            del st.session_state.resultados[nome]
                        if (
                            "lista_abas" in st.session_state
                            and nome in st.session_state.lista_abas
                        ):
                            st.session_state.lista_abas.remove(nome)
                        st.rerun()
