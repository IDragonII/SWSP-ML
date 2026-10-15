"""URLs de la API de seguimiento (Semanas 7, 9, 10 y 11)."""
from rest_framework.routers import SimpleRouter

from .views import (
    ActividadViewSet,
    ClimaViewSet,
    IncidenciaViewSet,
    UsoRecursoViewSet,
)

router = SimpleRouter()
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("usos-recursos", UsoRecursoViewSet, basename="uso-recurso")
router.register("clima", ClimaViewSet, basename="clima")
router.register("incidencias", IncidenciaViewSet, basename="incidencia")

urlpatterns = router.urls
