"""Cálculos compartidos del panel (Semana 16) y de los reportes (Semana 17).

Una sola fuente de cálculo: los reportes importan de aquí los mismos
filtros, el mismo resumen agrupado con rendimiento PONDERADO y las
mismas marcas de provisional y pocos datos que pinta el panel, de modo
que con los mismos filtros ambas cifras coinciden. Ningún reporte
reimplementa estos cálculos.

Las funciones devuelven números crudos (Decimals): quien responde la
API los formatea como texto con 2 decimales —convención global— y los
generadores de Excel/PDF los escriben como números.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from campanias.models import Campania
from productores.views import _id_numerico

# Decimales de las cifras agregadas (ha y kg)
PRECISION = Decimal("0.01")

# Mínimo de campañas de una fila para considerar su promedio representativo
MINIMO_CAMPANIAS_FILA = 3

ESTADOS_CAMPANIA = (
    "PLANIFICADA",
    "EN_PRODUCCION",
    "COSECHADA",
    "CERRADA",
    "CANCELADA",
)
MENSAJE_ESTADO = (
    "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, CERRADA o CANCELADA."
)


def ahora_lima():
    """Hora actual en la zona del proyecto (America/Lima) con huso."""
    return timezone.localtime()


def texto(valor):
    """Cifra decimal a texto con 2 decimales (None se queda en null)."""
    if valor is None:
        return None
    return str(Decimal(valor).quantize(PRECISION, rounding=ROUND_HALF_UP))


def cuantizar(valor, decimales=2):
    """Cifra decimal redondeada a N decimales, para los archivos (None
    se queda en None)."""
    if valor is None:
        return None
    patron = Decimal(1).scaleb(-decimales)
    return Decimal(valor).quantize(patron, rounding=ROUND_HALF_UP)


def id_existente(params, campo, modelo, mensaje):
    """Id numérico que además existe en la tabla (si viene en la URL)."""
    if not params.get(campo):
        return None
    ident = _id_numerico(params[campo], campo)
    if not modelo.objects.filter(pk=ident).exists():
        raise ValidationError({campo: mensaje})
    return ident


def estado_de_campania(params):
    """?estado= con la misma validación de los listados (400 si no es
    uno de los cinco estados; sin parámetro devuelve None)."""
    estado = params.get("estado")
    if not estado:
        return None
    if estado not in ESTADOS_CAMPANIA:
        raise ValidationError({"estado": MENSAJE_ESTADO})
    return estado


def filtros_eco(params):
    """Los filtros del panel ya convertidos, para el eco de la respuesta.

    Un id no numérico responde 400 aquí (la conversión es la misma que
    aplica aplicar_filtros_produccion).
    """
    return {
        "periodo": params.get("periodo") or None,
        "cultivo": (
            _id_numerico(params["cultivo"], "cultivo")
            if params.get("cultivo")
            else None
        ),
        "provincia": (
            _id_numerico(params["provincia"], "provincia")
            if params.get("provincia")
            else None
        ),
        "distrito": (
            _id_numerico(params["distrito"], "distrito")
            if params.get("distrito")
            else None
        ),
        "comunidad": (
            _id_numerico(params["comunidad"], "comunidad")
            if params.get("comunidad")
            else None
        ),
    }


def aplicar_filtros_produccion(base, params):
    """Los cinco filtros del panel sobre un queryset de Produccion:
    periodo, cultivo, provincia, distrito y comunidad (la ubicación es
    la de la parcela). Un id no numérico → 400."""
    if params.get("periodo"):
        base = base.filter(campania__periodo=params["periodo"])
    if params.get("cultivo"):
        base = base.filter(
            campania__cultivo_id=_id_numerico(params["cultivo"], "cultivo")
        )
    if params.get("provincia"):
        base = base.filter(
            campania__parcela__comunidad__distrito__provincia_id=_id_numerico(
                params["provincia"], "provincia"
            )
        )
    if params.get("distrito"):
        base = base.filter(
            campania__parcela__comunidad__distrito_id=_id_numerico(
                params["distrito"], "distrito"
            )
        )
    if params.get("comunidad"):
        base = base.filter(
            campania__parcela__comunidad_id=_id_numerico(
                params["comunidad"], "comunidad"
            )
        )
    return base


def resumen_agrupado(base, agrupar="cultivo"):
    """Resumen agrupado (por cultivo o distrito) con números crudos.

    Por fila: campañas, superficie cosechada, producción kg,
    rendimiento PONDERADO (kg ÷ superficie cosechada, el que manda en el
    cierre), rendimiento promedio (media simple, solo comparación),
    provisional si queda alguna campaña sin cerrar y pocos_datos con
    menos de MINIMO_CAMPANIAS_FILA campañas. Orden: producción
    descendente y luego por clave.
    """
    if agrupar == "cultivo":
        grupos = base.values(
            clave=F("campania__cultivo_id"),
            etiqueta=F("campania__cultivo__nombre"),
        )
    elif agrupar == "distrito":
        grupos = base.values(
            clave=F("campania__parcela__comunidad__distrito_id"),
            etiqueta=F("campania__parcela__comunidad__distrito__nombre"),
        )
    else:
        raise ValueError(f"Agrupación no soportada: {agrupar}")
    filas = []
    for fila in (
        grupos.annotate(
            campanias=Count("id"),
            superficie_ha=Sum("superficie_cosechada_ha"),
            produccion_kg=Sum("produccion_kg"),
            rendimiento_promedio=Avg("rendimiento_kg_ha"),
            sin_cerrar=Count(
                "id", filter=Q(campania__estado=Campania.ESTADO_COSECHADA)
            ),
        )
        .order_by("-produccion_kg", "clave")
    ):
        superficie = fila["superficie_ha"]
        kilos = fila["produccion_kg"]
        filas.append(
            {
                "clave": fila["clave"],
                "etiqueta": fila["etiqueta"],
                "campanias": fila["campanias"],
                "superficie_ha": superficie,
                "produccion_kg": kilos,
                "rendimiento_kg_ha": (
                    None if not superficie else kilos / superficie
                ),
                "rendimiento_promedio_kg_ha": fila["rendimiento_promedio"],
                "provisional": fila["sin_cerrar"] > 0,
                "pocos_datos": fila["campanias"] < MINIMO_CAMPANIAS_FILA,
            }
        )
    return filas


def totales_de(base):
    """Totales crudos del conjunto (agregado general, sin agrupar)."""
    totales = base.aggregate(
        campanias=Count("id"),
        superficie_ha=Sum("superficie_cosechada_ha"),
        produccion_kg=Sum("produccion_kg"),
    )
    superficie = totales["superficie_ha"]
    totales["rendimiento_kg_ha"] = (
        None if not superficie else totales["produccion_kg"] / superficie
    )
    return totales
