import streamlit as st


def ui_metric_card(label, value, delta=None, help_text=None):
    st.markdown(
        f"""
    <div style="border:1px solid #ddd; padding:10px; border-radius:5px; text-align:center;">
        <small>{label}</small>
        <h3>{value}</h3>
        <p style="color:{'red' if delta and 'max' in str(delta).lower() else 'green'}">{delta if delta else ''}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def ui_status_badge(aprovado, ocupacao, max_cqt):
    color = "green" if aprovado else "red"
    msg = "APROVADO" if aprovado else "REPROVADO"
    st.markdown(
        f":{color}-background[**STATUS: {msg}** | Trafo: {ocupacao:.1f}% | CQT: {max_cqt:.2f}%]"
    )
