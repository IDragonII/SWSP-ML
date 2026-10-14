"""URLs de la API de seguimiento (Semanas 7 y 9)."""
from rest_framework.routers import SimpleRouter

from .views import ActividadViewSet, UsoRecursoViewSet

router = SimpleRouter()
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("usos-recursos", UsoRecursoViewSet, basename="uso-recurso")

urlpatterns = router.urls
