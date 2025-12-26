# frontend/views/editor.py
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
    if "current_project_name" not in st.session_state:
        st.session_state.current_project_name = "Meu Projeto"

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("### 💾 Salvar")
        proj_name = st.text_input(
            "Nome do Projeto", value=st.session_state.current_project_name
        )
        st.session_state.current_project_name = proj_name

        if st.button("Salvar Tudo", type="primary", use_container_width=True):
            if not proj_name.strip():
                st.error("Defina um nome.")
            else:
                with st.spinner("Salvando..."):
                    ok, msg = st.session_state.db.salvar_projeto(
                        proj_name,
                        st.session_state.cenarios,
                        st.session_state.params,
                        overwrite_id=st.session_state.get("current_project_db_id"),
                    )
                    if ok:
                        st.success(f"✅ {msg}")
                        if not st.session_state.get("current_project_db_id"):
                            nid = st.session_state.db.check_nome(proj_name)
                            if nid:
                                st.session_state.current_project_db_id = nid
                    else:
                        st.error(f"❌ {msg}")

        st.divider()
        if st.button("⬅️ Dashboard", use_container_width=True):
            st.session_state.current_view = "Dashboard"
            st.session_state.active_project_id = None
            st.rerun()

    # --- HEADER ---
    c_back, c_title = st.columns([1, 10])
    with c_back:
        if st.button("🏠"):
            st.session_state.current_view = "Dashboard"
            st.rerun()
    with c_title:
        novo_nome = st.text_input(
            "Nome Cenário", value=nome_cenario, label_visibility="collapsed"
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

    # --- EDITOR ---
    df_atual = st.session_state.cenarios[st.session_state.active_project_id]
    if df_atual.empty or "TRAFO" not in df_atual["PONTO"].values:
        row_trafo = pd.DataFrame(
            [
                {
                    "PONTO": "TRAFO",
                    "MONTANTE": "",
                    "METROS": 0.0,
                    "CABO": "",
                    "MONO": 0,
                    "BIFÁSICO": 0,
                    "TRIFÁSICO": 0,
                    "TRI ESPECIAL": 0,
                    "CARGA_ESP_KVA": 0.0,
                    "TIPO_IP": "Sem IP",
                    "QTD_IP": 0,
                }
            ]
        )
        df_atual = pd.concat([row_trafo, df_atual], ignore_index=True)
        st.session_state.cenarios[st.session_state.active_project_id] = df_atual

    params = st.session_state.params[st.session_state.active_project_id]

    with st.expander("🛠️ Parâmetros & Rede", expanded=True):
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
                "Perfil",
                perfis_opt,
                index=(
                    perfis_opt.index(params.get("perfil"))
                    if params.get("perfil") in perfis_opt
                    else 0
                ),
            )
        with p3:
            params["classe_tipo"] = st.selectbox(
                "Demanda",
                ["Automático", "Manual"],
                index=0 if params.get("classe_tipo") == "Automático" else 1,
            )
        with p4:
            params["classe_manual"] = st.selectbox(
                "Classe",
                ["A", "B", "C", "D"],
                disabled=(params["classe_tipo"] == "Automático"),
                index=["A", "B", "C", "D"].index(params.get("classe_manual", "A")),
            )

        cabos_opt = list(st.session_state.config_cabos.keys())
        ips_opt = list(st.session_state.config_ips.keys())

        col_cfg = {
            "PONTO": st.column_config.TextColumn("Ponto", required=True),
            "MONTANTE": st.column_config.TextColumn("Montante"),
            "METROS": st.column_config.NumberColumn(
                "Dist.(m)", min_value=0.0, format="%.1f"
            ),
            "CABO": st.column_config.SelectboxColumn(
                "Cabo", options=cabos_opt, required=False
            ),
            "TIPO_IP": st.column_config.SelectboxColumn(
                "IP", options=ips_opt, required=False
            ),
            "QTD_IP": st.column_config.NumberColumn("# IP", min_value=0, step=1),
            "CARGA_ESP_KVA": st.column_config.NumberColumn(
                "KVA Esp", min_value=0.0, format="%.2f"
            ),
            "MONO": st.column_config.NumberColumn("M", min_value=0),
            "BIFÁSICO": st.column_config.NumberColumn("B", min_value=0),
            "TRIFÁSICO": st.column_config.NumberColumn("T", min_value=0),
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
            auto_montante = st.checkbox("🔗 Auto-conectar")

        with c_calc:
            if st.button(
                f"🚀 PROCESSAR CÁLCULO", type="primary", use_container_width=True
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
                    st.error("Erros:")
                    [st.write(f"- {e}") for e in erros]
                else:
                    _executar_calculo_otimizado(nome_cenario, df_limpo)

    # --- RESULTADOS ---
    if nome_cenario in st.session_state.resultados:
        res = st.session_state.resultados[nome_cenario]
        kpis = res.get("kpis", {})
        df_res = res.get("df", pd.DataFrame())
        avisos = res.get("avisos", [])

        if not kpis:
            st.error("Erro no cálculo.")
        else:
            st.markdown("### 📈 Resultados")
            limites = kpis.get("limites_usados", {})
            val_oc = kpis.get("ocupacao", 0.0)
            val_qt = kpis.get("max_cqt", 0.0)

            aprovado = (
                (val_oc <= limites.get("sobrecarga_max", 100))
                and (val_qt <= limites.get("cqt_max", 6))
                and (not any("CRÍTICO" in a for a in avisos))
            )
            ui_status_badge(aprovado, val_oc, val_qt)

            t1, t2, t3, t4, t5 = st.tabs(
                [
                    "🔍 Diagnóstico",
                    "📋 Tabela",
                    "🕸️ Diagrama",
                    "🧪 Simulação",
                    "🗂️ Relatório",
                ]
            )

            with t1:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    ui_metric_card(
                        "Ocupação",
                        f"{val_oc:.1f}%",
                        f"Lim: {limites.get('sobrecarga_max')}%",
                    )
                with c2:
                    ui_metric_card(
                        "Queda Max", f"{val_qt:.2f}%", f"Lim: {limites.get('cqt_max')}%"
                    )
                with c3:
                    ui_metric_card("Demanda", f"{kpis.get('demanda', 0):.1f} kVA")
                with c4:
                    ui_metric_card("Clientes", f"{kpis.get('clientes', 0)}")

                analise_bari = DiagnosticoEngenharia.analisar_baricentro(
                    df_res, params["trafo_kva"]
                )
                if analise_bari["status"] == "OTIMIZADO":
                    st.success(f"**Baricentro:** {analise_bari['msg']}", icon="🎯")
                elif analise_bari["status"] == "SUGESTAO":
                    st.info(f"**Baricentro:** {analise_bari['msg']}", icon="📍")

                if avisos:
                    with st.expander("⚠️ Avisos", expanded=True):
                        for a in avisos:
                            st.write(f"{'🔥' if 'CRÍTICO' in a else '⚠️'} {a}")

            with t2:
                cols = [
                    "PONTO",
                    "MONTANTE",
                    "CABO",
                    "METROS",
                    "CQT_TRECHO",
                    "CQT_ACUMULADA",
                    "ICC_KA",
                    "SUGESTAO_BALANCEAMENTO",
                ]
                cols = [c for c in cols if c in df_res.columns]
                st.dataframe(df_res[cols], use_container_width=True, hide_index=True)

            with t3:
                grafico = gerar_diagrama(df_res, limites)
                if grafico:
                    st.graphviz_chart(grafico)

            with t4:
                render_simulation_module(nome_cenario, 0, df_res, params)

            with t5:
                st.info("Relatórios")
                c_pdf, c_csv = st.columns(2)
                centro_sug = ElectricalEngine.sugerir_centro_carga(df_res)
                with c_pdf:
                    try:
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
                    except Exception as e:
                        st.error(f"Erro PDF: {e}")

                with c_csv:
                    st.download_button(
                        "📊 Baixar CSV",
                        df_res.to_csv(index=False).encode("utf-8"),
                        f"{nome_cenario}.csv",
                        "text/csv",
                        use_container_width=True,
                    )


def _executar_calculo_otimizado(nome, df_input):
    with st.spinner("Calculando..."):
        cabos_s = {
            k: v["coef"] if isinstance(v, dict) else v
            for k, v in st.session_state.config_cabos.items()
        }
        ips_s = {
            k: v["pot"] if isinstance(v, dict) else v
            for k, v in st.session_state.config_ips.items()
        }
        # Ajuste para carregar demandas do DB se disponíveis
        demandas = st.session_state.get("config_demandas", [])
        cfg_ctx = {
            "cabos": cabos_s,
            "ips": ips_s,
            "perfis": st.session_state.config_perfis,
            "demandas": demandas,
        }

        df_res, kpis, avisos = ElectricalEngine.calcular(
            df_input, st.session_state.params[nome], cfg_ctx
        )

    st.session_state.resultados[nome] = {"df": df_res, "kpis": kpis, "avisos": avisos}
    st.rerun()


def render_simulation_module(nome_origem, idx, df_base, params_base):
    st.markdown("#### 🧪 Simulador de Recondutoração & Adequação")
    todos_cabos = list(st.session_state.config_cabos.keys())

    if "sim_cabos_allowed" not in st.session_state:
        padrao = [c for c in todos_cabos if "3x" in c.lower()]
        st.session_state.sim_cabos_allowed = padrao if padrao else todos_cabos

    with st.expander("⚙️ Configurar Condutores Permitidos"):
        selecionados = st.multiselect(
            "Selecione:",
            options=todos_cabos,
            default=st.session_state.sim_cabos_allowed,
            key=f"ms_sim_{idx}",
        )
        if selecionados != st.session_state.sim_cabos_allowed:
            st.session_state.sim_cabos_allowed = selecionados
            st.rerun()

    if st.button("▶️ Executar Otimização", type="primary", key=f"btn_sim_{idx}"):
        with st.spinner("Otimizando..."):
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
                st.session_state.sim_cabos_allowed,
            )
            st.session_state[f"sim_res_{idx}"] = res

    if f"sim_res_{idx}" in st.session_state:
        res = st.session_state[f"sim_res_{idx}"]
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Queda Tensão", f"{res['kpis']['max_cqt']:.2f}%")
        c2.metric("Trafo", f"{res['params_opt']['trafo_kva']} kVA")
        c3.markdown(f"**Status:** {res['msg']}")

        if res["log"]:
            st.table(
                pd.DataFrame([{"Ponto": k, "Troca": v} for k, v in res["log"].items()])
            )
            if st.button("Criar Novo Cenário Otimizado", key=f"btn_apply_{idx}"):
                new_n = f"{nome_origem}_Simulado"
                st.session_state.cenarios[new_n] = res["df"].copy()
                st.session_state.params[new_n] = copy.deepcopy(res["params_opt"])
                st.session_state.resultados[new_n] = {
                    "df": res["df"],
                    "kpis": res["kpis"],
                    "avisos": [],
                }
                st.success("Criado!")
                time.sleep(1)
                st.rerun()
