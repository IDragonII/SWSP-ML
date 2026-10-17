"""URLs de la API de seguimiento (Semanas 7, 9, 10, 11 y 12)."""
from rest_framework.routers import SimpleRouter

from .views import (
    ActividadViewSet,
    ClimaViewSet,
    EtapaCampaniaViewSet,
    IncidenciaViewSet,
    UsoRecursoViewSet,
)

router = SimpleRouter()
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("usos-recursos", UsoRecursoViewSet, basename="uso-recurso")
router.register("clima", ClimaViewSet, basename="clima")
router.register("incidencias", IncidenciaViewSet, basename="incidencia")
router.register("etapas-campania", EtapaCampaniaViewSet, basename="etapa-campania")

urlpatterns = router.urls
