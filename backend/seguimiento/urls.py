"""URLs de la API de actividades (Semana 7)."""
from rest_framework.routers import SimpleRouter

from .views import ActividadViewSet

router = SimpleRouter()
router.register("actividades", ActividadViewSet, basename="actividad")

urlpatterns = router.urls
