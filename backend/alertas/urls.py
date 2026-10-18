from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("alertas", views.AlertasViewSet, basename="alertas")

urlpatterns = [
    *router.urls,
]
