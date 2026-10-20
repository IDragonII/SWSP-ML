from django.contrib import admin

from .models import EntrenamientoML, ModeloML, Prediccion

# El admin solo consulta: los alta los dan el comando registrar_modelo
# (HU-171), la activación la API (HU-172) y las predicciones el
# servicio (HU-173). Ninguna de las tres se crea, edita ni borra aquí
# (decisiones 220 y 232).


@admin.register(EntrenamientoML)
class EntrenamientoMLAdmin(admin.ModelAdmin):
    list_display = ("fecha", "n_registros", "n_entrenamiento", "ejecutado_por")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ModeloML)
class ModeloMLAdmin(admin.ModelAdmin):
    list_display = ("algoritmo", "version", "activo", "mae", "rmse", "r2")
    list_filter = ("algoritmo", "activo")
    search_fields = ("version",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Prediccion)
class PrediccionAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "campania",
        "modelo",
        "rendimiento_predicho",
        "rendimiento_real",
        "error_abs",
    )
    list_filter = ("modelo",)
    date_hierarchy = "fecha"
    ordering = ("-fecha",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
