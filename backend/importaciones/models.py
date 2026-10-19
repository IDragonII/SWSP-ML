from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

TIPOS = [
    ("PRODUCTORES", "Productores"),
    ("PARCELAS", "Parcelas"),
    ("CAMPANIAS", "Campañas"),
    ("PRODUCCION", "Producción"),
]

ESTADOS = [
    ("EN_PROCESO", "En proceso"),
    ("COMPLETADA", "Completada"),
    ("CON_ERRORES", "Con errores"),
]


class Importacion(models.Model):
    """Registro de una ejecución del comando importar_historico (S20, RF-49/50).

    Una fila por ejecución completa (un tipo de archivo por ejecución):
    archivo, conteos y el informe de errores por fila en detalle_errores
    (JSONB, sin datos personales: el DNI va enmascarado). El estado nace
    EN_PROCESO; una ejecución interrumpida se marca CON_ERRORES y solo
    puede haber una EN_PROCESO a la vez (lo comprueba el comando). El
    diseño la define en 01_tablas.sql:457; tipo conserva PRODUCCION
    aunque el comando de la S20 solo implemente los tres tipos de la
    fase histórica (decisión: sin campos nuevos respecto al diseño).
    """

    TIPOS = TIPOS
    ESTADOS = ESTADOS

    archivo = models.CharField("archivo", max_length=200)
    tipo = models.CharField("tipo", max_length=20, choices=TIPOS)
    fecha = models.DateTimeField(
        "fecha", default=timezone.now, db_default=Now()
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importaciones",
        db_index=False,
        verbose_name="usuario",
    )
    filas_totales = models.PositiveIntegerField("filas totales", default=0)
    filas_ok = models.PositiveIntegerField("filas correctas", default=0)
    filas_error = models.PositiveIntegerField("filas con error", default=0)
    detalle_errores = models.JSONField("detalle de errores", null=True, blank=True)
    estado = models.CharField(
        "estado",
        max_length=15,
        choices=ESTADOS,
        default="EN_PROCESO",
        db_default="EN_PROCESO",
    )

    class Meta:
        db_table = "importaciones"
        verbose_name = "importación"
        verbose_name_plural = "importaciones"
        ordering = ("-fecha", "-id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    ("tipo__in", tuple(t[0] for t in TIPOS))
                ),
                name="ck_importacion_tipo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    ("estado__in", tuple(e[0] for e in ESTADOS))
                ),
                name="ck_importacion_estado",
            ),
            models.CheckConstraint(
                condition=models.Q(filas_totales__gte=0),
                name="ck_importacion_totales",
            ),
        ]
        indexes = [
            models.Index(fields=["fecha"], name="ix_importaciones_fecha"),
            models.Index(fields=["tipo"], name="ix_importaciones_tipo"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.archivo} · {self.estado}"
