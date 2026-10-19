"""Catálogo de variables del dataset (Semana 21, RF-51).

Una sola tabla en código que clasifica CADA columna de la vista:
su rol, a qué conjuntos pertenece y cuándo se conoce. Es el contrato
anti-fuga: lo que no está aquí no se usa, y lo que está declarado como
identificador, metadato, cobertura, seguimiento o fuga no entra en
ningún conjunto de entrenamiento (pruebas 352 y 353).

Conjuntos:
  plan        — Conjunto 1 «Plan» (principal): todo lo que se conoce o
                se decide antes de cosechar.
  plan_clima  — Conjunto 2 «Plan + clima del ciclo» (comparativo): el
                plan más el clima del ciclo completo, con la advertencia
                de que ese clima al predecir de verdad no existe y habría
                que estimarlo (no es una predicción real).

Supuestos del desarrollador (marcados como tales, pendientes del
responsable): cobertura mínima de clima 80 % y umbral de faltantes 40 %.
"""
import pandas as pd

CONJUNTO_PLAN = "plan"
CONJUNTO_CLIMA = "plan_clima"
CONJUNTOS = (CONJUNTO_PLAN, CONJUNTO_CLIMA)

# Roles posibles de una columna del catálogo
ROL_IDENTIFICADOR = "identificador"
ROL_OBJETIVO = "objetivo"
ROL_PREDICTOR = "predictor"
ROL_METADATO = "metadato"
ROL_COBERTURA = "cobertura"
ROL_SEGUIMIENTO = "seguimiento"
ROL_FUGA = "fuga"

# Supuestos míos (decisión S21): se anotan y se revisan con el responsable
COBERTURA_CLIMA_MINIMA = 0.80
UMBRAL_FALTANTES = 0.40

# Columnas del clima que solo valen con cobertura suficiente
COLUMNAS_CLIMA = (
    "precipitacion_acum_mm",
    "temp_prom_c",
    "humedad_prom_pct",
    "n_heladas",
)

# Misma tabla que docs/diccionario_variables.md (lo anotado allá y aquí
# debe coincidir; la prueba 352 comprueba que la vista está entera).
CATALOGO = {
    "campania_id": {
        "rol": ROL_IDENTIFICADOR,
        "conjuntos": (),
        "cuando": "Nunca",
        "observacion": "Identificador interno; solo para trazabilidad.",
    },
    "parcela_id": {
        "rol": ROL_IDENTIFICADOR,
        "conjuntos": (),
        "cuando": "Nunca",
        "observacion": "Identificador interno; solo para trazabilidad.",
    },
    "productor_id": {
        "rol": ROL_IDENTIFICADOR,
        "conjuntos": (),
        "cuando": "Nunca",
        "observacion": (
            "No es predictor: agrupa la validación para que un productor "
            "no aparezca en entrenamiento y en prueba a la vez."
        ),
    },
    "periodo": {
        "rol": ROL_METADATO,
        "conjuntos": (),
        "cuando": "Al planificar",
        "observacion": "Solo para describir los datos; no predice.",
    },
    "anio_campania": {
        "rol": ROL_METADATO,
        "conjuntos": (),
        "cuando": "Al planificar",
        "observacion": (
            "Un año nuevo queda fuera del rango visto: no se usa."
        ),
    },
    "cultivo": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Al planificar",
        "observacion": "Categoría; las raras se agrupan en «otra».",
    },
    "variedad": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Al planificar",
        "observacion": "Categoría; agrupa categorías raras por variedad.",
    },
    "superficie_sembrada_ha": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Al planificar",
        "observacion": "",
    },
    "altitud_msnm": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Es de la parcela",
        "observacion": "Sale si pasa del umbral de faltantes.",
    },
    "tipo_suelo": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Es de la parcela",
        "observacion": "Sale si pasa del umbral de faltantes.",
    },
    "pendiente": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Es de la parcela",
        "observacion": "Sale si pasa del umbral de faltantes.",
    },
    "sistema_riego": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Es de la parcela",
        "observacion": "Sale si pasa del umbral de faltantes.",
    },
    "origen": {
        "rol": ROL_METADATO,
        "conjuntos": (),
        "cuando": "Metadato",
        "observacion": (
            "SISTEMA/IMPORTADA: se usa para comparar y diagnosticar, "
            "nunca como predictor."
        ),
    },
    "precipitacion_acum_mm": {
        "rol": ROL_PREDICTOR,
        "conjuntos": (CONJUNTO_CLIMA,),
        "cuando": "Durante o después del ciclo",
        "observacion": (
            "Conjunto 2 solo: al predecir de verdad habría que "
            "estimarla; cobertura mínima del 80 %."
        ),
    },
    "temp_prom_c": {
        "rol": ROL_PREDICTOR,
        "conjuntos": (CONJUNTO_CLIMA,),
        "cuando": "Durante o después del ciclo",
        "observacion": "Conjunto 2 solo; cobertura mínima del 80 %.",
    },
    "humedad_prom_pct": {
        "rol": ROL_PREDICTOR,
        "conjuntos": (CONJUNTO_CLIMA,),
        "cuando": "Durante o después del ciclo",
        "observacion": "Conjunto 2 solo; cobertura mínima del 80 %.",
    },
    "n_heladas": {
        "rol": ROL_PREDICTOR,
        "conjuntos": (CONJUNTO_CLIMA,),
        "cuando": "Durante o después del ciclo",
        "observacion": "Conjunto 2 solo; cobertura mínima del 80 %.",
    },
    "dias_con_clima": {
        "rol": ROL_COBERTURA,
        "conjuntos": (),
        "cuando": "Cobertura",
        "observacion": (
            "Sirve para decidir si el clima del ciclo es válido; "
            "no es una variable predictiva."
        ),
    },
    "dias_ventana_clima": {
        "rol": ROL_COBERTURA,
        "conjuntos": (),
        "cuando": "Cobertura",
        "observacion": "Denominador de la cobertura de clima.",
    },
    "semilla_kg_ha": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Al sembrar",
        "observacion": "",
    },
    "fertilizante_kg_ha": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Total del ciclo (plan de manejo)",
        "observacion": (
            "En campañas del sistema es lo aplicado; se trata como plan."
        ),
    },
    "jornales_ha": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Total del ciclo (plan de manejo)",
        "observacion": (
            "En campañas del sistema es lo aplicado; se trata como plan."
        ),
    },
    "agua_m3_ha": {
        "rol": ROL_PREDICTOR,
        "conjuntos": CONJUNTOS,
        "cuando": "Total del ciclo (plan de manejo)",
        "observacion": (
            "En campañas del sistema es lo aplicado; se trata como plan."
        ),
    },
    "n_incidencias": {
        "rol": ROL_SEGUIMIENTO,
        "conjuntos": (),
        "cuando": "Durante el ciclo",
        "observacion": (
            "Reservada al futuro Conjunto 3 «Seguimiento»: ocurren "
            "durante el ciclo y solo las tienen las campañas del sistema."
        ),
    },
    "severidad_max": {
        "rol": ROL_SEGUIMIENTO,
        "conjuntos": (),
        "cuando": "Durante el ciclo",
        "observacion": "Reservada al futuro Conjunto 3 «Seguimiento».",
    },
    "n_aplicaciones": {
        "rol": ROL_SEGUIMIENTO,
        "conjuntos": (),
        "cuando": "Durante el ciclo",
        "observacion": "Reservada al futuro Conjunto 3 «Seguimiento».",
    },
    "dias_ciclo": {
        "rol": ROL_FUGA,
        "conjuntos": (),
        "cuando": "Después de cosechar",
        "observacion": (
            "Fuga: se calcula con la fecha de cosecha, que es futuro "
            "al predecir. Nunca entra en ningún conjunto."
        ),
    },
    "rendimiento_kg_ha": {
        "rol": ROL_OBJETIVO,
        "conjuntos": (),
        "cuando": "Después de cosechar",
        "observacion": "Variable objetivo; se predice, nunca se imputa.",
    },
}


def columnas_conjunto(conjunto):
    """Predictores de un conjunto, en el orden del catálogo."""
    if conjunto not in CONJUNTOS:
        raise ValueError(f"Conjunto desconocido: {conjunto!r}")
    return tuple(
        columna
        for columna, meta in CATALOGO.items()
        if meta["rol"] == ROL_PREDICTOR and conjunto in meta["conjuntos"]
    )


def sin_clasificar(columnas):
    """Columnas dadas que el catálogo no conoce (debe quedar vacío)."""
    return [c for c in columnas if c not in CATALOGO]


def rol_de(columna):
    """Rol de la columna; lanza KeyError si no está declarada."""
    return CATALOGO[columna]["rol"]


def es_excluida_de_entrenamiento(columna):
    """Toda columna que nunca puede ser predictiva en ningún conjunto."""
    meta = CATALOGO.get(columna)
    if meta is None:
        return True
    return meta["rol"] != ROL_PREDICTOR


def aplicar_cobertura_clima(datos):
    """Deja vacío el clima de las campañas con cobertura insuficiente.

    Una suma de precipitación sobre una ventana incompleta subestima la
    lluvia real: por debajo del % (COBERTURA_CLIMA_MINIMA) el clima de
    esa campaña se trata como faltante, no como promedio parcial. Las
    columnas de cobertura (dias_con_clima, dias_ventana_clima) se
    conservan: son las que permiten auditar la decisión.
    """
    resultado = datos.copy()
    if "dias_con_clima" not in resultado.columns:
        return resultado
    cubiertos = resultado["dias_con_clima"].fillna(0)
    if "dias_ventana_clima" in resultado.columns:
        ventana = resultado["dias_ventana_clima"].replace(0, float("nan"))
        fraccion = (cubiertos / ventana).fillna(0.0)
    else:
        fraccion = pd.Series(0.0, index=resultado.index)
    bajos = fraccion < COBERTURA_CLIMA_MINIMA
    for columna in COLUMNAS_CLIMA:
        if columna in resultado.columns:
            resultado.loc[bajos, columna] = float("nan")
    return resultado


def descartadas_por_faltantes(datos, conjunto=CONJUNTO_PLAN,
                              umbral=UMBRAL_FALTANTES):
    """Predictores del conjunto con más de umbral de vacíos.

    Devuelve {columna: fraccion_de_vacios} solo con las que superan el
    umbral: esas salen del conjunto y se informan (prueba 355).
    """
    fuera = {}
    for columna in columnas_conjunto(conjunto):
        if columna not in datos.columns:
            continue
        vacios = datos[columna].isna().mean()
        if vacios > umbral:
            fuera[columna] = float(vacios)
    return fuera
