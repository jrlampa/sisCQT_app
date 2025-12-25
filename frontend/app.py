# frontend/app.py
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import DatabaseManager
from frontend.views.dashboard import render_dashboard_projetos
from frontend.views.config import render_configuracoes_avancadas
from frontend.views.editor import render_editor_cenario

st.set_page_config(
    page_title="SisCQT Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session():
    if "db" not in st.session_state:
        st.session_state.db = DatabaseManager()
    if "engine_mode" not in st.session_state:
        st.session_state.engine_mode = "Motor Local (Offline)"
    if "current_view" not in st.session_state:
        st.session_state.current_view = "Dashboard"
    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None
    if "cenarios" not in st.session_state:
        st.session_state.cenarios = {}
        st.session_state.params = {}
        st.session_state.resultados = {}
        try:
            cabos, ips, trafos, perfis = st.session_state.db.load_configs()
            st.session_state.config_cabos = cabos
            st.session_state.config_trafos = trafos
            st.session_state.config_ips = ips
            st.session_state.config_perfis = perfis
        except:
            pass


init_session()

with st.sidebar:
    c1, c2 = st.columns([1, 1])
    with c1:
        if os.path.exists("frontend/static/logo_sisCQT.png"):
            st.image("frontend/static/logo_sisCQT.png", use_container_width=True)
        else:
            st.subheader("⚡ SisCQT")
    with c2:
        if os.path.exists("frontend/static/logo_im3.png"):
            st.image("frontend/static/logo_im3.png", use_container_width=True)
        else:
            st.info("IM3 Brasil")
    st.divider()

    if st.button(
        "📊 Dashboard",
        use_container_width=True,
        type="secondary" if st.session_state.current_view != "Dashboard" else "primary",
    ):
        st.session_state.current_view = "Dashboard"
        st.session_state.active_project_id = None
        st.rerun()
    if st.button(
        "⚙️ Configurações",
        use_container_width=True,
        type="secondary" if st.session_state.current_view != "Configs" else "primary",
    ):
        st.session_state.current_view = "Configs"
        st.session_state.active_project_id = None
        st.rerun()

    st.divider()
    icon = "☁️" if "Nuvem" in st.session_state.engine_mode else "💻"
    st.caption(f"Motor: {icon} {st.session_state.engine_mode}")

if st.session_state.current_view == "Dashboard":
    render_dashboard_projetos()
elif st.session_state.current_view == "Editor":
    if st.session_state.active_project_id:
        render_editor_cenario(st.session_state.active_project_id)
    else:
        st.session_state.current_view = "Dashboard"
        st.rerun()
elif st.session_state.current_view == "Configs":
    render_configuracoes_avancadas(st.session_state.db)
