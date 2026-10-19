"""exportar_dataset: vuelca vw_dataset_entrenamiento a un archivo fuera
del repositorio con su ficha técnica (Semana 21, HU-166, RF-51/RF-71).

    manage.py exportar_dataset --usuario ana --origen-datos demostracion
    manage.py exportar_dataset --usuario ana --origen-datos real --dry-run

Exige un usuario activo con el permiso ml.entrenar (hoy: solo el
Administrador) y una carpeta ML_EXPORT_DIR definida en el .env que
esté FUERA del repositorio. El ensayo (--dry-run) informa de cuántas
filas y columnas saldrían sin escribir nada ni dejar evento.

Orden con seguridad: primero se arma el archivo en memoria y se
registra el evento EXPORTAR del módulo «Machine Learning» (filas,
origen y huella, sin contenido); si la auditoría falla, NO se escribe
el archivo — el mismo criterio que la exportación de reportes.
"""
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from auditoria.registrar import registrar_evento
from ml import exportacion
from ml.columnas import consulta_exportacion
from usuarios.models import RolPermiso

PERMISO = "ml.entrenar"
MODULO_AUDITORIA = "Machine Learning"
ORIGENES = ("real", "demostracion")


class Command(BaseCommand):
    help = (
        "Exporta el dataset de entrenamiento a un CSV con ficha técnica "
        "en la carpeta ML_EXPORT_DIR (fuera del repositorio), dejando un "
        "evento de auditoría sin contenido de los datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuario",
            help=f"Usuario que ejecuta (debe tener el permiso {PERMISO}).",
        )
        parser.add_argument(
            "--origen-datos",
            choices=ORIGENES,
            help=(
                "Declaración obligatoria: si los datos son reales o de "
                "demostración (queda en la ficha y en los notebooks)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Informa filas y columnas sin escribir nada ni auditar.",
        )

    def handle(self, *args, **opciones):
        faltan = [n for n in ("usuario", "origen_datos") if not opciones[n]]
        if faltan:
            raise CommandError(
                "Faltan argumentos obligatorios: "
                +                 ", ".join(f"--{n.replace('_', '-')}" for n in faltan)
            )
        usuario = self._usuario(opciones["usuario"])
        origen = opciones["origen_datos"]
        carpeta = self._carpeta()

        consulta = consulta_exportacion()
        with connection.cursor() as cursor:
            cursor.execute(consulta)
            columnas = [col.name for col in cursor.description]
            filas = cursor.fetchall()

        if opciones["dry_run"]:
            self.stdout.write(
                f"Dry-run: se escribirían {len(filas)} filas y "
                f"{len(columnas)} columnas en {carpeta} "
                f"(origen de datos: {origen}). Sin cambios."
            )
            return

        # El archivo se arma en memoria: la huella de la ficha es la de
        # los bytes exactos que se van a escribir
        contenido = exportacion.bytes_csv(columnas, filas)
        huella = exportacion.huella_sha256(contenido)

        # Sin rastro no hay archivo: si la auditoría falla, no se escribe
        try:
            registrar_evento(
                usuario=usuario,
                accion="EXPORTAR",
                modulo=MODULO_AUDITORIA,
                detalle={
                    "filas": len(filas),
                    "origen_datos": origen,
                    "sha256": huella,
                },
            )
        except Exception as error:
            raise CommandError(
                "No se pudo registrar la auditoría de la exportación; "
                f"no se escribe el archivo. ({error})"
            ) from error

        marca = exportacion.marca_tiempo(
            datetime.now(exportacion.ZONA_LIMA)
        )
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta_csv = carpeta / f"dataset_{origen}_{marca}.csv"
        ruta_csv.write_bytes(contenido)

        ficha = exportacion.ficha_tecnica(
            filas=len(filas),
            columnas=columnas,
            huella=huella,
            origen_datos=origen,
        )
        ruta_ficha = carpeta / f"ficha_dataset_{origen}_{marca}.json"
        import json

        ruta_ficha.write_text(
            json.dumps(ficha, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Dataset exportado: {ruta_csv} ({len(filas)} filas, "
                f"{len(columnas)} columnas)"
            )
        )
        self.stdout.write(f"Ficha técnica: {ruta_ficha}")
        self.stdout.write(f"SHA-256: {huella}")
        self.stdout.write(f"Origen de los datos: {origen}")

    # ------------------------------------------------------------------ #
    def _usuario(self, username):
        User = get_user_model()
        try:
            usuario = User.objects.select_related("rol").get(
                username=username
            )
        except User.DoesNotExist:
            raise CommandError(f"No existe el usuario «{username}».")
        if not usuario.is_active:
            raise CommandError(f"El usuario «{username}» está inactivo.")
        tiene = RolPermiso.objects.filter(
            rol_id=usuario.rol_id, permiso__codigo=PERMISO
        ).exists()
        if not tiene:
            raise CommandError(
                f"El usuario «{username}» no tiene el permiso {PERMISO}."
            )
        return usuario

    def _carpeta(self):
        cruda = os.getenv("ML_EXPORT_DIR", "").strip()
        if not cruda:
            raise CommandError(
                "ML_EXPORT_DIR no está definido en el .env: define la "
                "carpeta de exportación (fuera del repositorio)."
            )
        try:
            return exportacion.validar_ruta(
                cruda, settings.BASE_DIR.parent
            )
        except exportacion.ErrorRuta as error:
            raise CommandError(str(error)) from error
