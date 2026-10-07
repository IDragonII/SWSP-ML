from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from . import ratelimit
from .models import Permiso, Rol, RolPermiso, Usuario


@admin.action(description="Desbloquear acceso de los usuarios seleccionados")
def desbloquear_acceso(modeladmin, request, queryset):
    """Desbloqueo manual del login desde el panel (docs/decisiones_seguridad.md §6)."""
    bloqueados = 0
    for usuario in queryset:
        if ratelimit.limpiar_acceso(usuario.username, motivo='manual'):
            bloqueados += 1
    modeladmin.message_user(
        request,
        f"Se procesaron {queryset.count()} usuario(s); {bloqueados} estaban bloqueados.",
    )


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    """Catálogo fijo: solo consulta (lo mantiene el desarrollador)."""

    list_display = ("codigo", "modulo", "accion", "descripcion")
    list_filter = ("modulo", "accion")
    search_fields = ("codigo", "descripcion")
    ordering = ("modulo", "codigo")
    readonly_fields = ("codigo", "modulo", "accion", "descripcion")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "es_sistema", "limita_a_asignados", "activo")
    list_filter = ("es_sistema", "activo", "limita_a_asignados")
    search_fields = ("nombre", "descripcion")
    # filter_horizontal no se puede con 'through' (admin.E013); sí autocomplete.
    autocomplete_fields = ("permisos",)

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.es_sistema:
            campos.append("nombre")
        return campos

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.es_sistema:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ("rol", "permiso")
    list_filter = ("rol", "permiso")
    search_fields = ("rol__nombre", "permiso__codigo")


@admin.register(Usuario)
class UsuarioAdmin(DjangoUserAdmin):
    # groups y user_permissions no existen en nuestro modelo (groups = None),
    # por eso se redefinen fieldsets, add_fieldsets y filter_horizontal.
    list_display = ("username", "email", "rol", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "rol")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = ()
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email", "telefono")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "last_login", "date_joined")}),
        ("Rol", {"fields": ("rol",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "rol", "is_staff", "is_superuser"),
            },
        ),
    )
    actions = (desbloquear_acceso,)


admin.site.site_header = "SIGPA-GA · Administración"
admin.site.site_title = "SIGPA-GA"
admin.site.index_title = "Panel de administración"
