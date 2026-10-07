"""Bloqueo de cuenta tras intentos fallidos de login.

Contadores en la caché de Django (LocMemCache en desarrollo). Los valores
salen de LOGIN_INTENTOS y LOGIN_BLOQUEO_MINUTOS del .env
(docs/decisiones_seguridad.md §6). En un despliegue con varios procesos la
caché debe ser compartida (§8). El desbloqueo es automático por tiempo y
manual desde el panel de Django (acción «Desbloquear acceso»).

Los mensajes nunca revelan si la cuenta existe: el bloqueo se calcula sobre
el nombre escrito, exista o no.
"""
import math
import time

from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger('sigpa.seguridad')

PREFIJO_FALLOS = 'sigpa:login:fallos:'
PREFIJO_BLOQUEO = 'sigpa:login:bloqueo:'


def _clave(username):
    return (username or '').strip()


def segundos_de_bloqueo(username):
    """None si la cuenta no está bloqueada; si lo está, segundos restantes (>= 1)."""
    valor = cache.get(PREFIJO_BLOQUEO + _clave(username))
    if valor is None:
        return None
    restante = valor - time.time()
    if restante <= 0:
        cache.delete(PREFIJO_BLOQUEO + _clave(username))
        return None
    return max(1, math.ceil(restante))


def registrar_fallo(username):
    """Suma un intento fallido. Devuelve (True, segundos) si lo bloqueó."""
    clave_fallos = PREFIJO_FALLOS + _clave(username)
    bloqueo_segundos = settings.LOGIN_BLOQUEO_MINUTOS * 60
    if cache.get(clave_fallos) is None:
        cache.set(clave_fallos, 0, timeout=bloqueo_segundos)
    try:
        fallos = cache.incr(clave_fallos)
    except ValueError:
        # La clave venció entre el get y el incr
        cache.set(clave_fallos, 1, timeout=bloqueo_segundos)
        fallos = 1
    if fallos >= settings.LOGIN_INTENTOS:
        cache.set(PREFIJO_BLOQUEO + _clave(username),
                  time.time() + bloqueo_segundos, timeout=bloqueo_segundos)
        cache.delete(clave_fallos)
        return True, bloqueo_segundos
    return False, 0


def limpiar_acceso(username, motivo='login'):
    """Borra fallos y bloqueo. Devuelve True si había un bloqueo activo.

    motivo='manual' viene del panel de Django; motivo='login' de un acceso
    correcto.
    """
    clave = _clave(username)
    habia_bloqueo = cache.get(PREFIJO_BLOQUEO + clave) is not None
    cache.delete(PREFIJO_FALLOS + clave)
    cache.delete(PREFIJO_BLOQUEO + clave)
    if habia_bloqueo:
        logger.info('login_desbloqueado username=%s motivo=%s', clave, motivo)
    return habia_bloqueo
