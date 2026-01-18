from rest_framework import serializers
from .models import Projeto, CenarioConfig, Trecho, CfgCabo, CfgIP, CfgTrafo, CfgPerfil

class CenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenarioConfig
        fields = '__all__'

class ProjetoSerializer(serializers.ModelSerializer):
    cenarios = CenarioSerializer(many=True, read_only=True)

    class Meta:
        model = Projeto
        fields = ['id', 'nome', 'data_criacao', 'cenarios']

class TrechoSerializer(serializers.ModelSerializer):
    # To correctly link to Projeto model, you might need to provide project_id or use a SlugRelatedField
    # For simplicity, we'll expose projeto as its ID and handle nome_cenario as a direct field
    projeto = serializers.PrimaryKeyRelatedField(queryset=Projeto.objects.all())

    class Meta:
        model = Trecho
        fields = '__all__'

class CfgCaboSerializer(serializers.ModelSerializer):
    class Meta:
        model = CfgCabo
        fields = '__all__'

class CfgIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = CfgIP
        fields = '__all__'

class CfgTrafoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CfgTrafo
        fields = '__all__'

class CfgPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = CfgPerfil
        fields = '__all__'
