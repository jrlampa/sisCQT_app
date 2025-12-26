# backend/reports.py
import os
from fpdf import FPDF
import datetime


def safe_text(text):
    if not isinstance(text, str):
        return str(text)
    # Limpeza de caracteres Unicode para Latin-1 (padrão FPDF)
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


class MemorialCalculoPDF(FPDF):
    def header(self):
        self.image(os.path.join("assets", "logo_siscqt.png"), 10, 8, 33)
        self.image(os.path.join("assets", "logo_im3.png"), 170, 8, 33)
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, safe_text("SisCQT - Memorial de Cálculo Elétrico"), 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.cell(
            0,
            10,
            safe_text(
                f'Gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}'
            ),
            0,
            1,
            "R",
        )
        self.ln(5)

    def chapter_title(self, label):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, safe_text(label), 0, 1, "L", 1)
        self.ln(4)

    def add_kpis(self, kpis):
        status = kpis.get("status_geral", "N/A")

        # Define cor baseada no status
        if status == "APROVADO":
            self.set_text_color(0, 128, 0)  # Verde
        elif "REPROVADO" in status or "CRÍTICO" in status:
            self.set_text_color(255, 0, 0)  # Vermelho

        self.set_font("Arial", "B", 12)
        self.cell(0, 10, safe_text(f"STATUS FINAL: {status}"), 0, 1)

        self.set_text_color(0, 0, 0)  # Reset para preto
        self.set_font("Arial", "", 10)
        self.cell(
            0,
            8,
            safe_text(f"Queda de Tensão Máxima: {kpis.get('max_cqt', 0):.2f}%"),
            0,
            1,
        )
        self.cell(
            0, 8, safe_text(f"Ocupação do Trafo: {kpis.get('ocupacao', 0):.2f}%"), 0, 1
        )
        self.ln(5)


def gerar_pdf(df_res, kpis, nome_projeto="Projeto"):
    pdf = MemorialCalculoPDF()
    pdf.add_page()

    pdf.chapter_title(f"Dados do Projeto: {nome_projeto}")
    pdf.add_kpis(kpis)

    pdf.chapter_title("Resultados por Ponto")
    pdf.set_font("Arial", "B", 8)
    # Cabeçalho da Tabela
    pdf.cell(30, 8, "PONTO", 1)
    pdf.cell(30, 8, "MONTANTE", 1)
    pdf.cell(30, 8, "QT ACUM (%)", 1)
    pdf.cell(30, 8, "CARGA (kVA)", 1)
    pdf.cell(30, 8, "ICC (kA)", 1)
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for _, row in df_res.iterrows():
        pdf.cell(30, 6, safe_text(row["PONTO"]), 1)
        pdf.cell(30, 6, safe_text(row["MONTANTE"]), 1)
        pdf.cell(30, 6, f"{row['CQT_ACUMULADA']:.2f}", 1)
        pdf.cell(30, 6, f"{row['CARGA_ACUMULADA_G']:.2f}", 1)
        pdf.cell(30, 6, f"{row['ICC_KA']:.3f}", 1)
        pdf.ln()

    return pdf.output(dest="S").encode("latin-1")
