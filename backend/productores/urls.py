"""URLs de la API de ubicación y productores (montadas bajo /api/)."""
from rest_framework.routers import SimpleRouter

from .views import (
    ComunidadViewSet,
    DistritoViewSet,
    ProductorViewSet,
    ProvinciaViewSet,
)

router = SimpleRouter()
router.register("ubicaciones/provincias", ProvinciaViewSet, basename="provincia")
router.register("ubicaciones/distritos", DistritoViewSet, basename="distrito")
router.register("ubicaciones/comunidades", ComunidadViewSet, basename="comunidad")
router.register("productores", ProductorViewSet, basename="productor")

urlpatterns = router.urls
