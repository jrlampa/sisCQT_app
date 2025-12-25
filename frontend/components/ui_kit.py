import streamlit as st


def ui_metric_card(label, value, delta=None, help_text=None):
    """Renderiza um card métrico estilizado."""
    st.markdown(
        f"""
        <div style="
            border: 1px solid #e0e0e0; 
            border-radius: 8px; 
            padding: 15px; 
            background-color: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;">
            <div style="color: #757575; font-size: 12px; font-weight: 600; text-transform: uppercase;">{label}</div>
            <div style="color: #212121; font-size: 24px; font-weight: 700; margin-top: 5px;">{value}</div>
            {f'<div style="color: {"#d32f2f" if delta and "-" not in delta else "#388e3c"}; font-size: 12px; margin-top: 5px;">{delta}</div>' if delta else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if help_text:
        st.caption(help_text)


def ui_status_badge(aprovado, ocupacao, max_cqt):
    """Renderiza uma barra de status visual."""
    color = "#4CAF50" if aprovado else "#F44336"
    text = (
        "✅ PROJETO APROVADO" if aprovado else "❌ PROJETO REPROVADO / COM RESTRIÇÕES"
    )

    st.markdown(
        f"""
        <div style="
            background-color: {color}; 
            color: white; 
            padding: 10px 20px; 
            border-radius: 8px; 
            font-weight: bold; 
            text-align: center; 
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {text} | Trafo: {ocupacao:.1f}% | Queda Máx: {max_cqt:.2f}%
        </div>
        """,
        unsafe_allow_html=True,
    )
