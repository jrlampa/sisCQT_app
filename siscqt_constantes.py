# siscqt_constantes.py

DB_FILE = 'siscqt_v24.db'
UNIT_DIVISOR = 100.0 

DEFAULT_PERFIS = [
    ("Padrão (Urbano)", 6.0, 100.0, 3000.0, 2000),
    ("RNT (Rural/Novo)", 3.0, 100.0, 5000.0, 1000),
    ("Massivos (Flex)", 6.0, 120.0, 3000.0, 2000),
    ("Temporário", 10.0, 130.0, 1000.0, 500)
]

# FORMATO: "Nome": [Coef_Queda, R_Ohm_km, X_Ohm_km]
# Dados aproximados para condutores de alumínio (CA/CAL) e cobre típicos
DEFAULT_CABOS_DATA = {
    "2#16(25)mm² Al": [0.7779, 1.91, 0.10], 
    "3x35+54.6mm² Al": [0.2416, 0.87, 0.09], 
    "3x50+54.6mm² Al": [0.1784, 0.64, 0.09],
    "3x50+50mm² Al": [0.1784, 0.64, 0.09], 
    "3x70+54.6mm² Al": [0.1248, 0.44, 0.08], 
    "3x95+54.6mm² Al": [0.0891, 0.32, 0.08],
    "3x150+70mm² Al": [0.0573, 0.21, 0.08], 
    "3# 4 - Al - F.P 1": [0.3159, 1.36, 0.11], 
    "3# 2 - Al - F.P 1": [0.1980, 0.85, 0.10],
    "3# 1/0 - Al - F.P 1": [0.1248, 0.54, 0.10], 
    "3# 2/0 - Al - F.P 1": [0.0990, 0.43, 0.09], 
    "3# 4/0 - Al - F.P 1": [0.0624, 0.27, 0.09],
    "MULTIPLEX 2#16 (16) CU": [0.2820, 1.15, 0.10],
    "1#6 (6) CU": [1.6800, 3.08, 0.12],
    "CONC 2#10 (10) CU": [0.7400, 1.83, 0.11]
}

# Compatibilidade: Dicionário simples só com coeficientes (usado em partes legado)
DEFAULT_CABOS = {k: v[0] for k, v in DEFAULT_CABOS_DATA.items()}

# Dicionário Avançado de Impedância para o Engine (ICC)
CABOS_IMPEDANCIA = {k: {'r': v[1], 'x': v[2]} for k, v in DEFAULT_CABOS_DATA.items()}

DEFAULT_IPS = {
    "Sem IP": 0.0, "IP 70W": 70.0, "IP 80W": 80.0, 
    "IP 150W": 150.0, "IP 250W": 250.0, "IP 400W": 400.0
}

DEFAULT_TRAFOS_LISTA = [15, 30, 45, 75, 112.5, 150, 225, 300]

DEFAULT_PARAMS = {
    "trafo_kva": 150, 
    "classe_tipo": "Automático", 
    "classe_manual": "A", 
    "fp_ip": 0.92,
    "perfil": "Padrão (Urbano)" 
}

COL_MAPPING = {
    "CARGA_DIST_KVA": "CARGA_DISTRIBUIDA",
    "CARGA_PONTUAL_KVA": "CARGA_PONTUAL_LOCAL",
    "TOTAL_LOCAL_KVA": "TOTAL_TRECHO_LOCAL",
    "ACUMULADA_KVA": "CARGA_ACUMULADA_G"
}

TABELA_DEMANDA = [
    (1, 5, 1.0, 1.6, 2.6, 4.0), (6, 10, 0.9, 1.4, 2.2, 3.4), (11, 15, 0.8, 1.2, 1.9, 3.0),
    (16, 20, 0.7, 1.1, 1.7, 2.6), (21, 25, 0.6, 0.9, 1.5, 2.3), (26, 30, 0.5, 0.9, 1.4, 2.1),
    (31, 40, 0.5, 0.8, 1.3, 2.0)
]

DEFAULT_COL_ORDER = ["PONTO", "MONTANTE", "METROS", "CABO", "MONO", "BIFÁSICO", "TRIFÁSICO", "TRI ESPECIAL", "CARGA_ESP_KVA", "TIPO_IP", "QTD_IP" ]

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
