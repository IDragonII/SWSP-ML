"""Hilo trabajador dentro del proceso web (despliegue gratuito, S24).

Render free solo ofrece web services (sin background workers ni cron),
así que el bucle de `procesar_entrenamientos` corre en un hilo daemon
del propio proceso gunicorn cuando `TRABAJADOR_EN_WEB=1`. El ciclo no
cambia: `--una-vez` reclama con `SELECT ... FOR UPDATE SKIP LOCKED` y
vigila el subproceso con su tope, latido y kill; solo cambia quién
duerme entre ciclos. En local y en las pruebas la bandera no existe y
no se arranca nada.

Al arrancar recupera las tareas huérfanas: si la instancia murió a
mitad de un entrenamiento, la fila quedó PROCESANDO sin nadie que la
vigile y el índice único `uq_tarea_activa` bloquearía todo el futuro;
aquí se marca FALLIDA para poder pedir el entrenamiento de nuevo.
"""
import logging
import os
import threading
import time

from django.core.management import call_command
from django.db import connection

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 5.0
MENSAJE_HUERFANA = (
    "Trabajador reiniciado: el entrenamiento quedó interrumpido "
    "(la instancia se reinició a mitad de tarea). Pídelo de nuevo."
)


def configurado():
    """True solo con TRABAJADOR_EN_WEB activo (Render)."""
    return os.getenv("TRABAJADOR_EN_WEB", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def iniciar():
    """Arranca el hilo del trabajador una vez si la bandera está activa.

    Devuelve True si se creó el hilo (la bandera mandó); en local y en
    las pruebas devuelve False sin tocar nada.
    """
    if not configurado():
        return False
    threading.Thread(
        target=bucle, name="trabajador-entrenamientos", daemon=True
    ).start()
    return True


def recuperar_huerfanas():
    """Marca FALLIDA toda tarea PROCESANDO encontrada al arrancar.

    Un solo trabajador por diseño: al abrirse el proceso, cualquier
    PROCESANDO es de un ciclo anterior que murió con la instancia
    (subproceso e hilo vigilante ya no existen). Devuelve cuántas
    tocó. Pendientes y completadas no se tocan.
    """
    from ml.models import TareaEntrenamiento

    huerfanas = TareaEntrenamiento.objects.filter(estado="PROCESANDO")
    total = huerfanas.count()
    if total:
        huerfanas.update(
            estado="FALLIDA",
            error=MENSAJE_HUERFANA,
            latido=None,
            progreso={"etapa": "recuperada", "pct": 100},
        )
        logger.warning(
            "%s tarea(s) de entrenamiento huérfana(s) marcada(s) FALLIDA",
            total,
        )
    return total


def bucle():
    """Recupera huérfanas y atiende tareas para siempre (hilo daemon)."""
    recuperar_huerfanas()
    while True:
        try:
            call_command("procesar_entrenamientos", "--una-vez")
        except Exception:  # noqa: BLE001 (el ciclo no debe morirse)
            logger.exception("ciclo del trabajador de entrenamientos falló")
        finally:
            connection.close()
        time.sleep(INTERVALO_SEGUNDOS)
