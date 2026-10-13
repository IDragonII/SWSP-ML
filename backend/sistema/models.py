from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class ParametroSistema(models.Model):
    """Parámetros configurables del sistema (01_tablas.sql:432-438).

    Las claves son fijas y se cargan con la migración 0001 (03_insert.sql
    las marca CONFIRMAR): por la API solo se edita el valor, con
    parametros.gestionar. fn_validar_produccion lee
    rendimiento_min_plausible y rendimiento_max_plausible para marcar
    requiere_revision; las alertas del Sprint 8 usarán dias_sin_actividad y
    umbral_rendimiento_bajo. Sin creado_en (el diseño no lo tiene);
    actualizado_en lo fija trg_parametros_sistema_actualizado.
    """

    clave = models.CharField("clave", max_length=60, unique=True)
    valor = models.CharField("valor", max_length=100)
    descripcion = models.CharField(
        "descripción", max_length=200, null=True, blank=True
    )
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "parametros_sistema"
        verbose_name = "parámetro del sistema"
        verbose_name_plural = "parámetros del sistema"
        ordering = ("clave",)

    def __str__(self):
        return f"{self.clave} = {self.valor}"
