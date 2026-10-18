"""respaldo_bd: volcado de la base con pg_dump fuera del repositorio.

Vuelta la base activa (por defecto `sigpa_ga`) en texto plano a la
carpeta `RESPALDO_DIR` del .env —que debe estar FUERA del repositorio—,
con `--clean --if-exists` para que el archivo se pueda restaurar aunque
haya objetos previos. Conserva los últimos `RESPALDO_KEEP` volcados
(por defecto 10) y borra los más antiguos.

La restauración recomendada (también lo hace la prueba 325):

    docker exec -i sigpa_db psql -U sigpa_user -d sigpa_ga \\
        -v ON_ERROR_STOP=1 -1 -f - < respaldo_sigpa_ga_2026-10-18_120000.sql

El cliente corre dentro del contenedor (o en el PATH local): ver
`sistema/respaldo.py`.
"""
import os
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sistema import respaldo


class Command(BaseCommand):
    help = "Vuelca la base a RESPALDO_DIR (fuera del repositorio) con pg_dump"

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            default=None,
            help="Carpeta destino (por defecto RESPALDO_DIR del .env)",
        )
        parser.add_argument(
            "--mantener",
            type=int,
            default=None,
            help="Volcados que se conservan (por defecto RESPALDO_KEEP o 10)",
        )

    def handle(self, *args, **opciones):
        carpeta = opciones["salida"] or os.getenv("RESPALDO_DIR", "").strip()
        if not carpeta:
            raise CommandError(
                "Falta RESPALDO_DIR en el .env (carpeta de respaldos, "
                "fuera del repositorio)."
            )
        destino_carpeta = Path(carpeta).expanduser().resolve()
        raiz = Path(settings.BASE_DIR).parent.resolve()
        try:
            destino_carpeta.relative_to(raiz)
        except ValueError:
            pass  # fuera del repositorio: correcto
        else:
            raise CommandError(
                f"RESPALDO_DIR ({destino_carpeta}) está dentro del "
                f"repositorio ({raiz}): los volcados no se versionan."
            )
        destino_carpeta.mkdir(parents=True, exist_ok=True)

        nombre_bd = settings.DATABASES["default"]["NAME"]
        archivo = destino_carpeta / (
            f"respaldo_{nombre_bd}_{datetime.now():%Y-%m-%d_%H%M%S}.sql"
        )
        inicio = time.monotonic()
        try:
            bytes_volcados = respaldo.volcar_a_archivo(
                archivo, extra=("--clean", "--if-exists")
            )
        except respaldo.RespaldoError as error:
            raise CommandError(str(error))
        segundos = time.monotonic() - inicio

        mantener = int(
            opciones["mantener"]
            or os.getenv("RESPALDO_KEEP", "10")
        )
        antiguos = sorted(destino_carpeta.glob(f"respaldo_{nombre_bd}_*.sql"))
        for viejo in antiguos[:-mantener] if mantener > 0 else []:
            viejo.unlink()

        self.stdout.write(
            self.style.SUCCESS(
                f"{archivo} ({bytes_volcados:,} bytes, {segundos:.1f} s; "
                f"conservados los últimos {mantener})"
            )
        )
