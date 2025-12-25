from fpdf import FPDF
from backend.constantes import MEMORIAL_TEXTO
import tempfile
import os


def safe_text(text):
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
    nome_proj,
    kpis,
    df,
    dot_diagram,
    custo_total,
    centro_carga,
    avisos,
    estudos_extras=None,
):
    pdf = PDFReport()
    pdf.add_page()
    pdf.chapter_title("1. Memorial Explicativo (Metodologia)")
    pdf.chapter_body_small(MEMORIAL_TEXTO)

    pdf.add_page()
    pdf.chapter_title("2. Resumo do Dimensionamento")
    limites = kpis.get("limites_usados", {})
    status = (
        "APROVADO"
        if (kpis["ocupacao"] <= limites.get("sobrecarga_max", 100))
        and (kpis["max_cqt"] <= limites.get("cqt_max", 6))
        else "COM RESTRIÇÕES"
    )

    texto_resumo = (
        f"Projeto: {nome_proj}\nStatus: {status}\nTrafo: {kpis['ocupacao']:.1f}%\n"
        f"Demanda: {kpis['demanda']:.2f} kVA\nQueda Max: {kpis['max_cqt']:.2f}%\n"
        f"Sugestão Centro de Carga: {centro_carga}"
    )
    pdf.chapter_body(texto_resumo)

    if avisos:
        pdf.set_text_color(200, 0, 0)
        pdf.chapter_body("Alertas:\n" + "\n".join(avisos))
        pdf.set_text_color(0, 0, 0)

    if dot_diagram:
        pdf.chapter_title("3. Diagrama Unifilar")
        img_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                dot_diagram.render(
                    filename=tmp.name.replace(".png", ""), format="png", cleanup=True
                )
                img_path = tmp.name
            pdf.image(img_path, x=10, w=190)
            pdf.ln(10)
        except:
            pass
        finally:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)

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

    return pdf.output(dest="S").encode("latin-1", errors="replace")
