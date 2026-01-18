from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Projeto, CenarioConfig, Trecho, CfgCabo, CfgIP, CfgTrafo, CfgPerfil
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
import pandas as pd

class CenarioAPITests(APITestCase):
    def setUp(self):
        """
        Set up the test environment. This method is called before every test.
        """
        # Create a project
        self.projeto = Projeto.objects.create(nome="Projeto Teste")

        # Create a scenario for the project
        self.cenario = CenarioConfig.objects.create(
            projeto=self.projeto,
            nome_cenario="Cenario de Teste",
            trafo_kva=75,
            classe_tipo="Automático"
        )

        # Create a default cable configuration required by the engine
        # This is needed by the engine in the CenarioAPITests
        CfgCabo.objects.create(nome="3x35+54.6mm² Al", coeficiente=0.8, preco=10.0)

        # Create network segments (Trechos) for the scenario
        # A simple network: TRAFO -> P1 -> P2
        Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="TRAFO",
            montante="",
            metros=0,
            cabo="",
        )
        Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="P1",
            montante="TRAFO",
            metros=100,
            cabo="3x35+54.6mm² Al",
            mono=10, # 10 single-phase clients
        )
        Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="P2",
            montante="P1",
            metros=50,
            cabo="3x35+54.6mm² Al",
            bi=5, # 5 two-phase clients
        )

    def test_calcular_endpoint(self):
        """
        Test the /api/cenarios/{pk}/calcular/ endpoint.
        """
        # Get the URL for the custom action
        url = reverse('siscqt_core:cenarioconfig-calcular', kwargs={'pk': self.cenario.pk})

        # Make the POST request to the endpoint
        response = self.client.post(url, format='json')

        # 1. Check for a successful response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Check if the response data contains the expected keys
        self.assertIn('resultados_calculo', response.data)
        self.assertIn('kpis', response.data)
        self.assertIn('avisos', response.data)

        # 3. Check the content of the results
        kpis = response.data['kpis']
        self.assertIn('demanda', kpis)
        self.assertIn('max_cqt', kpis)
        
        # 4. Check that the results are plausible
        self.assertGreater(kpis['demanda'], 0, "A demanda calculada deve ser maior que zero.")
        self.assertGreater(kpis['max_cqt'], 0, "A queda de tensão máxima deve ser maior que zero.")

        # 5. Check if the calculation results have the correct number of rows
        resultados = response.data['resultados_calculo']
        self.assertEqual(len(resultados), 3, "O resultado do cálculo deve conter 3 trechos (TRAFO, P1, P2).")

    def test_upload_excel_endpoint(self):
        """
        Test the /api/projetos/upload_excel/ endpoint.
        """
        excel_file_path = "CP_A052750522_CQT.xlsx"
        
        try:
            with open(excel_file_path, 'rb') as f:
                excel_content = f.read()
        except FileNotFoundError:
            self.fail(f"Test file not found: {excel_file_path}. Please ensure it's in the project root.")

        file_upload = SimpleUploadedFile(
            "CP_A052750522_CQT.xlsx",
            excel_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Get the URL for the custom action
        url = reverse('siscqt_core:projeto-upload-excel')
        
        response = self.client.post(
            f"{url}?project_name=CP_A052750522_CQT_Project",
            data={'file': file_upload},
            format='multipart'
        )

        # Check for a successful response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that a new project has been created
        self.assertTrue(Projeto.objects.filter(nome='CP_A052750522_CQT_Project').exists())

class CfgAPITests(APITestCase):
    def setUp(self):
        # Create a default cable configuration for testing purposes.
        CfgCabo.objects.create(nome="DEFAULT_CABO", coeficiente=0.5, preco=1.0)
        # Create a project and scenario for Trecho tests
        self.projeto = Projeto.objects.create(nome="Projeto Cfg Teste")
        self.cenario = CenarioConfig.objects.create(projeto=self.projeto, nome_cenario="Cenario Cfg Teste")
        Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="TRAFO",
            montante="",
            metros=0,
            cabo="",
        )
        Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="P1",
            montante="TRAFO",
            metros=100,
            cabo="DEFAULT_CABO",
            mono=10, # 10 single-phase clients
        )
        Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="P2",
            montante="P1",
            metros=50,
            cabo="DEFAULT_CABO",
            bi=5, # 5 two-phase clients
        )

    def test_cfgcabo_list_create(self):
        url = reverse('siscqt_core:cfgcabo-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Test create
        data = {'nome': 'TESTE', 'coeficiente': 1.0, 'preco': 5.0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CfgCabo.objects.count(), 2) # 1 from setup, 1 new

    def test_cfgcabo_retrieve_update_destroy(self):
        cabo = CfgCabo.objects.create(nome="TESTE_CABO_CRUD", coeficiente=1.5, preco=12.0)
        url = reverse('siscqt_core:cfgcabo-detail', kwargs={'pk': 'TESTE_CABO_CRUD'})

        # Test retrieve
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], 'TESTE_CABO_CRUD')

        # Test update
        data = {'nome': 'TESTE_CABO_CRUD', 'coeficiente': 1.8, 'preco': 15.0}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cabo.refresh_from_db()
        self.assertEqual(cabo.coeficiente, 1.8)

        # Test destroy
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CfgCabo.objects.count(), 1) # Original from CfgAPITests setup

    def test_cfgip_list_create(self):
        url = reverse('siscqt_core:cfgip-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Test create
        data = {'nome': 'IP_TESTE', 'potencia_watts': 100.0, 'preco': 50.0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CfgIP.objects.count(), 1) # 1 new

    def test_cfgip_retrieve_update_destroy(self):
        ip = CfgIP.objects.create(nome="IP_TESTE_CRUD", potencia_watts=150.0, preco=75.0)
        url = reverse('siscqt_core:cfgip-detail', kwargs={'pk': 'IP_TESTE_CRUD'})

        # Test retrieve
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], 'IP_TESTE_CRUD')

        # Test update
        data = {'nome': 'IP_TESTE_CRUD', 'potencia_watts': 200.0, 'preco': 100.0}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ip.refresh_from_db()
        self.assertEqual(ip.potencia_watts, 200.0)

        # Test destroy
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CfgIP.objects.count(), 0)

    def test_cfgtrafo_list_create(self):
        url = reverse('siscqt_core:cfgtrafo-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Test create
        data = {'kva': 112.5}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CfgTrafo.objects.count(), 1) # 1 new

    def test_cfgtrafo_retrieve_update_destroy(self):
        trafo = CfgTrafo.objects.create(kva=300.0)
        url = reverse('siscqt_core:cfgtrafo-detail', kwargs={'kva': str(300.0)})

        # Test retrieve
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['kva'], 300.0)

        # Test update
        data = {'kva': 300.0} # Primary key cannot be updated directly via PUT/PATCH on PK field
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Should still return 200 if nothing changed.

        # Test destroy
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CfgTrafo.objects.count(), 0)

    def test_cfgperfil_list_create(self):
        url = reverse('siscqt_core:cfgperfil-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Test create
        data = {'nome': 'PERFIL_TESTE', 'cqt_max': 5.0, 'sobrecarga_max': 90.0}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CfgPerfil.objects.count(), 1) # 1 new

    def test_cfgperfil_retrieve_update_destroy(self):
        perfil = CfgPerfil.objects.create(nome="PERFIL_CRUD", cqt_max=4.5, sobrecarga_max=85.0)
        url = reverse('siscqt_core:cfgperfil-detail', kwargs={'pk': 'PERFIL_CRUD'})

        # Test retrieve
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome'], 'PERFIL_CRUD')

        # Test update
        data = {'nome': 'PERFIL_CRUD', 'cqt_max': 4.0, 'sobrecarga_max': 80.0}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perfil.refresh_from_db()
        self.assertEqual(perfil.cqt_max, 4.0)

        # Test destroy
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CfgPerfil.objects.count(), 0)
    
    # --- Trecho API Tests ---
    def test_trecho_list_create(self):
        url = reverse('siscqt_core:trecho-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test create
        data = {
            'projeto': self.projeto.id,
            'nome_cenario': self.cenario.nome_cenario,
            'ponto': 'P3',
            'montante': 'P2',
            'metros': 75.0,
            'cabo': 'DEFAULT_CABO',
            'mono': 8, 'bi': 0, 'tri': 0, 'tri_esp': 0,
            'carga_esp': 0.0, 'tipo_ip': 'Sem IP', 'qtd_ip': 0
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Trecho.objects.filter(projeto=self.projeto).count(), 4) # 3 from setup, 1 new

    def test_trecho_retrieve_update_destroy(self):
        trecho = Trecho.objects.create(
            projeto=self.projeto,
            nome_cenario=self.cenario.nome_cenario,
            ponto="P_CRUD",
            montante="P2",
            metros=10.0,
            cabo="DEFAULT_CABO"
        )
        url = reverse('siscqt_core:trecho-detail', kwargs={'pk': trecho.pk})

        # Test retrieve
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ponto'], 'P_CRUD')

        # Test update
        data = {
            'projeto': self.projeto.id,
            'nome_cenario': self.cenario.nome_cenario,
            'ponto': 'P_CRUD_UPDATED', # Cannot change PK, but ponto is not PK
            'montante': 'P1',
            'metros': 15.0,
            'cabo': 'DEFAULT_CABO',
            'mono': 2, 'bi': 0, 'tri': 0, 'tri_esp': 0,
            'carga_esp': 0.0, 'tipo_ip': 'Sem IP', 'qtd_ip': 0
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trecho.refresh_from_db()
        self.assertEqual(trecho.metros, 15.0)
        self.assertEqual(trecho.ponto, 'P_CRUD_UPDATED') # Should update non-PK fields

        # Test destroy
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # 3 Trechos from CfgAPITests setUp are still there
        self.assertEqual(Trecho.objects.filter(projeto=self.projeto).count(), 3)