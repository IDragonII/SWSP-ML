"""Exportación del dataset a un archivo fuera del repositorio (S21).

Aquí vive lo reutilizable de HU-166: construir los bytes del CSV desde
la lista fija de columnas, calcular la huella SHA-256 y montar la ficha
técnica (fecha de Lima, filas, columnas, huella, origen de los datos y
semilla). El comando exportar_dataset se encarga de permisos, ruta y
auditoría.

El archivo se trata como dato sensible aunque no lleve nombres ni DNI:
la combinación de altitud, cultivo y período puede identificar una
parcela. Por eso la carpeta está definida en el .env, FUERA del repositorio
y de cualquier carpeta sincronizada en la nube, y no se sube a Git ni se
muestra en capturas.
"""
import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Semilla fija de la Semana 21: la misma que usa la validación, para que
# la ficha permita reproducir cualquier número que salga del archivo.
SEMILLA = 42

ZONA_LIMA = ZoneInfo("America/Lima")


class ErrorRuta(Exception):
    """La carpeta de exportación no está permitida."""


def ahora_lima():
    """Hora actual de Lima en ISO 8601 (la que lleva la ficha)."""
    return datetime.now(ZONA_LIMA).isoformat(timespec="seconds")


def validar_ruta(carpeta, raiz_repositorio):
    """Resuelve la carpeta y exige que quede fuera del repositorio.

    Devuelve la ruta resuelta o lanza ErrorRuta con el motivo (también
    rechaza la raíz del repo y cualquier subcarpeta suya).
    """
    resuelta = Path(carpeta).expanduser().resolve()
    raiz = Path(raiz_repositorio).resolve()
    if resuelta == raiz or raiz in resuelta.parents:
        raise ErrorRuta(
            f"La carpeta de exportación debe estar FUERA del repositorio "
            f"({raiz}); se indicó {resuelta}. Define ML_EXPORT_DIR en el "
            ".env con una ruta fuera de Git y de la nube."
        )
    return resuelta


def bytes_csv(columnas, filas):
    """Bytes UTF-8 con BOM del CSV: encabezado + filas (NULL → vacío).

    El punto decimal es el de Python («.») al serializar con csv.writer:
    el archivo es independiente de la configuración regional.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")
    escritor.writerow(columnas)
    for fila in filas:
        escritor.writerow("" if valor is None else valor for valor in fila)
    return buffer.getvalue().encode("utf-8-sig")


def huella_sha256(contenido):
    """SHA-256 en hex de los bytes exactos que se van a escribir."""
    return hashlib.sha256(contenido).hexdigest()


def ficha_tecnica(*, filas, columnas, huella, origen_datos, fecha=None):
    """Ficha técnica en JSON de una exportación."""
    return {
        "fecha": fecha or ahora_lima(),
        "filas": int(filas),
        "columnas": list(columnas),
        "sha256": huella,
        "origen_datos": origen_datos,
        "semilla": SEMILLA,
    }


def marca_tiempo(when=None):
    """Sello legible para nombrar los archivos de una exportación."""
    momento = when or datetime.now(ZONA_LIMA)
    return momento.strftime("%Y%m%d_%H%M%S")
