# frontend/app.py
import streamlit as st
import sys
import os

# CONFIGURA PATH PARA ENCONTRAR O BACKEND
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(root_dir)

# Importa do backend correto
from backend.db import DatabaseManager
from frontend.views.dashboard import render_dashboard_projetos
from frontend.views.config import render_configuracoes_avancadas
from frontend.views.editor import render_editor_cenario

# [CORREÇÃO] Apenas uma chamada de configuração de página
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

        # [CRÍTICO] Carrega as configurações do DB
        # O método load_configs agora retorna 5 itens (incluindo demandas)
        try:
            cabos, ips, trafos, perfis, demandas = st.session_state.db.load_configs()

            st.session_state.config_cabos = cabos
            st.session_state.config_ips = ips
            st.session_state.config_trafos = trafos
            st.session_state.config_perfis = perfis
            st.session_state.config_demandas = demandas
        except Exception as e:
            st.error(f"Erro crítico ao carregar configurações do banco: {e}")
            # Inicializa vazio para não quebrar a UI
            st.session_state.config_cabos = {}
            st.session_state.config_ips = {}
            st.session_state.config_trafos = []
            st.session_state.config_perfis = {}
            st.session_state.config_demandas = []


init_session()

# --- SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    c1, c2 = st.columns([1, 1])

    # Caminhos das imagens
    static_dir = os.path.join(current_dir, "static")
    path_logo_main = os.path.join(static_dir, "logo.png")
    path_logo_im3 = os.path.join(static_dir, "logoim3.png")

    with c1:
        if os.path.exists(path_logo_main):
            st.image(path_logo_main, use_container_width=True)
        else:
            st.subheader("⚡ SisCQT")

    with c2:
        if os.path.exists(path_logo_im3):
            st.image(path_logo_im3, use_container_width=True)
        else:
            st.caption("Enterprise Ed.")

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

# --- ROTEAMENTO ---
if st.session_state.get("current_view") == "Dashboard":
    render_dashboard_projetos()

elif st.session_state.get("current_view") == "Editor":
    if st.session_state.get("active_project_id"):
        # Garante que as demandas estejam no contexto (caso precise passar manualmente)
        render_editor_cenario(st.session_state.active_project_id)
    else:
        st.session_state.current_view = "Dashboard"
        st.rerun()

elif st.session_state.get("current_view") == "Configs":
    render_configuracoes_avancadas(st.session_state.db)
