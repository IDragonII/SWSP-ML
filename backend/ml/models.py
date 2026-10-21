"""Modelos de Machine Learning (Sprint 14, decisiones 216-219, 253-256).

Las cuatro tablas de `01_tablas.sql` con los mismos nombres y
restricciones: CHECK de algoritmo (los 3), MAE/RMSE ≥ 0, unicidad por
entrenamiento+algoritmo y por algoritmo+versión, un solo modelo activo
(índice único parcial), CHECK de intervalo e índices de campaña y
modelo. Diferencias normales del diseño a Django (decisión 217): nombres
de restricciones, `ON DELETE` declarado por Django y las identidades
`BIGINT` con el modo que genera el migrador.

La Semana 23 añade `tareas_entrenamiento` (decisión 253: el pedido del
Administrador y su progreso, con una sola tarea activa a la vez) y las
tres columnas de modelo-en-BD de `modelos_ml` (`contenido`, `huella` y
`versiones_librerias`, decisión 254): el trabajador guarda el `.joblib`
en la BD y el registro manual por comando sigue usando archivo +
manifiesto como fallback.

Los datos NO se crean desde el admin (se consulta aquí): el alta la da
el comando `registrar_modelo` (HU-171), la activación la API (HU-172)
y las predicciones el servicio (HU-173) — ineditables e inborrables
(decisión 232).
"""
from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

ALGORITMOS = [
    ("REGRESION_LINEAL", "Regresión lineal"),
    ("RANDOM_FOREST", "Random Forest"),
    ("GRADIENT_BOOSTING", "Gradient Boosting"),
]

ESTADOS_TAREA = [
    ("PENDIENTE", "Pendiente"),
    ("PROCESANDO", "En proceso"),
    ("COMPLETADA", "Completada"),
    ("FALLIDA", "Fallida"),
    ("CANCELADA", "Cancelada"),
]

ESTADOS_ACTIVOS_TAREA = ("PENDIENTE", "PROCESANDO")


class EntrenamientoML(models.Model):
    """Un entrenamiento ejecutado con `entrenar_modelos` (01_tablas.sql:385).

    `variables_usadas` guarda el objeto JSON de la decisión 223: lista
    de variables, conjunto, origen de los datos, huella del dataset,
    semilla y estrategia de validación.
    """

    fecha = models.DateTimeField("fecha", default=timezone.now, db_default=Now())
    n_registros = models.PositiveIntegerField("registros")
    n_entrenamiento = models.PositiveIntegerField("entrenamiento")
    n_prueba = models.PositiveIntegerField("prueba")
    variables_usadas = models.JSONField("variables usadas")
    observaciones = models.TextField("observaciones", null=True, blank=True)
    ejecutado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entrenamientos_ml",
        verbose_name="ejecutado por",
    )

    class Meta:
        db_table = "entrenamientos_ml"
        verbose_name = "entrenamiento"
        verbose_name_plural = "entrenamientos"
        ordering = ("-fecha", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(n_registros__gt=0),
                name="ck_entrenamiento_registros",
            ),
            models.CheckConstraint(
                condition=models.Q(n_entrenamiento__gt=0),
                name="ck_entrenamiento_entrenamiento",
            ),
            models.CheckConstraint(
                condition=models.Q(n_prueba__gte=0),
                name="ck_entrenamiento_prueba",
            ),
        ]

    def __str__(self):
        return f"Entrenamiento {self.id} · {self.n_registros} registros"


class ModeloML(models.Model):
    """Modelo entrenado, con sus métricas (01_tablas.sql).

    Un modelo por algoritmo y versión, con su artefacto `.joblib` en la
    BD (`contenido` + `huella`, decisión 254) o, en el registro manual,
    como archivo con huella en `ml_models/manifiesto.json` (fallback);
    `activo` admite solo una fila (índice único parcial
    `uq_modelo_activo`). La línea base no es una fila (decisión 224):
    sus métricas viven en `hiperparametros`. El CHECK `ck_modelo_tamano`
    (migración 0003) limita `contenido` a 20 MiB.
    """

    entrenamiento = models.ForeignKey(
        EntrenamientoML,
        on_delete=models.CASCADE,
        related_name="modelos",
        verbose_name="entrenamiento",
    )
    algoritmo = models.CharField("algoritmo", max_length=25, choices=ALGORITMOS)
    version = models.CharField("versión", max_length=20)
    mae = models.DecimalField("MAE", max_digits=10, decimal_places=2)
    rmse = models.DecimalField("RMSE", max_digits=10, decimal_places=2)
    r2 = models.DecimalField("R²", max_digits=8, decimal_places=4)
    hiperparametros = models.JSONField("hiperparámetros", null=True, blank=True)
    archivo = models.CharField("archivo", max_length=255, null=True, blank=True)
    contenido = models.BinaryField("contenido", null=True, blank=True)
    huella = models.CharField("huella", max_length=64, null=True, blank=True)
    versiones_librerias = models.JSONField(
        "versiones de librerías", null=True, blank=True
    )
    activo = models.BooleanField("activo", default=False)
    creado_en = models.DateTimeField(
        "creado el", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "modelos_ml"
        verbose_name = "modelo"
        verbose_name_plural = "modelos"
        ordering = ("-creado_en", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    algoritmo__in=["REGRESION_LINEAL", "RANDOM_FOREST",
                                   "GRADIENT_BOOSTING"]
                ),
                name="ck_modelo_algoritmo",
            ),
            models.CheckConstraint(
                condition=models.Q(mae__gte=0), name="ck_modelo_mae"
            ),
            models.CheckConstraint(
                condition=models.Q(rmse__gte=0), name="ck_modelo_rmse"
            ),
            models.UniqueConstraint(
                fields=["entrenamiento", "algoritmo"],
                name="uq_modelo_entrenamiento",
            ),
            models.UniqueConstraint(
                fields=["algoritmo", "version"], name="uq_modelo_version"
            ),
            models.UniqueConstraint(
                fields=["activo"],
                condition=models.Q(activo=True),
                name="uq_modelo_activo",
            ),
        ]

    def __str__(self):
        marca = " (activo)" if self.activo else ""
        return f"{self.algoritmo} v{self.version}{marca}"


class Prediccion(models.Model):
    """Predicción de rendimiento de una campaña (01_tablas.sql:413).

    `variables_entrada` guarda la copia exacta de lo que se envió al
    modelo (decisión 228: con el origen de cada valor de manejo). El
    intervalo queda en NULL a propósito (decisión 230). Al cosechar,
    `fn_produccion_post` completa (produccion.0003) rellena
    `rendimiento_real`, `error_abs` y `error_pct`.
    """

    campania = models.ForeignKey(
        "campanias.Campania",
        on_delete=models.CASCADE,
        related_name="predicciones",
        db_index=False,
        verbose_name="campaña",
    )
    modelo = models.ForeignKey(
        ModeloML,
        on_delete=models.PROTECT,
        related_name="predicciones",
        db_index=False,
        verbose_name="modelo",
    )
    fecha = models.DateTimeField("fecha", default=timezone.now, db_default=Now())
    dias_ciclo = models.PositiveIntegerField("días de ciclo", null=True, blank=True)
    variables_entrada = models.JSONField("variables de entrada")
    rendimiento_predicho = models.DecimalField(
        "rendimiento predicho", max_digits=10, decimal_places=2
    )
    produccion_estimada_kg = models.DecimalField(
        "producción estimada (kg)", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    intervalo_inferior = models.DecimalField(
        "intervalo inferior", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    intervalo_superior = models.DecimalField(
        "intervalo superior", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    rendimiento_real = models.DecimalField(
        "rendimiento real", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    error_abs = models.DecimalField(
        "error absoluto", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    error_pct = models.DecimalField(
        "error porcentual", max_digits=8, decimal_places=2,
        null=True, blank=True,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predicciones_realizadas",
        verbose_name="creado por",
    )

    class Meta:
        db_table = "predicciones"
        verbose_name = "predicción"
        verbose_name_plural = "predicciones"
        ordering = ("-fecha", "id")
        indexes = [
            models.Index(fields=["campania"], name="ix_predicciones_campania"),
            models.Index(fields=["modelo"], name="ix_predicciones_modelo"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(dias_ciclo__isnull=True)
                | models.Q(dias_ciclo__gte=0),
                name="ck_prediccion_dias",
            ),
            models.CheckConstraint(
                condition=models.Q(intervalo_inferior__isnull=True)
                | models.Q(intervalo_superior__isnull=True)
                | models.Q(
                    intervalo_inferior__lte=models.F("intervalo_superior")
                ),
                name="ck_prediccion_intervalo",
            ),
        ]

    def __str__(self):
        return f"Predicción {self.id} · campaña {self.campania_id}"


class TareaEntrenamiento(models.Model):
    """Pedido de entrenamiento hecho por el Administrador (decisión 253).

    El trabajador `procesar_entrenamientos` reclama la tarea pendiente
    con `SELECT ... FOR UPDATE SKIP LOCKED`, la marca PROCESANDO, escribe
    el latido cada 30 s y al terminar guarda el resultado (un
    `EntrenamientoML`) y las tres métricas. Solo puede haber **una**
    tarea activa en todo el sistema: el índice único parcial
    `uq_tarea_activa` sobre la constante con predicado
    `estado IN ('PENDIENTE','PROCESANDO')` lo garantiza en la BD (una
    segunda solicitud recibirá 409).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tareas_entrenamiento",
        verbose_name="usuario",
    )
    estado = models.CharField(
        "estado", max_length=15, choices=ESTADOS_TAREA, default="PENDIENTE"
    )
    progreso = models.JSONField("progreso", null=True, blank=True)
    latido = models.DateTimeField("latido", null=True, blank=True)
    observacion = models.CharField("observación", max_length=200, blank=True)
    resultado = models.ForeignKey(
        EntrenamientoML,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas",
        verbose_name="resultado",
    )
    error = models.TextField("error", null=True, blank=True)
    creado_en = models.DateTimeField(
        "creado el", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "tareas_entrenamiento"
        verbose_name = "tarea de entrenamiento"
        verbose_name_plural = "tareas de entrenamiento"
        ordering = ("-creado_en", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[clave for clave, _ in ESTADOS_TAREA]
                ),
                name="ck_tarea_estado",
            ),
            models.UniqueConstraint(
                models.Value(1),
                condition=models.Q(estado__in=ESTADOS_ACTIVOS_TAREA),
                name="uq_tarea_activa",
            ),
            models.CheckConstraint(
                condition=models.Q(estado="COMPLETADA")
                | models.Q(resultado__isnull=True),
                name="ck_tarea_resultado",
            ),
        ]

    def __str__(self):
        return f"Tarea {self.id} · {self.estado}"
