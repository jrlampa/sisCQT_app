# siscqt_canvas.py
import streamlit as st
import pandas as pd
import math
from streamlit_agraph import agraph, Node, Edge, Config

def _safe_id(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return ""
    return str(val).strip().upper()

def _calcular_corrente_estimada(kva, tensao_linha=220):
    """
    Calcula corrente trifásica estimada: I = (kVA * 1000) / (sqrt(3) * V_linha)
    """
    if kva <= 0.001: return 0.0
    try:
        return (kva * 1000) / (1.73205 * tensao_linha)
    except:
        return 0.0

def _recalcular_fluxo_correntes(df):
    """
    EXECUTA UM MINI-FLUXO DE CARGA VISUAL:
    Reconstroi a árvore e soma as correntes da ponta para a fonte 
    para preencher a 'Corrente Passante' que faltava no Engine.
    """
    # 1. Dicionários de Topologia e Carga
    adj = {}        # Pai -> Filhos
    local_I = {}    # Corrente Local (Drenada no ponto)
    
    # Mapeia todos os pontos
    todos_pontos = set(df['PONTO'].apply(_safe_id).unique())
    
    for _, row in df.iterrows():
        p = _safe_id(row.get('PONTO'))
        m = _safe_id(row.get('MONTANTE'))
        
        # Determina Carga Local kVA
        c_k = 0.0
        if 'TOTAL_TRECHO_LOCAL' in row:
            c_k = float(row['TOTAL_TRECHO_LOCAL'])
        else:
            c_k = float(row.get('CARGA_DISTRIBUIDA', 0)) + float(row.get('CARGA_PONTUAL_LOCAL', 0))
            
        # Calcula Amperagem Local (220V)
        local_I[p] = _calcular_corrente_estimada(c_k, 220)
        
        # Monta árvore (Quem é filho de quem)
        if m:
            if m not in adj: adj[m] = []
            adj[m].append(p)

    # 2. Função Recursiva para Somar (Passante = Local + Filhos)
    passante_I = {} # Cache
    
    def get_passante(no):
        if no in passante_I: return passante_I[no]
        
        # Começa com a corrente consumida neste próprio poste
        total = local_I.get(no, 0.0)
        
        # Soma a corrente que vem dos filhos (se houver)
        if no in adj:
            for filho in adj[no]:
                total += get_passante(filho)
        
        passante_I[no] = total
        return total

    # 3. Executa para todos os nós (garante que calculou tudo)
    for p in todos_pontos:
        get_passante(p)
        
    return local_I, passante_I

def converter_df_para_agraph(df: pd.DataFrame):
    nodes = []
    edges = []
    node_ids = set()
    
    if df.empty:
        return [], []

    # --- O PULO DO GATO ---
    # Calculamos as correntes aqui e agora!
    mapa_local_I, mapa_passante_I = _recalcular_fluxo_correntes(df)
    # ----------------------

    # 1. Identificar nós e propriedades
    dados_nos = {} 

    for _, row in df.iterrows():
        p = _safe_id(row.get('PONTO'))
        m = _safe_id(row.get('MONTANTE'))
        qt = row.get('CQT_ACUMULADA', 0.0)
        
        if p: dados_nos[p] = max(dados_nos.get(p, 0), qt)
        if m and m not in dados_nos: dados_nos[m] = 0

    # 2. Criar Nós
    for ponto, qt_acum in dados_nos.items():
        # Busca dados extras para o Tooltip
        row = df[df['PONTO'].astype(str) == str(ponto)]
        
        # Valores padrão
        carga_local_kva = 0.0
        clientes_txt = "M:0 / B:0 / T:0"
        
        # Pega as correntes calculadas pelo nosso "Mini-Fluxo"
        c_local = mapa_local_I.get(ponto, 0.0)
        c_passante = mapa_passante_I.get(ponto, 0.0)

        if not row.empty:
            r = row.iloc[0]
            if 'TOTAL_TRECHO_LOCAL' in r:
                carga_local_kva = float(r['TOTAL_TRECHO_LOCAL'])
            else:
                carga_local_kva = float(r.get('CARGA_DISTRIBUIDA', 0)) + float(r.get('CARGA_PONTUAL_LOCAL', 0))
            
            m_ = int(r.get('MONO', 0))
            b_ = int(r.get('BIFÁSICO', 0))
            t_ = int(r.get('TRIFÁSICO', 0))
            clientes_txt = f"M:{m_} / B:{b_} / T:{t_}"

        # Texto do Tooltip (Hover)
        tooltip_text = f"Ponto: {ponto}"
        tooltip_text += f"\nQueda Acum: {qt_acum:.2f}%"
        tooltip_text += f"\nCarga Local: {carga_local_kva:.2f} kVA"
        tooltip_text += f"\n--- Correntes (220V) ---"
        tooltip_text += f"\nLocal: {c_local:.1f} A"
        tooltip_text += f"\nPassante: {c_passante:.1f} A"
        tooltip_text += f"\n-----------------------"
        tooltip_text += f"\nClientes: {clientes_txt}"

        # Estilo Padrão
        color = "#FFFFFF" 
        label = ponto
        size = 25
        shape = "dot"
        font = {'color': 'black', 'face': 'arial', 'size': 16}
        
        # Estilo Condicional
        if ponto == "TRAFO":
            color = "#E3F2FD"
            size = 50 
            shape = "diamond"
            label = "TRAFO"
            tooltip_text = "Transformador (Fonte 220V)"
        elif qt_acum > 6.0:
            color = "#FFCDD2"
            label += f"\n({qt_acum:.1f}%)"
            
        nodes.append(Node(
            id=ponto,
            label=label,
            size=size,
            shape=shape,
            color=color,
            borderWidth=2,
            font=font,
            title=tooltip_text 
        ))
        node_ids.add(ponto)

    # 3. Criar Arestas
    for _, row in df.iterrows():
        p = _safe_id(row.get('PONTO'))
        m = _safe_id(row.get('MONTANTE'))
        
        if p and m and p != m and p in node_ids and m in node_ids:
            cabo_info = f"Trecho: {m} -> {p}\n"
            cabo_info += f"Cabo: {row.get('CABO', '?')}\n"
            cabo_info += f"Distância: {row.get('METROS', 0)} m\n"
            cabo_info += f"Queda Trecho: {row.get('CQT_TRECHO', 0):.2f}%"
            
            # Adiciona a corrente que PASSA nesse cabo (que é a Passante do Ponto de Destino)
            corr_no_cabo = mapa_passante_I.get(p, 0.0)
            cabo_info += f"\nCorrente: {corr_no_cabo:.1f} A"

            edges.append(Edge(
                source=m,
                target=p,
                color="#757575",
                width=2,
                title=cabo_info
            ))

    return nodes, edges

def render_interactive_diagram(df: pd.DataFrame):
    st.markdown("### 🕸️ Canvas Interativo")
    st.caption("Diagrama de Topologia (BT 220V). Passe o mouse para ver carga e correntes.")

    nodes, edges = converter_df_para_agraph(df)
    
    if not nodes:
        st.warning("Sem dados para exibir.")
        return

    config = Config(
        width="100%",
        height=550,
        directed=True,
        hierarchical=False, 
        fit=False,
        edges={"smooth": False, "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}}},
        physics={
            "barnesHut": {
                "gravitationalConstant": -3000, 
                "centralGravity": 0.4,
                "springLength": 120,           
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 1.0             
            },
            "solver": "barnesHut",
            "stabilization": {"enabled": True, "iterations": 1200, "fit": False}
        }
    )

    selecionado_id = agraph(nodes=nodes, edges=edges, config=config)

    if selecionado_id:
        st.divider()
        st.markdown(f"#### 📍 Detalhes do Ponto: **{selecionado_id}**")
        
        if selecionado_id == "TRAFO":
            st.info("Fonte de Alimentação - Baixa Tensão (220V)")
        else:
            dados = df[df['PONTO'].astype(str) == str(selecionado_id)]
            
            if not dados.empty:
                row = dados.iloc[0]
                
                # Recalcula aqui também para exibir no painel de detalhes
                # Nota: Em produção, o ideal é o Engine já ter isso, mas aqui recalculamos on-the-fly
                mapa_local, mapa_passante = _recalcular_fluxo_correntes(df)
                
                p_id = _safe_id(selecionado_id)
                carga_local = 0.0
                if 'TOTAL_TRECHO_LOCAL' in row:
                    carga_local = float(row['TOTAL_TRECHO_LOCAL'])
                else:
                    carga_local = float(row.get('CARGA_DISTRIBUIDA', 0)) + float(row.get('CARGA_PONTUAL_LOCAL', 0))
                
                corr_local = mapa_local.get(p_id, 0.0)
                corr_acum = mapa_passante.get(p_id, 0.0)
                
                queda_ac = row.get('CQT_ACUMULADA', 0.0)
                dist_m = row.get('METROS', 0.0)
                
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Queda Acum.", f"{queda_ac:.2f}%")
                c2.metric("Distância", f"{dist_m:.0f} m")
                c3.metric("Carga Local", f"{carga_local:.2f} kVA")
                c4.metric("Corr. Local", f"{corr_local:.1f} A", help="Consumo deste poste")
                c5.metric("Corr. Passante", f"{corr_acum:.1f} A", help="Soma das correntes deste ponto e todos a jusante")
                
                with st.expander("Ver Todos os Dados Técnicos (Raw)", expanded=False):
                    cols_to_drop = [c for c in dados.columns if 'OBJ' in c or 'IMPEDANCIA' in c]
                    st.dataframe(dados.drop(columns=cols_to_drop).T, use_container_width=True)
            else:
                st.warning("Dados não encontrados para este ponto.")