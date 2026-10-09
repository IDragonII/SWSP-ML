from django.db import models

_TIPOS_UNIDAD = [
    ("MASA", "Masa"),
    ("SUPERFICIE", "Superficie"),
    ("VOLUMEN", "Volumen"),
    ("LABOR", "Labor"),
    ("TIEMPO", "Tiempo"),
]
_TIPOS_UNIDAD_RECURSO = [
    ("MASA", "Masa"),
    ("VOLUMEN", "Volumen"),
    ("LABOR", "Labor"),
    ("TIEMPO", "Tiempo"),
]
_CATEGORIAS_RECURSO = [
    ("SEMILLA", "Semilla"),
    ("FERTILIZANTE", "Fertilizante"),
    ("ABONO", "Abono"),
    ("FITOSANITARIO", "Fitosanitario"),
    ("AGUA", "Agua"),
    ("MAQUINARIA", "Maquinaria"),
    ("MANO_OBRA", "Mano de obra"),
    ("COMBUSTIBLE", "Combustible"),
]
_CATEGORIAS_INCIDENCIA = [
    ("CLIMATICA", "Climática"),
    ("BIOLOGICA", "Biológica"),
    ("OTRA", "Otra"),
]
_TIPOS_AGENTE = [
    ("PLAGA", "Plaga"),
    ("ENFERMEDAD", "Enfermedad"),
]


class Cultivo(models.Model):
    """Catálogo de cultivos: nombre único, descripción y estado."""

    nombre = models.CharField("nombre", max_length=60)
    descripcion = models.TextField("descripción", null=True, blank=True)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "cultivos"
        verbose_name = "cultivo"
        verbose_name_plural = "cultivos"
        ordering = ("nombre",)
        constraints = [
            models.UniqueConstraint(fields=["nombre"], name="cultivos_nombre_key"),
        ]

    def __str__(self):
        return self.nombre


class Variedad(models.Model):
    """Variedad de un cultivo. uq_variedad_cultivo (id, cultivo) da la
    clave compuesta que usarán las campañas de la Semana 6."""

    cultivo = models.ForeignKey(
        Cultivo,
        on_delete=models.RESTRICT,
        related_name="variedades",
        verbose_name="cultivo",
        db_index=False,
    )
    nombre = models.CharField("nombre", max_length=80)
    descripcion = models.TextField("descripción", null=True, blank=True)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "variedades"
        verbose_name = "variedad"
        verbose_name_plural = "variedades"
        ordering = ("cultivo", "nombre")
        constraints = [
            models.UniqueConstraint(
                fields=["cultivo", "nombre"], name="uq_variedad"
            ),
            models.UniqueConstraint(
                fields=["id", "cultivo"], name="uq_variedad_cultivo"
            ),
        ]
        indexes = [
            models.Index(fields=["cultivo"], name="ix_variedades_cultivo"),
        ]

    def __str__(self):
        return f"{self.cultivo} · {self.nombre}"


class EtapaFenologica(models.Model):
    """Etapa del ciclo de un cultivo: nombre y orden dentro del cultivo
    (uq_etapa_nombre y uq_etapa_orden). Sin estado: se oculta desactivando
    el cultivo."""

    cultivo = models.ForeignKey(
        Cultivo,
        on_delete=models.RESTRICT,
        related_name="etapas",
        verbose_name="cultivo",
        db_index=False,
    )
    nombre = models.CharField("nombre", max_length=60)
    orden = models.SmallIntegerField("orden")

    class Meta:
        db_table = "etapas_fenologicas"
        verbose_name = "etapa fenológica"
        verbose_name_plural = "etapas fenológicas"
        ordering = ("cultivo", "orden")
        constraints = [
            models.UniqueConstraint(
                fields=["cultivo", "nombre"], name="uq_etapa_nombre"
            ),
            models.UniqueConstraint(
                fields=["cultivo", "orden"], name="uq_etapa_orden"
            ),
            models.CheckConstraint(
                condition=models.Q(orden__gt=0),
                name="etapas_fenologicas_orden_check",
            ),
        ]

    def __str__(self):
        return f"{self.cultivo} · {self.orden}. {self.nombre}"


class Unidad(models.Model):
    """Unidad de medida con factor a la unidad base de su tipo. Solo puede
    haber una base por tipo (uq_unidad_base_tipo)."""

    nombre = models.CharField("nombre", max_length=40)
    simbolo = models.CharField("símbolo", max_length=10)
    tipo = models.CharField("tipo", max_length=15, choices=_TIPOS_UNIDAD)
    factor_a_base = models.DecimalField(
        "factor a la base", max_digits=12, decimal_places=6
    )
    es_base = models.BooleanField("es base", default=False, db_default=False)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "unidades"
        verbose_name = "unidad"
        verbose_name_plural = "unidades"
        ordering = ("tipo", "nombre")
        constraints = [
            models.UniqueConstraint(fields=["nombre"], name="unidades_nombre_key"),
            models.UniqueConstraint(
                fields=["tipo"],
                condition=models.Q(es_base=True),
                name="uq_unidad_base_tipo",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=[v for v, _ in _TIPOS_UNIDAD]),
                name="unidades_tipo_check",
            ),
            models.CheckConstraint(
                condition=models.Q(factor_a_base__gt=0),
                name="unidades_factor_a_base_check",
            ),
            models.CheckConstraint(
                condition=models.Q(es_base=False)
                | models.Q(factor_a_base=1),
                name="ck_unidad_base",
            ),
        ]

    def __str__(self):
        return self.nombre


class TipoActividad(models.Model):
    """Catálogo fijo de actividades agrícolas: su código no cambia nunca
    (7 sembrados; Siembra y Cosecha no se desactivan)."""

    codigo = models.CharField("código", max_length=20)
    nombre = models.CharField("nombre", max_length=60)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "tipos_actividad"
        verbose_name = "tipo de actividad"
        verbose_name_plural = "tipos de actividad"
        ordering = ("codigo",)
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"], name="tipos_actividad_codigo_key"
            ),
        ]

    def __str__(self):
        return self.nombre


class Recurso(models.Model):
    """Insumo o recurso que se consume en las campañas."""

    nombre = models.CharField("nombre", max_length=80)
    categoria = models.CharField(
        "categoría", max_length=20, choices=_CATEGORIAS_RECURSO
    )
    tipo_unidad = models.CharField(
        "tipo de unidad", max_length=15, choices=_TIPOS_UNIDAD_RECURSO
    )
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "recursos"
        verbose_name = "recurso"
        verbose_name_plural = "recursos"
        ordering = ("categoria", "nombre")
        constraints = [
            models.UniqueConstraint(fields=["nombre"], name="recursos_nombre_key"),
            models.CheckConstraint(
                condition=models.Q(
                    categoria__in=[v for v, _ in _CATEGORIAS_RECURSO]
                ),
                name="recursos_categoria_check",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    tipo_unidad__in=[v for v, _ in _TIPOS_UNIDAD_RECURSO]
                ),
                name="recursos_tipo_unidad_check",
            ),
        ]

    def __str__(self):
        return self.nombre


class TipoIncidencia(models.Model):
    """Categoría de incidencia climática, biológica u otra."""

    nombre = models.CharField("nombre", max_length=60)
    categoria = models.CharField(
        "categoría", max_length=15, choices=_CATEGORIAS_INCIDENCIA
    )
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "tipos_incidencia"
        verbose_name = "tipo de incidencia"
        verbose_name_plural = "tipos de incidencia"
        ordering = ("categoria", "nombre")
        constraints = [
            models.UniqueConstraint(
                fields=["nombre"], name="tipos_incidencia_nombre_key"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    categoria__in=[v for v, _ in _CATEGORIAS_INCIDENCIA]
                ),
                name="tipos_incidencia_categoria_check",
            ),
        ]

    def __str__(self):
        return self.nombre


class Agente(models.Model):
    """Plaga o enfermedad que puede afectar las campañas."""

    nombre = models.CharField("nombre", max_length=100)
    tipo = models.CharField("tipo", max_length=12, choices=_TIPOS_AGENTE)
    activo = models.BooleanField("activo", default=True, db_default=True)

    class Meta:
        db_table = "agentes"
        verbose_name = "agente"
        verbose_name_plural = "agentes"
        ordering = ("nombre",)
        constraints = [
            models.UniqueConstraint(fields=["nombre"], name="agentes_nombre_key"),
            models.CheckConstraint(
                condition=models.Q(tipo__in=[v for v, _ in _TIPOS_AGENTE]),
                name="agentes_tipo_check",
            ),
        ]

    def __str__(self):
        return self.nombre
