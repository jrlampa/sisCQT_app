# siscqt_visual.py
import graphviz
import streamlit as st
import pandas as pd
import math

def gerar_diagrama(df: pd.DataFrame, limites: dict = None, baricentro_info: dict = None):
    """
    Gera objeto Graphviz otimizado.
    Aceita 'baricentro_info' {'ponto_proximo': 'XYZ', 'distancia': 123.0}
    """
    if df.empty: return None

    dot = graphviz.Digraph(comment='Rede SisCQT')
    dot.attr(rankdir='TB', splines='ortho', nodesep='0.5', ranksep='0.5') 
    dot.attr('edge', arrowhead='none', penwidth='1.2', color='#424242')
    
    lim_cqt = limites.get('cqt_max', 6.0) if limites else 6.0
    
    # Identifica ponto do baricentro para destaque
    ponto_baricentro = baricentro_info.get('ponto_proximo') if baricentro_info else None
    
    for _, row in df.iterrows():
        ponto = str(row['PONTO']).strip()
        montante = str(row['MONTANTE']).strip()
        if not ponto or ponto == "!!SEM_NOME!!": continue

        try: cqt = float(row.get('CQT_ACUMULADA', 0.0))
        except: cqt = 0.0
        
        fillcolor = "white"; color = "black"; penwidth = "1.0"
        
        # Cores Normativas
        if cqt > lim_cqt:
            fillcolor = "#FFCDD2"; color = "#C62828"; penwidth = "2.0"
        elif cqt > (lim_cqt * 0.8):
            fillcolor = "#FFE0B2"; color = "#EF6C00"
            
        # Destaque do Baricentro (Sobrepõe se for o caso)
        if ponto == ponto_baricentro:
            fillcolor = "#E1BEE7" # Roxo claro
            color = "#8E24AA"
            penwidth = "3.0"

        label_ext = f"{ponto}"
        if cqt > 0: label_ext += f"\n({cqt:.1f}%)"
        
        if ponto == ponto_baricentro:
            label_ext += "\n[Baricentro]"

        if ponto == "TRAFO":
            dot.node(ponto, label="TRAFO", shape='rect', style='filled, rounded', 
                     fillcolor='#2196F3', fontcolor='white', color='#0D47A1', fixedsize='true', width='0.8', height='0.4')
        else:
            dot.node(ponto, label="", xlabel=label_ext, shape='circle', style='filled', 
                     fillcolor=fillcolor, color=color, penwidth=penwidth, width='0.12', height='0.12', fixedsize='true')

        if montante and montante.upper() != 'NAN' and montante != "":
            dist = row.get('METROS', 0); lbl_e = f"{int(dist)}" if dist > 0 else ""
            dot.edge(montante, ponto, label=lbl_e, fontsize='7', color='#424242')

    return dot