"""Filtros compartidos de la bitácora (Semana 13 + Semana 18).

Una sola fuente: la pantalla /api/auditoria/ y el reporte de auditoría
(HU-156) aplican exactamente los mismos criterios, con los mismos
mensajes de 400, para que «lo que ves en pantalla» y «lo que exportas»
sean el mismo conjunto de eventos.

Parámetros admitidos: usuario (id), modulo, accion, tabla, registro
(id), ip, fecha_desde y fecha_hasta (formato AAAA-MM-DD validado aquí;
la validación de rango —obligatorio, 366 días, invertido, futuro— la hace
cada consumidor: la pantalla es indulgente, el reporte exige rango).
"""
from datetime import date

from rest_framework.exceptions import ValidationError


def aplicar_filtros(queryset, params):
    """Los filtros de la bitácora sobre su queryset, en este orden."""
    if params.get("usuario"):
        try:
            usuario_id = int(params["usuario"])
        except ValueError:
            raise ValidationError({"usuario": "Debe ser un id numérico."})
        queryset = queryset.filter(usuario_id=usuario_id)
    if params.get("modulo"):
        queryset = queryset.filter(modulo=params["modulo"])
    if params.get("accion"):
        queryset = queryset.filter(accion=params["accion"])
    if params.get("tabla"):
        queryset = queryset.filter(tabla=params["tabla"])
    if params.get("registro"):
        try:
            registro_id = int(params["registro"])
        except ValueError:
            raise ValidationError({"registro": "Debe ser un id numérico."})
        queryset = queryset.filter(registro_id=registro_id)
    if params.get("ip"):
        queryset = queryset.filter(ip=params["ip"])
    for campo, lookup in (
        ("fecha_desde", "fecha__date__gte"),
        ("fecha_hasta", "fecha__date__lte"),
    ):
        valor = params.get(campo)
        if not valor:
            continue
        try:
            date.fromisoformat(valor)
        except ValueError:
            raise ValidationError(
                {campo: "La fecha no es válida: usa el formato AAAA-MM-DD."}
            )
        queryset = queryset.filter(**{lookup: valor})
    return queryset
