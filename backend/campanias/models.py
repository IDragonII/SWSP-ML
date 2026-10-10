from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from catalogos.models import Cultivo, Variedad
from productores.models import Parcela


class Campania(models.Model):
    """Campaña agrícola: parcela + cultivo + ciclo (01_tablas.sql:228-253).

    Es la tabla central del dataset: cada campaña cerrada será una fila de
    entrenamiento. La variedad se enlaza con la clave compuesta
    fk_campania_variedad_cultivo (variedad_id, cultivo_id) creada por SQL
    propio en la migración 0001 —Django no soporta claves compuestas—; el
    estado lo mantiene trg_campanias_actualizado y la superficie, el estado
    inicial y las transiciones los controla fn_validar_campania (versión
    parcial del Sprint 3, migración 0002: cosechada y cerrada llegan en el
    Sprint 4 con una migración nueva que la reemplaza).
    """

    ESTADO_PLANIFICADA = "PLANIFICADA"
    ESTADO_EN_PRODUCCION = "EN_PRODUCCION"
    ESTADO_COSECHADA = "COSECHADA"
    ESTADO_CERRADA = "CERRADA"
    ESTADO_CANCELADA = "CANCELADA"
    ESTADOS = [
        (ESTADO_PLANIFICADA, "Planificada"),
        (ESTADO_EN_PRODUCCION, "En producción"),
        (ESTADO_COSECHADA, "Cosechada"),
        (ESTADO_CERRADA, "Cerrada"),
        (ESTADO_CANCELADA, "Cancelada"),
    ]
    # Una campaña ocupa la parcela mientras esté en uno de estos estados
    # (índice uq_campania_activa_por_parcela).
    ESTADOS_ACTIVOS = (ESTADO_PLANIFICADA, ESTADO_EN_PRODUCCION, ESTADO_COSECHADA)

    periodo = models.CharField("período", max_length=9)
    parcela = models.ForeignKey(
        Parcela,
        on_delete=models.PROTECT,
        related_name="campanias",
        verbose_name="parcela",
        db_index=False,
    )
    cultivo = models.ForeignKey(
        Cultivo,
        on_delete=models.PROTECT,
        related_name="campanias",
        verbose_name="cultivo",
        db_index=False,
    )
    # db_constraint=False: la restricción real del diseño es la clave
    # compuesta (variedad_id, cultivo_id), que agrega la migración 0001 con
    # SQL propio sobre uq_variedad_cultivo de la Semana 5.
    variedad = models.ForeignKey(
        Variedad,
        on_delete=models.PROTECT,
        related_name="campanias",
        verbose_name="variedad",
        db_index=False,
        db_constraint=False,
    )
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin_prevista = models.DateField("fecha de fin prevista")
    fecha_siembra = models.DateField(
        "fecha de siembra", null=True, blank=True
    )  # la llena la actividad de siembra (Sprint 4)
    superficie_sembrada_ha = models.DecimalField(
        "superficie sembrada (ha)", max_digits=8, decimal_places=2
    )
    estado = models.CharField(
        "estado",
        max_length=15,
        choices=ESTADOS,
        default=ESTADO_PLANIFICADA,
        db_default=ESTADO_PLANIFICADA,
    )
    observaciones = models.TextField("observaciones", null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campanias_creadas",
        verbose_name="creado por",
    )
    creado_en = models.DateTimeField(
        "creado en", default=timezone.now, db_default=Now()
    )
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "campanias"
        verbose_name = "campaña"
        verbose_name_plural = "campañas"
        ordering = ("-periodo", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(superficie_sembrada_ha__gt=0),
                name="ck_campania_superficie",
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_fin_prevista__gte=models.F("fecha_inicio")),
                name="ck_campania_fechas",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[
                        "PLANIFICADA",
                        "EN_PRODUCCION",
                        "COSECHADA",
                        "CERRADA",
                        "CANCELADA",
                    ]
                ),
                name="ck_campania_estado",
            ),
            # ck_campania_periodo (formato AAAA-AAAA y años consecutivos) y la
            # clave compuesta fk_campania_variedad_cultivo se agregan con SQL
            # en la migración 0001: Django no puede expresarlos.
        ]
        indexes = [
            models.Index(fields=["parcela"], name="ix_campanias_parcela"),
            models.Index(fields=["cultivo"], name="ix_campanias_cultivo"),
            models.Index(fields=["estado"], name="ix_campanias_estado"),
            models.Index(fields=["periodo"], name="ix_campanias_periodo"),
        ]

    def __str__(self):
        return f"{self.periodo} · {self.parcela} · {self.cultivo}"
