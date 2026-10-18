from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("dashboard", views.DashboardViewSet, basename="dashboard")

urlpatterns = [
    *router.urls,
]
