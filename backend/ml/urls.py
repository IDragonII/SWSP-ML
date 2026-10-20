"""URLs de la API de Machine Learning (Sprint 14, S22).

Cuatro recursos bajo /api/ (decisión 235): predicciones (historial y
predicción), modelos (métricas y activar), modelo-activo (banner) y
campanas-predecibles (selector de la pantalla Predicción).
"""
from rest_framework.routers import SimpleRouter

from .views import (
    CampaniaPredecibleViewSet,
    ModeloActivoViewSet,
    ModeloViewSet,
    PrediccionViewSet,
)

router = SimpleRouter()
router.register("ml/predicciones", PrediccionViewSet, basename="ml-prediccion")
router.register("ml/modelos", ModeloViewSet, basename="ml-modelo")
router.register(
    "ml/modelo-activo", ModeloActivoViewSet, basename="ml-modelo-activo"
)
router.register(
    "ml/campanas-predecibles", CampaniaPredecibleViewSet,
    basename="ml-campania-predecible",
)

urlpatterns = router.urls
