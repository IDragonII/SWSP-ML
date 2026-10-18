"""API de alertas (Semana 15, HU-124..HU-132).

Listado y detalle de alertas (alertas.ver), atención manual
(alertas.atender) y reapertura (alertas.atender). SIN escritura de
alertas por la API: las crea y cierra solo el sistema (el servicio de
evaluación); SIN borrado (405). Listado con pestañas por estado
(?estado=PENDIENTES|ATENDIDAS|TODAS, por defecto PENDIENTES), filtros
por tipo, campaña y productor, búsqueda por mensaje y código/nombre del
productor, orden pendientes primero y más recientes arriba, paginación
global (20 por página). El Técnico solo ve las alertas de SUS
productores asignados (reutiliza el filtro de la Semana 4).

Además: /alertas/resumen/ (conteo para la insignia del menú),
/alertas/evaluacion/ (GET: última evaluación y atraso; POST: evaluación
manual con parametros.gestionar y límite de una cada 5 minutos) y
/alertas/productores-en-riesgo/ (productores con alertas pendientes).
"""
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from auditoria.models import Auditoria
from auditoria.registrar import ip_de_request, registrar_evento
from productores.models import Productor
from productores.views import BusquedaPorNombre, PermisosPorAccion, SoloSusProductores

from .models import Alerta
from .serializers import (
    AlertaDetalleSerializer,
    AlertaListaSerializer,
    AtenderEscrituraSerializer,
)
from . import servicio

# Ventana del límite de la evaluación manual (HU-131: una cada 5 min)
_CLAVE_THROTTLE = "alertas:evaluar_manual"
_VENTANA_THROTTLE_SEGUNDOS = 300

# Umbral de atraso del proceso diario (HU-132)
_HORAS_ATRASO = 36


class PermisosAlerta(PermisosPorAccion):
    """Permisos de alertas: alertas.ver (leer) y alertas.atender
    (atender/reabrir; sembrados en la Semana 2)."""

    permiso_requerido = "alertas.ver"
    PERMISOS = {
        "list": "alertas.ver",
        "retrieve": "alertas.ver",
        "resumen": "alertas.ver",
        "productores_en_riesgo": "alertas.ver",
        "evaluacion": "alertas.ver",
        "evaluar": "parametros.gestionar",
        "atender": "alertas.atender",
        "reabrir": "alertas.atender",
    }


class AlertasViewSet(
    PermisosAlerta,
    SoloSusProductores,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Listado, detalle, atender y reabrir (sin POST/PATCH/DELETE)."""

    queryset = Alerta.objects.select_related(
        "productor", "campania", "incidencia", "atendida_por"
    )
    serializer_class = AlertaListaSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = (
        "mensaje",
        "productor__codigo",
        "productor__apellidos",
        "productor__nombres",
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AlertaDetalleSerializer
        return AlertaListaSerializer

    def get_queryset(self):
        queryset = self._filtrar_asignados(
            super().get_queryset(), "productor_id"
        )
        if self.action != "list":
            # El detalle, atender y reabrir ven cualquier estado: la
            # pestaña de estado (HU-127) es solo del listado
            return queryset
        params = self.request.query_params
        estado = params.get("estado", "PENDIENTES")
        if estado not in ("PENDIENTES", "ATENDIDAS", "TODAS"):
            raise ValidationError(
                {"estado": "Use PENDIENTES, ATENDIDAS o TODAS."}
            )
        if estado == "PENDIENTES":
            queryset = queryset.filter(atendida=False)
        elif estado == "ATENDIDAS":
            queryset = queryset.filter(atendida=True)
        if params.get("tipo"):
            tipo = params["tipo"]
            if tipo not in dict(Alerta.TIPOS):
                raise ValidationError(
                    {"tipo": "Use INCIDENCIA_SEVERA, SIN_ACTIVIDAD o RENDIMIENTO_BAJO."}
                )
            queryset = queryset.filter(tipo=tipo)
        if params.get("campania"):
            try:
                campania_id = int(params["campania"])
            except ValueError:
                raise ValidationError({"campania": "Debe ser un id numérico."})
            queryset = queryset.filter(campania_id=campania_id)
        if params.get("productor"):
            try:
                productor_id = int(params["productor"])
            except ValueError:
                raise ValidationError({"productor": "Debe ser un id numérico."})
            queryset = queryset.filter(productor_id=productor_id)
        return queryset

    @action(detail=False, methods=("get",), url_path="resumen")
    def resumen(self, request):
        """Conteo de pendientes para la insignia del menú (HU-127) y
        por_tipo para la franja del dashboard (Semana 16): la insignia
        sigue leyendo solo «pendientes»; la clasificación sale completa
        con ceros, con la misma regla de alcance."""
        pendientes = self._filtrar_asignados(
            Alerta.objects.all(), "productor_id"
        ).filter(atendida=False)
        por_tipo = {codigo: 0 for codigo, _ in Alerta.TIPOS}
        for fila in pendientes.values("tipo").annotate(total=Count("id")):
            por_tipo[fila["tipo"]] = fila["total"]
        return Response({"pendientes": pendientes.count(), "por_tipo": por_tipo})

    @action(
        detail=False, methods=("get",), url_path="productores-en-riesgo"
    )
    def productores_en_riesgo(self, request):
        """Productores con alertas pendientes (HU-126): cada uno con su
        conteo, los tipos pendientes y la alerta más reciente."""
        base = self._filtrar_asignados(
            Alerta.objects.filter(atendida=False), "productor_id"
        )
        agregados = (
            base.values("productor_id")
            .annotate(pendientes=Count("id"))
            .order_by("-pendientes", "productor_id")
        )
        ids = [a["productor_id"] for a in agregados]
        por_id = {
            p.pk: p
            for p in Productor.objects.filter(pk__in=ids).select_related(
                "comunidad__distrito__provincia"
            )
        }
        tipos_por_productor = {}
        for fila in base.values("productor_id", "tipo").distinct():
            tipos_por_productor.setdefault(fila["productor_id"], []).append(
                fila["tipo"]
            )
        ultima_por_productor = {}
        for alerta in base.order_by("productor_id", "-creada_en"):
            ultima_por_productor.setdefault(alerta.productor_id, alerta)
        filas = []
        for agregado in agregados:
            pid = agregado["productor_id"]
            productor = por_id.get(pid)
            if productor is None:
                continue
            ultima = ultima_por_productor.get(pid)
            filas.append(
                {
                    "productor": pid,
                    "productor_codigo": productor.codigo,
                    "productor_nombre": (
                        f"{productor.apellidos} {productor.nombres}".strip()
                    ),
                    "distrito": productor.comunidad.distrito.nombre,
                    "provincia": productor.comunidad.distrito.provincia.nombre,
                    "pendientes": agregado["pendientes"],
                    "tipos": sorted(tipos_por_productor.get(pid, [])),
                    "ultima_alerta": ultima.mensaje if ultima else None,
                    "ultima_alerta_en": ultima.creada_en if ultima else None,
                }
            )
        return Response({"results": filas})

    @action(detail=False, methods=("get",), url_path="evaluacion")
    def evaluacion(self, request):
        """Estado del proceso diario (HU-132): última evaluación y si
        está atrasada (más de 36 horas)."""
        ultimo = (
            Auditoria.objects.filter(
                modulo="alertas", tabla="alertas", detalle__resumen=True
            )
            .order_by("-fecha")
            .first()
        )
        ahora = timezone.now()
        atrasada = ultimo is None or (
            (ahora - ultimo.fecha).total_seconds() > _HORAS_ATRASO * 3600
        )
        return Response(
            {
                "ultima_evaluacion": ultimo.fecha if ultimo else None,
                "atrasada": atrasada,
                "umbral_horas": _HORAS_ATRASO,
            }
        )

    @action(detail=False, methods=("post",), url_path="evaluar")
    def evaluar(self, request):
        """Evaluación manual (HU-131): parametros.gestionar y una cada
        5 minutos (límite propio con caché, patrón del rate limit de
        login). dry_run admite el parámetro por cuerpo. El 429 se
        construye a mano (como el del cambio de contraseña): el
        manejador global de Throttled sobrescribiría este mensaje."""
        inicio = cache.get(_CLAVE_THROTTLE)
        if inicio is not None:
            transcurrido = int(timezone.now().timestamp() - float(inicio))
            restante = max(1, _VENTANA_THROTTLE_SEGUNDOS - transcurrido)
            respuesta = Response(
                {
                    "detail": "Espera 5 minutos entre evaluaciones manuales.",
                    "retry_after": restante,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            respuesta["Retry-After"] = str(restante)
            return respuesta
        dry_run = request.data.get("dry_run", False)
        if not isinstance(dry_run, bool):
            raise ValidationError({"dry_run": "Debe ser true o false."})
        resultado = servicio.evaluar_todo(dry_run=dry_run)
        cache.set(
            _CLAVE_THROTTLE,
            timezone.now().timestamp(),
            timeout=_VENTANA_THROTTLE_SEGUNDOS,
        )
        return Response({**resultado, "dry_run": dry_run})

    @action(detail=True, methods=("post",), url_path="atender")
    def atender(self, request, pk=None):
        """Atención manual (HU-125): alertas.atender; nota opcional."""
        alerta = self.get_object()
        if alerta.atendida:
            raise ValidationError({"estado": "La alerta ya está atendida."})
        escritor = AtenderEscrituraSerializer(data=request.data)
        escritor.is_valid(raise_exception=True)
        nota = (escritor.validated_data.get("nota") or "").strip() or None
        with transaction.atomic():
            alerta.atendida = True
            alerta.atendida_por = request.user
            alerta.atendida_en = timezone.now()
            alerta.nota_atencion = nota
            alerta.save(
                update_fields=(
                    "atendida",
                    "atendida_por",
                    "atendida_en",
                    "nota_atencion",
                )
            )
            registrar_evento(
                usuario=request.user,
                accion="MODIFICAR",
                modulo="alertas",
                tabla="alertas",
                registro_id=alerta.pk,
                detalle={"operacion": "atender", "nota": nota},
                ip=ip_de_request(request),
            )
        return Response(AlertaDetalleSerializer(
            alerta, context=self.get_serializer_context()
        ).data)

    @action(detail=True, methods=("post",), url_path="reabrir")
    def reabrir(self, request, pk=None):
        """Reabre una alerta atendida A MANO (HU-125): las cerradas
        automáticamente se reabren solas con la condición."""
        alerta = self.get_object()
        if not alerta.atendida:
            raise ValidationError({"estado": "La alerta no está atendida."})
        if alerta.atendida_por is None:
            raise ValidationError(
                {
                    "estado": (
                        "La alerta se cerró automáticamente: se reabre "
                        "sola si la condición vuelve a cumplirse."
                    )
                }
            )
        alerta.atendida = False
        alerta.atendida_por = None
        alerta.atendida_en = None
        alerta.nota_atencion = None
        with transaction.atomic():
            alerta.save(
                update_fields=(
                    "atendida",
                    "atendida_por",
                    "atendida_en",
                    "nota_atencion",
                )
            )
            registrar_evento(
                usuario=request.user,
                accion="MODIFICAR",
                modulo="alertas",
                tabla="alertas",
                registro_id=alerta.pk,
                detalle={"operacion": "reabrir"},
                ip=ip_de_request(request),
            )
        return Response(AlertaDetalleSerializer(
            alerta, context=self.get_serializer_context()
        ).data)
