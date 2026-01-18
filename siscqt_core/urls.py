# siscqt_core/urls.py
from django.urls import path
from . import views

app_name = 'siscqt_core'

urlpatterns = [
    path('', views.listar_projetos, name='listar_projetos'),
    path('projeto/<int:projeto_id>/', views.detalhe_projeto, name='detalhe_projeto'),
    path('projeto/<int:projeto_id>/cenario/<int:cenario_id>/', views.detalhe_projeto, name='detalhe_projeto_cenario'),
    path('upload/', views.upload_excel_projeto, name='upload_excel_projeto'),
    path('cenario/<int:cenario_id>/editar/', views.editar_cenario, name='editar_cenario'),
    path('projeto/<int:projeto_id>/excluir/', views.excluir_projeto, name='excluir_projeto'),
    path('cenario/<int:cenario_id>/excluir/', views.excluir_cenario, name='excluir_cenario'),
    path('projeto/<int:projeto_id>/criar_cenario/', views.criar_cenario, name='criar_cenario'),
    path('projeto/<int:projeto_id>/exportar_excel/', views.exportar_projeto_excel, name='exportar_projeto_excel'),

    # Configurações Gerais
    path('configuracoes/', views.configuracoes, name='configuracoes'),

    # CfgCabo URLs
    path('configuracoes/cabos/', views.listar_cabos, name='listar_cabos'),
    path('configuracoes/cabos/criar/', views.criar_cabo, name='criar_cabo'),
    path('configuracoes/cabos/editar/<str:nome_cabo>/', views.editar_cabo, name='editar_cabo'),
    path('configuracoes/cabos/excluir/<str:nome_cabo>/', views.excluir_cabo, name='excluir_cabo'),

    # CfgIP URLs
    path('configuracoes/ips/', views.listar_ips, name='listar_ips'),
    path('configuracoes/ips/criar/', views.criar_ip, name='criar_ip'),
    path('configuracoes/ips/editar/<str:nome_ip>/', views.editar_ip, name='editar_ip'),
    path('configuracoes/ips/excluir/<str:nome_ip>/', views.excluir_ip, name='excluir_ip'),

    # CfgTrafo URLs
    path('configuracoes/trafos/', views.listar_trafos, name='listar_trafos'),
    path('configuracoes/trafos/criar/', views.criar_trafo, name='criar_trafo'),
    path('configuracoes/trafos/editar/<str:kva_trafo>/', views.editar_trafo, name='editar_trafo'),
    path('configuracoes/trafos/excluir/<str:kva_trafo>/', views.excluir_trafo, name='excluir_trafo'),

    # CfgPerfil URLs
    path('configuracoes/perfis/', views.listar_perfis, name='listar_perfis'),
    path('configuracoes/perfis/criar/', views.criar_perfil, name='criar_perfil'),
    path('configuracoes/perfis/editar/<str:nome_perfil>/', views.editar_perfil, name='editar_perfil'),
    path('configuracoes/perfis/excluir/<str:nome_perfil>/', views.excluir_perfil, name='excluir_perfil'),
]