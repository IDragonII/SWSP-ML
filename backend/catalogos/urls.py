"""URLs de la API de catálogos (Semana 5)."""
from rest_framework.routers import SimpleRouter

from .views import (
    AgenteViewSet,
    CultivoViewSet,
    EtapaViewSet,
    RecursoViewSet,
    TipoActividadViewSet,
    TipoIncidenciaViewSet,
    UnidadViewSet,
    VariedadViewSet,
)

router = SimpleRouter()
router.register("cultivos", CultivoViewSet, basename="cultivo")
router.register("variedades", VariedadViewSet, basename="variedad")
router.register("etapas-fenologicas", EtapaViewSet, basename="etapa")
router.register("unidades", UnidadViewSet, basename="unidad")
router.register("tipos-actividad", TipoActividadViewSet, basename="tipo-actividad")
router.register("recursos", RecursoViewSet, basename="recurso")
router.register("tipos-incidencia", TipoIncidenciaViewSet, basename="tipo-incidencia")
router.register("agentes", AgenteViewSet, basename="agente")

urlpatterns = router.urls
