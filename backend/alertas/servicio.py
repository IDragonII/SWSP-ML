"""Servicio de evaluación de alertas (Semana 15, HU-124..HU-132).

La lógica vive en la aplicación, no en triggers: se ejecuta al confirmar
cada escritura relevante (los ganchos transaction.on_commit de
seguimiento y produccion) y en el barrido diario (el comando
evaluar_alertas o la evaluación manual con parametros.gestionar). La
evaluación nunca bloquea el negocio: un fallo se registra en el log y
pasa — el barrido diario es la red de seguridad.

Tipos que se generan hoy: INCIDENCIA_SEVERA (incidencia con severidad
ALTA y sin anular; una sola por incidencia) y SIN_ACTIVIDAD (campaña
planificada ya iniciada o en producción sin actividades recientes; una
pendiente por campaña, con periodo de gracia tras la atención manual).
RENDIMIENTO_BAJO está permitido en la tabla pero se generará con el
modelo de regresión (Sprint 14), no aquí.

Cierre automático: cuando la condición deja de cumplirse, la alerta
pendiente queda atendida SIN usuario y SIN nota (así se distingue de la
atención manual). Una alerta cerrada automáticamente se reabre sola si
la condición vuelve; una atendida a mano solo se reabre por la API.

Mensajes en español, sin nombres, DNI ni teléfono (RF-63/RF-64): solo
código de campaña, cultivo, tipo de incidencia y fechas. La fecha del
mensaje es fija; los días transcurridos se calculan al leer (API).
"""
import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from auditoria.registrar import registrar_evento
from campanias.models import Campania
from seguimiento.models import Actividad, Incidencia
from sistema.models import ParametroSistema

from .models import Alerta

logger = logging.getLogger(__name__)

TZ_LIMA = ZoneInfo("America/Lima")

# Estados cuya campaña aún espera trabajo: solo ellos generan
# SIN_ACTIVIDAD (una campaña cosechada/cerrada/cancelada ya no).
_ESTADOS_EVALUABLES = (Campania.ESTADO_PLANIFICADA, Campania.ESTADO_EN_PRODUCCION)

_DIAS_POR_DEFECTO = 30


def fecha_hoy():
    """Fecha civil de Lima (el backend guarda UTC; el sistema es de Perú)."""
    return timezone.now().astimezone(TZ_LIMA).date()


def _dias_sin_actividad():
    """Umbral del parámetro dias_sin_actividad (entero ≥ 1; por defecto 30).

    La validación del 1–365 la hace el serializer de parámetros (S15);
    aquí se defiende la lectura por si la fila se toca a mano en la BD.
    """
    try:
        fila = ParametroSistema.objects.get(clave="dias_sin_actividad")
        valor = int(fila.valor)
    except (ParametroSistema.DoesNotExist, ValueError, TypeError):
        return _DIAS_POR_DEFECTO
    return valor if valor >= 1 else _DIAS_POR_DEFECTO


def _cerrar_automaticamente(alerta):
    """Cierra la alerta como la cierra el sistema: sin usuario y sin nota."""
    alerta.atendida = True
    alerta.atendida_por = None
    alerta.atendida_en = timezone.now()
    alerta.nota_atencion = None
    alerta.save(update_fields=("atendida", "atendida_por", "atendida_en", "nota_atencion"))


def evaluar_incidencia(incidencia):
    """Crea, reabre o cierra la alerta INCIDENCIA_SEVERA de una incidencia.

    Devuelve {"creadas": n, "cerradas": m} (cada número 0 o 1).
    """
    resultado = {"creadas": 0, "cerradas": 0}
    condicion = (not incidencia.anulada) and incidencia.severidad == Incidencia.ALTA
    alerta = Alerta.objects.filter(incidencia=incidencia).first()
    if condicion:
        if alerta is None:
            campania = incidencia.campania
            Alerta.objects.create(
                productor=campania.parcela.productor,
                campania=campania,
                incidencia=incidencia,
                tipo=Alerta.TIPO_INCIDENCIA_SEVERA,
                mensaje=(
                    f"Incidencia severa de {incidencia.tipo_incidencia.nombre} "
                    f"el {incidencia.fecha} en la campaña {campania.periodo}."
                )[:250],
            )
            resultado["creadas"] = 1
        elif alerta.atendida and alerta.atendida_por is None:
            # Cierre automático anterior y la condición volvió: se reabre
            alerta.atendida = False
            alerta.atendida_en = None
            alerta.save(update_fields=("atendida", "atendida_en"))
    else:
        if alerta is not None and not alerta.atendida:
            _cerrar_automaticamente(alerta)
            resultado["cerradas"] = 1
    return resultado


def evaluar_campania(campania, hoy=None):
    """Crea, reabre o cierra la alerta SIN_ACTIVIDAD de una campaña.

    Devuelve {"creadas": n, "cerradas": m} (cada número 0 o 1).
    """
    resultado = {"creadas": 0, "cerradas": 0}
    hoy = hoy or fecha_hoy()
    evaluable = (
        campania.estado in _ESTADOS_EVALUABLES and campania.fecha_inicio <= hoy
    )
    pendiente = Alerta.objects.filter(
        campania=campania, tipo=Alerta.TIPO_SIN_ACTIVIDAD, atendida=False
    ).first()
    if not evaluable:
        if pendiente is not None:
            _cerrar_automaticamente(pendiente)
            resultado["cerradas"] = 1
        return resultado
    umbral = _dias_sin_actividad()
    ultima_actividad = Actividad.objects.filter(
        campania=campania, anulada=False
    ).aggregate(fecha=Max("fecha"))["fecha"]
    referencia = ultima_actividad or campania.fecha_siembra or campania.fecha_inicio
    dias = (hoy - referencia).days
    if dias <= umbral:
        if pendiente is not None:
            _cerrar_automaticamente(pendiente)
            resultado["cerradas"] = 1
        return resultado
    if pendiente is not None:
        return resultado
    if _en_periodo_de_gracia(campania, hoy, umbral):
        return resultado
    Alerta.objects.get_or_create(
        campania=campania,
        tipo=Alerta.TIPO_SIN_ACTIVIDAD,
        atendida=False,
        defaults={
            "productor": campania.parcela.productor,
            "mensaje": (
                f"La campaña {campania.periodo} ({campania.cultivo.nombre}) "
                f"no registra actividades desde el {referencia}."
            )[:250],
        },
    )
    resultado["creadas"] = 1
    return resultado


def _en_periodo_de_gracia(campania, hoy, umbral):
    """True si la última atención MANUAL de esta campaña+tipo fue hace < umbral días.

    Tras atender a mano una SIN_ACTIVIDAD no se reabre la lluvia de
    alertas hasta pasados los mismos días del parámetro (HU-131).
    """
    ultima_manual = (
        Alerta.objects.filter(
            campania=campania,
            tipo=Alerta.TIPO_SIN_ACTIVIDAD,
            atendida=True,
        )
        .exclude(atendida_por=None)
        .order_by("-atendida_en")
        .first()
    )
    if ultima_manual is None or ultima_manual.atendida_en is None:
        return False
    atendida_hoy = ultima_manual.atendida_en.astimezone(TZ_LIMA).date()
    return (hoy - atendida_hoy).days < umbral


def evaluar_todo(hoy=None, dry_run=False):
    """Barrido completo de condiciones: crea, reabre y cierra alertas.

    dry_run=True evalúa sin escribir (la transacción se revierte; no
    registra el evento de auditoría). Devuelve {"creadas": n, "cerradas": m}.
    """
    hoy = hoy or fecha_hoy()
    with transaction.atomic():
        resultado = {"creadas": 0, "cerradas": 0}
        campanias_evaluables = Campania.objects.filter(
            estado__in=_ESTADOS_EVALUABLES, fecha_inicio__lte=hoy
        ).select_related("parcela__productor", "cultivo")
        for campania in campanias_evaluables:
            parcial = evaluar_campania(campania, hoy=hoy)
            resultado["creadas"] += parcial["creadas"]
            resultado["cerradas"] += parcial["cerradas"]
        # Pendientes de campañas que dejaron de ser evaluables (estado)
        campanias_evaluables_ids = set(campanias_evaluables.values_list("id", flat=True))
        for alerta in Alerta.objects.filter(
            tipo=Alerta.TIPO_SIN_ACTIVIDAD, atendida=False
        ).select_related("campania"):
            if alerta.campania_id not in campanias_evaluables_ids:
                _cerrar_automaticamente(alerta)
                resultado["cerradas"] += 1
        for incidencia in Incidencia.objects.filter(
            severidad=Incidencia.ALTA, anulada=False
        ).select_related("campania__parcela__productor", "tipo_incidencia"):
            parcial = evaluar_incidencia(incidencia)
            resultado["creadas"] += parcial["creadas"]
            resultado["cerradas"] += parcial["cerradas"]
        # Pendientes cuya condición ya no se cumple (anulada, severidad
        # rebajada o campaña ya no evaluable) — red de seguridad
        for alerta in Alerta.objects.filter(
            tipo=Alerta.TIPO_INCIDENCIA_SEVERA, atendida=False
        ).select_related("incidencia"):
            incidencia = alerta.incidencia
            condicion = incidencia is not None and (
                not incidencia.anulada
            ) and incidencia.severidad == Incidencia.ALTA
            if not condicion:
                _cerrar_automaticamente(alerta)
                resultado["cerradas"] += 1
        if dry_run:
            transaction.set_rollback(True)
        else:
            registrar_evento(
                usuario=None,
                accion="MODIFICAR",
                modulo="alertas",
                tabla="alertas",
                detalle={
                    "resumen": True,
                    "creadas": resultado["creadas"],
                    "cerradas": resultado["cerradas"],
                },
            )
    return resultado


def tras_confirmar(tipo, obj):
    """Agenda la evaluación de una incidencia o campaña tras el COMMIT.

    Se llama dentro del bloque atómico del evento de negocio: la
    evaluación ve los datos confirmados (relee el registro —algún trigger
    pudo cambiar el estado en memoria—) y un fallo no revierte el negocio
    (se loguea y pasa; el barrido diario lo recoge).
    """
    modelo = Incidencia if tipo == "incidencia" else Campania
    pk = obj.pk
    if tipo == "incidencia":
        select = ("campania__parcela__productor", "campania__cultivo", "tipo_incidencia")
    else:
        select = ("parcela__productor", "cultivo")

    def _hacer():
        try:
            recargado = modelo.objects.select_related(*select).get(pk=pk)
            if tipo == "incidencia":
                evaluar_incidencia(recargado)
            else:
                evaluar_campania(recargado)
        except modelo.DoesNotExist:
            pass
        except Exception:
            logger.exception(
                "alertas: falló la evaluación de %s id=%s", tipo, pk
            )

    transaction.on_commit(_hacer)
