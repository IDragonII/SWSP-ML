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


# Constantes de parcela a nivel de módulo: la clase anidada Meta no puede
# ver los nombres definidos en el cuerpo de Parcela (alcance de clase)
_TIPOS_SUELO = [
    ("ARENOSO", "Arenoso"),
    ("FRANCO", "Franco"),
    ("ARCILLOSO", "Arcilloso"),
    ("OTRO", "Otro"),
]
_PENDIENTES = [
    ("PLANA", "Plana"),
    ("SUAVE", "Suave"),
    ("MODERADA", "Moderada"),
    ("FUERTE", "Fuerte"),
]
_DISPONIBILIDADES_AGUA = [
    ("ESCASA", "Escasa"),
    ("MEDIA", "Media"),
    ("ABUNDANTE", "Abundante"),
]
_SISTEMAS_RIEGO = [
    ("SECANO", "Secano"),
    ("GRAVEDAD", "Gravedad"),
    ("ASPERSION", "Aspersión"),
    ("GOTEO", "Goteo"),
]


class Parcela(models.Model):
    """Terreno de un productor. El código P-001 lo asigna la base de datos
    (trigger trg_parcelas_codigo, migración 0004) y actualizado_en lo
    mantiene trg_parcelas_actualizado (reutiliza fn_set_actualizado_en de la
    migración 0002)."""

    ESTADO_ACTIVA = "ACTIVA"
    ESTADO_INACTIVA = "INACTIVA"
    ESTADOS = [
        (ESTADO_ACTIVA, "Activa"),
        (ESTADO_INACTIVA, "Inactiva"),
    ]

    TIPOS_SUELO = _TIPOS_SUELO
    PENDIENTES = _PENDIENTES
    DISPONIBILIDADES_AGUA = _DISPONIBILIDADES_AGUA
    SISTEMAS_RIEGO = _SISTEMAS_RIEGO

    codigo = models.CharField(
        "código", max_length=15, unique=True, default="", blank=True
    )
    productor = models.ForeignKey(
        Productor,
        on_delete=models.PROTECT,
        related_name="parcelas",
        verbose_name="productor",
        db_index=False,
    )
    comunidad = models.ForeignKey(
        Comunidad,
        on_delete=models.PROTECT,
        related_name="parcelas",
        verbose_name="comunidad",
        db_index=False,
    )
    referencia_ubicacion = models.CharField(
        "referencia de ubicación", max_length=200, null=True, blank=True
    )
    superficie_ha = models.DecimalField("superficie (ha)", max_digits=8, decimal_places=2)
    altitud_msnm = models.IntegerField("altitud (msnm)")
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    tipo_suelo = models.CharField(
        "tipo de suelo", max_length=20, choices=TIPOS_SUELO, null=True, blank=True
    )
    pendiente = models.CharField(
        "pendiente", max_length=15, choices=PENDIENTES, null=True, blank=True
    )
    disponibilidad_agua = models.CharField(
        "disponibilidad de agua",
        max_length=15,
        choices=DISPONIBILIDADES_AGUA,
        null=True,
        blank=True,
    )
    sistema_riego = models.CharField(
        "sistema de riego",
        max_length=20,
        choices=SISTEMAS_RIEGO,
        null=True,
        blank=True,
    )
    estado = models.CharField(
        "estado",
        max_length=10,
        choices=ESTADOS,
        default=ESTADO_ACTIVA,
        db_default=ESTADO_ACTIVA,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parcelas_creadas",
        verbose_name="creado por",
    )
    creado_en = models.DateTimeField(
        "creado en", default=timezone.now, db_default=Now()
    )
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "parcelas"
        verbose_name = "parcela"
        verbose_name_plural = "parcelas"
        ordering = ("codigo",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(superficie_ha__gt=0),
                name="ck_parcelas_superficie",
            ),
            models.CheckConstraint(
                condition=models.Q(altitud_msnm__gte=0, altitud_msnm__lte=6500),
                name="ck_parcelas_altitud",
            ),
            models.CheckConstraint(
                condition=models.Q(latitud__gte=-90, latitud__lte=90),
                name="ck_parcelas_latitud",
            ),
            models.CheckConstraint(
                condition=models.Q(longitud__gte=-180, longitud__lte=180),
                name="ck_parcelas_longitud",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo_suelo__in=[v for v, _ in _TIPOS_SUELO]),
                name="ck_parcelas_tipo_suelo",
            ),
            models.CheckConstraint(
                condition=models.Q(pendiente__in=[v for v, _ in _PENDIENTES]),
                name="ck_parcelas_pendiente",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    disponibilidad_agua__in=[v for v, _ in _DISPONIBILIDADES_AGUA]
                ),
                name="ck_parcelas_disponibilidad_agua",
            ),
            models.CheckConstraint(
                condition=models.Q(sistema_riego__in=[v for v, _ in _SISTEMAS_RIEGO]),
                name="ck_parcelas_sistema_riego",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=["ACTIVA", "INACTIVA"]),
                name="ck_parcelas_estado",
            ),
            # Diseño: las dos coordenadas o ninguna (ck_parcela_coordenadas)
            models.CheckConstraint(
                condition=(
                    models.Q(latitud__isnull=True, longitud__isnull=True)
                    | models.Q(latitud__isnull=False, longitud__isnull=False)
                ),
                name="ck_parcela_coordenadas",
            ),
        ]
        indexes = [
            models.Index(fields=["productor"], name="ix_parcelas_productor"),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.productor}"


class AsignacionTecnico(models.Model):
    """Qué productores ve cada usuario cuyo rol tiene limita_a_asignados.
    Desactivar (activo=false) conserva la fila sin efecto; no se borra nada."""

    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asignaciones",
        verbose_name="técnico",
        db_index=False,
    )
    productor = models.ForeignKey(
        Productor,
        on_delete=models.CASCADE,
        related_name="asignaciones_tecnico",
        verbose_name="productor",
        db_index=False,
    )
    fecha_asignacion = models.DateField(
        "fecha de asignación",
        default=timezone.localdate,
        db_default=Now(),
    )
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "asignaciones_tecnico"
        verbose_name = "asignación de técnico"
        verbose_name_plural = "asignaciones de técnico"
        ordering = ("-fecha_asignacion", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["tecnico", "productor"], name="uq_asignacion"
            ),
        ]
        indexes = [
            # uq_asignacion cubre los filtros por técnico (prefijo)
            models.Index(fields=["productor"], name="ix_asignaciones_productor"),
        ]

    def __str__(self):
        return f"{self.tecnico} → {self.productor}"
