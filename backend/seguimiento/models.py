from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import TipoActividad


class Actividad(models.Model):
    """Actividad productiva registrada sobre una campaña (01_tablas.sql:270-286).

    Una fila por acción ejecutada (preparación, siembra, aplicación…). La
    densidad de siembra solo aplica al tipo SIEMBRA: el par valor+unidad es
    obligatorio o vacío (ck_actividad_densidad). La anulación es «borrado
    lógico» (decisión de la Semana 7): no borra filas porque la traza debe
    conservarse y el dataset de entrenamiento las excluye. Al anular o
    reactivar, fn_actividad_siembra recalcula campanias.fecha_siembra.

    fn_validar_fecha_campania y fn_actividad_siembra las instala la migración
    0002 (triggers trg_actividades_fecha, trg_actividades_siembra y
    trg_actividades_actualizado); fn_set_actualizado_en la aporta
    productores.0002.
    """

    UNIDAD_KG_HA = "KG_HA"
    UNIDAD_PLANTAS_M2 = "PLANTAS_M2"
    UNIDADES_DENSIDAD = [
        (UNIDAD_KG_HA, "kg/ha"),
        (UNIDAD_PLANTAS_M2, "plantas/m²"),
    ]

    campania = models.ForeignKey(
        Campania,
        on_delete=models.CASCADE,
        related_name="actividades",
        verbose_name="campaña",
        db_index=False,
    )
    tipo_actividad = models.ForeignKey(
        TipoActividad,
        on_delete=models.PROTECT,
        related_name="actividades",
        verbose_name="tipo de actividad",
        db_index=False,
    )
    fecha = models.DateField("fecha")
    metodo = models.CharField("método", max_length=100, blank=True)
    densidad_siembra = models.DecimalField(
        "densidad de siembra", max_digits=10, decimal_places=2, null=True, blank=True
    )
    densidad_unidad = models.CharField(
        "unidad de densidad",
        max_length=10,
        choices=UNIDADES_DENSIDAD,
        null=True,
        blank=True,
    )
    horas = models.DecimalField(
        "horas", max_digits=5, decimal_places=1, null=True, blank=True
    )
    costo = models.DecimalField(
        "costo", max_digits=10, decimal_places=2, null=True, blank=True
    )
    observaciones = models.TextField("observaciones", blank=True)
    anulada = models.BooleanField("anulada", default=False, db_default=False)
    motivo_anulacion = models.TextField(
        "motivo de anulación", null=True, blank=True
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades_registradas",
        verbose_name="registrado por",
        db_index=False,
    )
    creado_en = models.DateTimeField("creado en", default=timezone.now, db_default=Now())
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "actividades"
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        ordering = ("-fecha", "id")
        constraints = [
            # valor y unidad de densidad, juntos o vacíos (igual que el diseño)
            models.CheckConstraint(
                condition=models.Q(densidad_siembra__isnull=True, densidad_unidad__isnull=True)
                | models.Q(densidad_siembra__isnull=False, densidad_unidad__isnull=False),
                name="ck_actividad_densidad",
            ),
            models.CheckConstraint(
                condition=models.Q(densidad_siembra__isnull=True)
                | models.Q(densidad_siembra__gt=0),
                name="ck_actividad_densidad_valor",
            ),
            models.CheckConstraint(
                condition=models.Q(densidad_unidad__isnull=True)
                | models.Q(densidad_unidad__in=["KG_HA", "PLANTAS_M2"]),
                name="ck_actividad_densidad_unidad",
            ),
            models.CheckConstraint(
                condition=models.Q(horas__isnull=True) | models.Q(horas__gte=0),
                name="ck_actividad_horas",
            ),
            models.CheckConstraint(
                condition=models.Q(costo__isnull=True) | models.Q(costo__gte=0),
                name="ck_actividad_costo",
            ),
            # anulada ⇒ motivo (el CHECK del diseño; nombre propio en PG)
            models.CheckConstraint(
                condition=models.Q(anulada=False) | models.Q(motivo_anulacion__isnull=False),
                name="ck_actividad_anulacion",
            ),
        ]
        indexes = [
            models.Index(fields=["campania", "fecha"], name="ix_actividades_campania"),
        ]

    def __str__(self):
        return f"{self.fecha} · {self.tipo_actividad} · {self.campania}"
