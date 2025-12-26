# siscqt_constantes.py

# --- 1. CONFIGURAÇÕES DE SISTEMA ---
DB_FILE = "siscqt_v24.db"
UNIT_DIVISOR = 100.0  # Fixo para hm (hectômetros) conforme norma
ENGINE_VERSION = "2.4.0-Normativa"

DEFAULT_PERFIS = [
    ("Massivos", 6.0, 120.0, 250.0, 2000),
    ("RNT", 3.0, 100.0, 250.0, 2000),
    ("Temporário", 6.0, 130.0, 250.0, 2000),
]

# --- 2. CONSTANTES NORMATIVAS (IMUTÁVEIS) ---
# FP fixos para evitar divergências entre blocos
FP_GERAL = 0.92
FP_IP = 1.0

# Tabela de Demanda Média (CNS-OMBR-MAT-19-0285)
TABELA_DEMANDA = [
    # (De, Até, Cls A, Cls B, Cls C, Cls D)
    (1, 5, 1.50, 2.50, 4.00, 6.00),
    (6, 10, 1.20, 2.00, 3.20, 5.00),
    (11, 20, 1.00, 1.60, 2.50, 4.00),
    (21, 50, 0.80, 1.20, 2.00, 3.00),
    (51, 9999, 0.50, 0.80, 1.30, 2.00),
]

# --- 3. MODELO DE CONDUTORES ---
# Fonte única de verdade para cabos. Unidade Coef: % / (kVA · hm)
DEFAULT_CABOS_DATA = {
    "2#16(25)mm² Al": [0.7779, 1.91, 0.10],
    "3x35+54.6mm² Al": [0.2416, 0.87, 0.09],
    "3x50+54.6mm² Al": [0.1784, 0.64, 0.09],
    "3x70+54.6mm² Al": [0.1248, 0.44, 0.08],
    "3x95+54.6mm² Al": [0.0891, 0.32, 0.08],
    "3x150+70mm² Al": [0.0573, 0.21, 0.08],
}

# Derivações automáticas para garantir sincronia total
DEFAULT_CABOS = {k: v[0] for k, v in DEFAULT_CABOS_DATA.items()}
CABOS_IMPEDANCIA = {k: {"r": v[1], "x": v[2]} for k, v in DEFAULT_CABOS_DATA.items()}

# --- 4. DEFAULTS OPERACIONAIS E UX ---
DEFAULT_IPS = {
    "Sem IP": 0.0,
    "IP 70W": 70.0,
    "IP 100W": 100.0,
    "IP 150W": 150.0,
    "IP 250W": 250.0,
    "IP 400W": 400.0,
}

DEFAULT_TRAFOS_LISTA = [15, 30, 45, 75, 112.5, 150, 225, 300]

DEFAULT_PARAMS = {
    "trafo_kva": 75.0,
    "fp_ip": FP_IP,
    "classe_tipo": "Automático",
    "classe_manual": "B",
    "perfil": "Massivos",
}

COL_MAPPING = {
    "CARGA_DIST_KVA": "CARGA_DISTRIBUIDA",
    "CARGA_PONTUAL_KVA": "CARGA_PONTUAL_LOCAL",
    "TOTAL_LOCAL_KVA": "TOTAL_TRECHO_LOCAL",
    "ACUMULADA_KVA": "CARGA_ACUMULADA_G",
}

DEFAULT_COL_ORDER = [
    "PONTO",
    "MONTANTE",
    "METROS",
    "CABO",
    "MONO",
    "BIFÁSICO",
    "TRIFÁSICO",
    "TRI ESPECIAL",
    "CARGA_ESP_KVA",
    "TIPO_IP",
    "QTD_IP",
]

# --- MEMORIAL  ---
MEMORIAL_TEXTO = """
MEMORIAL EXPLICATIVO
Metodologia de Calculo de Queda de Tensao (QT) - SisCQT
Conforme procedimento QTOS - ENEL

1. OBJETIVO
Este memorial tem por objetivo explicar a metodologia de calculo de Queda de Tensao (QT) utilizada no aplicativo SisCQT.

2. PREMISSAS ADOTADAS
- Todos os calculos sao realizados em kVA.
- O fator de potencia (FP = 0,92) e aplicado exclusivamente para conversao kW -> kVA.
- As cargas de Iluminacao Publica (IP) utilizam FP = 1.0.
- O calculo e realizado por trecho, com acumulacao radial.
- O coeficiente do condutor contempla tensao, sistema e fatores normativos.
- Aplica-se divisor 100 (m -> hm) conforme metodologia QTOS.

3. METODOLOGIA DE CALCULO
3.1 Calculo do Momento Eletrico
Momento = (Carga_local_distribuida / 2) + Carga_pontual_local + Carga_acumulada_jusante

3.2 Queda de Tensao do Trecho
QT_trecho = (Momento * Comprimento(m) / 100) * Coeficiente_condutor

3.3 Queda de Tensao Acumulada
QT_acumulada = QT_trecho + QT_acumulada_montante

4. CONTROLE DE CONSISTENCIA
O sistema verifica automaticamente limites de QT, sobrecarga e topologia.
"""
MEMORIAL_HTML = MEMORIAL_TEXTO.replace("\n", "<br>")
