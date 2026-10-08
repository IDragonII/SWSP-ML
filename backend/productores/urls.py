"""URLs de la API de ubicación, productores, parcelas y asignaciones."""
from rest_framework.routers import SimpleRouter

from .views import (
    AsignacionViewSet,
    ComunidadViewSet,
    DistritoViewSet,
    ParcelaViewSet,
    ProductorViewSet,
    ProvinciaViewSet,
)

router = SimpleRouter()
router.register("ubicaciones/provincias", ProvinciaViewSet, basename="provincia")
router.register("ubicaciones/distritos", DistritoViewSet, basename="distrito")
router.register("ubicaciones/comunidades", ComunidadViewSet, basename="comunidad")
router.register("productores", ProductorViewSet, basename="productor")
router.register("parcelas", ParcelaViewSet, basename="parcela")
router.register("asignaciones", AsignacionViewSet, basename="asignacion")

urlpatterns = router.urls
