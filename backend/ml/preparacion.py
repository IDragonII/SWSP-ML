"""Imputación y transformaciones dentro del pipeline (Semana 21).

preparar() parte del DataFrame limpio: exige tener los predictores del
conjunto, quita los que superan el umbral de faltantes del catálogo,
separa el objetivo (que NUNCA se imputa ni se escala) y arma el
ColumnTransformer de sklearn SIN ajustar.

La mediana de los numéricos y el escalado se aprenden con fit() solo
dentro del pliegue de entrenamiento: una fila de prueba nunca decide
la mediana ni la media (prueba 358). Las categorías vacías quedan como
«vacío» —un nivel propio, sin estadística que filtrar— y una categoría
que no se vio en entrenamiento se ignora, no se inventa (prueba 359).

Uso típico (notebook 02):

    X, y, pipeline, fuera = preparar(datos, conjunto="plan")
    pipeline.fit(X_train, y_train)   # dentro del pliegue, nunca antes
"""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.carga import COLUMNAS_NUMERICAS
from ml.catalogo import (
    CONJUNTO_PLAN,
    columnas_conjunto,
    descartadas_por_faltantes,
)

OBJETIVO = "rendimiento_kg_ha"


def columnas_del_pipeline(predictores):
    """(numéricas, categóricas) de una lista de predictores, en orden."""
    numericas = tuple(c for c in predictores if c in COLUMNAS_NUMERICAS)
    categoricas = tuple(c for c in predictores if c not in COLUMNAS_NUMERICAS)
    return numericas, categoricas


def construir_pipeline(predictores):
    """ColumnTransformer sin ajustar.

    - Numéricos: imputación por la mediana + estandarización (los dos
      estadísticos se aprenden con fit en el entrenamiento).
    - Categóricos: codificación one-hot que ignora categorías nuevas.
    - El objetivo no está aquí: no se imputa ni se transforma.
    """
    numericas, categoricas = columnas_del_pipeline(predictores)
    transformadores = []
    if numericas:
        transformadores.append(
            (
                "numerico",
                Pipeline(
                    [
                        ("imputar", SimpleImputer(strategy="median")),
                        ("escalar", StandardScaler()),
                    ]
                ),
                list(numericas),
            )
        )
    if categoricas:
        transformadores.append(
            (
                "categorico",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(categoricas),
            )
        )
    return ColumnTransformer(
        transformadores,
        remainder="drop",
        verbose_feature_names_out=False,
    )


def preparar(datos, conjunto=CONJUNTO_PLAN):
    """(X, y, pipeline, fuera) listos para la validación.

    - X: predictores del conjunto SIN los que superan el umbral de
      faltantes; si falta algún predictor del conjunto en datos se
      rechaza con su lista (nada se descarga en silencio).
    - y: el objetivo tal cual; filas sin objetivo debe haberlas sacado
      limpiar() antes.
    - fuera: {columna: fraccion_vacia} de lo descartado, para informar.
    """
    fuera = descartadas_por_faltantes(datos, conjunto)
    pedidos = tuple(c for c in columnas_conjunto(conjunto) if c not in fuera)
    faltantes = [c for c in pedidos if c not in datos.columns]
    if faltantes:
        raise ValueError(
            "Faltan predictores del conjunto en los datos: "
            + ", ".join(faltantes)
        )
    X = datos.loc[:, list(pedidos)].copy()
    _, categoricas = columnas_del_pipeline(pedidos)
    for columna in categoricas:
        X[columna] = X[columna].fillna("").astype(object)
    y = datos[OBJETIVO].copy()
    return X, y, construir_pipeline(pedidos), fuera
