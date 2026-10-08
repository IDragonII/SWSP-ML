"""Manejador de excepciones de DRF: mensajes 429 y 404 en español.

El 404 pasa a {"detail": "No encontrado."} (decisión 11 de
docs/decisiones_semana4.md): la API responde siempre en español, también
en los «No ... matches the given query» que DRF traduce por defecto.
El resto de errores conserva el comportamiento por defecto de DRF.
"""
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler as manejar_drf


def manejar_excepciones(exc, contexto):
    respuesta = manejar_drf(exc, contexto)
    if respuesta is None:
        return None
    if getattr(respuesta, "status_code", None) == 404:
        respuesta.data = {"detail": "No encontrado."}
        return respuesta
    if isinstance(exc, Throttled):
        espera = int(getattr(exc, 'wait', 0) or 0)
        respuesta.data = {
            'detail': f'Demasiadas solicitudes. Intenta de nuevo en {espera} segundos.',
            'retry_after': espera,
        }
        if espera:
            respuesta['Retry-After'] = str(espera)
    return respuesta
