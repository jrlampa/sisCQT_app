# siscqt_core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
import pandas as pd
from django.contrib import messages
from django.db import transaction
from io import BytesIO
from django.forms import modelform_factory

from .models import Projeto, Trecho, CenarioConfig, CfgCabo, CfgIP, CfgTrafo, CfgPerfil
from .services import ElectricalEngine
from .siscqt_constantes import DEFAULT_COL_ORDER, DEFAULT_PARAMS
from .forms import ExcelUploadForm, CenarioConfigForm, CfgCaboForm, CfgIPForm, CfgTrafoForm, CfgPerfilForm, CriarCenarioForm
from .excel_parser import importar_planilha_concessionaria


def listar_projetos(request):
    """
    View para listar todos os projetos existentes.
    """
    projetos = Projeto.objects.all()
    context = {
        'projetos': projetos
    }
    return render(request, 'siscqt_core/lista_projetos.html', context)

def detalhe_projeto(request, projeto_id, cenario_id=None): # Added cenario_id parameter
    """
    View para exibir os detalhes de um projeto e seus cenários,
    e demonstrar como o ElectricalEngine pode ser chamado.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    cenarios = CenarioConfig.objects.filter(projeto=projeto).order_by('nome_cenario') # Order scenarios

    resultados_calculo = {}
    active_cenario = None # To hold the currently active scenario

    if cenarios.exists():
        if cenario_id:
            active_cenario = get_object_or_404(CenarioConfig, pk=cenario_id, projeto=projeto)
        else:
            active_cenario = cenarios.first() # Default to the first scenario

        trechos_qs = Trecho.objects.filter(projeto=projeto, nome_cenario=active_cenario.nome_cenario)

        # Converter QuerySet de Trechos para DataFrame
        trechos_data = trechos_qs.values(
            'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
            'carga_esp', 'tipo_ip', 'qtd_ip'
        )
        df_trechos = pd.DataFrame(list(trechos_data))

        # Prepare parameters for the active scenario
        params = {
            'trafo_kva': active_cenario.trafo_kva,
            'classe_tipo': active_cenario.classe_tipo,
            'classe_manual': active_cenario.classe_manual,
            'fp_ip': active_cenario.fp_ip,
            'perfil': active_cenario.perfil,
        }

        # Load global configurations
        cfg_cabos_qs = CfgCabo.objects.all().values('nome', 'coeficiente', 'preco')
        cfg_ips_qs = CfgIP.objects.all().values('nome', 'potencia_watts', 'preco')
        cfg_perfis_qs = CfgPerfil.objects.all().values(
            'nome', 'cqt_max', 'sobrecarga_max', 'metros_max', 'clientes_max'
        )

        config_context = {
            'cabos': {c['nome']: {'coef': c['coeficiente'], 'preco': c['preco']} for c in cfg_cabos_qs},
            'ips': {ip['nome']: {'pot': ip['potencia_watts'], 'preco': ip['preco']} for ip in cfg_ips_qs},
            'perfis': {p['nome']: {'cqt_max': p['cqt_max'], 'sobrecarga_max': p['sobrecarga_max'],
                                    'metros_max': p['metros_max'], 'clientes_max': p['clientes_max']}
                       for p in cfg_perfis_qs},
        }

        # Call the calculation engine
        df_result, kpis, avisos = ElectricalEngine.calcular(df_trechos, params, config_context)
        
        resultados_calculo = {
            'df_result_html': df_result.to_html(classes='table table-striped', index=False) if not df_result.empty else "<p>Nenhum dado de cálculo.</p>",
            'kpis': kpis,
            'avisos': avisos,
        }


    context = {
        'projeto': projeto,
        'cenarios': cenarios,
        'active_cenario': active_cenario, # Pass active scenario to template
        'resultados_calculo': resultados_calculo
    }
    return render(request, 'siscqt_core/detalhe_projeto.html', context)

def upload_excel_projeto(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project_name = form.cleaned_data['project_name']
            excel_file = request.FILES['excel_file'] # Use request.FILES directly for file content

            # Check if project name already exists
            if Projeto.objects.filter(nome=project_name).exists():
                messages.error(request, f"Já existe um projeto com o nome '{project_name}'. Por favor, escolha outro nome.")
                return render(request, 'siscqt_core/upload_excel_projeto.html', {'form': form})

            try:
                # Read the uploaded file into BytesIO
                file_content = BytesIO(excel_file.read())
                
                # Parse the Excel file
                df_norm, trafo_kva, config_cabos_imp, classe_encontrada, erros_importacao = \
                    importar_planilha_concessionaria(file_content)

                if df_norm.empty and erros_importacao:
                    for error in erros_importacao:
                        messages.error(request, f"Erro de importação: {error}")
                    return render(request, 'siscqt_core/upload_excel_projeto.html', {'form': form})

                if erros_importacao:
                    for aviso in erros_importacao:
                        messages.warning(request, f"Aviso na importação: {aviso}")
                
                with transaction.atomic():
                    # 1. Create Projeto
                    projeto = Projeto.objects.create(nome=project_name)

                    # 2. Create CenarioConfig
                    # For simplicity, we create one scenario per uploaded file, named after the project
                    cenario_name = "Cenario Padrão" # Or use project_name if preferred
                    CenarioConfig.objects.create(
                        projeto=projeto,
                        nome_cenario=cenario_name,
                        trafo_kva=trafo_kva if trafo_kva else DEFAULT_PARAMS['trafo_kva'],
                        classe_tipo="Manual", # Assuming imported class is manual
                        classe_manual=classe_encontrada if classe_encontrada else DEFAULT_PARAMS['classe_manual'],
                        fp_ip=DEFAULT_PARAMS['fp_ip'], # Use default from constants for now
                        perfil=DEFAULT_PARAMS['perfil'] # Use default from constants for now
                    )

                    # 3. Create Trechos
                    trechos_to_create = []
                    for index, row in df_norm.iterrows():
                        trechos_to_create.append(
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
                            )
                        )
                    Trecho.objects.bulk_create(trechos_to_create)

                    # 4. Update CfgCabo (if new cables were imported)
                    for cabo_name, coef_val in config_cabos_imp.items():
                        # We only update coefficient here. Preco is not in the original import logic.
                        CfgCabo.objects.update_or_create(
                            nome=cabo_name,
                            defaults={'coeficiente': coef_val}
                        )

                messages.success(request, f"Projeto '{project_name}' importado com sucesso!")
                return redirect('siscqt_core:detalhe_projeto', projeto_id=projeto.id) # Redirect to the new project's detail page

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao processar o arquivo: {e}")
                
        else:
            # Form is not valid, re-render with errors
            pass # Errors will be displayed by the template

    else:
        form = ExcelUploadForm()
    
    return render(request, 'siscqt_core/upload_excel_projeto.html', {'form': form})


def editar_cenario(request, cenario_id):
    cenario = get_object_or_404(CenarioConfig, pk=cenario_id)
    
    if request.method == 'POST':
        form = CenarioConfigForm(request.POST, instance=cenario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cenário '{cenario.nome_cenario}' atualizado com sucesso!")
            return redirect('siscqt_core:detalhe_projeto', projeto_id=cenario.projeto.id)
    else:
        form = CenarioConfigForm(instance=cenario)
    
    context = {
        'form': form,
        'cenario': cenario,
        'projeto': cenario.projeto,
    }
    return render(request, 'siscqt_core/editar_cenario.html', context)


def configuracoes(request):
    return render(request, 'siscqt_core/configuracoes.html')

# --- CfgCabo CRUD Views ---
def listar_cabos(request):
    cabos = CfgCabo.objects.all().order_by('nome')
    context = {'cabos': cabos}
    return render(request, 'siscqt_core/cfg_cabos/listar_cabos.html', context)

def criar_cabo(request):
    if request.method == 'POST':
        form = CfgCaboForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Cabo '{form.cleaned_data['nome']}' criado com sucesso!")
                return redirect('siscqt_core:listar_cabos')
            except Exception as e:
                messages.error(request, f"Erro ao criar cabo: {e}")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgCaboForm()
    context = {'form': form, 'acao': 'Criar'}
    return render(request, 'siscqt_core/cfg_cabos/form_cabo.html', context)

def editar_cabo(request, nome_cabo):
    cabo = get_object_or_404(CfgCabo, nome=nome_cabo)
    if request.method == 'POST':
        form = CfgCaboForm(request.POST, instance=cabo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cabo '{cabo.nome}' atualizado com sucesso!")
            return redirect('siscqt_core:listar_cabos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgCaboForm(instance=cabo)
    context = {'form': form, 'cabo': cabo, 'acao': 'Editar'}
    return render(request, 'siscqt_core/cfg_cabos/form_cabo.html', context)

def excluir_cabo(request, nome_cabo):
    cabo = get_object_or_404(CfgCabo, nome=nome_cabo)
    if request.method == 'POST':
        cabo.delete()
        messages.success(request, f"Cabo '{cabo.nome}' excluído com sucesso!")
        return redirect('siscqt_core:listar_cabos')
    context = {'cabo': cabo}
    return render(request, 'siscqt_core/cfg_cabos/confirmar_exclusao_cabo.html', context)

# --- CfgIP CRUD Views ---
def listar_ips(request):
    ips = CfgIP.objects.all().order_by('nome')
    context = {'ips': ips}
    return render(request, 'siscqt_core/cfg_ips/listar_ips.html', context)

def criar_ip(request):
    if request.method == 'POST':
        form = CfgIPForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"IP '{form.cleaned_data['nome']}' criado com sucesso!")
                return redirect('siscqt_core:listar_ips')
            except Exception as e:
                messages.error(request, f"Erro ao criar IP: {e}")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgIPForm()
    context = {'form': form, 'acao': 'Criar'}
    return render(request, 'siscqt_core/cfg_ips/form_ip.html', context)

def editar_ip(request, nome_ip):
    ip_cfg = get_object_or_404(CfgIP, nome=nome_ip)
    if request.method == 'POST':
        form = CfgIPForm(request.POST, instance=ip_cfg)
        if form.is_valid():
            form.save()
            messages.success(request, f"IP '{ip_cfg.nome}' atualizado com sucesso!")
            return redirect('siscqt_core:listar_ips')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgIPForm(instance=ip_cfg)
    context = {'form': form, 'ip_cfg': ip_cfg, 'acao': 'Editar'}
    return render(request, 'siscqt_core/cfg_ips/form_ip.html', context)

def excluir_ip(request, nome_ip):
    ip_cfg = get_object_or_404(CfgIP, nome=nome_ip)
    if request.method == 'POST':
        ip_cfg.delete()
        messages.success(request, f"IP '{ip_cfg.nome}' excluído com sucesso!")
        return redirect('siscqt_core:listar_ips')
    context = {'ip_cfg': ip_cfg}
    return render(request, 'siscqt_core/cfg_ips/confirmar_exclusao_ip.html', context)

# --- CfgTrafo CRUD Views ---
def listar_trafos(request):
    trafos = CfgTrafo.objects.all().order_by('kva')
    context = {'trafos': trafos}
    return render(request, 'siscqt_core/cfg_trafos/listar_trafos.html', context)

def criar_trafo(request):
    if request.method == 'POST':
        form = CfgTrafoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Trafo de {form.cleaned_data['kva']} kVA criado com sucesso!")
                return redirect('siscqt_core:listar_trafos')
            except Exception as e:
                messages.error(request, f"Erro ao criar trafo: {e}")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgTrafoForm()
    context = {'form': form, 'acao': 'Criar'}
    return render(request, 'siscqt_core/cfg_trafos/form_trafo.html', context)

def editar_trafo(request, kva_trafo):
    trafo = get_object_or_404(CfgTrafo, kva=kva_trafo)
    if request.method == 'POST':
        form = CfgTrafoForm(request.POST, instance=trafo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Trafo de {trafo.kva} kVA atualizado com sucesso!")
            return redirect('siscqt_core:listar_trafos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgTrafoForm(instance=trafo)
    context = {'form': form, 'trafo': trafo, 'acao': 'Editar'}
    return render(request, 'siscqt_core/cfg_trafos/form_trafo.html', context)

def excluir_trafo(request, kva_trafo):
    trafo = get_object_or_404(CfgTrafo, kva=kva_trafo)
    if request.method == 'POST':
        trafo.delete()
        messages.success(request, f"Trafo de {trafo.kva} kVA excluído com sucesso!")
        return redirect('siscqt_core:listar_trafos')
    context = {'trafo': trafo}
    return render(request, 'siscqt_core/cfg_trafos/confirmar_exclusao_trafo.html', context)


# --- CfgPerfil CRUD Views ---
def listar_perfis(request):
    perfis = CfgPerfil.objects.all().order_by('nome')
    context = {'perfis': perfis}
    return render(request, 'siscqt_core/cfg_perfis/listar_perfis.html', context)

def criar_perfil(request):
    if request.method == 'POST':
        form = CfgPerfilForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Perfil '{form.cleaned_data['nome']}' criado com sucesso!")
                return redirect('siscqt_core:listar_perfis')
            except Exception as e:
                messages.error(request, f"Erro ao criar perfil: {e}")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgPerfilForm()
    context = {'form': form, 'acao': 'Criar'}
    return render(request, 'siscqt_core/cfg_perfis/form_perfil.html', context)

def editar_perfil(request, nome_perfil):
    perfil = get_object_or_404(CfgPerfil, nome=nome_perfil)
    if request.method == 'POST':
        form = CfgPerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, f"Perfil '{perfil.nome}' atualizado com sucesso!")
            return redirect('siscqt_core:listar_perfis')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CfgPerfilForm(instance=perfil)
    context = {'form': form, 'perfil': perfil, 'acao': 'Editar'}
    return render(request, 'siscqt_core/cfg_perfis/form_perfil.html', context)

def excluir_perfil(request, nome_perfil):
    perfil = get_object_or_404(CfgPerfil, nome=nome_perfil)
    if request.method == 'POST':
        perfil.delete()
        messages.success(request, f"Perfil '{perfil.nome}' excluído com sucesso!")
        return redirect('siscqt_core:listar_perfis')
    context = {'perfil': perfil}
    return render(request, 'siscqt_core/cfg_perfis/confirmar_exclusao_perfil.html', context)

def excluir_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if request.method == 'POST':
        projeto.delete()
        messages.success(request, f"Projeto '{projeto.nome}' e todos os seus cenários foram excluídos com sucesso!")
        return redirect('siscqt_core:listar_projetos')
    context = {'projeto': projeto}
    return render(request, 'siscqt_core/confirmar_exclusao_projeto.html', context)

def excluir_cenario(request, cenario_id):
    cenario = get_object_or_404(CenarioConfig, pk=cenario_id)
    projeto = cenario.projeto
    if request.method == 'POST':
        cenario.delete()
        messages.success(request, f"Cenário '{cenario.nome_cenario}' excluído com sucesso do projeto '{projeto.nome}'!")
        return redirect('siscqt_core:detalhe_projeto', projeto_id=projeto.id)
    context = {'cenario': cenario, 'projeto': projeto}
    return render(request, 'siscqt_core/confirmar_exclusao_cenario.html', context)

def criar_cenario(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    if request.method == 'POST':
        form = CriarCenarioForm(request.POST, projeto_id=projeto.id)
        if form.is_valid():
            new_cenario_name = form.cleaned_data['nome_cenario']
            copy_from_cenario = form.cleaned_data['copy_from_cenario']

            # Check for duplicate scenario name within the project
            if CenarioConfig.objects.filter(projeto=projeto, nome_cenario=new_cenario_name).exists():
                messages.error(request, f"Já existe um cenário com o nome '{new_cenario_name}' neste projeto.")
                context = {'form': form, 'projeto': projeto}
                return render(request, 'siscqt_core/criar_cenario.html', context)

            with transaction.atomic():
                if copy_from_cenario:
                    # Copy CenarioConfig
                    new_cenario_config = CenarioConfig.objects.create(
                        projeto=projeto,
                        nome_cenario=new_cenario_name,
                        trafo_kva=copy_from_cenario.trafo_kva,
                        classe_tipo=copy_from_cenario.classe_tipo,
                        classe_manual=copy_from_cenario.classe_manual,
                        fp_ip=copy_from_cenario.fp_ip,
                        perfil=copy_from_cenario.perfil
                    )
                    # Copy associated Trechos
                    trechos_to_create = []
                    for trecho in Trecho.objects.filter(projeto=projeto, nome_cenario=copy_from_cenario.nome_cenario):
                        trechos_to_create.append(
                            Trecho(
                                projeto=projeto,
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
                    messages.success(request, f"Cenário '{new_cenario_name}' criado a partir de '{copy_from_cenario.nome_cenario}' com sucesso!")
                else:
                    # Create blank CenarioConfig
                    CenarioConfig.objects.create(
                        projeto=projeto,
                        nome_cenario=new_cenario_name,
                        # Use default values for other fields
                        trafo_kva=DEFAULT_PARAMS['trafo_kva'],
                        classe_tipo="Automático", # Default
                        classe_manual="A", # Default
                        fp_ip=DEFAULT_PARAMS['fp_ip'],
                        perfil=DEFAULT_PARAMS['perfil']
                    )
                    messages.success(request, f"Cenário '{new_cenario_name}' em branco criado com sucesso!")
            
            return redirect('siscqt_core:detalhe_projeto', projeto_id=projeto.id)
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarCenarioForm(projeto_id=projeto.id)
    
    context = {
        'form': form,
        'projeto': projeto,
    }
    return render(request, 'siscqt_core/criar_cenario.html', context)

def exportar_projeto_excel(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    cenarios = CenarioConfig.objects.filter(projeto=projeto).order_by('nome_cenario')

    if not cenarios.exists():
        messages.error(request, f"Nenhum cenário encontrado para o projeto '{projeto.nome}' para exportar.")
        return redirect('siscqt_core:detalhe_projeto', projeto_id=projeto.id)

    output = BytesIO()
    # Using 'xlsxwriter' engine for better compatibility and features if available, otherwise 'openpyxl'
    try:
        # Check if xlsxwriter is installed, otherwise default to openpyxl
        import xlsxwriter
        engine = 'xlsxwriter'
    except ImportError:
        engine = 'openpyxl'
        
    with pd.ExcelWriter(output, engine=engine) as writer:
        for cenario in cenarios:
            trechos_qs = Trecho.objects.filter(projeto=projeto, nome_cenario=cenario.nome_cenario)
            df_trechos = pd.DataFrame(list(trechos_qs.values(
                'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
                'carga_esp', 'tipo_ip', 'qtd_ip'
            )))

            # Prepare parameters for the scenario
            params = {
                'trafo_kva': cenario.trafo_kva,
                'classe_tipo': cenario.classe_tipo,
                'classe_manual': cenario.classe_manual,
                'fp_ip': cenario.fp_ip,
                'perfil': cenario.perfil,
            }

            # Load global configurations
            cfg_cabos_qs = CfgCabo.objects.all().values('nome', 'coeficiente', 'preco')
            cfg_ips_qs = CfgIP.objects.all().values('nome', 'potencia_watts', 'preco')
            cfg_perfis_qs = CfgPerfil.objects.all().values(
                'nome', 'cqt_max', 'sobrecarga_max', 'metros_max', 'clientes_max'
            )

            config_context = {
                'cabos': {c['nome']: {'coef': c['coeficiente'], 'preco': c['preco']} for c in cfg_cabos_qs},
                'ips': {ip['nome']: {'pot': ip['potencia_watts'], 'preco': ip['preco']} for ip in cfg_ips_qs},
                'perfis': {p['nome']: {'cqt_max': p['cqt_max'], 'sobrecarga_max': p['sobrecarga_max'],
                                        'metros_max': p['metros_max'], 'clientes_max': p['clientes_max']}
                           for p in cfg_perfis_qs},
            }

            # Call the calculation engine
            df_result, kpis, avisos = ElectricalEngine.calcular(df_trechos, params, config_context)

            # Write results to Excel sheet
            sheet_name = cenario.nome_cenario[:31] # Excel sheet name max 31 chars
            df_result.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Optionally add KPI and Aviso data to a separate sheet or cell in the same sheet
            # For simplicity, just adding results DF to each sheet.
        
    output.seek(0)
    filename = f"SisCQT_Projeto_{projeto.nome}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
