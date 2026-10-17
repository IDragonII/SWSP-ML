from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('usuarios', views.UsuarioViewSet, basename='usuario')
router.register('roles', views.RolViewSet, basename='rol')

urlpatterns = [
    # Autenticación
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', views.RenovarSesionView.as_view(), name='refresh'),
    path('auth/logout/', views.CerrarSesionView.as_view(), name='logout'),
    path('auth/me/', views.DatosSesionView.as_view(), name='me'),
    # Semana 13 (HU-112): cambio de la propia contraseña
    path('auth/cambiar-clave/', views.CambiarClaveView.as_view(), name='cambiar-clave'),
    # Gestión de usuarios (Semana 12; sustituye al endpoint de prueba)
    *router.urls,
]
