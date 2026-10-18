"""matriz_rutas: genera docs/matriz_rutas_por_rol.md.

La matriz de rutas por rol (Entrega 1, Semana 19) se calcula desde la
introspección de `config.urls` + los permisos reales de `roles_permisos`
(módulo `sistema.matriz_rutas`); este comando solo la vierte a disco.

Regenerar tras añadir una ruta o tocar permisos de un rol: la prueba 319
falla si el documento está desactualizado.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from sistema import matriz_rutas as mr


class Command(BaseCommand):
    help = "Genera docs/matriz_rutas_por_rol.md desde config.urls y la BD"

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            default=None,
            help="Ruta del .md (por defecto docs/matriz_rutas_por_rol.md)",
        )

    def handle(self, *args, **opciones):
        destino = (
            Path(opciones["salida"])
            if opciones["salida"]
            else mr.ruta_doc()
        )
        try:
            texto = mr.generar_markdown()
        except Exception as error:  # noqa: BLE001 - aviso de gestión
            raise CommandError(f"No se pudo generar la matriz: {error}")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        filas = len(texto.splitlines())
        self.stdout.write(
            self.style.SUCCESS(f"{destino} generado ({filas} líneas)")
        )
