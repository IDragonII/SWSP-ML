from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class Provincia(models.Model):
    """Primer nivel de ubicación: nombre único y estado."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "provincias"
        verbose_name = "provincia"
        verbose_name_plural = "provincias"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class Distrito(models.Model):
    """Segundo nivel de ubicación: pertenece a una provincia (uq_distrito)."""

    provincia = models.ForeignKey(
        Provincia,
        on_delete=models.PROTECT,
        related_name="distritos",
        verbose_name="provincia",
        db_index=False,
    )
    nombre = models.CharField("nombre", max_length=80)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "distritos"
        verbose_name = "distrito"
        verbose_name_plural = "distritos"
        ordering = ("nombre",)
        constraints = [
            models.UniqueConstraint(
                fields=["provincia", "nombre"], name="uq_distrito"
            ),
        ]
        indexes = [
            models.Index(fields=["provincia"], name="ix_distritos_provincia"),
        ]

    def __str__(self):
        return self.nombre


class Comunidad(models.Model):
    """Tercer nivel de ubicación: pertenece a un distrito (uq_comunidad)."""

    distrito = models.ForeignKey(
        Distrito,
        on_delete=models.PROTECT,
        related_name="comunidades",
        verbose_name="distrito",
        db_index=False,
    )
    nombre = models.CharField("nombre", max_length=100)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "comunidades"
        verbose_name = "comunidad"
        verbose_name_plural = "comunidades"
        ordering = ("nombre",)
        constraints = [
            models.UniqueConstraint(
                fields=["distrito", "nombre"], name="uq_comunidad"
            ),
        ]
        indexes = [
            models.Index(fields=["distrito"], name="ix_comunidades_distrito"),
        ]

    def __str__(self):
        return self.nombre


class Productor(models.Model):
    """Ficha base del productor. El código PROD-000N lo asigna la BD
    (trigger trg_productores_codigo, migración 0002) y actualizado_en lo
    mantiene el trigger trg_productores_actualizado."""

    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_INACTIVO = "INACTIVO"
    ESTADOS = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    codigo = models.CharField(
        "código", max_length=12, unique=True, default="", blank=True
    )
    nombres = models.CharField("nombres", max_length=100)
    apellidos = models.CharField("apellidos", max_length=100)
    dni = models.CharField("DNI", max_length=8, unique=True)
    telefono = models.CharField("teléfono", max_length=15, null=True, blank=True)
    comunidad = models.ForeignKey(
        Comunidad,
        on_delete=models.PROTECT,
        related_name="productores",
        verbose_name="comunidad",
        db_index=False,
    )
    referencia_ubicacion = models.CharField(
        "referencia de ubicación", max_length=200, null=True, blank=True
    )
    fecha_incorporacion = models.DateField(
        "fecha de incorporación",
        default=timezone.localdate,
        db_default=Now(),
    )
    estado = models.CharField(
        "estado",
        max_length=10,
        choices=ESTADOS,
        default=ESTADO_ACTIVO,
        db_default=ESTADO_ACTIVO,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productores_creados",
        verbose_name="creado por",
    )
    creado_en = models.DateTimeField(
        "creado en", default=timezone.now, db_default=Now()
    )
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "productores"
        verbose_name = "productor"
        verbose_name_plural = "productores"
        ordering = ("apellidos", "nombres")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(dni__regex=r"^[0-9]{8}$"),
                name="ck_productores_dni",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=["ACTIVO", "INACTIVO"]),
                name="ck_productores_estado",
            ),
        ]
        indexes = [
            models.Index(fields=["comunidad"], name="ix_productores_comunidad"),
            models.Index(fields=["estado"], name="ix_productores_estado"),
            models.Index(
                fields=["apellidos", "nombres"], name="ix_productores_apellidos"
            ),
        ]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres}"
