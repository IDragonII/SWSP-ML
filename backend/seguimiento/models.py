from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import (
    Agente,
    EtapaFenologica,
    Recurso,
    TipoActividad,
    TipoIncidencia,
    Unidad,
)
from productores.models import Parcela


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


class Clima(models.Model):
    """Registro climático diario de una parcela (01_tablas.sql:324-342).

    Una fila por parcela y día (uq_clima_parcela_fecha): no hay anulación
    ni borrado (decisión de la Semana 10) — un error se corrige editando el
    mismo registro. Al menos una medida o la helada marcada lo validan en la
    API; las reglas de rango viven en los CHECK y, en la API, además la
    mínima ≤ máxima y el promedio entre ambas.

    Campos calculados por el servidor (nunca por el cliente): temp_prom
    como punto medio si vienen mínima y máxima, helada derivada del umbral
    del sistema cuando hay mínima y fuente (MANUAL o API; editar a mano un
    registro de API lo convierte en MANUAL). El umbral vive en
    parametros_sistema (clave umbral_helada_c, Semana 10).

    trg_clima_actualizado (migración 0006) fija actualizado_en con
    fn_set_actualizado_en de productores.0002: es el único trigger de la
    tabla, porque el resto de sus reglas son restricciones de la tabla.
    """

    FUENTE_MANUAL = "MANUAL"
    FUENTE_API = "API"
    FUENTES = [
        (FUENTE_MANUAL, "Manual"),
        (FUENTE_API, "API"),
    ]

    parcela = models.ForeignKey(
        Parcela,
        on_delete=models.CASCADE,
        related_name="registros_clima",
        verbose_name="parcela",
        db_index=False,
    )
    fecha = models.DateField("fecha")
    temp_min = models.DecimalField(
        "temperatura mínima (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    temp_max = models.DecimalField(
        "temperatura máxima (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    temp_prom = models.DecimalField(
        "temperatura promedio (°C)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    precipitacion_mm = models.DecimalField(
        "precipitación (mm)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    humedad_pct = models.DecimalField(
        "humedad (%)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    viento_ms = models.DecimalField(
        "viento (m/s)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    radiacion_mj = models.DecimalField(
        "radiación (MJ/m²)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    helada = models.BooleanField("helada", default=False, db_default=False)
    fuente = models.CharField(
        "fuente",
        max_length=10,
        choices=FUENTES,
        default=FUENTE_MANUAL,
        db_default="MANUAL",
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clima_registrado",
        verbose_name="registrado por",
        db_index=False,
    )
    creado_en = models.DateTimeField("creado en", default=timezone.now, db_default=Now())
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "clima"
        verbose_name = "registro de clima"
        verbose_name_plural = "registros de clima"
        ordering = ("-fecha", "id")
        constraints = [
            # Rangos del diseño (01_tablas.sql:328-334): las temperaturas
            # entre −30 y 45, precipitación/viento/radiación ≥ 0 y humedad
            # entre 0 y 100; NULL no se toca.
            models.CheckConstraint(
                condition=models.Q(temp_min__isnull=True)
                | models.Q(temp_min__gte=-30, temp_min__lte=45),
                name="ck_clima_temp_min_rango",
            ),
            models.CheckConstraint(
                condition=models.Q(temp_max__isnull=True)
                | models.Q(temp_max__gte=-30, temp_max__lte=45),
                name="ck_clima_temp_max_rango",
            ),
            models.CheckConstraint(
                condition=models.Q(temp_prom__isnull=True)
                | models.Q(temp_prom__gte=-30, temp_prom__lte=45),
                name="ck_clima_temp_prom_rango",
            ),
            models.CheckConstraint(
                condition=models.Q(precipitacion_mm__isnull=True)
                | models.Q(precipitacion_mm__gte=0),
                name="ck_clima_precipitacion",
            ),
            models.CheckConstraint(
                condition=models.Q(humedad_pct__isnull=True)
                | models.Q(humedad_pct__gte=0, humedad_pct__lte=100),
                name="ck_clima_humedad",
            ),
            models.CheckConstraint(
                condition=models.Q(viento_ms__isnull=True) | models.Q(viento_ms__gte=0),
                name="ck_clima_viento",
            ),
            models.CheckConstraint(
                condition=models.Q(radiacion_mj__isnull=True)
                | models.Q(radiacion_mj__gte=0),
                name="ck_clima_radiacion",
            ),
            # ck_clima_temp del diseño: la mínima no supera a la máxima
            models.CheckConstraint(
                condition=models.Q(temp_min__isnull=True)
                | models.Q(temp_max__isnull=True)
                | models.Q(temp_min__lte=models.F("temp_max")),
                name="ck_clima_temp",
            ),
            # Una fila por parcela y día (uq_clima_parcela_fecha; también
            # sirve de índice, como en el diseño)
            models.UniqueConstraint(
                fields=["parcela", "fecha"], name="uq_clima_parcela_fecha"
            ),
        ]
        indexes = [
            models.Index(fields=["fecha"], name="ix_clima_fecha"),
        ]

    def __str__(self):
        return f"{self.fecha} · {self.parcela}"


class Incidencia(models.Model):
    """Evento que afecta a una campaña (01_tablas.sql:309-322).

    Helada, sequía, granizada, plaga, enfermedad… con fecha, tipo y
    severidad; puede haber varias el mismo día y del mismo tipo (no hay
    unicidad). La anulación es lógica (decisión de la Semana 11): una
    incidencia tiene consecuencias (resumen de campaña, variables del
    dataset y, en el Sprint 8, alertas), así que se anula con motivo y no
    se borra — la API no ofrece DELETE.

    Solo las campañas PLANIFICADA, EN_PRODUCCION o COSECHADA admiten
    registros y la fecha debe caer dentro del período (las comprueba
    fn_validar_fecha_campania con trg_incidencias_fecha). La superficie
    afectada no puede superar la sembrada y el agente solo se indica en
    tipos biológicos (fn_validar_incidencia con
    trg_incidencias_superficie; la validación es por categoría del
    catálogo, no por nombre — limitación anotada). El producto aplicado
    es texto libre, solo informativo.

    Los 3 triggers los crea la migración 0008; fn_validar_fecha_campania
    y fn_set_actualizado_en las aportan seguimiento.0002 y
    productores.0002 (la reversión no las toca).
    """

    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    SEVERIDADES = [
        (BAJA, "Baja"),
        (MEDIA, "Media"),
        (ALTA, "Alta"),
    ]

    campania = models.ForeignKey(
        Campania,
        on_delete=models.CASCADE,
        related_name="incidencias",
        verbose_name="campaña",
        db_index=False,
    )
    tipo_incidencia = models.ForeignKey(
        TipoIncidencia,
        on_delete=models.PROTECT,
        related_name="incidencias",
        verbose_name="tipo de incidencia",
        db_index=False,
    )
    fecha = models.DateField("fecha")
    severidad = models.CharField("severidad", max_length=10, choices=SEVERIDADES)
    descripcion = models.TextField("descripción")
    superficie_afectada_ha = models.DecimalField(
        "superficie afectada (ha)",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    agente = models.ForeignKey(
        Agente,
        on_delete=models.PROTECT,
        related_name="incidencias",
        verbose_name="agente",
        null=True,
        blank=True,
        db_index=False,
    )
    producto_aplicado = models.CharField(
        "producto aplicado", max_length=100, null=True, blank=True
    )
    anulada = models.BooleanField("anulada", default=False, db_default=False)
    motivo_anulacion = models.TextField(
        "motivo de anulación", null=True, blank=True
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidencias_registradas",
        verbose_name="registrado por",
        db_index=False,
    )
    creado_en = models.DateTimeField("creado en", default=timezone.now, db_default=Now())
    actualizado_en = models.DateTimeField(
        "actualizado en", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "incidencias"
        verbose_name = "incidencia"
        verbose_name_plural = "incidencias"
        ordering = ("-fecha", "id")
        constraints = [
            # Severidad entre baja, media y alta (diseño 01_tablas.sql)
            models.CheckConstraint(
                condition=models.Q(severidad__in=("BAJA", "MEDIA", "ALTA")),
                name="ck_incidencia_severidad",
            ),
            # Superficie afectada ≥ 0; NULL no se toca
            models.CheckConstraint(
                condition=models.Q(superficie_afectada_ha__isnull=True)
                | models.Q(superficie_afectada_ha__gte=0),
                name="ck_incidencia_superficie",
            ),
            # anulada ⇒ motivo (el CHECK de la Semana 11)
            models.CheckConstraint(
                condition=models.Q(anulada=False)
                | models.Q(motivo_anulacion__isnull=False),
                name="ck_incidencia_anulacion",
            ),
        ]
        indexes = [
            models.Index(
                fields=["campania", "fecha"], name="ix_incidencias_campania"
            ),
            models.Index(fields=["agente"], name="ix_incidencias_agente"),
        ]

    def __str__(self):
        return f"{self.fecha} · {self.tipo_incidencia} · {self.campania}"


class SeguimientoEtapa(models.Model):
    """Etapa fenológica alcanzada por una campaña (01_tablas.sql:258-268).

    Primera pieza de la línea de tiempo (Semana 12): una fila por etapa
    del cultivo que la campaña alcanzó, con fecha de inicio y fin (vacía
    mientras está en curso) y quién la registró. La misma etapa no se
    repite dentro de una campaña (uq_seguimiento_etapa) y el fin no puede
    ser anterior al inicio (ck_seguimiento_fechas).

    A diferencia de las demás tablas de seguimiento, el diseño **no le
    da fechas de creación/cambio** (solo registrado_por): «etapa» no
    altera el dataset ni las alertas, así que corregirla en su momento
    basta — la auditoría del Sprint 7 cubre quién y cuándo, cuando
    exista (decisión de la Semana 12).

    Sin anulación ni borrado: corregir es editar (mismas validaciones),
    la API no ofrece DELETE. Los 2 triggers (trg_seguimiento_fecha con
    fn_validar_fecha_campania y trg_seguimiento_etapa con
    fn_validar_etapa) los crea la migración 0010; con ellos el diseño
    queda completo: 24 de 24.
    """

    campania = models.ForeignKey(
        Campania,
        on_delete=models.CASCADE,
        related_name="etapas",
        verbose_name="campaña",
        db_index=False,
    )
    etapa = models.ForeignKey(
        EtapaFenologica,
        on_delete=models.PROTECT,
        related_name="registros",
        verbose_name="etapa",
        db_index=False,
    )
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField("fecha de fin", null=True, blank=True)
    observaciones = models.TextField("observaciones", null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="etapas_registradas",
        verbose_name="registrado por",
        db_index=False,
    )

    class Meta:
        db_table = "seguimiento_etapas"
        verbose_name = "etapa de seguimiento"
        verbose_name_plural = "etapas de seguimiento"
        ordering = ("-fecha_inicio", "id")
        constraints = [
            # Una etapa por campaña (el diseño: uq_seguimiento_etapa)
            models.UniqueConstraint(
                fields=["campania", "etapa"], name="uq_seguimiento_etapa"
            ),
            # fecha_fin ≥ fecha_inicio (NULL = en curso)
            models.CheckConstraint(
                condition=models.Q(fecha_fin__isnull=True)
                | models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="ck_seguimiento_fechas",
            ),
        ]
        indexes = [
            # Índice del diseño: ix_seguimiento_campania
            models.Index(fields=["campania"], name="ix_seguimiento_campania"),
        ]

    def __str__(self):
        return f"{self.etapa} · {self.fecha_inicio} · {self.campania}"
