# siscqt_core/forms.py
from django import forms
from .models import CenarioConfig, CfgTrafo, CfgPerfil, CfgCabo, CfgIP, Projeto
from .siscqt_constantes import DEFAULT_PARAMS

class ExcelUploadForm(forms.Form):
    project_name = forms.CharField(max_length=255, label="Nome do Projeto",
                                   help_text="Nome único para o novo projeto.")
    excel_file = forms.FileField(label="Selecione o arquivo Excel (.xls/.xlsx)",
                                 help_text="Envie a planilha da concessionária.")

class CenarioConfigForm(forms.ModelForm):
    # Override fields to use dynamic choices for trafo_kva and perfil
    trafo_kva = forms.ModelChoiceField(
        queryset=CfgTrafo.objects.all().order_by('kva'),
        to_field_name='kva',
        empty_label="Selecione um Trafo",
        required=False,
        label="Trafo kVA"
    )
    perfil = forms.ModelChoiceField(
        queryset=CfgPerfil.objects.all().order_by('nome'),
        to_field_name='nome',
        empty_label="Selecione um Perfil",
        required=False,
        label="Perfil"
    )

    class Meta:
        model = CenarioConfig
        fields = ['nome_cenario', 'trafo_kva', 'classe_tipo', 'classe_manual', 'fp_ip', 'perfil']
        widgets = {
            'nome_cenario': forms.TextInput(attrs={'placeholder': 'Nome do Cenário'}),
            'classe_tipo': forms.Select(choices=[('Automático', 'Automático'), ('Manual', 'Manual')]),
            'classe_manual': forms.Select(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]),
            'fp_ip': forms.NumberInput(attrs={'step': '0.01', 'min': '0.0', 'max': '1.0'}),
        }
        labels = {
            'nome_cenario': "Nome do Cenário",
            'classe_tipo': "Classe de Demanda (Tipo)",
            'classe_manual': "Classe de Demanda (Manual)",
            'fp_ip': "Fator de Potência IP",
        }
        help_texts = {
            'nome_cenario': "Nome que identifica este cenário dentro do projeto.",
            'trafo_kva': "Potência do transformador associado a este cenário.",
            'classe_tipo': "Escolha como a classe de demanda será definida.",
            'classe_manual': "Se 'Manual', selecione a classe.",
            'fp_ip': "Fator de potência para cargas de iluminação pública.",
            'perfil': "Perfil de carregamento e limites para este cenário.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for ModelChoiceFields if instance exists, as ModelChoiceField
        # can sometimes struggle with initial value for objects that are primary keys (kva, nome)
        if self.instance and self.instance.pk:
            if self.instance.trafo_kva:
                self.initial['trafo_kva'] = self.instance.trafo_kva
            if self.instance.perfil:
                self.initial['perfil'] = self.instance.perfil
        
        # Ensure 'Manual' is selected if 'classe_manual' has a value
        if self.initial.get('classe_manual') and not self.initial.get('classe_tipo'):
            self.initial['classe_tipo'] = 'Manual'
        elif not self.initial.get('classe_tipo'):
             self.initial['classe_tipo'] = 'Automático' # Default to Automatic

        # Hide classe_manual if classe_tipo is Automatic
        if self.data.get('classe_tipo') == 'Automático' or (self.instance and self.instance.classe_tipo == 'Automático' and not self.data):
            self.fields['classe_manual'].required = False
            self.fields['classe_manual'].widget.attrs['style'] = 'display:none;'
        else:
            self.fields['classe_manual'].required = True

        # Dynamic queryset for CfgTrafo and CfgPerfil to ensure they are available
        self.fields['trafo_kva'].queryset = CfgTrafo.objects.all().order_by('kva')
        self.fields['perfil'].queryset = CfgPerfil.objects.all().order_by('nome')


class CfgCaboForm(forms.ModelForm):
    class Meta:
        model = CfgCabo
        fields = ['nome', 'coeficiente', 'preco']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do Cabo'}),
            'coeficiente': forms.NumberInput(attrs={'step': '0.0001'}),
            'preco': forms.NumberInput(attrs={'step': '0.01'}),
        }
        labels = {
            'nome': "Nome",
            'coeficiente': "Coeficiente",
            'preco': "Preço (R$)",
        }

class CfgIPForm(forms.ModelForm):
    class Meta:
        model = CfgIP
        fields = ['nome', 'potencia_watts', 'preco']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do IP'}),
            'potencia_watts': forms.NumberInput(attrs={'step': '0.1'}),
            'preco': forms.NumberInput(attrs={'step': '0.01'}),
        }
        labels = {
            'nome': "Nome",
            'potencia_watts': "Potência (Watts)",
            'preco': "Preço (R$)",
        }

class CfgTrafoForm(forms.ModelForm):
    class Meta:
        model = CfgTrafo
        fields = ['kva']
        widgets = {
            'kva': forms.NumberInput(attrs={'step': '0.1'}),
        }
        labels = {
            'kva': "KVA do Trafo",
        }

class CfgPerfilForm(forms.ModelForm):
    class Meta:
        model = CfgPerfil
        fields = ['nome', 'cqt_max', 'sobrecarga_max', 'metros_max', 'clientes_max']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do Perfil'}),
            'cqt_max': forms.NumberInput(attrs={'step': '0.1'}),
            'sobrecarga_max': forms.NumberInput(attrs={'step': '0.1'}),
            'metros_max': forms.NumberInput(attrs={'step': '0.1'}),
            'clientes_max': forms.NumberInput(attrs={'step': '1'}),
        }
        labels = {
            'nome': "Nome",
            'cqt_max': "CQT Máx (%)",
            'sobrecarga_max': "Sobrecarga Máx (%)",
            'metros_max': "Metros Máx (m)",
            'clientes_max': "Clientes Máx",
        }

class CriarCenarioForm(forms.Form):
    nome_cenario = forms.CharField(max_length=255, label="Nome do Novo Cenário")
    # This field will be populated dynamically in the view based on the project_id
    copy_from_cenario = forms.ModelChoiceField(
        queryset=CenarioConfig.objects.none(),  # Will be set in __init__
        required=False,
        empty_label="Criar Cenário Em Branco",
        label="Copiar de um Cenário Existente"
    )

    def __init__(self, *args, **kwargs):
        projeto_id = kwargs.pop('projeto_id', None)
        super().__init__(*args, **kwargs)
        if projeto_id:
            self.fields['copy_from_cenario'].queryset = CenarioConfig.objects.filter(projeto_id=projeto_id)