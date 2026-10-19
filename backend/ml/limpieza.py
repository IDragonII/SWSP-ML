"""Limpieza del dataset con su tabla de exclusiones (Semana 21).

EXCLUSIONES es la única fuente de verdad de lo que se saca del dataset:
cada regla declara sus columnas, la condición que la dispara, el motivo
que queda en el resumen y la máscara que la aplica (la misma tabla que
se documenta en docs/ml_preparacion.md). limpiar() la recorre en orden
— si una fila incumple dos, se lleva el motivo de la primera — y
devuelve un resumen SOLO con conteos: nunca el contenido de las filas.

Solo se excluyen filas imposibles o sin objetivo. Lo inusual NO se
excluye: un rendimiento altísimo es un dato, no un error.
"""
import pandas as pd

IDENTIFICADORES = ("campania_id", "parcela_id", "productor_id")

EXCLUSIONES = (
    {
        "motivo": "Sin identificadores",
        "condicion": "algún identificador vacío",
        "columnas": IDENTIFICADORES,
        "mascara": lambda datos: datos.loc[
            :, list(IDENTIFICADORES)
        ].isna().any(axis=1),
    },
    {
        "motivo": "Superficie sin sentido",
        "condicion": "superficie_sembrada_ha <= 0",
        "columnas": ("superficie_sembrada_ha",),
        "mascara": lambda datos: datos["superficie_sembrada_ha"] <= 0,
    },
    {
        "motivo": "Altitud fuera de rango",
        "condicion": "altitud_msnm < 0 o > 6000 m",
        "columnas": ("altitud_msnm",),
        "mascara": lambda datos: (datos["altitud_msnm"] < 0)
        | (datos["altitud_msnm"] > 6000),
    },
    {
        "motivo": "Sin objetivo",
        "condicion": "rendimiento_kg_ha vacío o <= 0",
        "columnas": ("rendimiento_kg_ha",),
        "mascara": lambda datos: datos["rendimiento_kg_ha"].isna()
        | (datos["rendimiento_kg_ha"] <= 0),
    },
)


def limpiar(datos):
    """Aplica la tabla de exclusiones y devuelve (filas_limpias, resumen).

    El resumen trae entradas, salida, excluidas y los conteos por motivo:
    la suma por motivo cuadra siempre con filas_excluidas (prueba 357).
    """
    restantes = datos.copy()
    entrada = int(len(restantes))
    por_motivo = {}
    for regla in EXCLUSIONES:
        columnas = regla["columnas"]
        if any(c not in restantes.columns for c in columnas):
            continue
        mascara = regla["mascara"](restantes)
        n = int(mascara.sum())
        if n:
            por_motivo[regla["motivo"]] = n
            restantes = restantes[~mascara]
    salida = int(len(restantes))
    resumen = {
        "filas_entrada": entrada,
        "filas_salida": salida,
        "filas_excluidas": entrada - salida,
        "por_motivo": por_motivo,
    }
    return restantes, resumen
