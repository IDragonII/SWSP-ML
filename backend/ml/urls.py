"""URLs de la API de Machine Learning (Sprint 14, S22, S23).

Seis recursos bajo /api/ (decisión 235 ampliada por la 263):
predicciones (historial y predicción), modelos (métricas, columnas de
BD y activar), modelo-activo (banner), campanas-predecibles (selector
de la pantalla Predicción), estado-datos (¿hay datos para entrenar?) y
entrenamientos (historial, alta, cancelación y resultados).
"""
from rest_framework.routers import SimpleRouter

from .views import (
    CampaniaPredecibleViewSet,
    EstadoDatosViewSet,
    ModeloActivoViewSet,
    ModeloViewSet,
    PrediccionViewSet,
    TareaEntrenamientoViewSet,
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
router.register(
    "ml/estado-datos", EstadoDatosViewSet, basename="ml-estado-datos"
)
router.register(
    "ml/entrenamientos", TareaEntrenamientoViewSet,
    basename="ml-entrenamiento",
)

urlpatterns = router.urls
