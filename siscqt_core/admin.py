from django.contrib import admin
from .models import Projeto, CenarioConfig, Trecho, CfgCabo, CfgIP, CfgTrafo, CfgPerfil

# --- Inline Admin for related models ---
class CenarioConfigInline(admin.TabularInline):
    model = CenarioConfig
    extra = 1 # Number of empty forms to display
    fields = ['nome_cenario', 'trafo_kva', 'classe_tipo', 'classe_manual', 'fp_ip', 'perfil']
    # You might need to make CfgTrafo and CfgPerfil foreign keys in CenarioConfig
    # to select them directly in admin.
    # For now, it will show their PKs.

class TrechoInline(admin.TabularInline):
    model = Trecho
    extra = 1
    fields = [
        'ponto', 'montante', 'metros', 'cabo', 'mono', 'bi', 'tri', 'tri_esp',
        'carga_esp', 'tipo_ip', 'qtd_ip', 'nome_cenario' # nome_cenario is important for linking
    ]


# --- Model Admins ---
@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data_criacao')
    search_fields = ('nome',)
    list_filter = ('data_criacao',)
    inlines = [CenarioConfigInline] # Manage scenarios directly from project


@admin.register(CenarioConfig)
class CenarioConfigAdmin(admin.ModelAdmin):
    list_display = ('nome_cenario', 'projeto', 'trafo_kva', 'perfil', 'classe_tipo', 'classe_manual')
    list_filter = ('projeto', 'classe_tipo', 'perfil')
    search_fields = ('nome_cenario', 'projeto__nome')
    raw_id_fields = ('projeto',) # For easier selection of related project
    # Removed TrechoInline here


@admin.register(Trecho)
class TrechoAdmin(admin.ModelAdmin):
    list_display = ('ponto', 'montante', 'projeto', 'nome_cenario', 'metros', 'cabo', 'mono', 'bi', 'tri')
    list_filter = ('projeto', 'nome_cenario', 'cabo', 'tipo_ip')
    search_fields = ('ponto', 'montante', 'cabo', 'projeto__nome', 'nome_cenario')
    raw_id_fields = ('projeto',) # nome_cenario is just a charfield, not a foreign key here.

@admin.register(CfgCabo)
class CfgCaboAdmin(admin.ModelAdmin):
    list_display = ('nome', 'coeficiente', 'preco')
    search_fields = ('nome',)

@admin.register(CfgIP)
class CfgIPAdmin(admin.ModelAdmin):
    list_display = ('nome', 'potencia_watts', 'preco')
    search_fields = ('nome',)

@admin.register(CfgTrafo)
class CfgTrafoAdmin(admin.ModelAdmin):
    list_display = ('kva',)
    search_fields = ('kva',)

@admin.register(CfgPerfil)
class CfgPerfilAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cqt_max', 'sobrecarga_max', 'metros_max', 'clientes_max')
    search_fields = ('nome',)