from django.urls import path

from . import views

urlpatterns = [
    # Autenticación
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', views.RenovarSesionView.as_view(), name='refresh'),
    path('auth/logout/', views.CerrarSesionView.as_view(), name='logout'),
    path('auth/me/', views.DatosSesionView.as_view(), name='me'),
    # Usuarios (endpoint de prueba protegido con usuarios.crear)
    path('usuarios/', views.CrearUsuarioView.as_view(), name='crear-usuario'),
]
