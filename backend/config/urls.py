"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
import os

# Ruta del panel de Django: configurable con ADMIN_URL en el .env (Semana 19)
# para no anunciar /admin/ en producción; siempre con barra final.
ADMIN_URL = os.getenv("ADMIN_URL", "admin/")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('api/', include('usuarios.urls')),
    path('api/', include('productores.urls')),
    path('api/', include('catalogos.urls')),
    path('api/', include('campanias.urls')),
    path('api/', include('seguimiento.urls')),
    path('api/', include('produccion.urls')),
    path('api/', include('sistema.urls')),
    path('api/', include('auditoria.urls')),
    path('api/', include('alertas.urls')),
    path('api/', include('dashboard.urls')),
    path('api/', include('reportes.urls')),
    path('api/', include('ml.urls')),
]
