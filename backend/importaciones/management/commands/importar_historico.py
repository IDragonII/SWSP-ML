"""importar_historico: carga datos históricos desde CSV o XLSX (S20, RF-49/50).

Un tipo de archivo por ejecución (productores, parcelas o campañas con su
producción), validando cada fila con las reglas de negocio de la API
(importaciones/servicio.py). Ejemplos de uso:

    manage.py importar_historico --plantilla campanias --salida D:\\imp\\campanias.xlsx
    manage.py importar_historico --tipo campanias --archivo D:\\imp\\campanias.csv --usuario ana
    manage.py importar_historico --tipo productores --archivo prod.xlsx --usuario ana --dry-run

El usuario necesita el permiso importacion.ejecutar en su rol. Solo puede
haber una importación EN_PROCESO a la vez: una interrumpida a la fuerza
queda marcada CON_ERRORES (el comando lo hace con try/except); --forzar
libera una que haya quedado huérfana (proceso matado). Cada ejecución
real deja un registro en la tabla importaciones, un informe CSV de
errores en IMPORTACION_DIR (sin datos personales: el DNI va enmascarado),
un único evento de auditoría y una pasada de alertas al final.
--dry-run valida todo y no escribe nada (la transacción se revierte).
"""
import csv
import os
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from alertas.servicio import evaluar_todo
from auditoria.registrar import registrar_evento
from usuarios.models import RolPermiso

from importaciones import servicio
from importaciones.models import Importacion
from importaciones.plantillas import generar_plantilla

TIPOS = ("productores", "parcelas", "campanias")
PERMISO = "importacion.ejecutar"


class Command(BaseCommand):
    help = (
        "Importa datos históricos (productores, parcelas o campañas con su "
        "producción) desde un CSV o un Excel con las reglas de la API e "
        "informe de errores por fila sin datos personales."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tipo",
            choices=TIPOS,
            help="Tipo de archivo a importar (productores, parcelas o campanias).",
        )
        parser.add_argument(
            "--archivo",
            help="Ruta del .csv o .xlsx con los datos (máx. 5 MB y 5000 filas).",
        )
        parser.add_argument(
            "--usuario",
            help=f"Usuario que ejecuta (su rol debe tener el permiso {PERMISO}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida todo y muestra el resultado sin escribir nada.",
        )
        parser.add_argument(
            "--forzar",
            action="store_true",
            help=(
                "Marca como CON_ERRORES la importación EN_PROCESO que haya "
                "quedado interrumpida y continúa."
            ),
        )
        parser.add_argument(
            "--plantilla",
            choices=TIPOS,
            help="Genera la plantilla .xlsx del tipo en --salida y termina.",
        )
        parser.add_argument(
            "--salida",
            help="Ruta del .xlsx a escribir con --plantilla.",
        )

    def handle(self, *args, **opciones):
        if opciones["plantilla"]:
            self._plantilla(opciones)
            return

        faltan = [n for n in ("tipo", "archivo", "usuario") if not opciones[n]]
        if faltan:
            raise CommandError(
                "Faltan argumentos obligatorios: "
                + ", ".join(f"--{n}" for n in faltan)
                + " (o usa --plantilla --salida)."
            )
        tipo = opciones["tipo"]
        usuario = self._usuario(opciones["usuario"])
        ruta = Path(opciones["archivo"])
        try:
            filas = servicio.leer_archivo(tipo, ruta)
        except servicio.ErrorArchivo as error:
            raise CommandError(str(error))

        seco = opciones["dry_run"]
        registro = None
        if not seco:
            self._liberar_previa(opciones["forzar"])
            registro = Importacion.objects.create(
                archivo=ruta.name,
                tipo=tipo.upper(),
                usuario=usuario,
                filas_totales=len(filas),
            )

        try:
            if seco:
                with transaction.atomic():
                    resultado = self._importar(tipo, filas, usuario)
                    transaction.set_rollback(True)
            else:
                resultado = self._importar(tipo, filas, usuario)
        except servicio.ErrorArchivo as error:
            self._romper(registro, str(error))
            raise CommandError(str(error))
        except KeyboardInterrupt:
            self._romper(registro, "Ejecución interrumpida por el usuario.")
            raise CommandError(
                "Importación interrumpida: el registro queda CON_ERRORES."
            )
        except Exception as error:
            self._romper(registro, f"Fallo inesperado: {error}")
            raise CommandError(f"La importación falló: {error}")

        if registro is not None:
            registro.filas_ok = resultado.creadas + resultado.omitidas
            registro.filas_error = len(resultado.errores)
            registro.estado = (
                "CON_ERRORES" if resultado.errores else "COMPLETADA"
            )
            registro.detalle_errores = resultado.errores or None
            registro.save()

        self._resumen(ruta, tipo, resultado, seco)

        if resultado.errores and not seco:
            ruta_informe = self._escribir_informe(tipo, resultado.errores)
            if ruta_informe:
                self.stdout.write(f"Informe de errores: {ruta_informe}")

        if seco:
            return

        registrar_evento(
            usuario=usuario,
            accion="CREAR",
            modulo="importaciones",
            tabla="importaciones",
            registro_id=registro.pk,
            detalle={
                "tipo": tipo,
                "archivo": ruta.name,
                "filas_totales": resultado.totales,
                "filas_ok": resultado.creadas + resultado.omitidas,
                "filas_error": len(resultado.errores),
            },
        )
        try:
            alertas = evaluar_todo()
        except Exception as error:
            self.stdout.write(
                self.style.WARNING(
                    f"No se pudieron evaluar las alertas al terminar: {error}"
                )
            )
        else:
            self.stdout.write(
                f"Alertas: creadas {alertas['creadas']} · "
                f"cerradas {alertas['cerradas']}"
            )

    # ------------------------------------------------------------------ #
    def _plantilla(self, opciones):
        if not opciones["salida"]:
            raise CommandError(
                "Con --plantilla hay que indicar --salida (ruta del .xlsx)."
            )
        ruta = Path(opciones["salida"]).expanduser()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        generar_plantilla(opciones["plantilla"], ruta)
        self.stdout.write(self.style.SUCCESS(f"Plantilla escrita en {ruta}"))

    def _usuario(self, username):
        User = get_user_model()
        try:
            usuario = User.objects.select_related("rol").get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No existe el usuario «{username}».")
        if not usuario.is_active:
            raise CommandError(f"El usuario «{username}» está inactivo.")
        permisos = set(
            RolPermiso.objects.filter(rol_id=usuario.rol_id).values_list(
                "permiso__codigo", flat=True
            )
        )
        if PERMISO not in permisos:
            raise CommandError(
                f"El usuario «{username}» no tiene el permiso {PERMISO}."
            )
        return usuario

    def _liberar_previa(self, forzar):
        previa = (
            Importacion.objects.filter(estado="EN_PROCESO").order_by("-id").first()
        )
        if previa is None:
            return
        if not forzar:
            raise CommandError(
                f"Ya hay una importación EN_PROCESO (id {previa.pk}, "
                f"{previa.fecha:%Y-%m-%d %H:%M}, archivo {previa.archivo}). "
                "Si quedó interrumpida, repite con --forzar."
            )
        previa.estado = "CON_ERRORES"
        previa.detalle_errores = [
            {"fila": 0, "columna": "", "mensaje": "Marcada CON_ERRORES por --forzar."}
        ]
        previa.save()
        self.stdout.write(
            f"Importación EN_PROCESO {previa.pk} marcada CON_ERRORES (--forzar)."
        )

    def _romper(self, registro, mensaje):
        if registro is None:
            return
        registro.estado = "CON_ERRORES"
        registro.detalle_errores = [
            {"fila": 0, "columna": "", "mensaje": mensaje}
        ]
        registro.save()

    def _importar(self, tipo, filas, usuario):
        if tipo == "productores":
            return servicio.importar_productores(filas, usuario)
        if tipo == "parcelas":
            return servicio.importar_parcelas(filas, usuario)
        return servicio.importar_campanias(filas, usuario)

    def _resumen(self, ruta, tipo, resultado, seco):
        sufijo = " (dry-run: sin cambios)" if seco else ""
        self.stdout.write(f"Archivo: {ruta} · tipo: {tipo}{sufijo}")
        self.stdout.write(f"Filas de datos: {resultado.totales}")
        self.stdout.write(f"  creadas:       {resultado.creadas}")
        self.stdout.write(f"  ya existían:   {resultado.omitidas}")
        self.stdout.write(f"  con error:     {len(resultado.errores)}")
        for error in resultado.errores:
            columna = f" [{error['columna']}]" if error["columna"] else ""
            self.stdout.write(
                f" Fila {error['fila']}{columna}: {error['mensaje']}"
            )

    def _escribir_informe(self, tipo, errores):
        carpeta = os.getenv("IMPORTACION_DIR", "").strip()
        if not carpeta:
            self.stdout.write(
                self.style.WARNING(
                    "IMPORTACION_DIR no está definido: el informe de errores no "
                    "se escribe (siguen en la consola y en el registro)."
                )
            )
            return None
        destino = Path(carpeta).expanduser()
        destino.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = destino / f"informe_importacion_{tipo}_{marca}.csv"
        with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(("fila", "columna", "mensaje"))
            for error in errores:
                escritor.writerow(
                    (error["fila"], error["columna"], error["mensaje"])
                )
        return ruta
