"""Entrenamiento y evaluación de los tres algoritmos (Semana 22).

Los mismos pliegues agrupados por productor (semilla 42) para los tres
candidatos Y para la línea base: nadie entrena con un corte distinto.
Los hiperparámetros son FIJOS (criterio_seleccion.md): con 13 campañas,
buscar parámetros sobreajusta.

Métricas (por candidato):
- `mae`/`rmse`: media de los RMSE/MAE por pliegue (la que usa el
  criterio) y `desvio_rmse`: desvío estándar entre particiones.
- `r2`/`mape`: calculados sobre TODAS las predicciones de prueba
  acumuladas (cada fila prueba exactamente una vez); MAPE solo si no
  hay rendimientos en cero (si los hay, queda en None).
- `por_cultivo`: igual, agrupado por cultivo (un promedio general
  puede esconder un cultivo mal predicho).

`estrategia_de(n)` fija de antemano qué se hace según el tramo:
n < 30 → CV agrupada simple; 30–99 → CV repetida (5 × 5);
n >= 100 → holdout final del 20 % usado una sola vez + CV en el 80 %.
"""
import json
import math
import statistics
from copy import deepcopy

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

from ml import criterio, linea_base, validacion
from ml.carga import COLUMNAS_NUMERICAS
from ml.catalogo import CONJUNTO_PLAN
from ml.exportacion import SEMILLA
from ml.preparacion import preparar

NOMBRES = criterio.ORDEN_SIMPLICIDAD

# Fábricas e hiperparámetros en una sola tabla: los hiperparámetros que
# se guardan en modelos_ml.hiperparametros son los mismos con los que se
# entrena, sin duplicarlos en dos sitios (decisión 223).
_FABRICAS = (
    ("REGRESION_LINEAL", LinearRegression, {}),
    ("RANDOM_FOREST", RandomForestRegressor, {
        "n_estimators": 300,
        "min_samples_leaf": 3,
        "random_state": SEMILLA,
        "n_jobs": -1,
    }),
    ("GRADIENT_BOOSTING", GradientBoostingRegressor, {
        "n_estimators": 200,
        "learning_rate": 0.05,
        "max_depth": 2,
        "random_state": SEMILLA,
    }),
)


def constructores():
    """{algoritmo: fábrica de estimador} con hiperparámetros fijos."""
    def fabrica(clase, params):
        return lambda: clase(**params)

    return {
        nombre: fabrica(clase, params)
        for nombre, clase, params in _FABRICAS
    }


def hiperparametros_de(algoritmo):
    """Hiperparámetros fijos del algoritmo (para modelos_ml)."""
    for nombre, _, params in _FABRICAS:
        if nombre == algoritmo:
            return dict(params)
    raise KeyError(f"Algoritmo desconocido: {algoritmo!r}")


def estrategia_de(n):
    """Estrategia de evaluación fijada ANTES de ver resultados."""
    if n >= 100:
        return {
            "nombre": "holdout_final_20",
            "pliegues": 5,
            "repeticiones": 1,
            "holdout": 0.2,
        }
    if n >= 30:
        return {
            "nombre": "cv_repetida",
            "pliegues": 5,
            "repeticiones": 5,
            "holdout": None,
        }
    return {
        "nombre": "cv_agrupada",
        "pliegues": 5,
        "repeticiones": 1,
        "holdout": None,
    }


def _tubo(prep, fabrica):
    """Pipeline completo: preparación SIN ajustar + estimador."""
    return Pipeline(
        [("preparar", deepcopy(prep)), ("modelo", fabrica())]
    )


def entrenar_completo(datos, algoritmo, conjunto=CONJUNTO_PLAN):
    """(pipeline ajustado con TODOS los datos, X, y) — para guardar."""
    X, y, prep, _ = preparar(datos, conjunto=conjunto)
    tubo = _tubo(prep, constructores()[algoritmo])
    tubo.fit(X, y)
    # Rango visto en el entrenamiento: el servicio avisa si una
    # predición cae fuera de él (decisión 229, «si se alcanzó»). Viaja
    # serializado dentro del propio .joblib.
    rangos = {}
    for columna in X.columns:
        if columna not in COLUMNAS_NUMERICAS:
            continue
        vista = X[columna].dropna()
        if len(vista):
            rangos[columna] = {
                "min": float(vista.min()),
                "max": float(vista.max()),
            }
    tubo.rangos_entrenamiento_ = rangos
    return tubo, X, y


def _metricas_pliegues(rmses, maes):
    return {
        "mae": float(statistics.fmean(maes)),
        "rmse": float(statistics.fmean(rmses)),
        "desvio_rmse": (
            float(statistics.stdev(rmses)) if len(rmses) > 1 else 0.0
        ),
    }


def _metricas_pooled(reales, predichos):
    reales = np.asarray(reales, dtype=float)
    predichos = np.asarray(predichos, dtype=float)
    errores = predichos - reales
    r2 = 1.0 - float(np.sum(errores**2)) / float(
        np.sum((reales - np.mean(reales)) ** 2)
    ) if len(reales) > 1 and np.std(reales) > 0 else float("nan")
    mape = None
    if np.all(reales != 0):
        mape = float(np.mean(np.abs(errores / reales)) * 100)
    return {"r2": r2, "mape": mape}


def _por_cultivo(cultivos, reales, predichos):
    if cultivos is None:
        return None
    grupos = {}
    for cultivo, real, pred in zip(cultivos, reales, predichos):
        clave = str(cultivo)
        grupos.setdefault(clave, {"reales": [], "predichos": []})
        grupos[clave]["reales"].append(real)
        grupos[clave]["predichos"].append(pred)
    salida = {}
    for cultivo, valores in sorted(grupos.items()):
        m = linea_base.evaluar(valores["reales"], valores["predichos"])
        salida[cultivo] = {
            "mae": m["mae"],
            "rmse": m["rmse"],
            "filas": m["filas"],
        }
    return salida


def evaluar(datos, estrategia=None, conjunto=CONJUNTO_PLAN, semilla=SEMILLA):
    """Evalúa los tres candidatos y la línea base con el mismo corte.

    Devuelve:
    {
      "estrategia": {...},
      "candidatos": {algoritmo: {mae, rmse, desvio_rmse, r2, mape,
                                 rmse_pliegues, por_cultivo}},
      "linea_base": {mae, rmse, desvio_rmse, r2, mape, por_cultivo},
      "prueba_final": {algoritmo: {...}} | None,   # solo holdout
      "fuera": {...},
      "n": n,
    }
    """
    X, y, prep, fuera = preparar(datos, conjunto=conjunto)
    grupos = validacion.grupos_de(datos)
    cultivos = (
        datos["cultivo"].tolist() if "cultivo" in datos.columns else None
    )
    n = len(datos)
    plan = dict(estrategia or estrategia_de(n))

    indices_train = []
    indices_test = []
    if plan.get("holdout"):
        corte = GroupShuffleSplit(
            n_splits=1, test_size=plan["holdout"], random_state=semilla
        )
        train_tmp, prueba_final = next(
            corte.split(X, None, grupos)
        )
        sub_grupos = grupos[train_tmp]
        for rep in range(plan["repeticiones"]):
            cortes = validacion.particiones(
                datos.iloc[train_tmp],
                n_pliegues=min(plan["pliegues"], len(set(sub_grupos))),
                semilla=semilla + rep,
            )
            for tr, te in cortes:
                indices_train.append(train_tmp[tr])
                indices_test.append(train_tmp[te])
        plan["_holdout"] = (train_tmp, prueba_final)
    else:
        n_grupos = len(set(grupos))
        for rep in range(plan["repeticiones"]):
            cortes = validacion.particiones(
                datos,
                n_pliegues=min(plan["pliegues"], n_grupos),
                semilla=semilla + rep,
            )
            indices_train.extend(
                tr for tr, _ in cortes
            )
            indices_test.extend(te for _, te in cortes)

    acumulados = {
        nombre: {"rmses": [], "maes": [], "reales": [], "predichos": [],
                  "cultivos": []}
        for nombre in (*NOMBRES, criterio.LINEA_BASE)
    }

    for train, prueba in zip(indices_train, indices_test):
        media = linea_base.predecir_media(y.iloc[train])
        pred_base = np.full(len(prueba), media, dtype=float)
        reales = y.iloc[prueba].to_numpy(dtype=float)
        m_base = linea_base.evaluar(reales, pred_base)
        acumulados[criterio.LINEA_BASE]["rmses"].append(m_base["rmse"])
        acumulados[criterio.LINEA_BASE]["maes"].append(m_base["mae"])
        acumulados[criterio.LINEA_BASE]["reales"].extend(reales)
        acumulados[criterio.LINEA_BASE]["predichos"].extend(pred_base)
        if cultivos is not None:
            acumulados[criterio.LINEA_BASE]["cultivos"].extend(
                cultivos[i] for i in prueba
            )
        for nombre, fabrica in constructores().items():
            tubo = _tubo(prep, fabrica)
            tubo.fit(X.iloc[train], y.iloc[train])
            pred = tubo.predict(X.iloc[prueba])
            errores = pred - reales
            acumulados[nombre]["rmses"].append(
                float(np.sqrt(np.mean(errores**2)))
            )
            acumulados[nombre]["maes"].append(float(np.mean(np.abs(errores))))
            acumulados[nombre]["reales"].extend(reales)
            acumulados[nombre]["predichos"].extend(pred)
            if cultivos is not None:
                acumulados[nombre]["cultivos"].extend(
                    cultivos[i] for i in prueba
                )

    candidatos = {}
    for nombre in NOMBRES:
        acc = acumulados[nombre]
        metricas = _metricas_pliegues(acc["rmses"], acc["maes"])
        metricas.update(_metricas_pooled(acc["reales"], acc["predichos"]))
        metricas["rmse_pliegues"] = [round(v, 4) for v in acc["rmses"]]
        if cultivos is not None:
            metricas["por_cultivo"] = _por_cultivo(
                acc["cultivos"], acc["reales"], acc["predichos"]
            )
        candidatos[nombre] = metricas

    acc = acumulados[criterio.LINEA_BASE]
    base = _metricas_pliegues(acc["rmses"], acc["maes"])
    base.update(_metricas_pooled(acc["reales"], acc["predichos"]))
    base["rmse_pliegues"] = [round(v, 4) for v in acc["rmses"]]
    if cultivos is not None:
        base["por_cultivo"] = _por_cultivo(
            acc["cultivos"], acc["reales"], acc["predichos"]
        )

    resultado = {
        "estrategia": {
            "nombre": plan["nombre"],
            "pliegues": plan["pliegues"],
            "repeticiones": plan["repeticiones"],
            "holdout": plan.get("holdout"),
            "semilla": semilla,
        },
        "candidatos": candidatos,
        "linea_base": base,
        "prueba_final": None,
        "fuera": fuera,
        "n": n,
    }

    if plan.get("_holdout"):
        train_tmp, prueba_final = plan["_holdout"]
        final = {}
        reales_f = y.iloc[prueba_final].to_numpy(dtype=float)
        media_f = linea_base.predecir_media(y.iloc[train_tmp])
        m_base = linea_base.evaluar(
            reales_f, np.full(len(prueba_final), media_f, dtype=float)
        )
        final[criterio.LINEA_BASE] = m_base
        for nombre, fabrica in constructores().items():
            tubo = _tubo(prep, fabrica)
            tubo.fit(X.iloc[train_tmp], y.iloc[train_tmp])
            pred = tubo.predict(X.iloc[prueba_final])
            final[nombre] = linea_base.evaluar(reales_f, pred)
        resultado["prueba_final"] = final
        resultado["estrategia"]["n_prueba"] = len(prueba_final)
        resultado["estrategia"]["n_entrenamiento"] = len(train_tmp)
    else:
        resultado["estrategia"]["n_prueba"] = 0
        resultado["estrategia"]["n_entrenamiento"] = n

    return resultado


def resumenes_de(resultado):
    """Entrada del criterio a partir del resultado de evaluar()."""
    resumenes = {
        nombre: {
            "rmse": datos["rmse"],
            "desvio": datos["desvio_rmse"],
        }
        for nombre, datos in resultado["candidatos"].items()
    }
    resumenes[criterio.LINEA_BASE] = {"rmse": resultado["linea_base"]["rmse"]}
    return resumenes


def aplicar_criterio(resultado):
    """(dict del criterio) aplicado al resultado de evaluar()."""
    return criterio.elegir(resumenes_de(resultado))


def nombre_tramo(n):
    """Tramo de datos en la terminología del criterio."""
    if n >= 100:
        return "100 o más reales"
    if n >= 30:
        return "30 a 99 reales"
    return "menos de 30 reales"


def informe_markdown(resultado, resumen, *, origen, version, archivo):
    """Informe de resultados (docs/informe_resultados_ml.md)."""
    lineas = [
        "# Informe de resultados de los modelos de rendimiento",
        "",
        "> **Semana 22 — generación automática de `entrenar_modelos` "
        f"(versión {version}).**",
        "> Criterio de selección: `docs/criterio_seleccion.md`, "
        "escrito antes de entrenar.",
        "",
        "## Datos",
        "",
        f"- Archivo: `{archivo}`",
        f"- Origen declarado: **{origen}**",
        f"- Filas usadas: **{resultado['n']}** "
        f"(tramo: {nombre_tramo(resultado['n'])})",
        f"- Estrategia: {resultado['estrategia']['nombre']} "
        f"({resultado['estrategia']['pliegues']} pliegues × "
        f"{resultado['estrategia']['repeticiones']} repetición(es), "
        f"semilla {resultado['estrategia']['semilla']}, agrupado por "
        "productor)",
        "",
        "## Tabla comparativa (validación agrupada)",
        "",
        "| Algoritmo | MAE (kg/ha) | RMSE (kg/ha) | Desvío entre pliegues | R² | MAPE |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    def fila(nombre, m):
        mape = f"{m['mape']:.2f} %" if m.get("mape") is not None else "—"
        return (
            f"| {nombre} | {m['mae']:.2f} | {m['rmse']:.2f} | "
            f"{m.get('desvio_rmse', 0):.2f} | {m['r2']:.3f} | {mape} |"
        )

    for nombre in NOMBRES:
        lineas.append(fila(nombre, resultado["candidatos"][nombre]))
    lineas.append(fila("Línea base (media)", resultado["linea_base"]))
    lineas.append("")

    if resultado.get("prueba_final"):
        lineas += [
            "## Conjunto de prueba final (20 %, usado una sola vez)",
            "",
            "| Algoritmo | MAE | RMSE |",
            "|---|---:|---:|",
        ]
        for nombre in (*NOMBRES, criterio.LINEA_BASE):
            m = resultado["prueba_final"][nombre]
            lineas.append(
                f"| {nombre} | {m['mae']:.2f} | {m['rmse']:.2f} |"
            )
        lineas.append("")

    lineas += [
        "## Criterio aplicado",
        "",
        f"**Resultado:** {resumen['motivo']}",
        "",
    ]
    if resumen["elegido"]:
        lineas += [
            f"**Modelo elegido:** {resumen['elegido']}",
            "",
        ]

    primer = next(
        (m for m in resultado["candidatos"].values() if m.get("por_cultivo")),
        None,
    )
    if primer:
        lineas += ["## Métricas por cultivo (elegido)", ""]
        elegido = resumen["elegido"] or NOMBRES[0]
        por_cultivo = resultado["candidatos"][elegido].get("por_cultivo")
        if por_cultivo:
            lineas += [
                "| Cultivo | Filas | MAE | RMSE |",
                "|---|---:|---:|---:|",
            ]
            for cultivo, m in por_cultivo.items():
                lineas.append(
                    f"| {cultivo} | {m['filas']} | {m['mae']:.2f} | "
                    f"{m['rmse']:.2f} |"
                )
            lineas.append("")

    lineas += [
        "## Qué se puede afirmar",
        "",
    ]
    if resultado["n"] < 30 or origen != "real":
        lineas += [
            "- **Los datos son de demostración o menores de 30 "
            "campañas:** estas métricas son una **verificación técnica "
            "del flujo**, NO un resultado de la tesis.",
            "- El sistema está comprobado: entrena, compara, elige con "
            "el criterio escrito y guarda el modelo.",
        ]
    else:
        lineas += [
            "- Resultados presentables con sus limitaciones declaradas "
            "(tamaño de los datos y tramo de validación).",
        ]
    lineas += [
        "- Ningún modelo se activa si no mejora a la línea base.",
        "",
        "---",
        "",
        "Limitaciones y mejoras futuras: "
        "`docs/limitaciones_conocidas.md`.",
        "",
    ]
    return "\n".join(lineas)


def a_json(resultado):
    """Resultado serializable (para resultados_v*.json)."""
    return json.loads(json.dumps(resultado, ensure_ascii=False, default=str))
