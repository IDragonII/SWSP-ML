"""evaluar_alertas: barrido de condiciones de alertas (Semana 15).

Pensado para el proceso diario programado (cron/systemd/Task Scheduler,
aún sin programar en la instalación — pendiente para el .tex): recorre
las campañas evaluables y las incidencias severas, crea las alertas que
corresponden y cierra las que ya no (HU-124..HU-131). Idempotente: se
puede ejecutar muchas veces al día sin duplicar nada.

--dry-run muestra lo que haría sin escribir nada (la transacción se
revierte y no se registra el evento de auditoría). --hoy permite fijar
la fecha de evaluación para pruebas, pero solo si DEBUG está activo.
"""
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from alertas.servicio import evaluar_todo


class Command(BaseCommand):
    help = (
        "Evalúa las condiciones de alerta: crea las que corresponden "
        "(incidencias severas y campañas sin actividad) y cierra "
        "automáticamente las que ya no. Idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que haría sin escribir nada.",
        )
        parser.add_argument(
            "--hoy",
            help=(
                "Fecha de evaluación (AAAA-MM-DD) para probar; solo se "
                "admite si DEBUG está activo."
            ),
        )

    def handle(self, *args, **opciones):
        hoy = None
        if opciones["hoy"]:
            if not settings.DEBUG:
                raise CommandError("--hoy solo se admite si DEBUG está activo.")
            try:
                hoy = date.fromisoformat(opciones["hoy"])
            except ValueError:
                raise CommandError("La fecha --hoy debe tener el formato AAAA-MM-DD.")
        resultado = evaluar_todo(hoy=hoy, dry_run=opciones["dry_run"])
        sufijo = " (dry-run, sin cambios)" if opciones["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Alertas creadas: {resultado['creadas']} · "
                f"cerradas: {resultado['cerradas']}{sufijo}"
            )
        )
