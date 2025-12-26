# siscqt_gui.py
import streamlit as st
import pandas as pd
import time
import copy
import tempfile
import os
from typing import Dict, Any, List, Optional
from fpdf import FPDF
from siscqt_engine import ElectricalEngine
from siscqt_utils import DiagnosticoEngenharia, SimuladorReadequacao
from siscqt_constantes import DEFAULT_COL_ORDER, MEMORIAL_TEXTO
from siscqt_visual import gerar_diagrama

# IMPORTAÇÃO CENTRALIZADA
from normalizacao_dados import sanitizar

# =============================================================================
# 1. UTILITÁRIOS DE EXPORTAÇÃO (PDF)
# =============================================================================


def safe_text(text: Any) -> str:
    """Sanitiza strings para compatibilidade com encoding Latin-1 (PDF)."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


class PDFReport(FPDF):
    """Classe responsável pela estrutura do documento PDF (Header/Footer)."""

    def header(self):
        self.set_font("Arial", "B", 15)
        self.cell(0, 10, safe_text("Memorial de Cálculo - SisCQT (QTOS)"), 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, safe_text(f"Página {self.page_no()}"), 0, 0, "C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, safe_text(title), 0, 1, "L", 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 6, safe_text(body))
        self.ln()

    def chapter_body_small(self, body):
        self.set_font("Arial", "", 9)
        self.multi_cell(0, 5, safe_text(body))
        self.ln()


def gerar_pdf(
    nome_proj: str,
    kpis: Dict,
    df: pd.DataFrame,
    dot_diagram: Any,
    custo_total: float,
    centro_carga: Dict,
    avisos: List[str],
    estudos_extras: Optional[Dict] = None,
) -> bytes:
    """
    Gera o memorial de cálculo completo em PDF.
    Inclui: Metodologia, Resumo, Diagrama, Tabela Técnica e Sugestões.
    """
    pdf = PDFReport()

    # 1. Memorial Explicativo
    pdf.add_page()
    pdf.chapter_title("1. Memorial Explicativo (Metodologia)")
    pdf.chapter_body_small(MEMORIAL_TEXTO)

    # 2. Resumo
    pdf.add_page()
    pdf.chapter_title("2. Resumo do Dimensionamento")
    limites = kpis.get("limites_usados", {})
    lim_oc = limites.get("sobrecarga_max", 100.0)
    lim_qd = limites.get("cqt_max", 6.0)
    val_ocupacao = kpis.get("ocupacao", 0.0)
    val_max_cqt = kpis.get("max_cqt", 0.0)
    val_demanda = kpis.get("demanda", 0.0)

    status = (
        "APROVADO"
        if val_ocupacao <= lim_oc and val_max_cqt <= lim_qd
        else "COM RESTRIÇÕES"
    )
    texto_resumo = (
        f"Projeto: {nome_proj}\nStatus: {status}\nTrafo: {val_ocupacao:.1f}%\n"
        f"Demanda: {val_demanda:.2f} kVA\nQueda Max: {val_max_cqt:.2f}%\n"
        f"Custo Estimado: R$ {custo_total:,.2f}\nSugestão Centro de Carga: {centro_carga}"
    )
    pdf.chapter_body(texto_resumo)

    if avisos:
        pdf.set_text_color(200, 0, 0)
        pdf.chapter_body("Alertas e Diagnósticos:\n" + "\n".join(avisos))
        pdf.set_text_color(0, 0, 0)

    # 3. Diagrama
    if dot_diagram:
        pdf.chapter_title("3. Diagrama Unifilar")
        img_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp_name = tmp.name
            base_name = tmp_name.replace(".png", "")
            img_path = dot_diagram.render(
                filename=base_name, format="png", cleanup=True
            )
            pdf.image(img_path, x=10, w=190)
            pdf.ln(10)
        except:
            pass
        finally:
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except:
                    pass

    # 4. Tabela Técnica
    pdf.add_page()
    pdf.chapter_title("4. Tabela Técnica")
    pdf.set_font("Arial", "B", 8)
    cols = [
        ("PONTO", 20),
        ("CABO", 45),
        ("DIST(m)", 15),
        ("QT ACUM", 15),
        ("ICC(kA)", 15),
        ("BALANÇO", 70),
    ]
    for c, w in cols:
        pdf.cell(w, 7, safe_text(c), 1)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, r in df.iterrows():
        p = safe_text(str(r["PONTO"])[:10])
        c = safe_text(str(r["CABO"])[:22])
        m = f"{r.get('METROS',0):.0f}"
        q = f"{r.get('CQT_ACUMULADA',0):.2f}%"
        icc = f"{r.get('ICC_KA',0):.3f}"
        bal = safe_text(str(r.get("SUGESTAO_BALANCEAMENTO", "-"))[:40])
        pdf.cell(20, 6, p, 1)
        pdf.cell(45, 6, c, 1)
        pdf.cell(15, 6, m, 1)
        pdf.cell(15, 6, q, 1)
        pdf.cell(15, 6, icc, 1)
        pdf.cell(70, 6, bal, 1)
        pdf.ln()

    # 5. Sugestões Extras (Baricentro e Engenharia)
    if estudos_extras:
        pdf.add_page()
        pdf.chapter_title("5. Alternativas de Engenharia (Sugestões)")
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(
            0,
            5,
            safe_text(
                "NOTA: Esta seção apresenta sugestões conceituais baseadas em heurísticas "
                "de engenharia para apoio à decisão. Não constituem projeto executivo."
            ),
        )
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)

        bari = estudos_extras.get("baricentro", {})
        if bari:
            msg = bari.get("msg", "")
            pdf.multi_cell(0, 6, safe_text(f"Analise de Baricentro: {msg}"))
            pdf.ln(2)

        sugs = estudos_extras.get("sugestoes", [])
        if sugs:
            for s in sugs:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, safe_text(f">> {s['titulo']}"), 0, 1)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, safe_text(s["texto"]))
                pdf.ln(3)

    return pdf.output(dest="S").encode("latin-1", errors="replace")


# =============================================================================
# 2. CONFIGURAÇÕES GLOBAIS
# =============================================================================


def render_config_page(db_manager):
    """Renderiza a página de configurações globais (Condutores, Trafos, IPs, Perfis)."""
    st.markdown("### Configurações de Sistema")
    st.info("Parâmetros globais aplicáveis a novos projetos e recálculos.")

    t1, t2, t3, t4, t5 = st.tabs(
        ["Condutores", "Transformadores", "Iluminação", "Perfis", "🧪 Simulação"]
    )

    with t1:
        _render_config_cabos(db_manager)
    with t2:
        _render_config_trafos(db_manager)
    with t3:
        _render_config_ips(db_manager)
    with t4:
        _render_config_perfis(db_manager)
    with t5:
        _render_config_simulacao()


def _render_config_cabos(db_manager):
    raw_cabos = st.session_state.config_cabos
    rows = []
    for k, v in raw_cabos.items():
        if isinstance(v, dict):
            rows.append(
                {"nome": k, "coeficiente": v["coef"], "preco": v.get("preco", 0.0)}
            )
        else:
            rows.append({"nome": k, "coeficiente": v, "preco": 0.0})

    df_cabos = pd.DataFrame(rows)
    edited_cabos = st.data_editor(
        df_cabos,
        num_rows="dynamic",
        key="edit_cabos",
        hide_index=True,
        use_container_width=True,
        column_config={
            "nome": st.column_config.TextColumn("Descrição", required=True),
            "coeficiente": st.column_config.NumberColumn("Coef. Queda", format="%.4f"),
            "preco": st.column_config.NumberColumn(
                "Preço/m (R$)", format="R$ %.2f", min_value=0.0
            ),
        },
    )
    if st.button("Salvar Alterações em Condutores", key="save_cabos"):
        ok, msg = db_manager.update_configs("cabos", edited_cabos)
        if ok:
            st.success(msg)
            new_dict = {}
            for _, r in edited_cabos.iterrows():
                new_dict[r["nome"]] = {"coef": r["coeficiente"], "preco": r["preco"]}
            st.session_state.config_cabos = new_dict
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)


def _render_config_trafos(db_manager):
    df_trafos = pd.DataFrame(st.session_state.config_trafos, columns=["kva"])
    edited_trafos = st.data_editor(
        df_trafos,
        num_rows="dynamic",
        key="edit_trafos",
        hide_index=True,
        use_container_width=True,
    )
    if st.button("Salvar Padronização de Trafos", key="save_trafos"):
        ok, msg = db_manager.update_configs("trafos", edited_trafos)
        if ok:
            st.success(msg)
            st.session_state.config_trafos = sorted(edited_trafos["kva"].tolist())
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)


def _render_config_ips(db_manager):
    raw_ips = st.session_state.config_ips
    rows_ip = []
    for k, v in raw_ips.items():
        if isinstance(v, dict):
            rows_ip.append(
                {"nome": k, "potencia_watts": v["pot"], "preco": v.get("preco", 0.0)}
            )
        else:
            rows_ip.append({"nome": k, "potencia_watts": v, "preco": 0.0})

    df_ips = pd.DataFrame(rows_ip)
    edited_ips = st.data_editor(
        df_ips,
        num_rows="dynamic",
        key="edit_ips",
        hide_index=True,
        use_container_width=True,
        column_config={
            "nome": st.column_config.TextColumn("Tipo", required=True),
            "potencia_watts": st.column_config.NumberColumn(
                "Potência (W)", format="%.1f"
            ),
            "preco": st.column_config.NumberColumn(
                "Preço Unit. (R$)", format="R$ %.2f", min_value=0.0
            ),
        },
    )
    if st.button("Salvar Configuração de IP", key="save_ips"):
        ok, msg = db_manager.update_configs("ips", edited_ips)
        if ok:
            st.success(msg)
            new_dict = {}
            for _, r in edited_ips.iterrows():
                new_dict[r["nome"]] = {"pot": r["potencia_watts"], "preco": r["preco"]}
            st.session_state.config_ips = new_dict
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)


def _render_config_perfis(db_manager):
    rows = []
    for nome, dados in st.session_state.config_perfis.items():
        rows.append({**dados, "nome": nome})

    df_perfis = pd.DataFrame(rows)
    edited_perfis = st.data_editor(
        df_perfis,
        num_rows="dynamic",
        key="edit_perfis",
        hide_index=True,
        use_container_width=True,
    )
    if st.button("Salvar Perfis Normativos", key="save_perfis"):
        ok, msg = db_manager.update_configs("perfis", edited_perfis)
        if ok:
            st.success(msg)
            new_perfis = {}
            for _, r in edited_perfis.iterrows():
                new_perfis[r["nome"]] = r.to_dict()
            st.session_state.config_perfis = new_perfis
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)


def _render_config_simulacao():
    st.markdown("##### 🧪 Parâmetros de Simulação")
    todos_cabos = list(st.session_state.config_cabos.keys())
    if "sim_cabos_allowed" not in st.session_state:
        padrao = [c for c in todos_cabos if "3x" in c.lower()]
        st.session_state.sim_cabos_allowed = padrao if padrao else todos_cabos

    selecionados = st.multiselect(
        "Condutores Habilitados:",
        options=todos_cabos,
        default=st.session_state.sim_cabos_allowed,
        key="ms_sim_cabos",
    )
    if selecionados != st.session_state.sim_cabos_allowed:
        st.session_state.sim_cabos_allowed = selecionados
        st.rerun()


# =============================================================================
# 3. RENDERIZAÇÃO DE ABAS DE PROJETO
# =============================================================================


def render_aba(nome, idx):
    """Orquestrador principal da aba de projeto (Edição -> Resultados)."""
    esta_calculado = nome in st.session_state.resultados

    # 1. Header e Parâmetros
    _render_header_aba(nome, idx)
    _render_parametros_aba(nome, idx, disabled=esta_calculado)
    st.markdown("---")

    # 2. Modo Edição ou Resultados
    if not esta_calculado:
        _render_modo_edicao(nome, idx)
    else:
        _render_modo_resultados(nome, idx)


def _render_header_aba(nome, idx):
    """Renderiza input de nome e botão de excluir."""
    with st.container():
        c_id, c_action = st.columns([3, 1])
        with c_id:
            new_n = st.text_input(
                "Identificação",
                value=nome,
                key=f"rn_{idx}",
                placeholder="Ex: CQT-001",
                label_visibility="collapsed",
            )
            # Lógica de renomeação de aba
            if new_n != nome and new_n.strip():
                if new_n in st.session_state.lista_abas:
                    st.error("Nome duplicado")
                    st.stop()
                st.session_state.lista_abas[idx] = new_n
                st.session_state.cenarios[new_n] = st.session_state.cenarios.pop(nome)
                st.session_state.params[new_n] = st.session_state.params.pop(nome)
                if nome in st.session_state.resultados:
                    st.session_state.resultados[new_n] = (
                        st.session_state.resultados.pop(nome)
                    )
                st.rerun()
        with c_action:
            if st.button("🗑️", key=f"del_{idx}", help="Excluir"):
                st.session_state.delete_tab = nome
                st.rerun()


def _render_parametros_aba(nome, idx, disabled=False):
    """Renderiza seletores de Trafo, Perfil e Classe."""
    p = st.session_state.params[nome]
    trafos_opt = st.session_state.config_trafos
    perfis_opt = list(st.session_state.config_perfis.keys())

    with st.container():
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)

        # Trafo
        with c_p1:
            curr_trafo = p.get("trafo_kva", 150)
            if curr_trafo not in trafos_opt:
                trafos_opt.append(curr_trafo)
                trafos_opt.sort()
            p["trafo_kva"] = st.selectbox(
                "Trafo (kVA)",
                trafos_opt,
                index=trafos_opt.index(curr_trafo),
                key=f"tr_{idx}",
                disabled=disabled,
            )

        # Perfil
        with c_p2:
            curr_perf = p.get("perfil", perfis_opt[0] if perfis_opt else "")
            idx_perf = perfis_opt.index(curr_perf) if curr_perf in perfis_opt else 0
            p["perfil"] = st.selectbox(
                "Perfil",
                perfis_opt,
                index=idx_perf,
                key=f"perf_{idx}",
                disabled=disabled,
            )

        # Classe Automática/Manual
        with c_p3:
            p["classe_tipo"] = st.selectbox(
                "Classe",
                ["Automático", "Manual"],
                index=0 if p.get("classe_tipo") == "Automático" else 1,
                key=f"tm_{idx}",
                disabled=disabled,
            )

        # Classe Manual
        with c_p4:
            dis_m = p["classe_tipo"] == "Automático"
            p["classe_manual"] = st.selectbox(
                "Man.",
                ["A", "B", "C", "D"],
                key=f"cm_{idx}",
                disabled=disabled or dis_m,
            )

        st.session_state.params[nome] = p


def _render_modo_edicao(nome, idx):
    """Renderiza o editor de dados de entrada (Levantamento de Rede)."""
    st.subheader("Levantamento de Rede")
    cabos_opt = list(st.session_state.config_cabos.keys())
    ips_opt = list(st.session_state.config_ips.keys())
    final_col_order = st.session_state.get(f"col_order_{idx}", DEFAULT_COL_ORDER)

    col_cfg_edit = {
        "PONTO": st.column_config.TextColumn("Ponto", required=True, width="small"),
        "MONTANTE": st.column_config.TextColumn("Montante", width="small"),
        "METROS": st.column_config.NumberColumn(
            "Dist.(m)", min_value=0.0, format="%.1f", width="small"
        ),
        "CABO": st.column_config.SelectboxColumn(
            "Condutor", options=cabos_opt, required=False, width="medium"
        ),
        "TIPO_IP": st.column_config.SelectboxColumn(
            "Ilum. Pública", options=ips_opt, required=False, width="medium"
        ),
        "QTD_IP": st.column_config.NumberColumn(
            "Qtd IP", min_value=0, step=1, width="small"
        ),
        "CARGA_ESP_KVA": st.column_config.NumberColumn(
            "Esp.(kVA)", min_value=0.0, format="%.2f", width="small"
        ),
        "TRI ESPECIAL": st.column_config.NumberColumn(
            "3F Esp", min_value=0, step=1, width="small"
        ),
        "MONO": st.column_config.NumberColumn("M", min_value=0, width="small"),
        "BIFÁSICO": st.column_config.NumberColumn("B", min_value=0, width="small"),
        "TRIFÁSICO": st.column_config.NumberColumn("T", min_value=0, width="small"),
    }

    with st.form(key=f"form_calc_{idx}"):
        df_atual = st.session_state.cenarios[nome]
        edited_df_form = st.data_editor(
            df_atual.reset_index(drop=True),
            key=f"ed_form_{idx}",
            num_rows="dynamic",
            use_container_width=True,
            column_config=col_cfg_edit,
            column_order=final_col_order,
            hide_index=True,
        )
        c_auto, c_sub = st.columns([1, 4])
        with c_auto:
            auto_ligar = st.checkbox("Auto-Montante", value=False)
        with c_sub:
            submitted = st.form_submit_button(
                "PROCESSAR CÁLCULO", type="primary", use_container_width=True
            )

    if submitted:
        # Lógica de auto-preenchimento de montante (UX)
        if auto_ligar and len(edited_df_form) > 1:
            for i in range(1, len(edited_df_form)):
                if not str(edited_df_form.iat[i, 1]).strip():
                    edited_df_form.iat[i, 1] = edited_df_form.iat[i - 1, 0]

        # --- NORMALIZAÇÃO CENTRALIZADA ---
        # 1. Sanitização (Tipos, Strings, TRAFO)
        df_limpo, erros_sanit = sanitizar(
            edited_df_form, valid_ips=st.session_state.config_ips
        )

        # 2. Validação Topológica (Duplicatas, Orfãos) - Ainda no Engine
        erros_topo = ElectricalEngine.validar_preenchimento(df_limpo)

        st.session_state.cenarios[nome] = df_limpo
        erros_totais = erros_sanit + erros_topo

        if erros_totais:
            st.session_state[f"alert_error_{idx}"] = erros_totais
            st.rerun()
        else:
            if f"alert_error_{idx}" in st.session_state:
                del st.session_state[f"alert_error_{idx}"]
            _executar_calculo(nome, df_limpo)

    if f"alert_error_{idx}" in st.session_state:
        st.error("Erros encontrados:")
        for e in st.session_state[f"alert_error_{idx}"]:
            st.write(f"- {e}")


def _render_modo_resultados(nome, idx):
    """Renderiza dashboard de resultados, métricas e abas técnicas."""
    res = st.session_state.resultados[nome]
    k = res.get("kpis", {})
    df_res = res.get("df", pd.DataFrame())
    avisos = res.get("avisos", [])
    limites = k.get("limites_usados", {})

    # 1. Métricas Principais
    _render_status_header(k, limites, avisos)
    _render_metricas_principais(k, limites, nome, idx)

    # 2. Abas de Detalhes
    t_diag, t_tec, t_bal, t_vis, t_sim, t_doc = st.tabs(
        [
            "🔍 Diagnóstico",
            "📋 Tabela Técnica",
            "⚖️ Balanceamento",
            "🕸️ Diagrama",
            "🧪 Simulação",
            "🗂️ Documentação",
        ]
    )

    with t_diag:
        _render_aba_diagnostico(df_res, k, avisos, limites)
    with t_tec:
        _render_aba_tecnica(df_res)
    with t_bal:
        _render_aba_balanceamento(df_res)
    with t_vis:
        _render_aba_visualizacao(df_res, limites, k.get("baricentro", {}))
    with t_sim:
        render_simulation_module(nome, idx, df_res, st.session_state.params[nome])
    with t_doc:
        _render_aba_documentacao(nome, res, limites)


def _render_status_header(k, limites, avisos):
    val_oc = k.get("ocupacao", 0.0)
    val_qt = k.get("max_cqt", 0.0)
    aprovado = (
        (val_oc <= limites.get("sobrecarga_max", 100))
        and (val_qt <= limites.get("cqt_max", 6))
        and not any("CRÍTICO" in a for a in avisos)
    )
    st.markdown(
        f"""<div style="background-color:{'#E8F5E9' if aprovado else '#FFEBEE'}; color:{'#2E7D32' if aprovado else '#C62828'}; padding: 8px; border-radius: 4px; border: 1px solid {'#A5D6A7' if aprovado else '#EF9A9A'}; text-align: center; font-weight: bold; margin-bottom: 10px;">{'PROJETO APROVADO' if aprovado else 'RESTRITO / REPROVADO'}</div>""",
        unsafe_allow_html=True,
    )


def _render_metricas_principais(k, limites, nome, idx):
    val_oc = k.get("ocupacao", 0.0)
    val_qt = k.get("max_cqt", 0.0)
    centro_sug = k.get("baricentro", {})

    ck1, ck2, ck3, ck4, ck5 = st.columns([1, 1, 1, 1.2, 0.5])

    ck1.metric(
        "Ocupação",
        f"{val_oc:.1f}%",
        f"Max {limites.get('sobrecarga_max', 100)}%",
        delta_color="inverse",
    )
    ck2.metric(
        "Queda Max",
        f"{val_qt:.2f}%",
        f"Max {limites.get('cqt_max', 6)}%",
        delta_color="inverse",
    )
    ck3.metric("Demanda", f"{k.get('demanda',0):.1f} kVA")

    ponto_sug = centro_sug.get("ponto_proximo", "N/A")
    dist_ideal = centro_sug.get("distancia_ideal", 0)
    sub_label = (
        f"({dist_ideal:.0f}m)"
        if (isinstance(dist_ideal, (int, float)) and dist_ideal > 0)
        else ""
    )
    ck4.metric("Baricentro", f"{ponto_sug}", sub_label)

    with ck5:
        st.write("")
        if st.button("✏️", key=f"btn_edit_{idx}", help="Editar Levantamento"):
            del st.session_state.resultados[nome]
            st.rerun()


def _render_aba_diagnostico(df_res, k, avisos, limites):
    st.markdown("#### Análise Técnica do Circuito")
    c_left, c_right = st.columns(2, gap="large")

    val_oc = k.get("ocupacao", 0.0)
    val_qt = k.get("max_cqt", 0.0)
    centro_sug = k.get("baricentro", {})
    aprovado = val_oc <= limites.get("sobrecarga_max", 100) and val_qt <= limites.get(
        "cqt_max", 6
    )

    with c_left:
        st.info("##### 1. Conformidade Normativa (Leitura)")
        if aprovado and not any("CRÍTICO" in a for a in avisos):
            st.success(
                "O circuito atende a todos os critérios normativos configurados.",
                icon="✅",
            )
        else:
            if val_oc > limites.get("sobrecarga_max", 100):
                st.error(
                    f"**Sobrecarga:** O transformador opera acima do limite ({val_oc:.1f}%).",
                    icon="🔥",
                )
            if val_qt > limites.get("cqt_max", 6):
                st.error(
                    f"**Queda de Tensão:** Violação do limite de {limites.get('cqt_max')}% na ponta do circuito.",
                    icon="📉",
                )
            if avisos:
                st.markdown("**Alertas Pontuais:**")
                for a in avisos:
                    if "CRÍTICO" in a:
                        st.markdown(f"- 🔴 {a}")
                    elif "ALERTA" in a:
                        st.markdown(f"- ⚠️ {a}")

    with c_right:
        st.warning("##### 2. Alternativas de Engenharia (Sugestões)")
        # Baricentro
        msg_bari = centro_sug.get("msg", "Não calculado.")
        if "Baricentro" in msg_bari:
            st.info(f"**Análise de Localização:** {msg_bari}", icon="📍")
        else:
            st.write(f"**Análise de Localização:** {msg_bari}")

        # Recomendações
        recs = DiagnosticoEngenharia.gerar_recomendacoes(df_res, k, avisos)
        if recs:
            for r in recs:
                with st.expander(f"💡 {r['titulo']}", expanded=True):
                    st.write(r["texto"])
        elif aprovado:
            st.caption("Sem recomendações de engenharia adicionais necessárias.")


def _render_aba_tecnica(df_res):
    cols_show = [
        "PONTO",
        "MONTANTE",
        "CABO",
        "METROS",
        "CQT_TRECHO",
        "CQT_ACUMULADA",
        "ICC_KA",
    ]
    st.dataframe(
        df_res[cols_show],
        use_container_width=True,
        hide_index=True,
        column_config={
            "CQT_TRECHO": st.column_config.NumberColumn("QT Trecho", format="%.2f"),
            "CQT_ACUMULADA": st.column_config.NumberColumn("QT Acum", format="%.2f"),
        },
    )


def _render_aba_balanceamento(df_res):
    st.info("Apoio à Decisão: Sugestão de fases.")
    st.dataframe(
        df_res[["PONTO", "MONO", "BIFÁSICO", "TRIFÁSICO", "SUGESTAO_BALANCEAMENTO"]],
        use_container_width=True,
        hide_index=True,
    )


def _render_aba_visualizacao(df_res, limites, centro_sug):
    grafico = gerar_diagrama(df_res, limites, baricentro_info=centro_sug)
    if grafico:
        st.graphviz_chart(grafico)
    else:
        st.warning("Não foi possível gerar o diagrama.")


def _render_aba_documentacao(nome, res, limites):
    st.markdown("#### 📄 Geração de Documentação Técnica")
    k = res.get("kpis", {})
    df_res = res.get("df")
    avisos = res.get("avisos", [])
    centro_sug = k.get("baricentro", {})
    recs = DiagnosticoEngenharia.gerar_recomendacoes(df_res, k, avisos)

    ctx_extras = {"baricentro": centro_sug, "sugestoes": recs}

    try:
        pdf_bytes = gerar_pdf(
            nome,
            k,
            df_res,
            gerar_diagrama(df_res, limites),
            0.0,
            centro_sug,
            avisos,
            estudos_extras=ctx_extras,
        )
        st.download_button("Baixar PDF", pdf_bytes, f"{nome}.pdf", "application/pdf")
    except Exception as e:
        st.error(f"Erro PDF: {e}")

    st.download_button(
        "Baixar CSV", df_res.to_csv(index=False).encode("utf-8"), f"{nome}.csv"
    )


# =============================================================================
# 4. MÓDULO DE SIMULAÇÃO (READEQUAÇÃO)
# =============================================================================


def render_simulation_module(nome_origem, idx, df_base, params_base):
    """Renderiza interface e executa lógica do simulador de recondutoração."""
    st.markdown("#### 🧪 Simulador de Recondutoração (Apoio à Decisão)")
    st.info(
        """
        **⚠️ IMPORTANTE:** Esta ferramenta aplica automaticamente cabos de maior seção em trechos críticos, 
        seguindo uma lógica hierárquica (Fonte → Carga). Os resultados são hipóteses de cálculo.
        """,
        icon="👷",
    )

    # Configuração de Cabos
    todos_cabos = list(st.session_state.config_cabos.keys())
    if (
        "sim_cabos_allowed" not in st.session_state
        or not st.session_state.sim_cabos_allowed
    ):
        padrao = [
            c for c in todos_cabos if "3x" in c.lower() or "150" in c or "70" in c
        ]
        st.session_state.sim_cabos_allowed = padrao if padrao else todos_cabos

    with st.expander("⚙️ Configurar Cabos Permitidos na Simulação", expanded=False):
        selecionados = st.multiselect(
            "Selecione os condutores que o simulador pode utilizar:",
            options=todos_cabos,
            default=st.session_state.sim_cabos_allowed,
            key=f"ms_sim_{idx}",
        )
        if selecionados != st.session_state.sim_cabos_allowed:
            st.session_state.sim_cabos_allowed = selecionados
            st.rerun()

    # Execução
    if st.button(
        "▶️ Executar Simulação de Recondutoração", type="primary", key=f"btn_sim_{idx}"
    ):
        with st.spinner("Simulando correções topológicas..."):
            cabos_s = {
                k: v["coef"] if isinstance(v, dict) else v
                for k, v in st.session_state.config_cabos.items()
            }
            ips_s = {
                k: v["pot"] if isinstance(v, dict) else v
                for k, v in st.session_state.config_ips.items()
            }
            full_cfg = {
                "cabos": cabos_s,
                "ips": ips_s,
                "perfis": st.session_state.config_perfis,
            }

            resultado = SimuladorReadequacao.executar(
                nome_origem,
                df_base,
                params_base,
                full_cfg,
                st.session_state.sim_cabos_allowed,
            )

            # --- INTEGRAÇÃO BALANCEAMENTO DE FASES ---
            df_sim = resultado["df"]
            ordem_sim = ElectricalEngine.calcular_ordem_topologica(df_sim)
            pmap_sim = {p: i for i, p in enumerate(df_sim["PONTO"])}
            ElectricalEngine.balancear_fases(df_sim, ordem_sim, pmap_sim)
            resultado["df"] = df_sim  # Atualiza com sugestões
            # ------------------------------------------

            st.session_state[f"sim_res_{idx}"] = resultado

    # Resultados da Simulação
    if f"sim_res_{idx}" in st.session_state:
        _render_resultados_simulacao(
            st.session_state[f"sim_res_{idx}"], df_base, nome_origem, idx, params_base
        )


def _render_resultados_simulacao(res, df_base, nome_origem, idx, params_base):
    st.divider()
    c1, c2, c3 = st.columns(3)
    qt_antes = df_base["CQT_ACUMULADA"].max()
    qt_depois = res["kpis"]["max_cqt"]
    delta_qt = qt_depois - qt_antes
    houve_melhoria_tecnica = delta_qt < -0.01
    houve_trocas = len(res["log"]) > 0

    c1.metric("QT Antes", f"{qt_antes:.2f}%")
    c2.metric(
        "QT Simulada", f"{qt_depois:.2f}%", f"{delta_qt:.2f}%", delta_color="inverse"
    )

    status_msg = (
        "Simulação apresentou ganho."
        if houve_melhoria_tecnica
        else "Sem alteração viável."
    )
    if houve_trocas:
        status_msg = "Simulação realizada com alterações."
    c3.markdown(f"**Status:** {status_msg}")

    if houve_melhoria_tecnica or houve_trocas:
        st.write("##### Relatório de Impacto:")
        if houve_trocas:
            st.caption("Trechos recondutorados (Trafo → Ponta):")
            st.table(
                pd.DataFrame([{"Ponto": p, "Troca": t} for p, t in res["log"].items()])
            )
        elif houve_melhoria_tecnica:
            st.info(
                "ℹ️ Redução observada decorre da reavaliação de impedância sem troca física."
            )

        st.markdown("---")
        c_name, c_btn = st.columns([3, 1])
        nome_novo = c_name.text_input(
            "Nome do Novo Cenário:",
            value=f"{nome_origem} (Sim)",
            key=f"input_sim_name_{idx}",
        )

        c_btn.write("")
        c_btn.write("")
        if c_btn.button("✅ Criar Aba", key=f"btn_accept_sim_{idx}"):
            if nome_novo in st.session_state.lista_abas:
                st.error("Nome já existe!")
            else:
                st.session_state.lista_abas.append(nome_novo)
                st.session_state.cenarios[nome_novo] = res["df"].copy()
                st.session_state.params[nome_novo] = copy.deepcopy(params_base)
                st.session_state.resultados[nome_novo] = {
                    "df": res["df"],
                    "kpis": res["kpis"],
                    "avisos": [],
                }
                st.success(f"Cenário '{nome_novo}' criado com sucesso!")
                time.sleep(1)
                st.rerun()
    else:
        st.warning("O simulador não encontrou alterações viáveis.")


def _executar_calculo(nome, df_input):
    """Prepara contexto e chama ElectricalEngine para cálculo."""
    cabos_simple = {
        k: v["coef"] if isinstance(v, dict) else v
        for k, v in st.session_state.config_cabos.items()
    }
    ips_simple = {
        k: v["pot"] if isinstance(v, dict) else v
        for k, v in st.session_state.config_ips.items()
    }
    cfg_ctx = {
        "cabos": cabos_simple,
        "ips": ips_simple,
        "perfis": st.session_state.config_perfis,
    }

    df_res, kpis, avisos = ElectricalEngine.calcular(
        df_input, st.session_state.params[nome], cfg_ctx
    )

    # --- INTEGRAÇÃO BALANCEAMENTO DE FASES ---
    ordem = ElectricalEngine.calcular_ordem_topologica(df_res)
    pmap = {p: i for i, p in enumerate(df_res["PONTO"])}
    ElectricalEngine.balancear_fases(df_res, ordem, pmap)
    # ------------------------------------------

    st.session_state.resultados[nome] = {"df": df_res, "kpis": kpis, "avisos": avisos}
    st.rerun()
