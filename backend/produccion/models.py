from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import Unidad


class Produccion(models.Model):
    """Producción y rendimiento de una campaña (01_tablas.sql:344-362).

    Una sola producción por campaña (UNIQUE en campania). produccion_kg,
    rendimiento_kg_ha, requiere_revision y motivo_revision los calcula
    fn_validar_produccion (migración 0002): lo que mande el cliente se
    sobrescribe. Registrar la producción pasa la campaña de EN_PRODUCCION a
    COSECHADA y fn_produccion_post completa (migración 0003) compara lo
    predicho con lo real en las predicciones de la campaña. «Deshacer
    cosecha» es la única
    excepción al «nada se borra» (Semana 8): elimina la fila mientras la
    campaña no esté CERRADA.

    fn_set_actualizado_en la aporta productores.0002; los umbrales de
    revisión viven en sistema.parametros_sistema.
    """

    CALIDAD_PRIMERA = "PRIMERA"
    CALIDAD_SEGUNDA = "SEGUNDA"
    CALIDAD_TERCERA = "TERCERA"
    CALIDADES = [
        (CALIDAD_PRIMERA, "Primera"),
        (CALIDAD_SEGUNDA, "Segunda"),
        (CALIDAD_TERCERA, "Tercera"),
    ]

    campania = models.OneToOneField(
        Campania,
        on_delete=models.PROTECT,
        related_name="produccion",
        verbose_name="campaña",
        db_index=False,
    )
    fecha_cosecha = models.DateField("fecha de cosecha")
    superficie_cosechada_ha = models.DecimalField(
        "superficie cosechada (ha)", max_digits=8, decimal_places=2
    )
    cantidad_producida = models.DecimalField(
        "cantidad producida", max_digits=12, decimal_places=3
    )
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.PROTECT,
        related_name="producciones",
        verbose_name="unidad",
        db_index=False,
    )
    # Los dos campos siguientes los llena fn_validar_produccion en cada
    # INSERT/UPDATE; el valor que mande el cliente se sobrescribe.
    produccion_kg = models.DecimalField(
        "producción (kg)", max_digits=10, decimal_places=2
    )
    perdida_kg = models.DecimalField(
        "pérdida (kg)", max_digits=10, decimal_places=2, default=0, db_default=0
    )
    calidad = models.CharField(
        "calidad", max_length=15, choices=CALIDADES, null=True, blank=True
    )
    rendimiento_kg_ha = models.DecimalField(
        "rendimiento (kg/ha)", max_digits=10, decimal_places=2
    )
    requiere_revision = models.BooleanField(
        "requiere revisión", default=False, db_default=False
    )
    motivo_revision = models.CharField(
        "motivo de revisión", max_length=200, null=True, blank=True
    )
    incluir_en_entrenamiento = models.BooleanField(
        "incluir en entrenamiento", default=True, db_default=True
    )
    observaciones = models.TextField("observaciones", blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="producciones_registradas",
        verbose_name="registrado por",
        db_index=False,
    )
    creado_en = models.DateTimeField("creado en", default=timezone.now, db_default=Now())
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "producciones"
        verbose_name = "producción"
        verbose_name_plural = "producciones"
        ordering = ("-fecha_cosecha", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(superficie_cosechada_ha__gt=0),
                name="ck_produccion_superficie",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_producida__gte=0),
                name="ck_produccion_cantidad",
            ),
            models.CheckConstraint(
                condition=models.Q(produccion_kg__gte=0),
                name="ck_produccion_kg",
            ),
            models.CheckConstraint(
                condition=models.Q(perdida_kg__gte=0),
                name="ck_produccion_perdida",
            ),
            models.CheckConstraint(
                condition=models.Q(calidad__isnull=True)
                | models.Q(calidad__in=["PRIMERA", "SEGUNDA", "TERCERA"]),
                name="ck_produccion_calidad",
            ),
        ]

    def __str__(self):
        return f"{self.campania} · {self.rendimiento_kg_ha} kg/ha"
