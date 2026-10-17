from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class Permiso(models.Model):
    """Catálogo fijo de acciones permitidas (lo mantiene el desarrollador)."""

    codigo = models.CharField("código", max_length=60, unique=True)
    modulo = models.CharField("módulo", max_length=40)
    accion = models.CharField("acción", max_length=30)
    descripcion = models.CharField("descripción", max_length=150, null=True, blank=True)

    class Meta:
        db_table = "permisos"
        verbose_name = "permiso"
        verbose_name_plural = "permisos"
        ordering = ("modulo", "codigo")

    def __str__(self):
        return self.codigo


class Rol(models.Model):
    """Conjunto de permisos. Los del sistema no se pueden eliminar."""

    nombre = models.CharField("nombre", max_length=50, unique=True)
    descripcion = models.CharField("descripción", max_length=200, null=True, blank=True)
    es_sistema = models.BooleanField("es de sistema", default=False, db_default=False)
    limita_a_asignados = models.BooleanField(
        "limita a asignados", default=False, db_default=False
    )
    activo = models.BooleanField("activo", default=True, db_default=True)
    permisos = models.ManyToManyField(
        Permiso, through="RolPermiso", related_name="roles", verbose_name="permisos"
    )

    class Meta:
        db_table = "roles"
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class RolPermiso(models.Model):
    """Asignación de un permiso a un rol (uq_rol_permiso evita repetirlo)."""

    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)

    class Meta:
        db_table = "roles_permisos"
        verbose_name = "permiso de rol"
        verbose_name_plural = "permisos de rol"
        constraints = [
            models.UniqueConstraint(fields=["rol", "permiso"], name="uq_rol_permiso")
        ]

    def __str__(self):
        return f"{self.rol} → {self.permiso}"


class Usuario(AbstractUser):
    """Cuenta del sistema con rol obligatorio (hereda las 8 columnas de Django)."""

    telefono = models.CharField(
        "teléfono", max_length=15, blank=True, default="", db_default=""
    )
    debe_cambiar_clave = models.BooleanField(
        "debe cambiar contraseña", default=False, db_default=False
    )
    rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, related_name="usuarios", verbose_name="rol"
    )

    # Los permisos y grupos propios de Django no se usan: hay roles propios.
    groups = None
    user_permissions = None

    # Overrides para igualar los DEFAULT de 01_tablas.sql
    first_name = models.CharField(
        "nombres", max_length=150, blank=True, default="", db_default=""
    )
    last_name = models.CharField(
        "apellidos", max_length=150, blank=True, default="", db_default=""
    )
    email = models.EmailField(
        "correo", max_length=254, blank=True, default="", db_default=""
    )
    is_superuser = models.BooleanField(
        "superusuario", default=False, db_default=False
    )
    is_staff = models.BooleanField("es del personal", default=False, db_default=False)
    is_active = models.BooleanField("activo", default=True, db_default=True)
    date_joined = models.DateTimeField(
        "fecha de alta", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
