"""API de Machine Learning (Sprint 14, HU-172/HU-173/HU-177, S22;
entrenamientos S23, HU-180..HU-182).

Seis recursos (decisión 235 ampliada por la 263), todos en español y
con la misma red de seguridad que el comando `registrar_modelo`:

- `predicciones`: lista y ficha con ml.ver_predicciones; POST con
  ml.predecir llama al servicio (225-231). Sin escritura de
  predicciones: PUT/PATCH/DELETE no existen y responden 405, y los
  campos protegidos (modelo, resultados, errores, creador) jamás
  llegan del cliente (232).
- `modelos`: lista con métricas (ml.ver_modelos) y activar con
  ml.activar_modelo vía registro.activar_modelo, con los mismos
  controles que el comando (222). Con la S23 trae las columnas de la
  BD: huella, versiones de librerías y `en_bd` (263).
- `modelo-activo`: el modelo vigente para el banner de demostración
  (239); si no hay activo responde 404.
- `campanas-predecibles`: el selector de la pantalla Predicción:
  PLANIFICADA o EN_PRODUCCION (227), y para el Técnico solo de sus
  productores asignados.
- `estado-datos` (S23): cuántas filas tiene la vista de entrenamiento,
  si alcanzan el mínimo y el sello de honestidad ML_ORIGEN_DATOS
  (262-263); solo ml.entrenar.
- `entrenamientos` (S23): historial y alta de tareas (263); el alta
  admite una sola tarea activa en todo el sistema (409, decisión 255),
  tiene límite de 5 por día y usuario (261) y se cancela con
  `{id}/cancelar/` mientras siga activa. `{id}/resultados/` devuelve
  la tabla comparativa de los 3 candidatos (264).

El Técnico ve solo predicciones y campañas de SUS productores (404 en
lo ajeno, el mismo que si no existiera; decisión 227) y no recibe
quién predijo (233). El Coordinador consulta predicciones pero no
predecir ni ver modelos (384). Predecir tiene límite de 30 por hora y
usuario (232). No hay AuditoriaMixin: la auditoría CREAR la escriben
registro y servicio (234); el ViewSet declara `auditoria_modulo` para
el recorrido de la prueba 233.
"""
from django.db import IntegrityError, connection, transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from campanias.models import Campania
from productores.views import PermisosPorAccion, filtrar_asignados

from . import registro, servicio, trabajo
from .models import (
    ESTADOS_ACTIVOS_TAREA,
    ModeloML,
    Prediccion,
    TareaEntrenamiento,
)
from .serializers import (
    CampaniaPredecibleSerializer,
    ModeloListaSerializer,
    PrediccionDetalleSerializer,
    PrediccionEscrituraSerializer,
    PrediccionListaSerializer,
    ResultadoEntrenamientoSerializer,
    TareaEntrenamientoSerializer,
)

_ORDEN_PREDICCIONES = ("-fecha", "id")
_ORDEN_MODELOS = ("-creado_en", "id")

# Filtro del historial (HU-177): pendientes son las predicciones sin
# comparación aún; el valor vacío o «todas» no filtra.
COMPARACIONES = {
    None: {},
    "": {},
    "todas": {},
    "pendiente": {"rendimiento_real__isnull": True},
    "comparada": {"rendimiento_real__isnull": False},
}


class PermisosML(PermisosPorAccion):
    """ml.* sembrados en usuarios.0002: Técnico de campo (predecir y
    ver_predicciones), Coordinador (solo ver_predicciones) y
    Administrador (todos, incluye entrenar, activar y ver modelos)."""

    permiso_requerido = "ml.ver_predicciones"
    PERMISOS = {
        "list": "ml.ver_predicciones",
        "retrieve": "ml.ver_predicciones",
        "create": "ml.predecir",
    }


class PrediccionViewSet(
    PermisosML, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Historial (lista y ficha) y predicción; sin update ni delete."""

    auditoria_modulo = registro.MODULO_AUDITORIA
    throttle_classes = (ScopedRateThrottle,)

    def get_serializer_class(self):
        if self.action == "create":
            return PrediccionEscrituraSerializer
        if self.action == "retrieve":
            return PrediccionDetalleSerializer
        return PrediccionListaSerializer

    def get_queryset(self):
        comparacion = self.request.query_params.get("comparacion")
        if comparacion not in COMPARACIONES:
            raise ValidationError(
                {"comparacion": "Use pendiente, comparada o todas."}
            )
        base = Prediccion.objects.select_related(
            "campania", "campania__parcela", "campania__parcela__productor",
            "campania__cultivo", "campania__variedad",
            "modelo", "modelo__entrenamiento", "creado_por",
        ).order_by(*_ORDEN_PREDICCIONES).filter(
            **COMPARACIONES[comparacion]
        )
        return filtrar_asignados(
            base, self.request.user, campo="campania__parcela__productor_id"
        )

    def get_throttles(self):
        """Límite de 30 por hora y usuario solo al predecir (232)."""
        self.throttle_scope = (
            "ml_prediccion" if self.action == "create" else None
        )
        return super().get_throttles()

    def create(self, request, *args, **kwargs):
        """Predecir vía servicio: el cliente solo manda campaña y
        planificados; los 4xx en español los traduce el servicio."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campania = serializer.validated_data["campania"]
        planificados = {
            clave: serializer.validated_data[clave]
            for clave in servicio.CLAVES_PLANIFICADAS
            if serializer.validated_data.get(clave) is not None
        }
        try:
            resultado = servicio.predecir(
                campania, request.user, planificados=planificados
            )
        except servicio.ErrorVariables as error:
            raise ValidationError({"planificados": str(error)})
        except servicio.ErrorEstado as error:
            raise ValidationError({"estado": str(error)})
        except (servicio.ErrorSinModelo, servicio.ErrorModelo) as error:
            return Response({"detail": str(error)}, status=409)
        datos = PrediccionDetalleSerializer(
            resultado["prediccion"], context={"request": request}
        ).data
        return Response(datos, status=201)


class ModeloViewSet(PermisosML, mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    """Métricas de los modelos entrenados y activación (222)."""

    queryset = ModeloML.objects.select_related("entrenamiento").order_by(
        *_ORDEN_MODELOS
    )
    serializer_class = ModeloListaSerializer
    PERMISOS = {
        "list": "ml.ver_modelos",
        "activar": "ml.activar_modelo",
    }

    @action(detail=True, methods=("post",), url_path="activar")
    def activar(self, request, pk=None):
        """POST /modelos/{id}/activar/: un solo modelo activo, con
        archivo, huella y predicción de prueba (mismos controles que el
        comando; decisión 222)."""
        modelo = self.get_object()
        try:
            registro.activar_modelo(modelo, request.user)
        except registro.ErrorRegistro as error:
            return Response({"detail": str(error)}, status=400)
        return Response(self.get_serializer(modelo).data)


class ModeloActivoViewSet(PermisosML, viewsets.GenericViewSet):
    """GET /modelo-activo/: el modelo vigente para el banner de la
    pantalla Modelos y Predicción (239); sin activo, 404."""

    queryset = ModeloML.objects.none()
    serializer_class = ModeloListaSerializer
    PERMISOS = {"list": "ml.ver_modelos"}

    def list(self, request, *args, **kwargs):
        modelo = registro.modelo_activo()
        if modelo is None:
            return Response(
                {"detail": "No hay ningún modelo activo."}, status=404
            )
        return Response(self.get_serializer(modelo).data)


class CampaniaPredecibleViewSet(
    PermisosML, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """Selector de campañas donde se puede predecir (227): PLANIFICADA
    o EN_PRODUCCION y, para el Técnico, solo de sus asignados."""

    serializer_class = CampaniaPredecibleSerializer
    PERMISOS = {"list": "ml.predecir"}

    def get_queryset(self):
        base = Campania.objects.filter(
            estado__in=servicio.ELEGIBLES
        ).select_related(
            "parcela", "parcela__productor", "cultivo", "variedad"
        ).order_by("-fecha_inicio", "id")
        return filtrar_asignados(
            base, self.request.user, campo="parcela__productor_id"
        )


_DETALLE_NO_ACTIVA = (
    "Ya hay un entrenamiento en curso: espere a que termine o "
    "cancelelo desde la pantalla."
)
_DETALLE_TERMINADA = "La tarea ya terminó: no se puede cancelar."


class EstadoDatosViewSet(PermisosML, viewsets.GenericViewSet):
    """GET /estado-datos: la pantalla Entrenar pregunta al sistema si
    hay datos suficientes (decisión 263) y con qué sello de honestidad
    (262). Solo ml.entrenar."""

    queryset = TareaEntrenamiento.objects.none()
    serializer_class = TareaEntrenamientoSerializer
    PERMISOS = {"list": "ml.entrenar"}

    def list(self, request, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM vw_dataset_entrenamiento")
            filas = cursor.fetchone()[0]
        origen = trabajo.datos_de_entorno()
        return Response(
            {
                "filas": filas,
                "minimo_entrenamiento": registro.MINIMO_REGISTROS,
                "listo": filas >= registro.MINIMO_REGISTROS,
                "origen_datos": origen,
                "datos_demostracion": "demostr" in origen.lower(),
            }
        )


class TareaEntrenamientoViewSet(
    PermisosML, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Historial, alta y cancelación de las tareas de entrenamiento
    (decisión 263). El frontend consulta el progreso cada 5 s solo
    mientras hay tarea activa."""

    queryset = TareaEntrenamiento.objects.select_related(
        "usuario", "resultado"
    ).order_by("-creado_en", "id")
    serializer_class = TareaEntrenamientoSerializer
    auditoria_modulo = registro.MODULO_AUDITORIA
    throttle_classes = (ScopedRateThrottle,)
    PERMISOS = {
        "list": "ml.entrenar",
        "retrieve": "ml.entrenar",
        "create": "ml.entrenar",
        "cancelar": "ml.entrenar",
        "resultados": "ml.entrenar",
    }

    def get_throttles(self):
        """5 por día y por usuario solo al pedir un entrenamiento (261)."""
        self.throttle_scope = (
            "ml_entrenamiento" if self.action == "create" else None
        )
        return super().get_throttles()

    def create(self, request, *args, **kwargs):
        """Alta de la tarea: una sola activa en todo el sistema (409,
        decisión 255); la carrera con otro trabajador la resuelve el
        índice único `uq_tarea_activa`."""
        if TareaEntrenamiento.objects.filter(
            estado__in=ESTADOS_ACTIVOS_TAREA
        ).exists():
            return Response({"detail": _DETALLE_NO_ACTIVA}, status=409)
        try:
            with transaction.atomic():
                tarea = TareaEntrenamiento.objects.create(
                    usuario=request.user
                )
        except IntegrityError:
            return Response({"detail": _DETALLE_NO_ACTIVA}, status=409)
        return Response(self.get_serializer(tarea).data, status=201)

    @action(detail=True, methods=("post",))
    def cancelar(self, request, pk=None):
        """POST /entrenamientos/{id}/cancelar/: solo mientras siga
        activa (251); el trabajador mata el subproceso al verla."""
        tarea = self.get_object()
        cambiadas = TareaEntrenamiento.objects.filter(
            pk=tarea.pk, estado__in=ESTADOS_ACTIVOS_TAREA
        ).update(estado="CANCELADA")
        if not cambiadas:
            return Response({"detail": _DETALLE_TERMINADA}, status=409)
        tarea.refresh_from_db()
        return Response(self.get_serializer(tarea).data)

    @action(detail=True, methods=("get",))
    def resultados(self, request, pk=None):
        """GET /entrenamientos/{id}/resultados/: los 3 candidatos con
        el criterio escrito (264); sin resultado aún, 404."""
        tarea = self.get_object()
        if tarea.resultado_id is None:
            return Response(
                {"detail": "La tarea aún no tiene resultado."}, status=404
            )
        return Response(
            ResultadoEntrenamientoSerializer(tarea.resultado).data
        )
