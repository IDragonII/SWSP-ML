"""URLs de la API de parámetros del sistema (Semana 8)."""
from rest_framework.routers import SimpleRouter

from .views import ParametroViewSet

router = SimpleRouter()
router.register("parametros", ParametroViewSet, basename="parametro")

urlpatterns = router.urls
