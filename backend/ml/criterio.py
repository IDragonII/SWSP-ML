"""Criterio de selección del modelo (Semana 22, decisión 210).

La regla está escrita y commiteada ANTES del primer entrenamiento en
`docs/criterio_seleccion.md` y aquí se aplica tal cual (prueba 367):

1. Gana el MENOR RMSE medio en la validación agrupada.
2. Si la diferencia con un candidato más simple es menor que UN DESVÍO
   ESTÁNDAR entre particiones (el del mejor), gana el más simple, en
   orden: regresión lineal → Random Forest → Gradient Boosting.
3. Además debe MEJORAR A LA LÍNEA BASE; si no, no se elige ninguno.

No hay hueco aquí para mirar los resultados y decidir otra cosa.
"""
LINEA_BASE = "LINEA_BASE"

ORDEN_SIMPLICIDAD = (
    "REGRESION_LINEAL",
    "RANDOM_FOREST",
    "GRADIENT_BOOSTING",
)

NO_SUPERA_BASE = (
    "Ningún modelo mejora la línea base: no se elige ninguno "
    "(queda registrado como evidencia)."
)


class ErrorCriterio(ValueError):
    """Faltan candidatos o claves para aplicar el criterio."""


def elegir(resumenes):
    """Aplica la regla escrita.

    `resumenes` = {
        "REGRESION_LINEAL": {"rmse": media, "desvio": sigma},
        "RANDOM_FOREST":    {...},
        "GRADIENT_BOOSTING": {...},
        "LINEA_BASE":       {"rmse": media},
    }

    Devuelve {"elegido": nombre o None, "motivo": str, "sigma": float}.
    """
    faltan = [
        nombre
        for nombre in (*ORDEN_SIMPLICIDAD, LINEA_BASE)
        if nombre not in resumenes
    ]
    if faltan:
        raise ErrorCriterio(
            "El criterio necesita los tres candidatos y la línea base; "
            f"faltan: {', '.join(faltan)}."
        )
    for nombre in ORDEN_SIMPLICIDAD:
        if "rmse" not in resumenes[nombre]:
            raise ErrorCriterio(f"Falta el RMSE de {nombre}.")

    mejor = min(ORDEN_SIMPLICIDAD, key=lambda n: resumenes[n]["rmse"])
    rmse_mejor = float(resumenes[mejor]["rmse"])
    sigma = float(resumenes[mejor].get("desvio") or 0.0)

    # Candidatos dentro del desvío del mejor (el mejor siempre incluido)
    cerca = [
        n
        for n in ORDEN_SIMPLICIDAD
        if float(resumenes[n]["rmse"]) - rmse_mejor < sigma
    ]
    elegido = min(cerca, key=lambda n: ORDEN_SIMPLICIDAD.index(n))

    rmse_base = float(resumenes[LINEA_BASE]["rmse"])
    if rmse_base <= float(resumenes[elegido]["rmse"]):
        return {"elegido": None, "motivo": NO_SUPERA_BASE, "sigma": sigma}

    if elegido == mejor:
        motivo = (
            f"{elegido} gana con el menor RMSE ({rmse_mejor:.2f}); la "
            f"diferencia con los demás supera el desvío ({sigma:.2f})."
        )
    else:
        motivo = (
            f"El RMSE de {elegido} "
            f"({resumenes[elegido]['rmse']:.2f}) está a menos de un "
            f"desvío ({sigma:.2f}) del mejor ({mejor}, {rmse_mejor:.2f}) "
            "y gana la regla de simplicidad: lineal > Random Forest > "
            "Gradient Boosting."
        )
    return {"elegido": elegido, "motivo": motivo, "sigma": sigma}
