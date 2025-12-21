# siscqt_protecao.py
import pandas as pd
import numpy as np
import re

class EngineProtecao:
    
    # --- DADOS PADRÃO (Norma Enel/Rio) ---
    DB_CABOS_IMPEDANCIA = {
        "150mm": {"r": 0.2775, "x": 0.0867},
        "95mm":  {"r": 0.4311, "x": 0.0902},
        "50mm":  {"r": 0.8634, "x": 0.0943},
        "35mm":  {"r": 1.1694, "x": 0.0974},
        "120mm": {"r": 0.3540, "x": 0.0880},
        "70mm":  {"r": 0.6470, "x": 0.0920},
        "25mm":  {"r": 1.5000, "x": 0.1000},
        "16mm":  {"r": 2.3000, "x": 0.1050},
        "10mm":  {"r": 3.6000, "x": 0.1100},
    }

    SUGESTAO_ELO = {
        10: "1H", 15: "1H", 30: "2H", 45: "3H", 
        75: "5K", 112.5: "6K", 150: "8K", 225: "10K", 300: "15K"
    }

    DB_ELOS_CORRENTE = {
        "1H": 2.0, "2H": 3.5, "3H": 5.0, "5H": 8.0, 
        "1K": 2.0, "2K": 3.5, "3K": 5.2, "5K": 8.0, "6K": 10.5,
        "8K": 13.5, "10K": 16.0, "12K": 19.0, "15K": 24.0, "20K": 31.0
    }
    
    # --- FUNÇÕES AUXILIARES ---

    @staticmethod
    def _norm(valor):
        """Padroniza IDs (remove .0 e espaços)"""
        if pd.isna(valor) or valor is None or str(valor).strip() == "":
            return None
        s = str(valor).strip().upper()
        if s.endswith(".0"): s = s[:-2] 
        return s

    @staticmethod
    def _get_capacidade_elo(nome_elo):
        """Extrai o valor numérico do nome do elo (ex: '6K' -> 6.0)"""
        try:
            match = re.match(r"(\d+(\.\d+)?)", str(nome_elo))
            if match:
                return float(match.group(1))
        except:
            pass
        return 9999.0 # Valor alto para não dar erro falso se falhar parse

    @staticmethod
    def identificar_impedancia_cabo(nome_cabo):
        nome_norm = str(nome_cabo).lower().replace(" ", "")
        for bitola, imp in EngineProtecao.DB_CABOS_IMPEDANCIA.items():
            if bitola in nome_norm:
                return imp["r"], imp["x"]
        return 0.8634, 0.0943

    @staticmethod
    def calcular_impedancia_trafo(kva, v_secundario=220, z_percent=3.5):
        if kva <= 0: return complex(0.01, 0.01)
        z_base = (v_secundario ** 2) / (kva * 1000)
        z_abs = z_base * (z_percent / 100.0)
        return complex(z_abs * 0.2, z_abs * 0.98)

    @staticmethod
    def executar_calculo_icc(df_rede, kva_trafo, elo_fusivel=None):
        df = df_rede.copy()
        V_FASE = 127.0 
        
        # 1. Impedância da Fonte (Trafo)
        z_fonte = EngineProtecao.calcular_impedancia_trafo(kva_trafo, v_secundario=220)
        
        # Inicializa colunas
        df['R_ACUM'] = 0.0
        df['X_ACUM'] = 0.0
        df['ICC_A'] = 0.0
        # df['DEBUG_INFO'] removido conforme solicitado
        
        mapa_r = {}
        mapa_x = {}
        
        # 2. DETECÇÃO DE RAÍZES
        todos_pontos = set(df['PONTO'].apply(EngineProtecao._norm).dropna())
        
        raizes_encontradas = set()
        for nome_fonte in ["TRAFO", "FONTE", "SUB", "0"]:
            mapa_r[nome_fonte] = z_fonte.real
            mapa_x[nome_fonte] = z_fonte.imag
            raizes_encontradas.add(nome_fonte)

        # 3. Propagação
        pendentes = df.to_dict('records')
        processados = set(raizes_encontradas)
        
        # Fallback para primeira linha se necessário
        if not pendentes: return df, "Erro"
        primeiro_montante = EngineProtecao._norm(pendentes[0]['MONTANTE'])
        if not primeiro_montante: 
            pass
        elif primeiro_montante not in processados:
             mapa_r[primeiro_montante] = z_fonte.real
             mapa_x[primeiro_montante] = z_fonte.imag
             processados.add(primeiro_montante)

        max_loops = len(pendentes) * 4
        count = 0
        
        while pendentes and count < max_loops:
            count += 1
            linha = pendentes.pop(0)
            
            ponto = EngineProtecao._norm(linha['PONTO'])
            montante = EngineProtecao._norm(linha['MONTANTE'])
            
            if not montante:
                r_pai = z_fonte.real
                x_pai = z_fonte.imag
            elif montante in processados:
                r_pai = mapa_r[montante]
                x_pai = mapa_x[montante]
            else:
                pendentes.append(linha)
                continue
            
            r_km, x_km = EngineProtecao.identificar_impedancia_cabo(linha.get('CABO', ''))
            try:
                dist_km = float(linha.get('METROS', 0)) / 1000.0
            except:
                dist_km = 0.0
            
            r_total = r_pai + (r_km * dist_km)
            x_total = x_pai + (x_km * dist_km)
            
            mapa_r[ponto] = r_total
            mapa_x[ponto] = x_total
            processados.add(ponto)
            
            z_mag = np.sqrt(r_total**2 + x_total**2)
            icc = (V_FASE / z_mag) if z_mag > 0.0001 else 99999.0
            
            idx = df.index[df['PONTO'] == linha['PONTO']].tolist()
            if idx:
                df.loc[idx, 'R_ACUM'] = r_total
                df.loc[idx, 'X_ACUM'] = x_total
                df.loc[idx, 'ICC_A'] = icc

        # 4. Análise Inteligente
        if not elo_fusivel:
            elo_fusivel = EngineProtecao.SUGESTAO_ELO.get(kva_trafo, "?K")
        
        # --- NOVO: VALIDAÇÃO DE CARGA NOMINAL ---
        # Corrente Nominal no Primário (13.8kV)
        # Inom = kVA / (sqrt(3) * 13.8)
        i_nominal_prim = kva_trafo / (1.732 * 13.8)
        
        # Capacidade do Elo (ex: 1H = 1A, 6K = 6A)
        cap_elo = EngineProtecao._get_capacidade_elo(elo_fusivel)
        
        elo_subdimensionado = False
        # Se a corrente nominal for maior que a do elo, ele queima na carga!
        if i_nominal_prim > cap_elo:
            elo_subdimensionado = True

        i_fusao_minima = EngineProtecao.DB_ELOS_CORRENTE.get(elo_fusivel, 0.0)
        
        def analisar(icc):
            if icc <= 0.1: return "⚠️ ERRO DADOS"
            
            # 1. Cheque de Sobrecarga (Prioridade Máxima)
            if elo_subdimensionado:
                return "❌ ELO SUBDIMENSIONADO"
            
            if i_fusao_minima == 0: return "S/ INFO"
            
            # 2. Cheque de Curto-Circuito
            icc_primario = icc / 62.7
            ratio = icc_primario / i_fusao_minima
            
            if ratio < 1.0: return "🔴 FALHA (NÃO ATUA)" # ICC muito baixo
            if ratio < 1.5: return "⚠️ RISCO (LENTO)"
            return "✅ OK"

        df['STATUS_PROT'] = df['ICC_A'].apply(analisar)
        df['ICC_KA'] = df['ICC_A'] / 1000.0
        
        return df, elo_fusivel