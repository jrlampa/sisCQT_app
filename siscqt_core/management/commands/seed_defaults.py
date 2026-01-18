# siscqt_core/management/commands/seed_defaults.py
from django.core.management.base import BaseCommand
from siscqt_core.models import CfgPerfil, CfgCabo, CfgIP, CfgTrafo
from siscqt_core.siscqt_constantes import (
    DEFAULT_PERFIS,
    DEFAULT_CABOS_DATA,
    DEFAULT_IPS,
    DEFAULT_TRAFOS_LISTA,
)

class Command(BaseCommand):
    help = 'Seeds the database with default configuration data (Cabos, IPs, Trafos, Perfis).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding default configuration data..."))

        # Seed CfgPerfil
        if not CfgPerfil.objects.exists():
            for perfil_data in DEFAULT_PERFIS:
                CfgPerfil.objects.create(
                    nome=perfil_data[0],
                    cqt_max=perfil_data[1],
                    sobrecarga_max=perfil_data[2],
                    metros_max=perfil_data[3],
                    clientes_max=perfil_data[4]
                )
            self.stdout.write(self.style.SUCCESS("Default CfgPerfis seeded successfully."))
        else:
            self.stdout.write(self.style.NOTICE("CfgPerfis already exist, skipping seeding."))

        # Seed CfgCabo
        if not CfgCabo.objects.exists():
            for nome, data in DEFAULT_CABOS_DATA.items():
                CfgCabo.objects.create(
                    nome=nome,
                    coeficiente=data[0],
                    preco=0.0 # Default preco is 0.0 in DB, not present in DEFAULT_CABOS_DATA
                )
            self.stdout.write(self.style.SUCCESS("Default CfgCabos seeded successfully."))
        else:
            self.stdout.write(self.style.NOTICE("CfgCabos already exist, skipping seeding."))

        # Seed CfgIP
        if not CfgIP.objects.exists():
            for nome, potencia_watts in DEFAULT_IPS.items():
                CfgIP.objects.create(
                    nome=nome,
                    potencia_watts=potencia_watts,
                    preco=0.0 # Default preco is 0.0 in DB
                )
            self.stdout.write(self.style.SUCCESS("Default CfgIPs seeded successfully."))
        else:
            self.stdout.write(self.style.NOTICE("CfgIPs already exist, skipping seeding."))

        # Seed CfgTrafo
        if not CfgTrafo.objects.exists():
            for kva in DEFAULT_TRAFOS_LISTA:
                CfgTrafo.objects.create(kva=kva)
            self.stdout.write(self.style.SUCCESS("Default CfgTrafos seeded successfully."))
        else:
            self.stdout.write(self.style.NOTICE("CfgTrafos already exist, skipping seeding."))

        self.stdout.write(self.style.SUCCESS("Default data seeding process finished."))
