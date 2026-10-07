"""cargar_ubicacion: carga provincias, distritos y comunidades desde un
CSV o un Excel (decisión 2 de docs/decisiones_semana3.md).

Idempotente: se puede ejecutar muchas veces sin duplicar nada; informa de
las filas creadas, las que ya existían y las fallidas (sin detenerse).
La lista de ejemplo (datos de prueba) está en datos/ejemplo_ubicaciones.csv
y vive fuera de las migraciones.
"""
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from productores.models import Comunidad, Distrito, Provincia

COLUMNAS = ("provincia", "distrito", "comunidad")
ARCHIVO_POR_DEFECTO = (
    Path(settings.BASE_DIR).parent / "datos" / "ejemplo_ubicaciones.csv"
)


class Command(BaseCommand):
    help = (
        "Carga la lista de ubicación (CSV o Excel) de forma idempotente: "
        "crea lo que falta, no duplica si se ejecuta de nuevo e informa "
        "de filas creadas, existentes y fallidas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            default=str(ARCHIVO_POR_DEFECTO),
            help=(
                "Ruta del .csv o .xlsx con columnas provincia, distrito y "
                "comunidad (por defecto: datos/ejemplo_ubicaciones.csv)"
            ),
        )

    def handle(self, *args, **opciones):
        ruta = Path(opciones["archivo"])
        if not ruta.exists():
            raise CommandError(f"No se encuentra el archivo: {ruta}")
        try:
            filas = list(self._leer_filas(ruta))
        except ValueError as e:
            raise CommandError(str(e))

        creadas = existentes = fallidas = 0
        nuevas = dict.fromkeys(COLUMNAS, 0)
        errores = []

        for numero, fila in filas:
            try:
                creada = self._procesar_fila(fila, nuevas)
            except ValueError as e:
                fallidas += 1
                errores.append(f"  Fila {numero}: {e}")
            else:
                if creada:
                    creadas += 1
                else:
                    existentes += 1

        self.stdout.write(f"Archivo: {ruta}")
        self.stdout.write(f"Filas leídas:      {creadas + existentes + fallidas}")
        self.stdout.write(f"Filas creadas:     {creadas}")
        self.stdout.write(f"Filas ya existían: {existentes}")
        self.stdout.write(f"Filas fallidas:    {fallidas}")
        self.stdout.write(
            "Entidades creadas: "
            f"provincias {nuevas['provincia']} · "
            f"distritos {nuevas['distrito']} · "
            f"comunidades {nuevas['comunidad']}"
        )
        if errores:
            self.stdout.write("Detalle de fallidas:")
            for error in errores:
                self.stdout.write(error)

    def _leer_filas(self, ruta):
        """Devuelve (número de fila, dict con las 3 columnas normalizadas)."""
        if ruta.suffix.lower() == ".xlsx":
            yield from self._leer_excel(ruta)
        else:
            yield from self._leer_csv(ruta)

    def _leer_csv(self, ruta):
        with open(ruta, encoding="utf-8-sig", newline="") as archivo:
            lector = csv.DictReader(archivo)
            lector.fieldnames = [
                (nombre or "").strip().lower() for nombre in lector.fieldnames
            ]
            self._exigir_columnas(lector.fieldnames)
            for indice, fila in enumerate(lector, start=2):
                yield indice, self._normalizar(fila)

    def _leer_excel(self, ruta):
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                "Para leer .xlsx hay que instalar openpyxl (requirements.txt)."
            )
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        hoja = libro.active
        iterador = hoja.iter_rows(values_only=True)
        try:
            cabecera = next(iterador)
        except StopIteration:
            raise ValueError("El archivo está vacío.")
        nombres = [(str(c) if c is not None else "").strip().lower() for c in cabecera]
        self._exigir_columnas(nombres)
        for indice, valores in enumerate(iterador, start=2):
            fila = {
                nombre: ("" if valor is None else str(valor)).strip()
                for nombre, valor in zip(nombres, valores)
            }
            yield indice, self._normalizar(fila)

    @staticmethod
    def _exigir_columnas(nombres):
        if "provincia" not in nombres:
            raise ValueError(
                "El archivo debe llevar una columna llamada «provincia» "
                f"(columnas encontradas: {', '.join(nombres) or 'ninguna'})."
            )

    @staticmethod
    def _normalizar(fila):
        return {
            columna: (fila.get(columna) or "").strip() for columna in COLUMNAS
        }

    @staticmethod
    def _procesar_fila(fila, nuevas):
        """Crea lo que falte de la fila. Devuelve True si creó algo nuevo."""
        provincia = fila["provincia"]
        distrito = fila["distrito"]
        comunidad = fila["comunidad"]

        if not provincia and not distrito and not comunidad:
            raise ValueError("fila vacía")
        if not provincia:
            raise ValueError("falta la provincia")
        if comunidad and not distrito:
            raise ValueError("hay comunidad pero falta el distrito")

        creada_algo = False

        provincia_obj, creada = Provincia.objects.get_or_create(nombre=provincia)
        if creada:
            nuevas["provincia"] += 1
            creada_algo = True

        if not distrito:
            return creada_algo

        distrito_obj, creada = Distrito.objects.get_or_create(
            provincia=provincia_obj, nombre=distrito
        )
        if creada:
            nuevas["distrito"] += 1
            creada_algo = True

        if not comunidad:
            return creada_algo

        _, creada = Comunidad.objects.get_or_create(
            distrito=distrito_obj, nombre=comunidad
        )
        if creada:
            nuevas["comunidad"] += 1
            creada_algo = True

        return creada_algo
