"""Entrenamiento desde el sistema (Semana 23, decisiones 259-262).

`entrenar_desde_sistema` es el núcleo del comando trabajador
`procesar_entrenamientos` (F2): lee el dataset de
vw_dataset_entrenamiento en memoria — SIN CSV y sin ML_EXPORT_DIR —
sigue la MISMA ruta que el comando `entrenar_modelos` (limpieza →
estrategia de evaluación → criterio escrito → tubo completo con la
semilla 42) y da de alta el resultado con `registro.registrar` usando
el artefacto en la BD (`contenido`, decisión 260).

El origen de los datos es siempre el sistema: `origen_datos` queda en
"sistema" (decisión 259) y `ML_ORIGEN_DATOS` solo sella la honestidad
en `datos_de` (262); si dice demostración, registrar exige la bandera
de desarrollo. Registrar NUNCA activa el modelo (inamovible: entrenar
no activa, decisión 251).
"""
import io
import os

import joblib

from ml import carga, entrenamiento, limpieza, registro


class ErrorTrabajo(Exception):
    """El entrenamiento no llega al registro: el motivo es el dato."""


def datos_de_entorno():
    """Sello de honestidad desde ML_ORIGEN_DATOS (default «real»)."""
    return os.getenv("ML_ORIGEN_DATOS", "real").strip() or "real"


def entrenar_desde_datos(datos, *, huella_dataset, version, datos_de):
    """Evalúa, aplica el criterio y serializa el tubo del elegido.

    Devuelve (salida, contenido): `salida` es el mismo diccionario de
    métricas que guarda el comando en resultados_v<version>.json, y
    `contenido` son los bytes .joblib del modelo elegido, listos para
    `registro.registrar(contenido=...)`. Lanza ErrorTrabajo si no hay
    datos suficientes o si ningún modelo supera a la línea base.
    """
    limpio, resumen = limpieza.limpiar(datos)
    if len(limpio) < 5:
        raise ErrorTrabajo(
            f"Quedan {len(limpio)} filas tras la limpieza: no hay datos "
            "suficientes para validar por grupos."
        )

    plan = entrenamiento.estrategia_de(len(limpio))
    resultado = entrenamiento.evaluar(limpio, estrategia=plan)
    resolucion = entrenamiento.aplicar_criterio(resultado)
    if not resolucion["elegido"]:
        raise ErrorTrabajo(
            "Ningún modelo supera a la línea base: no hay nada que "
            "registrar."
        )

    tubo, _, _ = entrenamiento.entrenar_completo(
        limpio, resolucion["elegido"]
    )
    buffer = io.BytesIO()
    joblib.dump(tubo, buffer)
    contenido = buffer.getvalue()

    salida = entrenamiento.a_json(resultado)
    salida.update(
        {
            "version": str(version),
            "sha256_dataset": huella_dataset,
            "origen_datos": "sistema",
            "datos_de": datos_de,
            "excluidas": resumen.get("filas_excluidas"),
            "criterio": resolucion,
            "criterio_archivo": "docs/criterio_seleccion.md",
        }
    )
    return salida, contenido


def entrenar_desde_sistema(*, usuario, version, datos_de=None,
                           desarrollo=False, activar=False):
    """Entrena desde la vista y registra 1 entrenamiento + 3 modelos.

    Devuelve el resumen de registro.registrar con la clave adicional
    `resultados` (las métricas completas que quedaron en la BD).
    """
    if datos_de is None:
        datos_de = datos_de_entorno()

    datos = carga.cargar_desde_bd()
    salida, contenido = entrenar_desde_datos(
        datos,
        huella_dataset=carga.huella_desde_bd(),
        version=version,
        datos_de=datos_de,
    )
    resumen = registro.registrar(
        usuario=usuario,
        resultados=salida,
        version=version,
        contenido=contenido,
        desarrollo=desarrollo,
        activar=activar,
    )
    resumen["resultados"] = salida
    return resumen
