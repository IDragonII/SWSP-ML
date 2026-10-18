"""Reglas de dependencia entre permisos (Semana 14, HU-115).

Un permiso controla acciones, no datos (el alcance sigue siendo la
asignación de productores). Crear, editar o desactivar en un módulo
exige poder ver ese módulo; las parejas especiales (alertas, reportes y
Machine Learning) siguen la misma idea. Las reglas viven en el código: el
Administrador no crea ni edita permisos, y quien agregue un permiso nuevo
debe registrar aquí su dependencia si la tiene. Se comprueba en el alta
de un rol, en la creación «basado en» y en cada reemplazo del conjunto.
"""
from rest_framework.exceptions import ValidationError

MODULOS_ESTANDAR = (
    'usuarios',
    'catalogos',
    'productores',
    'parcelas',
    'campanias',
    'actividades',
    'recursos',
    'clima',
    'incidencias',
    'produccion',
)

DEPENDENCIAS = {
    f'{modulo}.{accion}': f'{modulo}.ver'
    for modulo in MODULOS_ESTANDAR
    for accion in ('crear', 'editar', 'desactivar')
}
DEPENDENCIAS.update(
    {
        'alertas.atender': 'alertas.ver',
        'reportes.exportar': 'reportes.ver',
        'ml.predecir': 'ml.ver_predicciones',
        'ml.entrenar': 'ml.ver_modelos',
        'ml.activar_modelo': 'ml.ver_modelos',
    }
)


def faltantes_de_dependencias(codigos):
    """Parejas (código, requerido) que faltan en el conjunto."""
    conjunto = set(codigos)
    return [
        (codigo, requerido)
        for codigo, requerido in sorted(DEPENDENCIAS.items())
        if codigo in conjunto and requerido not in conjunto
    ]


def validar_dependencias(codigos):
    """Rechaza el conjunto si alguna dependencia falta, nombrándola."""
    faltantes = faltantes_de_dependencias(codigos)
    if faltantes:
        raise ValidationError(
            {
                'permisos': [
                    f'Para «{codigo}» hace falta «{requerido}».'
                    for codigo, requerido in faltantes
                ]
            }
        )
