import streamlit as st
import pandas as pd
import time

try:
    from frontend.api_client import APIClient

    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


def render_configuracoes_avancadas(db_manager):
    st.title("⚙️ Configurações do Sistema")
    st.markdown("Personalize os parâmetros de engenharia e comportamento do sistema.")

    t_sys, t_cabos, t_traf, t_ips, t_perf = st.tabs(
        ["☁️ Sistema", "🔌 Condutores", "⚡ Trafos", "💡 IP", "📏 Perfis"]
    )

    with t_sys:
        st.subheader("Motor de Cálculo")
        st.info("Defina onde o processamento matemático pesado será executado.")
        opcoes = ["Motor Local (Offline)"]
        if API_AVAILABLE:
            opcoes.append("Nuvem / API (Online)")

        current = st.session_state.get("engine_mode", opcoes[0])
        if current not in opcoes:
            current = opcoes[0]

        new_mode = st.radio(
            "Selecione o Ambiente:", opcoes, index=opcoes.index(current)
        )
        if new_mode != st.session_state.engine_mode:
            st.session_state.engine_mode = new_mode
            st.toast("Modo de motor atualizado!", icon="💾")
            time.sleep(0.5)
            st.rerun()

    with t_cabos:
        _render_editor_tabela_config(db_manager, "cabos", st.session_state.config_cabos)
    with t_traf:
        df_trafos = pd.DataFrame(st.session_state.config_trafos, columns=["kva"])
        edited = st.data_editor(
            df_trafos, num_rows="dynamic", use_container_width=True, key="edit_trafos"
        )
        if st.button("Salvar Trafos"):
            ok, msg = db_manager.update_configs("trafos", edited)
            if ok:
                st.success(msg)
                st.session_state.config_trafos = sorted(edited["kva"].tolist())
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    with t_ips:
        _render_editor_tabela_config(db_manager, "ips", st.session_state.config_ips)
    with t_perf:
        rows = []
        [
            rows.append({**v, "nome": k})
            for k, v in st.session_state.config_perfis.items()
        ]
        df_p = pd.DataFrame(rows)
        edited_p = st.data_editor(
            df_p, num_rows="dynamic", use_container_width=True, key="edit_perfis"
        )
        if st.button("Salvar Perfis"):
            ok, msg = db_manager.update_configs("perfis", edited_p)
            if ok:
                st.success(msg)
                new_perfis = {}
                [
                    new_perfis.update({r["nome"]: r.to_dict()})
                    for _, r in edited_p.iterrows()
                ]
                st.session_state.config_perfis = new_perfis
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)


def _render_editor_tabela_config(db, type_key, data_dict):
    rows = []
    for k, v in data_dict.items():
        if isinstance(v, dict):
            r = {"nome": k}
            r.update(v)
            rows.append(r)
        else:
            rows.append({"nome": k, "valor": v})

    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df, num_rows="dynamic", use_container_width=True, key=f"edit_{type_key}"
    )

    if st.button(f"Salvar {type_key.title()}"):
        df_to_save = edited.copy()
        if type_key == "cabos" and "coef" in df_to_save.columns:
            df_to_save.rename(columns={"coef": "coeficiente"}, inplace=True)
        elif type_key == "ips" and "pot" in df_to_save.columns:
            df_to_save.rename(columns={"pot": "potencia_watts"}, inplace=True)

        ok, msg = db.update_configs(type_key, df_to_save)
        if ok:
            st.success(msg)
            new_dict = {}
            for _, r in edited.iterrows():
                val = r.to_dict()
                key = val.pop("nome")
                new_dict[key] = val
            if type_key == "cabos":
                st.session_state.config_cabos = new_dict
            if type_key == "ips":
                st.session_state.config_ips = new_dict
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)
