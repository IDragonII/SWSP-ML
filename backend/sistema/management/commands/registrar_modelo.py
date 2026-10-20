"""registrar_modelo: da de alta un entrenamiento con sus 3 modelos.

    manage.py registrar_modelo --usuario admin [--metricas R]
        [--archivo R] [--version-modelo 1] [--activar] [--desarrollo]
        [--dry-run]

Lee `resultados_v<version>.json` de `entrenar_modelos` (o la ruta
indicada con --metricas) y da de alta 1 entrenamiento y los 3 modelos
con sus métricas (HU-171, decisiones 220-224). Exige usuario activo
con el permiso ml.entrenar, al menos 30 campañas, la bandera
--desarrollo para modelos de demostración y una versión sin registrar;
el archivo .joblib debe estar en el manifiesto de huellas (o viene de
fuera: se copia a ml_models/ y se registra su huella) y pasa una
predicción de prueba antes de tocar la base.

Con --activar activa el modelo elegido (permiso ml.activar_modelo:
un solo modelo activo, con auditoría ACTIVAR/DESACTIVAR). Con
--dry-run valida y informa sin escribir nada. El entrenamiento y el
registro se hacen fuera de la interfaz (decisión 209); la bandera
--version-modelo reemplaza a --version (decisión 246).
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from ml import guardado, registro
from ml.registro import ErrorRegistro


class Command(BaseCommand):
    help = (
        "Registra las métricas de un entrenamiento como 1 entrenamiento "
        "y 3 modelos, con huella verificada y auditoría CREAR."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuario",
            help="Usuario que ejecuta (debe tener el permiso ml.entrenar).",
        )
        parser.add_argument(
            "--metricas",
            help="Ruta de resultados_vN.json (default: la de la versión).",
        )
        parser.add_argument(
            "--archivo",
            help="Ruta del .joblib del modelo elegido (default: el de "
            "ml_models/ para esa versión).",
        )
        parser.add_argument(
            "--version-modelo",
            default="1",
            help="Versión a registrar (default: 1; «--version» lo "
            "reserva Django).",
        )
        parser.add_argument(
            "--activar",
            action="store_true",
            help="Activa el modelo elegido en la misma corrida "
            "(permiso ml.activar_modelo).",
        )
        parser.add_argument(
            "--desarrollo",
            action="store_true",
            help="Admite registrar un modelo de demostración (solo para "
            "desarrollo; bandera explícita de la decisión 221).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida y informa sin escribir nada.",
        )

    def handle(self, *args, **opciones):
        if not opciones["usuario"]:
            raise CommandError("Falta el argumento obligatorio --usuario.")
        usuario = self._usuario(opciones["usuario"])
        version = opciones["version_modelo"]
        destino = guardado.carpeta()

        resultados = self._resultados(opciones["metricas"], version)
        archivo = Path(opciones["archivo"]) if opciones["archivo"] else None

        try:
            resumen = registro.registrar(
                usuario=usuario,
                resultados=resultados,
                version=version,
                archivo=archivo,
                desarrollo=opciones["desarrollo"],
                activar=opciones["activar"],
                seco=opciones["dry_run"],
            )
        except ErrorRegistro as error:
            raise CommandError(str(error)) from error

        if resumen.get("seco"):
            self.stdout.write(
                f"Dry-run: se registraría la versión {resumen['version']} "
                f"con {resumen['n']} registros (origen: {resumen['origen']}), "
                f"modelo elegido {resumen['elegido']}."
            )
            self.stdout.write(f"Huella del archivo: {resumen['huella']}")
            if resumen.get("copiar"):
                self.stdout.write(
                    "El archivo se copiaría a ml_models/ y su huella se "
                    "añadiría al manifiesto."
                )
            if resumen.get("activar"):
                self.stdout.write("Se activaría el modelo elegido.")
            self.stdout.write("Sin cambios.")
            return

        entrenamiento_ml = resumen["entrenamiento"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Entrenamiento #{entrenamiento_ml.id} registrado: "
                f"{resumen['n']} registros (origen: {resumen['origen']})"
            )
        )
        for modelo in resumen["modelos"]:
            marca = " [elegido]" if modelo.algoritmo == resumen["elegido"] else ""
            self.stdout.write(
                f"  - {modelo.algoritmo} v{modelo.version}: "
                f"MAE {modelo.mae} · RMSE {modelo.rmse} · "
                f"R² {modelo.r2}{marca}"
            )
        self.stdout.write(f"Huella: {resumen['huella']}")
        if resumen.get("activado"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Modelo activo: {resumen['activado'].algoritmo} "
                    f"v{resumen['activado'].version}"
                )
            )

    # ------------------------------------------------------------------ #
    def _usuario(self, username):
        User = get_user_model()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No existe el usuario «{username}».")

    def _resultados(self, ruta, version):
        if ruta:
            archivo = Path(ruta)
            if not archivo.exists():
                raise CommandError(f"No existe el archivo {ruta}.")
            import json

            try:
                return json.loads(archivo.read_text(encoding="utf-8"))
            except ValueError as error:
                raise CommandError(
                    f"El archivo de métricas no es JSON válido: {error}"
                ) from error
        try:
            return guardado.leer_resultados(version)
        except guardado.ErrorManifiesto as error:
            raise CommandError(str(error)) from error
