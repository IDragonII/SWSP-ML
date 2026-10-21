"""procesar_entrenamientos: trabajador de las tareas de ML (S23, dec. 258).

    manage.py procesar_entrenamientos [--una-vez] [--dry-run]
    manage.py procesar_entrenamientos --ejecutar-tarea ID   (modo hijo)

Modo padre (proceso programado: Task Scheduler, systemd o docker
compose — decisión 252): cada 5 s busca la tarea PENDIENTE, la reclama
con `SELECT ... FOR UPDATE SKIP LOCKED` (dos trabajadores no pisan la
tarea, prueba 399) y la lanza en un SUBPROCESO (`--ejecutar-tarea`).
Mientras corre, el padre vigila:

- **tope de 15 minutos** → mata el árbol de procesos y FALLIDA;
- **latido del hijo con más de 5 minutos** (el hijo latía cada 30 s)
  → mata y FALLIDA;
- **estado CANCELADA** (marcado desde la API) → mata el árbol y el
  estado se queda CANCELADA.

El kill es portátil: `taskkill /F /T` en Windows y `os.killpg` en POSIX
(decisión 258): el sistema no se ata a un SO y muere el árbol entero.

Modo hijo: entrena SIEMPRE desde el sistema (decisión 259, sin CSV ni
ML_EXPORT_DIR vía `ml.trabajo`), latiendo cada 30 s; al terminar la
tarea queda COMPLETADA con su `EntrenamientoML`, o FALLIDA con el
error. El origen de datos lo declara `ML_ORIGEN_DATOS` (decisión 262):
si dice demostración, el registro se hace con la bandera de desarrollo.

--dry-run informa de las tareas sin tocar nada.
"""
import os
import signal
import subprocess
import sys
import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from ml import trabajo
from ml.models import TareaEntrenamiento

INTERVALO_SEGUNDOS = 5.0
MIRAR_CADA_SEGUNDOS = 0.5
TOPE_SEGUNDOS = 15 * 60
LATIDO_CADA_SEGUNDOS = 30.0
LATIDO_VENCIDO_SEGUNDOS = 5 * 60


class Command(BaseCommand):
    help = (
        "Reclama la tarea de entrenamiento pendiente y la ejecuta en un "
        "subproceso con tope de 15 minutos, latido de 30 s y kill portátil "
        "(Windows/POSIX). Un solo trabajador por tarea."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--una-vez",
            action="store_true",
            help="Un solo ciclo de reclamo/vigilancia (para cron).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra las tareas sin reclamar ni ejecutar nada.",
        )
        parser.add_argument(
            "--ejecutar-tarea",
            type=int,
            metavar="ID",
            help="Modo hijo: ejecuta la tarea ID (uso interno del padre).",
        )

    def handle(self, *args, **opciones):
        if opciones["ejecutar_tarea"] is not None:
            return self._hijo(opciones["ejecutar_tarea"])
        if opciones["dry_run"]:
            return self._dry_run()
        if opciones["una_vez"]:
            self._ciclo()
            return
        self.stdout.write(
            "Trabajador de entrenamientos activo (Ctrl+C para detener)."
        )
        try:
            while True:
                self._ciclo()
                time.sleep(INTERVALO_SEGUNDOS)
        except KeyboardInterrupt:
            self.stdout.write("Trabajador detenido.")

    # ------------------------------------------------------------------ #
    # Modo padre: reclamar y vigilar
    # ------------------------------------------------------------------ #
    def _dry_run(self):
        pendientes = TareaEntrenamiento.objects.filter(
            estado="PENDIENTE"
        ).count()
        procesando = TareaEntrenamiento.objects.filter(
            estado="PROCESANDO"
        ).count()
        self.stdout.write(
            f"Tareas: {pendientes} pendiente(s) · {procesando} en proceso"
            " (dry-run, sin cambios)."
        )

    def _reclamar(self):
        """La tarea PENDIENTE → PROCESANDO con latido, o None.

        SKIP LOCKED: si otro trabajador tiene la fila tomada, éste no
        espera ni la pisa (prueba 399).
        """
        with transaction.atomic():
            tarea = (
                TareaEntrenamiento.objects
                .select_for_update(skip_locked=True)
                .filter(estado="PENDIENTE")
                .order_by("creado_en", "id")
                .first()
            )
            if tarea is None:
                return None
            tarea.estado = "PROCESANDO"
            tarea.latido = timezone.now()
            tarea.progreso = {"etapa": "reclamada", "pct": 5}
            tarea.save(update_fields=("estado", "latido", "progreso"))
            return tarea

    def _ciclo(self):
        """Reclama (si hay) y vigila un subproceso. Devuelve True si hubo."""
        tarea = self._reclamar()
        if tarea is None:
            return False
        self.stdout.write(
            f"Tarea {tarea.pk}: reclamada; el entrenamiento corre en un "
            "subproceso…"
        )
        self._vigilar(tarea)
        return True

    def _comando_hijo(self, tarea):
        return [
            sys.executable,
            "manage.py",
            "procesar_entrenamientos",
            "--ejecutar-tarea",
            str(tarea.pk),
        ]

    def _matar_arbol(self, proceso):
        """Kill portátil del árbol de procesos (decisión 258)."""
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proceso.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                os.killpg(os.getpgid(proceso.pid), signal.SIGKILL)
        except OSError:
            pass  # el proceso puede haber muerto solo
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    def _fallar(self, tarea, motivo):
        tarea.estado = "FALLIDA"
        tarea.error = motivo
        tarea.save(update_fields=("estado", "error"))
        self.stdout.write(
            self.style.WARNING(f"Tarea {tarea.pk}: FALLIDA — {motivo}")
        )

    def _vigilar(self, tarea):
        """Espera al hijo imponiendo tope, latido y cancelación."""
        inicio = time.monotonic()
        proceso = subprocess.Popen(
            self._comando_hijo(tarea),
            cwd=str(settings.BASE_DIR),
            start_new_session=(os.name != "nt"),
        )
        while proceso.poll() is None:
            if time.monotonic() - inicio >= TOPE_SEGUNDOS:
                self._matar_arbol(proceso)
                self._fallar(
                    tarea,
                    f"Interrumpido por el trabajador: se alcanzó el tope "
                    f"de {int(TOPE_SEGUNDOS)} s.",
                )
                return
            tarea.refresh_from_db(fields=("estado", "latido"))
            if tarea.estado == "CANCELADA":
                self._matar_arbol(proceso)
                self.stdout.write(
                    f"Tarea {tarea.pk}: cancelada desde la interfaz; "
                    "subproceso detenido."
                )
                return
            latido = tarea.latido
            vencido = (
                latido is None
                or (timezone.now() - latido).total_seconds()
                >= LATIDO_VENCIDO_SEGUNDOS
            )
            if vencido:
                self._matar_arbol(proceso)
                self._fallar(
                    tarea,
                    f"Interrumpido por el trabajador: el latido lleva más "
                    f"de {int(LATIDO_VENCIDO_SEGUNDOS)} s sin sonar.",
                )
                return
            time.sleep(MIRAR_CADA_SEGUNDOS)

        codigo = proceso.returncode
        tarea.refresh_from_db(fields=("estado", "observacion", "error"))
        if codigo != 0 and tarea.estado == "PROCESANDO":
            self._fallar(
                tarea, tarea.error or f"El subproceso terminó con código {codigo}."
            )
        else:
            self.stdout.write(
                f"Tarea {tarea.pk}: {tarea.get_estado_display().lower()}."
            )

    # ------------------------------------------------------------------ #
    # Modo hijo: ejecutar la tarea
    # ------------------------------------------------------------------ #
    def _latir(self, tarea_id, fin):
        """Actualiza el latido cada LATIDO_CADA_SEGUNDOS hasta `fin`."""
        try:
            while not fin.wait(LATIDO_CADA_SEGUNDOS):
                TareaEntrenamiento.objects.filter(pk=tarea_id).update(
                    latido=timezone.now()
                )
        except Exception:  # noqa: BLE001 (la BD puede estar cerrándose)
            return
        finally:
            connection.close()

    def _hijo(self, tarea_id):
        try:
            tarea = TareaEntrenamiento.objects.get(pk=tarea_id)
        except TareaEntrenamiento.DoesNotExist:
            raise CommandError(f"La tarea {tarea_id} no existe.")
        if tarea.estado != "PROCESANDO":
            raise CommandError(
                f"La tarea {tarea_id} no está en proceso "
                f"(estado actual: {tarea.estado})."
            )

        fin = threading.Event()
        latidor = threading.Thread(
            target=self._latir, args=(tarea.pk, fin), daemon=True
        )
        latidor.start()

        datos_de = trabajo.datos_de_entorno()
        try:
            resumen = trabajo.entrenar_desde_sistema(
                usuario=tarea.usuario,
                version=str(tarea.pk),
                datos_de=datos_de,
                desarrollo="demostr" in datos_de.lower(),
            )
        except Exception as error:  # noqa: BLE001 (cualquier fallo → FALLIDA)
            fin.set()
            tarea.estado = "FALLIDA"
            tarea.error = str(error)
            tarea.progreso = {"etapa": "error", "pct": 100}
            tarea.save(update_fields=("estado", "error", "progreso"))
            raise CommandError(str(error)) from error
        finally:
            fin.set()

        tarea.estado = "COMPLETADA"
        tarea.resultado = resumen["entrenamiento"]
        tarea.progreso = {"etapa": "completada", "pct": 100}
        tarea.observacion = (
            f"Modelo v{resumen['version']} registrado: {resumen['elegido']}"
        )
        tarea.error = None
        tarea.save(
            update_fields=(
                "estado", "resultado", "progreso", "observacion", "error"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Tarea {tarea.pk}: COMPLETADA "
                f"(modelo v{resumen['version']}, {resumen['elegido']})."
            )
        )
