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


# --- Cambio de contraseña propio (Semana 13, HU-112) --------------------
# Máximo CAMBIO_CLAVE_INTENTOS intentos (éxito o fallo) por usuario y hora:
# un atacante con la sesión robada no puede probar contraseñas nuevas.
PREFIJO_CAMBIO_CLAVE = 'sigpa:cambio_clave:'
CAMBIO_CLAVE_INTENTOS = 5
CAMBIO_CLAVE_VENTANA_SEGUNDOS = 3600


def registrar_cambio_clave(username):
    """Suma un intento de cambio de contraseña propio.

    Devuelve (True, 0) si cabe en el límite; (False, segundos_restantes)
    si se superó el máximo de la hora en curso.
    """
    clave = PREFIJO_CAMBIO_CLAVE + _clave(username)
    ahora = time.time()
    registro = cache.get(clave)
    if not isinstance(registro, dict) or ahora >= registro.get('expira', 0):
        cache.set(
            clave,
            {'intentos': 1, 'expira': ahora + CAMBIO_CLAVE_VENTANA_SEGUNDOS},
            timeout=CAMBIO_CLAVE_VENTANA_SEGUNDOS,
        )
        return True, 0
    registro['intentos'] += 1
    cache.set(clave, registro, timeout=CAMBIO_CLAVE_VENTANA_SEGUNDOS)
    if registro['intentos'] > CAMBIO_CLAVE_INTENTOS:
        return False, max(1, math.ceil(registro['expira'] - ahora))
    return True, 0


def limpiar_cambio_clave(username):
    """Borra el contador tras un cambio exitoso (la ventana no castiga
    al usuario que sí cambió su contraseña)."""
    cache.delete(PREFIJO_CAMBIO_CLAVE + _clave(username))
