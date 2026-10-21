"""Guardado y verificación de los archivos .joblib (Semana 22).

Los modelos viven en `backend/ml_models/`, **versionados en Git junto
con el código** y con un manifiesto de huellas SHA-256: el disco de las
plataformas es temporal, así que el archivo viaja con el repositorio.
joblib usa pickle, así que SOLO se cargan archivos generados por el
equipo y con la huella registrada en `manifiesto.json` (decisiones 214
y 226; pruebas 368, 371 y 392).

Además aquí se guardan `resultados_v<version>.json` (las métricas de
la última corrida de `entrenar_modelos`), que `registrar_modelo` lee
para dar de alta los tres modelos.
"""
import hashlib
import json
from pathlib import Path

import joblib
from django.conf import settings

NOMBRE_MANIFIESTO = "manifiesto.json"

# Versiones fijadas en requirements.txt: el artefacto guardado en la BD
# se sella con ellas para saber con qué entorno se entrenó (decisión
# 254). La prueba 398 las contrasta con el archivo real.
VERSIONES_LIBRERIAS = {
    "pandas": "3.0.6",
    "numpy": "2.5.4",
    "scikit-learn": "1.9.1",
    "joblib": "1.6.0",
}


class ErrorManifiesto(Exception):
    """El archivo no existe en el manifiesto o su huella no coincide."""


def versiones_librerias():
    """Copia de las versiones selladas en los modelos de la BD."""
    return dict(VERSIONES_LIBRERIAS)


def carpeta(destino=None):
    """backend/ml_models/ (o la carpeta indicada, para pruebas)."""
    if destino is not None:
        return Path(destino)
    return Path(settings.BASE_DIR) / "ml_models"


def nombre_archivo(algoritmo, version):
    return f"{algoritmo.lower()}_v{version}.joblib"


def nombre_resultados(version):
    return f"resultados_v{version}.json"


def huella_de(ruta):
    """SHA-256 de los bytes exactos del archivo."""
    resumen = hashlib.sha256()
    with Path(ruta).open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 16), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def guardar(tubo, algoritmo, version, destino=None):
    """joblib.dump del pipeline; devuelve la ruta escrita."""
    carpeta_destino = carpeta(destino)
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    ruta = carpeta_destino / nombre_archivo(algoritmo, version)
    joblib.dump(tubo, ruta)
    return ruta


def manifiesto(destino=None):
    """{nombre_archivo: {"sha256": ..., ...}} (vacío si no existe)."""
    ruta = carpeta(destino) / NOMBRE_MANIFIESTO
    if not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def registrar_archivo(ruta, destino=None, **meta):
    """Añade la huella del archivo al manifiesto y lo reescribe.

    Devuelve la huella registrada. El manifiesto es el que versiona
    Git: sin entrada, el archivo no se carga.
    """
    carpeta_destino = carpeta(destino)
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    huella = huella_de(ruta)
    datos = manifiesto(destino)
    datos[Path(ruta).name] = {"sha256": huella, **meta}
    (carpeta_destino / NOMBRE_MANIFIESTO).write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return huella


def verificar(ruta, destino=None):
    """True si el archivo existe en el manifiesto con la misma huella."""
    entrada = manifiesto(destino).get(Path(ruta).name)
    if not entrada or not Path(ruta).exists():
        return False
    return huella_de(ruta) == entrada["sha256"]


def cargar_verificado(ruta, destino=None):
    """joblib.load SOLO si la huella coincide con el manifiesto."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorManifiesto(f"No existe el archivo {ruta.name}.")
    entrada = manifiesto(destino).get(ruta.name)
    if entrada is None:
        raise ErrorManifiesto(
            f"El archivo {ruta.name} no está en el manifiesto de huellas."
        )
    huella = huella_de(ruta)
    if huella != entrada["sha256"]:
        raise ErrorManifiesto(
            f"La huella de {ruta.name} no coincide con la registrada "
            "(archivo alterado o de otro equipo)."
        )
    return joblib.load(ruta)


def guardar_resultados(resultado, version, destino=None):
    """Escribe resultados_v<version>.json con las métricas de la corrida."""
    carpeta_destino = carpeta(destino)
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    ruta = carpeta_destino / nombre_resultados(version)
    ruta.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return ruta


def leer_resultados(version, destino=None):
    ruta = carpeta(destino) / nombre_resultados(version)
    if not ruta.exists():
        raise ErrorManifiesto(f"No existe {ruta.name}.")
    return json.loads(ruta.read_text(encoding="utf-8"))
