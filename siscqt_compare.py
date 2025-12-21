# siscqt_compare.py
import pandas as pd

class ComparadorEngine:
    """
    Classe dedicada exclusivamente a comparar dois dataframes de resultados (Cenários).
    Isolada para não afetar o funcionamento do motor principal.
    """
    
    @staticmethod
    def calcular_custo_material(df: pd.DataFrame, config_cabos: dict, config_ips: dict) -> float:
        """Calcula o custo total estimado (Cabos + Luminárias) de um cenário."""
        total = 0.0
        
        # Garante que as colunas existem
        if df.empty: return 0.0
        
        for _, row in df.iterrows():
            # 1. Custo do Cabo
            cabo = str(row.get('CABO', '')).strip()
            metros = float(row.get('METROS', 0.0))
            
            if cabo in config_cabos:
                dados = config_cabos[cabo]
                # Suporta tanto o formato antigo (float) quanto o novo (dict {'coef':, 'preco':})
                preco_metro = dados.get('preco', 0.0) if isinstance(dados, dict) else 0.0
                total += (preco_metro * metros)

            # 2. Custo da IP
            tipo_ip = str(row.get('TIPO_IP', '')).strip()
            qtd_ip = int(row.get('QTD_IP', 0))
            
            if tipo_ip in config_ips:
                dados_ip = config_ips[tipo_ip]
                preco_ip = dados_ip.get('preco', 0.0) if isinstance(dados_ip, dict) else 0.0
                total += (preco_ip * qtd_ip)
                
        return total

    @staticmethod
    def gerar_relatorio_comparativo(nome_a, dados_a, nome_b, dados_b, configs_full):
        """
        Gera um dicionário com todos os dados necessários para a tela de comparação.
        A = Base (ex: Atual)
        B = Proposto (ex: Projeto)
        """
        res_a = dados_a # Espera-se o dicionário de resultados {'df': ..., 'kpis': ...}
        res_b = dados_b
        
        df_a = res_a['df'].set_index('PONTO')
        df_b = res_b['df'].set_index('PONTO')

        # 1. Comparação Financeira
        custo_a = ComparadorEngine.calcular_custo_material(res_a['df'], configs_full['cabos'], configs_full['ips'])
        custo_b = ComparadorEngine.calcular_custo_material(res_b['df'], configs_full['cabos'], configs_full['ips'])

        # 2. Delta de KPIs
        kpis = {
            'ocupacao': {
                'v1': res_a['kpis'].get('ocupacao', 0), 
                'v2': res_b['kpis'].get('ocupacao', 0)
            },
            'queda_max': {
                'v1': res_a['kpis'].get('max_cqt', 0), 
                'v2': res_b['kpis'].get('max_cqt', 0)
            },
            'demanda': {
                'v1': res_a['kpis'].get('demanda', 0), 
                'v2': res_b['kpis'].get('demanda', 0)
            },
            'custo': {
                'v1': custo_a, 
                'v2': custo_b
            }
        }

        # 3. Detecção de Mudanças Físicas (Recondutoração)
        # Analisa apenas pontos que existem nos dois cenários
        pontos_comuns = df_a.index.intersection(df_b.index)
        lista_mudancas = []
        
        for ponto in pontos_comuns:
            row_a = df_a.loc[ponto]
            row_b = df_b.loc[ponto]
            
            cabo_a = str(row_a['CABO']).strip()
            cabo_b = str(row_b['CABO']).strip()
            
            # Se o cabo mudou, registramos como obra
            if cabo_a != cabo_b:
                dist = float(row_b['METROS'])
                # Quanto melhorou a tensão NESTE ponto específico?
                qt_antes = float(row_a['CQT_ACUMULADA'])
                qt_depois = float(row_b['CQT_ACUMULADA'])
                ganho = qt_antes - qt_depois 
                
                lista_mudancas.append({
                    'Ponto': ponto,
                    'De (Existente)': cabo_a,
                    'Para (Projetado)': cabo_b,
                    'Extensão (m)': dist,
                    'Melhoria QT (%)': ganho
                })

        return {
            'kpis': kpis,
            'obras': pd.DataFrame(lista_mudancas)
        }