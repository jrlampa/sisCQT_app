from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
import pandas as pd
from io import BytesIO
from django.db import transaction

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
from .services import ElectricalEngine
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

    @action(detail=True, methods=['post'], url_path='calcular')
    def calcular(self, request, pk=None):
        """
        Executa o cálculo elétrico para um cenário específico.
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
            # NOTA: 'demandas' não existe nos modelos atuais.
            # O motor legado pode precisar ser ajustado ou o modelo 'Demanda' precisa ser criado.
            'demandas': [] 
        }

        # 4. Chamar o motor de cálculo
        try:
            # Assumindo que a engine está em siscqt_core/services.py
            df_result, kpis, avisos = ElectricalEngine.calcular(df_trechos, params, config_context)

            # 5. Serializar e retornar a resposta
            # O DataFrame precisa ser convertido para um formato JSON
            resultados_json = df_result.to_dict(orient='records')

            return Response({
                'resultados_calculo': resultados_json,
                'kpis': kpis,
                'avisos': avisos
            })
        except Exception as e:
            return Response({'error': f"Erro durante o cálculo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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