# frontend/visual.py
import streamlit as st


def gerar_diagrama(df, limites):
    try:
        import graphviz
    except ImportError:
        st.warning("⚠️ Biblioteca 'graphviz' não instalada no Python.")
        return None

    try:
        dot = graphviz.Digraph(comment="Rede BT")
        dot.attr(rankdir="LR", size="10,10", ratio="fill")

        # Cores baseadas nos limites
        def get_color(val, limit, is_ocup=False):
            if val > limit:
                return "red"
            if val > limit * 0.9:
                return "orange"
            return "green" if is_ocup else "black"

        # Nós
        for _, row in df.iterrows():
            ponto = str(row["PONTO"])
            cqt = row.get("CQT_ACUMULADA", 0.0)

            # Estilo do Nó
            fill = "white"
            color = get_color(cqt, limites.get("cqt_max", 6.0))
            if ponto == "TRAFO":
                fill = "lightgrey"
                color = "black"

            label = f"{ponto}\n{cqt:.2f}%"
            dot.node(
                ponto,
                label,
                style="filled",
                fillcolor=fill,
                color=color,
                shape="box" if ponto == "TRAFO" else "ellipse",
            )

        # Arestas
        for _, row in df.iterrows():
            ponto = str(row["PONTO"])
            pai = str(row["MONTANTE"])
            if pai and pai in df["PONTO"].values:
                # Estilo da Linha (Vermelha se o trecho tiver problema)
                # Aqui simplificado para preto, mas pode ser dinâmico
                dot.edge(pai, ponto)

        return dot

    except Exception as e:
        # Captura erro de "ExecutableNotFound" comum no Windows/Docker Slim
        if "ExecutableNotFound" in str(e):
            st.warning(
                "⚠️ Software Graphviz não encontrado no servidor. O diagrama não pode ser gerado."
            )
        else:
            st.error(f"Erro ao gerar diagrama: {str(e)}")
        return None
