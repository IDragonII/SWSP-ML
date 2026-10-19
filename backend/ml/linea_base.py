"""Línea base de referencia (Semana 21): predecir la media.

El modelo más simple posible — y por eso es la barra del Sprint 13:
cualquier modelo que se entrene después tiene que ganarle en cada
pliegue de la validación agrupada. Solo calcula una media y dos
errores (MAE y RMSE, en las mismas unidades que el objetivo, kg/ha);
aquí no se entrena nada más (prueba 362).
"""
import math


def predecir_media(objetivo_entrenamiento):
    """La predicción constante: media del objetivo de ENTRENAMIENTO.

    Solo mira el entrenamiento: ni la prueba ni el total entran en la
    media (si entraran, la barra estaría trampeada).
    """
    valores = []
    for valor in objetivo_entrenamiento:
        if valor is None:
            continue
        numero = float(valor)
        if not math.isnan(numero):
            valores.append(numero)
    if not valores:
        raise ValueError(
            "La línea base no puede predecir: no hay objetivo en el "
            "entrenamiento."
        )
    return sum(valores) / len(valores)


def evaluar(objetivo_real, predicho):
    """MAE y RMSE de la predicción frente al objetivo real.

    Misma escala que rendimiento_kg_ha: si la línea base da un RMSE de
    250, un modelo tiene que bajar de 250 para ganar.
    """
    real = [float(v) for v in objetivo_real]
    adivinado = [float(v) for v in predicho]
    if not real:
        raise ValueError(
            "La evaluación necesita al menos una fila con objetivo real."
        )
    if len(real) != len(adivinado):
        raise ValueError(
            "La evaluación necesita la misma cantidad de valores "
            "reales y predichos."
        )
    errores = [a - b for a, b in zip(real, adivinado)]
    mae = sum(abs(e) for e in errores) / len(errores)
    rmse = math.sqrt(sum(e * e for e in errores) / len(errores))
    return {"mae": mae, "rmse": rmse, "filas": len(real)}
