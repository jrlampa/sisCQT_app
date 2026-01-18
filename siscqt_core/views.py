from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
import pandas as pd
from io import BytesIO
from django.db import transaction
from django.http import HttpResponse # Import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

from .models import Projeto, CenarioConfig, Trecho, CfgCabo, CfgIP, CfgTrafo, CfgPerfil
from .serializers import (
    ProjetoSerializer,
    CenarioSerializer,
    TrechoSerializer,
    CfgCaboSerializer,
    CfgIPSerializer,
    CfgTrafoSerializer,
    CfgPerfilSerializer,
)
from .services import ElectricalEngine, DiagnosticoEngenharia, SimuladorReadequacao # Import all necessary services
from .excel_parser import importar_planilha_concessionaria
from .siscqt_constantes import DEFAULT_PARAMS

class ProjetoViewSet(viewsets.ModelViewSet):
    queryset = Projeto.objects.all()
    serializer_class = ProjetoSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload_excel(self, request, filename=None):
        """
        Endpoint para criar um novo projeto via upload de arquivo Excel.
        """
        if 'file' not in request.data:
            return Response({'error': 'Nenhum arquivo enviado.'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.data['file']
        project_name = request.query_params.get('project_name', file_obj.name.split('.')[0])
        
        if Projeto.objects.filter(nome=project_name).exists():
            return Response({'error': f"Já existe um projeto com o nome '{project_name}'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_content = BytesIO(file_obj.read())
            
            df_norm, trafo_kva, config_cabos_imp, classe_encontrada, erros_importacao = \
                importar_planilha_concessionaria(file_content)

            if df_norm.empty and erros_importacao:
                return Response({'errors': erros_importacao}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                projeto = Projeto.objects.create(nome=project_name)
                cenario_name = "Cenario Padrão"
                
                CenarioConfig.objects.create(
                    projeto=projeto,
                    nome_cenario=cenario_name,
                    trafo_kva=trafo_kva if trafo_kva else DEFAULT_PARAMS['trafo_kva'],
                    classe_tipo="Manual",
                    classe_manual=classe_encontrada if classe_encontrada else DEFAULT_PARAMS['classe_manual'],
                    fp_ip=DEFAULT_PARAMS['fp_ip'],
                    perfil=DEFAULT_PARAMS['perfil']
                )

                trechos_to_create = [
                    Trecho(
                        projeto=projeto,
                        nome_cenario=cenario_name,
                        ponto=row['PONTO'],
                        montante=row['MONTANTE'],
                        metros=row['METROS'],
                        cabo=row['CABO'],
                        mono=row['MONO'],
                        bi=row['BIFÁSICO'],
                        tri=row['TRIFÁSICO'],
                        tri_esp=row['TRI ESPECIAL'],
                        carga_esp=row['CARGA_ESP_KVA'],
                        tipo_ip=row['TIPO_IP'],
                        qtd_ip=row['QTD_IP'],
                    ) for index, row in df_norm.iterrows()
                ]
                Trecho.objects.bulk_create(trechos_to_create)

                for cabo_name, coef_val in config_cabos_imp.items():
                    CfgCabo.objects.update_or_create(
                        nome=cabo_name,
                        defaults={'coeficiente': coef_val}
                    )
            
            serializer = self.get_serializer(projeto)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f"Ocorreu um erro ao processar o arquivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CenarioViewSet(viewsets.ModelViewSet):
    queryset = CenarioConfig.objects.all()
    serializer_class = CenarioSerializer

    def create(self, request, *args, **kwargs):
        copy_from_cenario_id = request.data.get('copy_from_cenario_id')

        if copy_from_cenario_id:
            try:
                source_cenario = CenarioConfig.objects.get(pk=copy_from_cenario_id)
                new_cenario_name = request.data.get('nome_cenario')
                target_projeto_id = request.data.get('projeto') # Ensure 'projeto' is present in request.data

                if not new_cenario_name or not target_projeto_id:
                    return Response(
                        {"error": "New scenario name and project ID are required."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check for duplicate scenario name within the target project
                if CenarioConfig.objects.filter(
                    projeto_id=target_projeto_id,
                    nome_cenario=new_cenario_name
                ).exists():
                    return Response(
                        {"error": f"A scenario with the name '{new_cenario_name}' already exists in this project."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                with transaction.atomic():
                    # Create new CenarioConfig by copying from source
                    new_cenario = CenarioConfig.objects.create(
                        projeto_id=target_projeto_id,
                        nome_cenario=new_cenario_name,
                        trafo_kva=source_cenario.trafo_kva,
                        classe_tipo=source_cenario.classe_tipo,
                        classe_manual=source_cenario.classe_manual,
                        fp_ip=source_cenario.fp_ip,
                        perfil=source_cenario.perfil
                    )

                    # Copy associated Trechos
                    trechos_to_create = []
                    for trecho in Trecho.objects.filter(
                        projeto=source_cenario.projeto,
                        nome_cenario=source_cenario.nome_cenario
                    ):
                        trechos_to_create.append(
                            Trecho(
                                projeto_id=target_projeto_id, # Associate with target project
                                nome_cenario=new_cenario_name, # Associate with new scenario name
                                ponto=trecho.ponto,
                                montante=trecho.montante,
                                metros=trecho.metros,
                                cabo=trecho.cabo,
                                mono=trecho.mono,
                                bi=trecho.bi,
                                tri=trecho.tri,
                                tri_esp=trecho.tri_esp,
                                carga_esp=trecho.carga_esp,
                                tipo_ip=trecho.tipo_ip,
                                qtd_ip=trecho.qtd_ip,
                            )
                        )
                    Trecho.objects.bulk_create(trechos_to_create)

                serializer = self.get_serializer(new_cenario)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except CenarioConfig.DoesNotExist:
                return Response(
                    {"error": "Source scenario not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {"error": f"Error copying scenario: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Original create logic for non-copy operations
            return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='calcular')
    def calcular(self, request, pk=None):
        """
        Executa o cálculo elétrico para um cenário específico e retorna os resultados,
        KPIs, avisos e recomendações de engenharia.
        """
        cenario = self.get_object()
        projeto = cenario.projeto

        # 1. Obter Trechos e converter para DataFrame
        trechos_qs = Trecho.objects.filter(projeto=projeto, nome_cenario=cenario.nome_cenario)
        if not trechos_qs.exists():
            return Response({'error': 'Nenhum trecho encontrado para este cenário.'}, status=status.HTTP_404_NOT_FOUND)
        
        trechos_data = list(trechos_qs.values(
            'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
            'carga_esp', 'tipo_ip', 'qtd_ip'
        ))
        df_trechos = pd.DataFrame(trechos_data)
        df_trechos.columns = [col.upper() for col in df_trechos.columns]

        # 2. Preparar parâmetros do cenário
        params = {
            'trafo_kva': cenario.trafo_kva,
            'classe_tipo': cenario.classe_tipo,
            'classe_manual': cenario.classe_manual,
            'fp_ip': cenario.fp_ip,
            'perfil': cenario.perfil,
        }

        # 3. Carregar configurações globais
        cfg_cabos_qs = CfgCabo.objects.all()
        cfg_ips_qs = CfgIP.objects.all()
        cfg_perfis_qs = CfgPerfil.objects.all()
        
        config_context = {
            'cabos': {c.nome: {'coeficiente': c.coeficiente, 'preco': c.preco} for c in cfg_cabos_qs},
            'ips': {ip.nome: {'potencia_watts': ip.potencia_watts, 'preco': ip.preco} for ip in cfg_ips_qs},
            'perfis': {p.nome: {'cqt_max': p.cqt_max, 'sobrecarga_max': p.sobrecarga_max,
                                    'metros_max': p.metros_max, 'clientes_max': p.clientes_max}
                       for p in cfg_perfis_qs},
            'demandas': [] 
        }

        # 4. Chamar o motor de cálculo
        try:
            df_result, kpis, avisos = ElectricalEngine.calcular(df_trechos, params, config_context)

            # 5. Gerar Recomendações de Engenharia e Análise de Baricentro
            recom = DiagnosticoEngenharia.gerar_recomendacoes(df_result, kpis, avisos)
            baricentro_analysis = DiagnosticoEngenharia.analisar_baricentro(df_result, params['trafo_kva'])

            # Adicionar a análise de baricentro aos KPIs
            kpis['baricentro_analysis'] = baricentro_analysis

            # 6. Serializar e retornar a resposta
            resultados_json = df_result.to_dict(orient='records')

            return Response({
                'resultados_calculo': resultados_json,
                'kpis': kpis,
                'avisos': avisos,
                'recomendacoes': recom, # Include recommendations
            })
        except Exception as e:
            return Response({'error': f"Erro durante o cálculo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='simular_readequacao')
    def simular_readequacao(self, request, pk=None):
        """
        Executa a simulação de readequação para um cenário específico.
        """
        cenario = self.get_object()
        projeto = cenario.projeto

        # Get cabos_habilitados_nomes from request data
        cabos_habilitados_nomes = request.data.get('cabos_habilitados_nomes', [])
        if not cabos_habilitados_nomes:
            return Response(
                {'error': 'No enabled cables provided for simulation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Obter Trechos e converter para DataFrame
        trechos_qs = Trecho.objects.filter(projeto=projeto, nome_cenario=cenario.nome_cenario)
        if not trechos_qs.exists():
            return Response({'error': 'Nenhum trecho encontrado para este cenário.'}, status=status.HTTP_404_NOT_FOUND)
        
        trechos_data = list(trechos_qs.values(
            'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
            'carga_esp', 'tipo_ip', 'qtd_ip'
        ))
        df_trechos = pd.DataFrame(trechos_data)
        df_trechos.columns = [col.upper() for col in df_trechos.columns]

        # 2. Preparar parâmetros do cenário
        params = {
            'trafo_kva': cenario.trafo_kva,
            'classe_tipo': cenario.classe_tipo,
            'classe_manual': cenario.classe_manual,
            'fp_ip': cenario.fp_ip,
            'perfil': cenario.perfil,
        }

        # 3. Carregar configurações globais
        cfg_cabos_qs = CfgCabo.objects.all()
        cfg_ips_qs = CfgIP.objects.all()
        cfg_perfis_qs = CfgPerfil.objects.all()
        
        # Construct config_full matching ElectricalEngine.calcular's expectation for config_context
        config_full = {
            'cabos': {c.nome: {'coeficiente': c.coeficiente, 'preco': c.preco} for c in cfg_cabos_qs},
            'ips': {ip.nome: {'potencia_watts': ip.potencia_watts, 'preco': ip.preco} for ip in cfg_ips_qs},
            'perfis': {p.nome: {'cqt_max': p.cqt_max, 'sobrecarga_max': p.sobrecarga_max,
                                    'metros_max': p.metros_max, 'clientes_max': p.clientes_max}
                       for p in cfg_perfis_qs},
        }

        try:
            simulation_result = SimuladorReadequacao.executar(
                nome_origem=cenario.nome_cenario, # Pass scenario name as origin
                df_base=df_trechos,
                params=params,
                config_full=config_full, # Pass the correctly structured config_full
                cabos_habilitados_nomes=cabos_habilitados_nomes
            )

            # Return simulation results
            return Response({
                'df_simulated': simulation_result['df'].to_dict(orient='records'),
                'kpis_simulated': simulation_result['kpis'],
                'log_changes': simulation_result['log'],
                'iterations': simulation_result['iteracoes'],
                'message': simulation_result['msg'],
                'resolved': simulation_result['resolvido'],
            })
        except Exception as e:
            return Response({'error': f"Error during simulation: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export_csv') # Use GET for file download
    def export_excel_csv(self, request, pk=None):
        """
        Exports the calculation results for a specific scenario to a CSV file.
        """
        cenario = self.get_object()
        projeto = cenario.projeto

        # 1. Obtain Trechos and convert to DataFrame (same logic as calcular)
        trechos_qs = Trecho.objects.filter(projeto=projeto, nome_cenario=cenario.nome_cenario)
        if not trechos_qs.exists():
            return Response({'error': 'Nenhum trecho encontrado para este cenário.'}, status=status.HTTP_404_NOT_FOUND)
        
        trechos_data = list(trechos_qs.values(
            'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
            'carga_esp', 'tipo_ip', 'qtd_ip'
        ))
        df_trechos = pd.DataFrame(trechos_data)
        df_trechos.columns = [col.upper() for col in df_trechos.columns]

        # 2. Prepare parameters for the scenario (same logic as calcular)
        params = {
            'trafo_kva': cenario.trafo_kva,
            'classe_tipo': cenario.classe_tipo,
            'classe_manual': cenario.classe_manual,
            'fp_ip': cenario.fp_ip,
            'perfil': cenario.perfil,
        }

        # 3. Load global configurations (same logic as calcular)
        cfg_cabos_qs = CfgCabo.objects.all()
        cfg_ips_qs = CfgIP.objects.all()
        cfg_perfis_qs = CfgPerfil.objects.all()
        
        config_context = {
            'cabos': {c.nome: {'coeficiente': c.coeficiente, 'preco': c.preco} for c in cfg_cabos_qs},
            'ips': {ip.nome: {'potencia_watts': ip.potencia_watts, 'preco': ip.preco} for ip in cfg_ips_qs},
            'perfis': {p.nome: {'cqt_max': p.cqt_max, 'sobrecarga_max': p.sobrecarga_max,
                                    'metros_max': p.metros_max, 'clientes_max': p.clientes_max}
                       for p in cfg_perfis_qs},
            'demandas': [] 
        }

        # 4. Call the calculation engine
        try:
            df_result, kpis, avisos = ElectricalEngine.calcular(df_trechos, params, config_context)

            # Generate CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{projeto.nome}_{cenario.nome_cenario}_resultados.csv"'
            df_result.to_csv(path_or_buf=response, index=False, sep=';', decimal=',')
            return response

        except Exception as e:
            return Response({'error': f"Error during CSV export: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export_pdf')
    def export_pdf(self, request, pk=None):
        """
        Exports the calculation results for a specific scenario to a PDF file.
        """
        cenario = self.get_object()
        projeto = cenario.projeto

        # 1. Obtain Trechos and convert to DataFrame (same logic as calcular)
        trechos_qs = Trecho.objects.filter(projeto=projeto, nome_cenario=cenario.nome_cenario)
        if not trechos_qs.exists():
            return Response({'error': 'Nenhum trecho encontrado para este cenário.'}, status=status.HTTP_404_NOT_FOUND)
        
        trechos_data = list(trechos_qs.values(
            'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
            'carga_esp', 'tipo_ip', 'qtd_ip'
        ))
        df_trechos = pd.DataFrame(trechos_data)
        df_trechos.columns = [col.upper() for col in df_trechos.columns]

        # 2. Prepare parameters for the scenario (same logic as calcular)
        params = {
            'trafo_kva': cenario.trafo_kva,
            'classe_tipo': cenario.classe_tipo,
            'classe_manual': cenario.classe_manual,
            'fp_ip': cenario.fp_ip,
            'perfil': cenario.perfil,
        }

        # 3. Load global configurations (same logic as calcular)
        cfg_cabos_qs = CfgCabo.objects.all()
        cfg_ips_qs = CfgIP.objects.all()
        cfg_perfis_qs = CfgPerfil.objects.all()
        
        config_context = {
            'cabos': {c.nome: {'coeficiente': c.coeficiente, 'preco': c.preco} for c in cfg_cabos_qs},
            'ips': {ip.nome: {'potencia_watts': ip.potencia_watts, 'preco': ip.preco} for ip in cfg_ips_qs},
            'perfis': {p.nome: {'cqt_max': p.cqt_max, 'sobrecarga_max': p.sobrecarga_max,
                                    'metros_max': p.metros_max, 'clientes_max': p.clientes_max}
                       for p in cfg_perfis_qs},
            'demandas': [] 
        }

        # 4. Call the calculation engine
        try:
            df_result, kpis, avisos = ElectricalEngine.calcular(df_trechos, params, config_context)
            recom = DiagnosticoEngenharia.gerar_recomendacoes(df_result, kpis, avisos)

            # Generate PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{projeto.nome}_{cenario.nome_cenario}_relatorio.pdf"'

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            story.append(Paragraph(f"Relatório de Cálculo - Projeto: {projeto.nome}, Cenário: {cenario.nome_cenario}", styles['h1']))
            story.append(Spacer(1, 0.2 * inch)) # inch needs to be imported, or use a numeric value

            # KPIs
            story.append(Paragraph("<b>Indicadores de Desempenho (KPIs):</b>", styles['h3']))
            for key, value in kpis.items():
                if isinstance(value, dict): # For nested structures like baricentro_analysis
                    story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", styles['Normal']))
                    for sub_key, sub_value in value.items():
                        story.append(Paragraph(f"  {sub_key.replace('_', ' ').title()}: {sub_value}", styles['Normal']))
                else:
                    story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            # Warnings
            if avisos:
                story.append(Paragraph("<b>Avisos:</b>", styles['h3']))
                for aviso in avisos:
                    story.append(Paragraph(f"- {aviso}", styles['Normal']))
                story.append(Spacer(1, 0.2 * inch))

            # Recommendations
            if recom:
                story.append(Paragraph("<b>Recomendações:</b>", styles['h3']))
                for rec in recom:
                    story.append(Paragraph(f"- {rec}", styles['Normal']))
                story.append(Spacer(1, 0.2 * inch))

            # Results Table
            story.append(Paragraph("<b>Resultados Detalhados dos Trechos:</b>", styles['h3']))
            data = [df_result.columns.tolist()] + df_result.values.tolist()
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)

            doc.build(buffer, story)
            response.write(buffer.getvalue())
            buffer.close()
            return response

        except Exception as e:
            return Response({'error': f"Error during PDF export: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrechoViewSet(viewsets.ModelViewSet):
    queryset = Trecho.objects.all()
    serializer_class = TrechoSerializer

    def get_queryset(self):
        queryset = Trecho.objects.all()
        projeto_id = self.request.query_params.get('projeto_id')
        nome_cenario = self.request.query_params.get('nome_cenario')

        if projeto_id:
            queryset = queryset.filter(projeto_id=projeto_id)
        if nome_cenario:
            queryset = queryset.filter(nome_cenario=nome_cenario)
            
        return queryset

class CfgCaboViewSet(viewsets.ModelViewSet):
    queryset = CfgCabo.objects.all()
    serializer_class = CfgCaboSerializer

class CfgIPViewSet(viewsets.ModelViewSet):
    queryset = CfgIP.objects.all()
    serializer_class = CfgIPSerializer

class CfgTrafoViewSet(viewsets.ModelViewSet):
    queryset = CfgTrafo.objects.all()
    serializer_class = CfgTrafoSerializer
    lookup_field = 'kva' # Specify that 'kva' is the lookup field
    lookup_value_regex = '[0-9.]+' # Allow dots in the primary key for float values

class CfgPerfilViewSet(viewsets.ModelViewSet):
    queryset = CfgPerfil.objects.all()
    serializer_class = CfgPerfilSerializer
