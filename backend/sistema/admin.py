from django.contrib import admin

from .models import ParametroSistema


@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ("clave", "valor", "actualizado_en")
    search_fields = ("clave", "descripcion")
    # Las claves son fijas (Semana 8): se consultan y se editan valores,
    # no se crean ni se borran filas desde la administración.
    readonly_fields = ("clave", "actualizado_en")
