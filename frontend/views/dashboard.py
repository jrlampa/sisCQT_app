import streamlit as st
import pandas as pd
from backend.constantes import DEFAULT_COL_ORDER, DEFAULT_PARAMS


def render_dashboard_projetos():
    st.title("📊 Dashboard de Projetos")
    st.markdown("Gerencie seus estudos de rede e simulações ativas.")

    col_act, col_info = st.columns([1, 4])
    with col_act:
        if st.button("➕ Novo Cenário", type="primary", use_container_width=True):
            new_id = f"Estudo-{len(st.session_state.cenarios) + 1:03d}"
            if new_id not in st.session_state.cenarios:
                st.session_state.cenarios[new_id] = pd.DataFrame(
                    columns=DEFAULT_COL_ORDER
                )
                st.session_state.params[new_id] = DEFAULT_PARAMS.copy()
                st.session_state.active_project_id = new_id
                st.session_state.current_view = "Editor"
                st.rerun()

    st.divider()

    if not st.session_state.cenarios:
        st.info("Nenhum cenário ativo. Clique em 'Novo Cenário' para começar.")
        return

    st.subheader("Cenários em Aberto")
    cols = st.columns(3)
    for i, (nome, df) in enumerate(st.session_state.cenarios.items()):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"#### 📁 {nome}")
                n_pontos = len(df)
                status = "Não calculado"
                if nome in st.session_state.resultados:
                    res = st.session_state.resultados[nome]
                    kpis = res["kpis"]
                    if kpis.get("ocupacao", 0) > 100 or kpis.get("max_cqt", 0) > 6:
                        status = "🔴 Crítico"
                    else:
                        status = "🟢 Aprovado"

                st.caption(f"Pontos: {n_pontos} | Status: {status}")

                b1, b2 = st.columns([2, 1])
                with b1:
                    if st.button(
                        "Abrir Editor", key=f"open_{nome}", use_container_width=True
                    ):
                        st.session_state.active_project_id = nome
                        st.session_state.current_view = "Editor"
                        st.rerun()
                with b2:
                    if st.button("🗑️", key=f"del_{nome}", help="Excluir"):
                        del st.session_state.cenarios[nome]
                        if nome in st.session_state.params:
                            del st.session_state.params[nome]
                        if nome in st.session_state.resultados:
                            del st.session_state.resultados[nome]
                        st.rerun()
