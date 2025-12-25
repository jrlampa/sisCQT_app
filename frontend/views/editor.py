import streamlit as st
import pandas as pd
import time
import copy
from backend.engine import ElectricalEngine
from backend.utils import DiagnosticoEngenharia, SimuladorReadequacao
from backend.constantes import DEFAULT_COL_ORDER
from frontend.visual import gerar_diagrama
from frontend.components.ui_kit import ui_metric_card, ui_status_badge
from frontend.views.reporting import gerar_pdf

try:
    from frontend.api_client import APIClient

    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


def render_editor_cenario(nome_cenario):
    # --- HEADER ---
    c_back, c_title = st.columns([1, 10])
    with c_back:
        if st.button("⬅️", help="Voltar ao Dashboard"):
            st.session_state.current_view = "Dashboard"
            st.session_state.active_project_id = None
            st.rerun()
    with c_title:
        novo_nome = st.text_input(
            "Nome do Cenário",
            value=nome_cenario,
            label_visibility="collapsed",
            key="edit_cenario_name",
        )
        if novo_nome != nome_cenario:
            if novo_nome not in st.session_state.cenarios:
                st.session_state.cenarios[novo_nome] = st.session_state.cenarios.pop(
                    nome_cenario
                )
                st.session_state.params[novo_nome] = st.session_state.params.pop(
                    nome_cenario
                )
                if nome_cenario in st.session_state.resultados:
                    st.session_state.resultados[novo_nome] = (
                        st.session_state.resultados.pop(nome_cenario)
                    )
                st.session_state.active_project_id = novo_nome
                st.rerun()

    df_atual = st.session_state.cenarios[st.session_state.active_project_id]
    params = st.session_state.params[st.session_state.active_project_id]

    # --- INPUT ---
    with st.expander("🛠️ Parâmetros Técnicos & Topologia", expanded=True):
        p1, p2, p3, p4 = st.columns(4)
        trafos_opt = st.session_state.config_trafos
        perfis_opt = list(st.session_state.config_perfis.keys())

        with p1:
            params["trafo_kva"] = st.selectbox(
                "Trafo (kVA)",
                trafos_opt,
                index=(
                    trafos_opt.index(params.get("trafo_kva", 75))
                    if params.get("trafo_kva") in trafos_opt
                    else 0
                ),
            )
        with p2:
            params["perfil"] = st.selectbox(
                "Perfil de Rede",
                perfis_opt,
                index=(
                    perfis_opt.index(params.get("perfil"))
                    if params.get("perfil") in perfis_opt
                    else 0
                ),
            )
        with p3:
            params["classe_tipo"] = st.selectbox(
                "Método de Demanda",
                ["Automático", "Manual"],
                index=0 if params.get("classe_tipo") == "Automático" else 1,
            )
        with p4:
            dis = params["classe_tipo"] == "Automático"
            params["classe_manual"] = st.selectbox(
                "Classe Manual",
                ["A", "B", "C", "D"],
                disabled=dis,
                index=["A", "B", "C", "D"].index(params.get("classe_manual", "A")),
            )

        st.markdown("#### 📐 Levantamento de Rede")
        cabos_opt = list(st.session_state.config_cabos.keys())
        ips_opt = list(st.session_state.config_ips.keys())

        col_cfg = {
            "PONTO": st.column_config.TextColumn("Ponto", required=True, width="small"),
            "MONTANTE": st.column_config.TextColumn("Montante", width="small"),
            "METROS": st.column_config.NumberColumn(
                "Dist.(m)", min_value=0.0, format="%.1f", width="small"
            ),
            "CABO": st.column_config.SelectboxColumn(
                "Cabo", options=cabos_opt, required=False, width="medium"
            ),
            "TIPO_IP": st.column_config.SelectboxColumn(
                "IP", options=ips_opt, required=False, width="medium"
            ),
            "QTD_IP": st.column_config.NumberColumn(
                "# IP", min_value=0, step=1, width="small"
            ),
            "CARGA_ESP_KVA": st.column_config.NumberColumn(
                "KVA Esp", min_value=0.0, format="%.2f", width="small"
            ),
            "MONO": st.column_config.NumberColumn("M", min_value=0, width="small"),
            "BIFÁSICO": st.column_config.NumberColumn("B", min_value=0, width="small"),
            "TRIFÁSICO": st.column_config.NumberColumn("T", min_value=0, width="small"),
        }

        edited_df = st.data_editor(
            df_atual,
            column_config=col_cfg,
            column_order=DEFAULT_COL_ORDER,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{nome_cenario}",
        )

        c_check, c_calc = st.columns([1, 2])
        with c_check:
            auto_montante = st.checkbox("🔗 Auto-conectar (Cascata)")

        with c_calc:
            mode_label = st.session_state.get("engine_mode", "Local")
            if st.button(
                f"🚀 PROCESSAR CÁLCULO ({'☁️ Nuvem' if 'Nuvem' in mode_label else '💻 Local'})",
                type="primary",
                use_container_width=True,
            ):
                if auto_montante and len(edited_df) > 1:
                    for i in range(1, len(edited_df)):
                        if not str(edited_df.iat[i, 1]).strip():
                            edited_df.iat[i, 1] = edited_df.iat[i - 1, 0]

                st.session_state.cenarios[nome_cenario] = edited_df
                df_limpo = ElectricalEngine.limpar_linhas_vazias(edited_df)
                erros = ElectricalEngine.validar_preenchimento(
                    df_limpo, st.session_state.config_ips
                )

                if erros:
                    st.error("🛑 Erros de Preenchimento:")
                    [st.write(f"- {e}") for e in erros]
                else:
                    _executar_calculo_otimizado(nome_cenario, df_limpo)

    # --- RESULTADOS ---
    if nome_cenario in st.session_state.resultados:
        res = st.session_state.resultados[nome_cenario]
        kpis, df_res, avisos = res["kpis"], res["df"], res["avisos"]

        st.markdown("### 📈 Resultados do Dimensionamento")
        limites = kpis.get("limites_usados", {})
        aprovado = (
            (kpis["ocupacao"] <= limites.get("sobrecarga_max", 100))
            and (kpis["max_cqt"] <= limites.get("cqt_max", 6))
            and (not any("CRÍTICO" in a for a in avisos))
        )
        ui_status_badge(aprovado, kpis["ocupacao"], kpis["max_cqt"])

        t1, t2, t3, t4, t5 = st.tabs(
            ["🔍 Diagnóstico", "📋 Tabela", "🕸️ Diagrama", "🧪 Simulação", "🗂️ Relatório"]
        )

        with t1:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ui_metric_card(
                    "Ocupação Trafo",
                    f"{kpis['ocupacao']:.1f}%",
                    f"Limite: {limites.get('sobrecarga_max')}%",
                )
            with c2:
                ui_metric_card(
                    "Queda Tensão Máx",
                    f"{kpis['max_cqt']:.2f}%",
                    f"Limite: {limites.get('cqt_max')}%",
                )
            with c3:
                ui_metric_card("Demanda Total", f"{kpis['demanda']:.1f} kVA")
            with c4:
                ui_metric_card("Clientes", f"{kpis['clientes']}")

            analise_bari = DiagnosticoEngenharia.analisar_baricentro(
                df_res, params["trafo_kva"]
            )
            if analise_bari["status"] == "OTIMIZADO":
                st.success(f"**Baricentro:** {analise_bari['msg']}", icon="🎯")
            elif analise_bari["status"] == "SUGESTAO":
                st.info(f"**Baricentro:** {analise_bari['msg']}", icon="📍")

            if avisos:
                with st.expander("⚠️ Diário de Bordo", expanded=True):
                    for a in avisos:
                        st.write(f"{'🔥' if 'CRÍTICO' in a else '⚠️'} {a}")

        with t2:
            st.dataframe(
                df_res[
                    [
                        "PONTO",
                        "MONTANTE",
                        "CABO",
                        "METROS",
                        "CQT_TRECHO",
                        "CQT_ACUMULADA",
                        "ICC_KA",
                        "SUGESTAO_BALANCEAMENTO",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        with t3:
            grafico = gerar_diagrama(df_res, limites)
            if grafico:
                st.graphviz_chart(grafico)
        with t4:
            render_simulation_module(nome_cenario, df_res, params)
        with t5:
            st.info("Exportação de Documentos.")
            c_pdf, c_csv = st.columns(2)
            centro_sug = ElectricalEngine.sugerir_centro_carga(df_res)
            with c_pdf:
                pdf_bytes = gerar_pdf(
                    nome_cenario,
                    kpis,
                    df_res,
                    gerar_diagrama(df_res, limites),
                    0.0,
                    centro_sug,
                    avisos,
                )
                st.download_button(
                    "📄 Baixar PDF",
                    pdf_bytes,
                    f"{nome_cenario}.pdf",
                    "application/pdf",
                    use_container_width=True,
                )
            with c_csv:
                st.download_button(
                    "📊 Baixar CSV",
                    df_res.to_csv(index=False).encode("utf-8"),
                    f"{nome_cenario}.csv",
                    "text/csv",
                    use_container_width=True,
                )


def _executar_calculo_otimizado(nome, df_input):
    mode = st.session_state.get("engine_mode", "Local")
    with st.spinner(f"Calculando via {mode}..."):
        time.sleep(0.3)
        if "Nuvem" in mode and API_AVAILABLE:
            df_res, kpis, avisos = APIClient.calcular_via_api(
                df_input, st.session_state.params[nome]
            )
            if df_res.empty:
                st.error("Erro API")
                return
        else:
            cabos_s = {
                k: v["coef"] if isinstance(v, dict) else v
                for k, v in st.session_state.config_cabos.items()
            }
            ips_s = {
                k: v["pot"] if isinstance(v, dict) else v
                for k, v in st.session_state.config_ips.items()
            }
            cfg_ctx = {
                "cabos": cabos_s,
                "ips": ips_s,
                "perfis": st.session_state.config_perfis,
            }
            df_res, kpis, avisos = ElectricalEngine.calcular(
                df_input, st.session_state.params[nome], cfg_ctx
            )

        st.session_state.resultados[nome] = {
            "df": df_res,
            "kpis": kpis,
            "avisos": avisos,
        }
        st.toast("Sucesso!", icon="✅")
        st.rerun()


def render_simulation_module(nome_origem, df_base, params_base):
    st.markdown("#### 🧪 Simulador Automático")
    if st.button("▶️ Otimizar Topologia", key=f"btn_sim_{nome_origem}"):
        with st.spinner("Simulando..."):
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
            res = SimuladorReadequacao.executar(
                nome_origem,
                df_base,
                params_base,
                full_cfg,
                list(st.session_state.config_cabos.keys()),
            )
            st.session_state[f"sim_last_{nome_origem}"] = res

    if f"sim_last_{nome_origem}" in st.session_state:
        res = st.session_state[f"sim_last_{nome_origem}"]
        c1, c2 = st.columns(2)
        c1.metric("Queda Original", f"{df_base['CQT_ACUMULADA'].max():.2f}%")
        c2.metric(
            "Queda Simulada", f"{res['kpis']['max_cqt']:.2f}%", delta_color="inverse"
        )
        if res["log"]:
            st.table(
                pd.DataFrame([{"Ponto": k, "Troca": v} for k, v in res["log"].items()])
            )
            if st.button("Aplicar como Novo Cenário"):
                new_n = f"{nome_origem}_Otimizado"
                st.session_state.cenarios[new_n] = res["df"].copy()
                st.session_state.params[new_n] = copy.deepcopy(params_base)
                st.session_state.resultados[new_n] = {
                    "df": res["df"],
                    "kpis": res["kpis"],
                    "avisos": [],
                }
                st.success("Criado!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Sem melhorias possíveis.")
