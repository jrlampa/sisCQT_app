from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjetoViewSet,
    CenarioViewSet,
    TrechoViewSet,
    CfgCaboViewSet,
    CfgIPViewSet,
    CfgTrafoViewSet,
    CfgPerfilViewSet,
)

router = DefaultRouter()
router.register(r'projetos', ProjetoViewSet)
router.register(r'cenarios', CenarioViewSet)
router.register(r'trechos', TrechoViewSet) # Added TrechoViewSet
router.register(r'cabos', CfgCaboViewSet)
router.register(r'ips', CfgIPViewSet)
router.register(r'trafos', CfgTrafoViewSet)
router.register(r'perfis', CfgPerfilViewSet)

app_name = 'siscqt_core'

urlpatterns = [
    path('', include(router.urls)),
]
