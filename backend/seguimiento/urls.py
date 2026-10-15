"""URLs de la API de seguimiento (Semanas 7, 9 y 10)."""
from rest_framework.routers import SimpleRouter

from .views import ActividadViewSet, ClimaViewSet, UsoRecursoViewSet

router = SimpleRouter()
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("usos-recursos", UsoRecursoViewSet, basename="uso-recurso")
router.register("clima", ClimaViewSet, basename="clima")

urlpatterns = router.urls
