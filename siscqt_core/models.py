# C:\myworld\sisCQT_app\siscqt_core\models.py
from django.db import models

class Projeto(models.Model):
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome do Projeto")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ['-data_criacao']

    def __str__(self):
        return self.nome

class CenarioConfig(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='cenarios')
    nome_cenario = models.CharField(max_length=255, verbose_name="Nome do Cenário")
    trafo_kva = models.IntegerField(null=True, blank=True, verbose_name="Trafo kVA")
    classe_tipo = models.CharField(max_length=255, null=True, blank=True, verbose_name="Classe Tipo")
    classe_manual = models.CharField(max_length=255, null=True, blank=True, verbose_name="Classe Manual")
    fp_ip = models.FloatField(default=0.92, verbose_name="FP IP")
    perfil = models.CharField(max_length=255, default='Padrão (Urbano)', verbose_name="Perfil")

    class Meta:
        verbose_name = "Configuração de Cenário"
        verbose_name_plural = "Configurações de Cenários"
        unique_together = ('projeto', 'nome_cenario')

    def __str__(self):
        return f"{self.projeto.nome} - {self.nome_cenario}"

class Trecho(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='trechos')
    nome_cenario = models.CharField(max_length=255, verbose_name="Nome do Cenário")
    ponto = models.CharField(max_length=255, verbose_name="Ponto")
    montante = models.CharField(max_length=255, null=True, blank=True, verbose_name="Montante")
    metros = models.FloatField(null=True, blank=True, verbose_name="Metros")
    cabo = models.CharField(max_length=255, null=True, blank=True, verbose_name="Cabo")
    mono = models.IntegerField(default=0, verbose_name="Mono")
    bi = models.IntegerField(default=0, verbose_name="Bi")
    tri = models.IntegerField(default=0, verbose_name="Tri")
    tri_esp = models.IntegerField(default=0, verbose_name="Tri Especial")
    carga_esp = models.FloatField(null=True, blank=True, verbose_name="Carga Específica")
    tipo_ip = models.CharField(max_length=255, null=True, blank=True, verbose_name="Tipo IP")
    qtd_ip = models.IntegerField(default=0, verbose_name="Quantidade IP")

    class Meta:
        verbose_name = "Trecho"
        verbose_name_plural = "Trechos"
        unique_together = ('projeto', 'nome_cenario', 'ponto')
        indexes = [
            models.Index(fields=['projeto', 'nome_cenario']),
        ]

    def __str__(self):
        return f"{self.projeto.nome} - {self.nome_cenario} - {self.ponto}"

class CfgCabo(models.Model):
    nome = models.CharField(max_length=255, primary_key=True, verbose_name="Nome do Cabo")
    coeficiente = models.FloatField(verbose_name="Coeficiente")
    preco = models.FloatField(default=0.0, verbose_name="Preço")

    class Meta:
        verbose_name = "Configuração de Cabo"
        verbose_name_plural = "Configurações de Cabos"

    def __str__(self):
        return self.nome

class CfgIP(models.Model):
    nome = models.CharField(max_length=255, primary_key=True, verbose_name="Nome do IP")
    potencia_watts = models.FloatField(verbose_name="Potência (Watts)")
    preco = models.FloatField(default=0.0, verbose_name="Preço")

    class Meta:
        verbose_name = "Configuração de IP"
        verbose_name_plural = "Configurações de IPs"

    def __str__(self):
        return self.nome

class CfgTrafo(models.Model):
    kva = models.FloatField(primary_key=True, verbose_name="KVA do Trafo")

    class Meta:
        verbose_name = "Configuração de Trafo"
        verbose_name_plural = "Configurações de Trafos"

    def __str__(self):
        return f"{self.kva} kVA"

class CfgPerfil(models.Model):
    nome = models.CharField(max_length=255, primary_key=True, verbose_name="Nome do Perfil")
    cqt_max = models.FloatField(null=True, blank=True, verbose_name="CQT Máximo")
    sobrecarga_max = models.FloatField(null=True, blank=True, verbose_name="Sobrecarga Máxima")
    metros_max = models.FloatField(null=True, blank=True, verbose_name="Metros Máximos")
    clientes_max = models.IntegerField(null=True, blank=True, verbose_name="Clientes Máximos")

    class Meta:
        verbose_name = "Configuração de Perfil"
        verbose_name_plural = "Configurações de Perfis"

    def __str__(self):
        return self.nome