"""Carga y validación del CSV exportado (Semana 21, HU-167/168).

Comprueba columnas y tipos ANTES de que nadie use el archivo: faltantes
o desconocidas rechazan con su lista, y en cada columna numérica un
valor no vacío que no se pueda leer como número también rechaza
indicando columna y filas (prueba 351). Después aplica la política de
cobertura de clima del catálogo (máscara de faltantes, no de ceros).

El archivo lo escribe exportar_dataset con la lista fija de
ml.columnas; esta capa es la puerta que cualquier consumidor (notebooks,
Sprint 13) debe pasar.
"""
import pandas as pd

from ml.catalogo import aplicar_cobertura_clima
from ml.columnas import COLUMNAS_EXPORTADAS

# Columnas que deben venir como número (aceptan vacío = desconocido)
COLUMNAS_NUMERICAS = (
    "superficie_sembrada_ha",
    "altitud_msnm",
    "precipitacion_acum_mm",
    "temp_prom_c",
    "humedad_prom_pct",
    "n_heladas",
    "dias_con_clima",
    "dias_ventana_clima",
    "semilla_kg_ha",
    "fertilizante_kg_ha",
    "jornales_ha",
    "agua_m3_ha",
    "n_incidencias",
    "severidad_max",
    "n_aplicaciones",
    "dias_ciclo",
    "rendimiento_kg_ha",
)

# Identificadores: enteros obligatorios (la vista no admite vacíos)
COLUMNAS_ENTERAS = ("campania_id", "parcela_id", "productor_id", "anio_campania")

# De texto: se exige que existan como columna, no un valor concreto
COLUMNAS_TEXTO = (
    "periodo",
    "cultivo",
    "variedad",
    "tipo_suelo",
    "pendiente",
    "sistema_riego",
    "origen",
)


class ErrorCarga(Exception):
    """Archivo inválido: el mensaje lista columnas y filas del problema."""


def cargar(ruta, aplicar_clima=True):
    """Lee el CSV exportado, valida esquema y tipos, y devuelve el
    DataFrame con las políticas del catálogo ya aplicadas.

    - Faltan columnas declaradas → ErrorCarga con las faltantes.
    - Sobran columnas (desconocidas) → ErrorCarga con las desconocidas.
    - Un valor no vacío ilegible en una columna numérica → ErrorCarga
      con la columna y las primeras filas.
    - Identificadores vacíos o no enteros → ErrorCarga.
    - Si aplicar_clima, el clima con cobertura < 80 % queda vacío.
    """
    try:
        datos = pd.read_csv(ruta, encoding="utf-8-sig")
    except Exception as error:  # noqa: BLE001 (pandas lanza varios tipos)
        raise ErrorCarga(f"No se pudo leer el CSV: {error}") from error

    columnas = list(datos.columns)
    faltantes = [c for c in COLUMNAS_EXPORTADAS if c not in columnas]
    if faltantes:
        raise ErrorCarga(
            "Faltan columnas declaradas: " + ", ".join(faltantes)
        )
    desconocidas = [c for c in columnas if c not in COLUMNAS_EXPORTADAS]
    if desconocidas:
        raise ErrorCarga(
            "Columnas desconocidas (no están en la lista de exportación): "
            + ", ".join(desconocidas)
        )

    datos = datos[list(COLUMNAS_EXPORTADAS)].copy()

    for columna in COLUMNAS_NUMERICAS:
        originales = datos[columna]
        convertida = pd.to_numeric(originales, errors="coerce")
        mala = originales.notna() & convertida.isna()
        if mala.any():
            filas = [int(i) + 2 for i in datos.index[mala][:5]]
            raise ErrorCarga(
                f"Valores no numéricos en «{columna}»"
                f" (filas del archivo: {', '.join(map(str, filas))})"
            )
        datos[columna] = convertida

    for columna in COLUMNAS_ENTERAS:
        originales = datos[columna]
        convertida = pd.to_numeric(originales, errors="coerce")
        vacios = convertida.isna()
        if vacios.any():
            filas = [int(i) + 2 for i in datos.index[vacios][:5]]
            raise ErrorCarga(
                f"Identificador «{columna}» vacío o no entero"
                f" (filas del archivo: {', '.join(map(str, filas))})"
            )
        enteros = (convertida % 1 != 0)
        if enteros.any():
            filas = [int(i) + 2 for i in datos.index[enteros][:5]]
            raise ErrorCarga(
                f"Identificador «{columna}» con decimales"
                f" (filas del archivo: {', '.join(map(str, filas))})"
            )
        datos[columna] = convertida.astype("int64")

    for columna in COLUMNAS_TEXTO:
        datos[columna] = datos[columna].astype("string").fillna("")

    if aplicar_clima:
        datos = aplicar_cobertura_clima(datos)
    return datos
