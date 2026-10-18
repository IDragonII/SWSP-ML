from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("reportes", views.ReportesViewSet, basename="reportes")

urlpatterns = [
    *router.urls,
]
