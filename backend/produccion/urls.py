"""URLs de la API de producciones (Semana 8)."""
from rest_framework.routers import SimpleRouter

from .views import ProduccionViewSet

router = SimpleRouter()
router.register("producciones", ProduccionViewSet, basename="produccion")

urlpatterns = router.urls
