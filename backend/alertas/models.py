from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

TIPOS = [
    ("INCIDENCIA_SEVERA", "Incidencia severa"),
    ("SIN_ACTIVIDAD", "Sin actividad"),
    ("RENDIMIENTO_BAJO", "Rendimiento bajo"),
]


class Alerta(models.Model):
    """Aviso para el personal del proyecto (Semana 15, HU-124..HU-132).

    La crea y cierra solo el sistema: la API no admite altas, ediciones
    ni borrados. Una por incidencia severa (atendida o no) y, mientras
    estén pendientes, una por campaña y tipo para las de sin actividad y
    rendimiento bajo. El cierre automático queda como atendida sin
    usuario; una atendida a mano puede reabrirse. Cambios de diseño de
    la Semana 15 sobre 01_tablas.sql: incidencia_id, nota_atencion, el
    enlace exigido solo en las de incidencia severa y los índices
    únicos por incidencia y por campaña+tipo pendiente.
    """

    TIPO_INCIDENCIA_SEVERA = "INCIDENCIA_SEVERA"
    TIPO_SIN_ACTIVIDAD = "SIN_ACTIVIDAD"
    TIPO_RENDIMIENTO_BAJO = "RENDIMIENTO_BAJO"
    TIPOS = TIPOS

    productor = models.ForeignKey(
        "productores.Productor",
        on_delete=models.CASCADE,
        related_name="alertas",
        verbose_name="productor",
    )
    campania = models.ForeignKey(
        "campanias.Campania",
        on_delete=models.CASCADE,
        related_name="alertas",
        verbose_name="campaña",
    )
    incidencia = models.ForeignKey(
        "seguimiento.Incidencia",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alertas",
        verbose_name="incidencia",
    )
    tipo = models.CharField("tipo", max_length=25, choices=TIPOS)
    mensaje = models.CharField("mensaje", max_length=250)
    creada_en = models.DateTimeField(
        "creada el", default=timezone.now, db_default=Now()
    )
    atendida = models.BooleanField("atendida", default=False)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_atendidas",
        verbose_name="atendida por",
    )
    atendida_en = models.DateTimeField("atendida el", null=True, blank=True)
    nota_atencion = models.CharField(
        "nota de atención", max_length=250, null=True, blank=True
    )

    class Meta:
        db_table = "alertas"
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        ordering = ("atendida", "-creada_en", "-id")
        indexes = [
            models.Index(
                fields=["productor"],
                name="ix_alertas_pendientes",
                condition=models.Q(atendida=False),
            ),
            models.Index(fields=["campania"], name="ix_alertas_campania"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["incidencia"], name="uq_alerta_incidencia"
            ),
            models.UniqueConstraint(
                fields=["campania", "tipo"],
                condition=models.Q(
                    atendida=False,
                    tipo__in=("SIN_ACTIVIDAD", "RENDIMIENTO_BAJO"),
                ),
                name="uq_alerta_pendiente_campania_tipo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    ("tipo__in", ("INCIDENCIA_SEVERA", "SIN_ACTIVIDAD", "RENDIMIENTO_BAJO"))
                ),
                name="ck_alerta_tipo",
            ),
            models.CheckConstraint(
                condition=models.Q(atendida=True)
                | models.Q(atendida_en__isnull=True),
                name="ck_alerta_atendida",
            ),
            models.CheckConstraint(
                condition=models.Q(nota_atencion__isnull=True)
                | models.Q(atendida=True),
                name="ck_alerta_nota",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo="INCIDENCIA_SEVERA", incidencia__isnull=False)
                    | ~models.Q(tipo="INCIDENCIA_SEVERA", incidencia__isnull=True)
                ),
                name="ck_alerta_incidencia",
            ),
        ]

    def __str__(self):
        estado = "pendiente" if not self.atendida else "atendida"
        return f"{self.get_tipo_display()} · productor {self.productor_id} · {estado}"
