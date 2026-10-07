"""Manejador de excepciones de DRF: mensajes 429 en español con el tiempo.

El resto de errores conserva el comportamiento por defecto de DRF.
"""
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler as manejar_drf


def manejar_excepciones(exc, contexto):
    respuesta = manejar_drf(exc, contexto)
    if isinstance(exc, Throttled) and respuesta is not None:
        espera = int(getattr(exc, 'wait', 0) or 0)
        respuesta.data = {
            'detail': f'Demasiadas solicitudes. Intenta de nuevo en {espera} segundos.',
            'retry_after': espera,
        }
        if espera:
            respuesta['Retry-After'] = str(espera)
    return respuesta
