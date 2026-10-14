from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import Recurso, TipoActividad, Unidad


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


class UsoRecurso(models.Model):
    """Uso de un recurso en una campaña (01_tablas.sql:290-307).

    Una cantidad de un recurso usada en una fecha dentro de la campaña;
    la actividad es opcional (una fertilización puede llevar urea y
    fosfato en dos usos distintos). cantidad_base lo calcula
    fn_uso_recurso (migración 0004: cantidad × factor de la unidad, con
    la unidad del mismo tipo que el recurso). La anulación es lógica
    (Semana 9): los usos anulados salen del resumen por categoría y del
    dataset de entrenamiento.

    fn_validar_fecha_campania y fn_set_actualizado_en las aportan
    seguimiento.0002 y productores.0002 respectivamente: la migración
    0004 solo crea fn_uso_recurso y los 3 triggers de la tabla.
    """

    campania = models.ForeignKey(
        Campania,
        on_delete=models.CASCADE,
        related_name="usos_recursos",
        verbose_name="campaña",
        db_index=False,
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usos_recursos",
        verbose_name="actividad",
        db_index=False,
    )
    recurso = models.ForeignKey(
        Recurso,
        on_delete=models.PROTECT,
        related_name="usos",
        verbose_name="recurso",
        db_index=False,
    )
    fecha = models.DateField("fecha")
    cantidad = models.DecimalField("cantidad", max_digits=12, decimal_places=3)
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.PROTECT,
        related_name="usos_recursos",
        verbose_name="unidad",
        db_index=False,
    )
    # Lo llena fn_uso_recurso en cada INSERT/UPDATE; el valor que mande
    # el cliente se sobrescribe.
    cantidad_base = models.DecimalField(
        "cantidad base", max_digits=14, decimal_places=3
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
        related_name="usos_recursos_registrados",
        verbose_name="registrado por",
        db_index=False,
    )
    creado_en = models.DateTimeField("creado en", default=timezone.now, db_default=Now())
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "uso_recursos"
        verbose_name = "uso de recurso"
        verbose_name_plural = "usos de recursos"
        ordering = ("-fecha", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="ck_uso_recurso_cantidad",
            ),
            models.CheckConstraint(
                condition=models.Q(costo__isnull=True) | models.Q(costo__gte=0),
                name="ck_uso_recurso_costo",
            ),
            # anulada ⇒ motivo (el CHECK de la Semana 9)
            models.CheckConstraint(
                condition=models.Q(anulada=False)
                | models.Q(motivo_anulacion__isnull=False),
                name="ck_uso_recurso_anulacion",
            ),
        ]
        indexes = [
            models.Index(fields=["campania"], name="ix_uso_recursos_campania"),
            models.Index(fields=["recurso"], name="ix_uso_recursos_recurso"),
        ]

    def __str__(self):
        return f"{self.fecha} · {self.recurso} · {self.campania}"
