"""URLs de la API de campañas (Semana 6)."""
from rest_framework.routers import SimpleRouter

from .views import CampaniaViewSet

router = SimpleRouter()
router.register("campanias", CampaniaViewSet, basename="campania")

urlpatterns = router.urls
