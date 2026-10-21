"""Registro y activación de modelos (Sprint 14, HU-171/HU-172).

Dos funciones, una sola red de seguridad (decisiones 220-224):

- `registrar` da de alta **1 entrenamiento y 3 modelos** a partir de
  `resultados_v<version>.json` de `entrenar_modelos`: exige usuario
  activo con `ml.entrenar`, al menos 30 campañas, la bandera
  `--desarrollo` para modelos de demostración (221), versión sin usar
  (única por algoritmo), archivo con huella verificada y una
  predicción de prueba antes de tocar la base. Auditoría `CREAR`.
  El artefacto puede llegar como `contenido` (los bytes del .joblib
  guardados en la BD, ruta del trabajador, decisión 260) o como
  `archivo` con manifiesto (ruta del comando manual); uno u otro, no
  los dos. El sello de honestidad `datos_de` (decisión 262) viaja en
  `variables_usadas` cuando las métricas lo traen.
- `activar` exige `ml.activar_modelo`, que verifique el artefacto —
  archivo con manifiesto o contenido con su huella — y una predicción
  de prueba antes de tocar nada; en la MISMA transacción desactiva el
  anterior y activa el nuevo (un solo modelo activo), con eventos
  `DESACTIVAR` y `ACTIVAR` (222).

Los dos se usan desde el comando `registrar_modelo` y desde la API
(`POST /api/ml/modelos/{id}/activar/`), con los mismos permisos.
"""
import hashlib
import io
import shutil
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.db import transaction

from auditoria.registrar import registrar_evento
from ml import catalogo, entrenamiento, guardado, preparacion
from ml.models import EntrenamientoML, ModeloML
from usuarios.models import RolPermiso

MODULO_AUDITORIA = "Machine Learning"
MINIMO_REGISTROS = 30
PERMISO_REGISTRAR = "ml.entrenar"
PERMISO_ACTIVAR = "ml.activar_modelo"
# Tope de ck_modelo_tamano (decisión 254): 20 MiB por artefacto en la BD
LIMITE_CONTENIDO = 20 * 1024 * 1024
CLAVES_REQUERIDAS = (
    "n", "version", "origen_datos", "sha256_dataset", "estrategia",
    "candidatos", "linea_base", "criterio",
)


class ErrorRegistro(Exception):
    """Registro o activación rechazado: el mensaje explica el motivo."""


def _exigir(usuario, codigo):
    if usuario is None or not usuario.is_active:
        raise ErrorRegistro("El usuario debe existir y estar activo.")
    tiene = RolPermiso.objects.filter(
        rol_id=usuario.rol_id, permiso__codigo=codigo
    ).exists()
    if not tiene:
        raise ErrorRegistro(
            f"El usuario «{usuario.username}» no tiene el permiso {codigo}."
        )


def _decimal(valor, decimales):
    return Decimal(f"{float(valor):.{decimales}f}")


def _validar(resultados, version, desarrollo):
    """Comprobaciones previas; devuelve (elegido, n, origen)."""
    faltan = [clave for clave in CLAVES_REQUERIDAS if clave not in resultados]
    if faltan:
        raise ErrorRegistro(
            "El archivo de métricas no tiene los campos: "
            + ", ".join(faltan)
        )
    if str(resultados["version"]) != str(version):
        raise ErrorRegistro(
            f"Las métricas son de la versión «{resultados['version']}» y se "
            f"pidió registrar la «{version}»."
        )
    n = int(resultados["n"])
    if n < MINIMO_REGISTROS:
        raise ErrorRegistro(
            f"Se necesitan al menos {MINIMO_REGISTROS} campañas de "
            f"entrenamiento para registrar el modelo (hay {n})."
        )
    origen = str(resultados.get("origen_datos") or "")
    # Sello de honestidad (decisión 262): «demostración» en cualquiera
    # de los dos campos exige la bandera explícita de desarrollo.
    honestidad = str(resultados.get("datos_de") or "")
    if "demostr" in f"{origen} {honestidad}".lower() and not desarrollo:
        raise ErrorRegistro(
            f"El modelo fue entrenado con datos de {honestidad or origen}: "
            "en un entorno real solo se registra con la bandera explícita "
            "--desarrollo."
        )
    elegido = resultados["criterio"].get("elegido")
    if not elegido:
        raise ErrorRegistro(
            "El criterio no eligió ningún modelo (ninguno mejoró a la línea "
            "base): no hay archivo que registrar."
        )
    if elegido not in entrenamiento.NOMBRES:
        raise ErrorRegistro(f"Algoritmo elegido desconocido: {elegido}.")
    for algoritmo in entrenamiento.NOMBRES:
        candidato = resultados["candidatos"].get(algoritmo)
        if not isinstance(candidato, dict):
            raise ErrorRegistro(
                f"Faltan las métricas del algoritmo {algoritmo}."
            )
        for clave in ("mae", "rmse", "r2"):
            if clave not in candidato:
                raise ErrorRegistro(
                    f"Falta {clave} en las métricas de {algoritmo}."
                )
        if float(candidato["mae"]) < 0 or float(candidato["rmse"]) < 0:
            raise ErrorRegistro(
                f"Métricas negativas en {algoritmo}: MAE y RMSE no pueden "
                "ser negativos."
            )
    if "rmse" not in resultados["linea_base"]:
        raise ErrorRegistro("Falta la línea base en las métricas.")
    return elegido, n, origen


def _columnas_del_tubo(tubo):
    try:
        return list(tubo.named_steps["preparar"].feature_names_in_)
    except (AttributeError, KeyError, TypeError, NameError) as error:
        raise ErrorRegistro(
            "El archivo no es un pipeline de predicción del sistema."
        ) from error


def _probar(tubo, columnas):
    """Predicción de prueba sobre una fila sintética (decisión 222)."""
    numericas = set(preparacion.columnas_del_pipeline(columnas)[0])
    fila = {c: (0.0 if c in numericas else "") for c in columnas}
    try:
        valor = tubo.predict(pd.DataFrame([fila]))[0]
    except Exception as error:
        raise ErrorRegistro(
            f"La predicción de prueba falló: {error}"
        ) from error
    if not np.isfinite(float(valor)):
        raise ErrorRegistro(
            "La predicción de prueba devolvió un valor no finito."
        )


def _cargar_y_probar(ruta, destino):
    try:
        tubo = guardado.cargar_verificado(ruta, destino)
    except guardado.ErrorManifiesto as error:
        raise ErrorRegistro(str(error)) from error
    columnas = _columnas_del_tubo(tubo)
    _probar(tubo, columnas)
    return tubo, columnas


def _cargar_tubo_bytes(contenido):
    """joblib.load desde los bytes guardados en la BD + prueba de
    predicción (la misma red de seguridad que la ruta con manifiesto)."""
    try:
        tubo = joblib.load(io.BytesIO(contenido))
    except Exception as error:  # noqa: BLE001 (pickle lanza varios tipos)
        raise ErrorRegistro(
            f"El contenido del modelo no se pudo cargar: {error}"
        ) from error
    columnas = _columnas_del_tubo(tubo)
    _probar(tubo, columnas)
    return tubo, columnas


def _hiperparametros(candidato, linea_base):
    """Lo que guarda modelos_ml.hiperparametros (decisión 223)."""
    base = {clave: linea_base.get(clave)
            for clave in ("mae", "rmse", "r2", "desvio_rmse", "mape")
            if clave in linea_base}
    validacion = {clave: candidato.get(clave)
                  for clave in ("desvio_rmse", "mape", "rmse_pliegues",
                                "por_cultivo")
                  if clave in candidato}
    return {
        "hiperparametros": {},
        "linea_base": base,
        "validacion": validacion,
    }


def registrar(*, usuario, resultados, version, archivo=None,
              destino=None, contenido=None, desarrollo=False,
              activar=False, seco=False):
    """Alta de 1 entrenamiento y 3 modelos; devuelve un resumen.

    El artefacto del modelo elegido llega de dos formas (decisión 260):
    `contenido` (bytes del .joblib que quedan en modelos_ml.contenido,
    ruta del trabajador) o `archivo` (+ manifiesto de huellas, ruta del
    comando manual). No se admiten los dos a la vez.
    """
    _exigir(usuario, PERMISO_REGISTRAR)
    elegido, n, origen = _validar(resultados, version, desarrollo)
    if activar:
        # Permiso de la activación comprobado ANTES de escribir nada
        _exigir(usuario, PERMISO_ACTIVAR)
    if ModeloML.objects.filter(version=version).exists():
        raise ErrorRegistro(
            f"La versión «{version}» ya está registrada: cada versión solo "
            "se da de alta una vez."
        )
    if contenido is not None and archivo is not None:
        raise ErrorRegistro(
            "Indica contenido (modelo en la BD) o archivo (con manifiesto), "
            "no los dos."
        )

    # --- artefacto y huella (antes de tocar la base) --------------------
    huella_modelo = None
    if contenido is not None:
        # Modelo en la BD (decisión 254): sin disco ni manifiesto
        if len(contenido) > LIMITE_CONTENIDO:
            raise ErrorRegistro(
                f"El modelo pesa {len(contenido)} bytes: el máximo de "
                f"ck_modelo_tamano es {LIMITE_CONTENIDO} (20 MiB)."
            )
        huella_modelo = hashlib.sha256(contenido).hexdigest()
        tubo, columnas = _cargar_tubo_bytes(contenido)
        del tubo
        nombre = None
        if seco:
            return {
                "seco": True, "n": n, "origen": origen, "elegido": elegido,
                "version": version, "huella": huella_modelo,
                "copiar": False, "activar": activar,
                "variables": columnas,
            }
    else:
        carpeta_destino = guardado.carpeta(destino)
        nombre = guardado.nombre_archivo(elegido, version)
        ruta_final = carpeta_destino / nombre
        externo = Path(archivo).resolve() if archivo is not None else None
        es_externo = externo is not None and externo != ruta_final.resolve()

        if es_externo:
            if not externo.exists():
                raise ErrorRegistro(f"No existe el archivo {externo.name}.")
            huella = guardado.huella_de(externo)
            if seco:
                return {
                    "seco": True, "n": n, "origen": origen,
                    "elegido": elegido, "version": version, "huella": huella,
                    "copiar": True, "activar": activar,
                }
            carpeta_destino.mkdir(parents=True, exist_ok=True)
            shutil.copy2(externo, ruta_final)
            guardado.registrar_archivo(
                ruta_final,
                destino=destino,
                algoritmo=elegido,
                version=version,
                origen_datos=origen,
                n_registros=n,
            )
        else:
            if not guardado.verificar(ruta_final, destino):
                raise ErrorRegistro(
                    f"El archivo {nombre} no está en el manifiesto de huellas "
                    "o su huella no coincide (archivo alterado o ausente)."
                )
            if seco:
                tubo, columnas = _cargar_y_probar(ruta_final, destino)
                del tubo
                return {
                    "seco": True, "n": n, "origen": origen,
                    "elegido": elegido, "version": version,
                    "huella": guardado.huella_de(ruta_final),
                    "copiar": False, "activar": activar,
                    "variables": columnas,
                }

        tubo, columnas = _cargar_y_probar(ruta_final, destino)

    variables_usadas = {
        "variables": columnas,
        "conjunto": catalogo.CONJUNTO_PLAN,
        "origen_datos": origen,
        "sha256_dataset": resultados["sha256_dataset"],
        "semilla": resultados["estrategia"].get("semilla"),
        "estrategia": resultados["estrategia"],
        # El veredicto viaja con el entrenamiento: la pantalla de
        # resultados lo lee para marcar el recomendado (decisión 264)
        "criterio": resultados["criterio"],
    }
    if "datos_de" in resultados:
        variables_usadas["datos_de"] = resultados["datos_de"]
    linea_base = resultados["linea_base"]
    activado = None

    with transaction.atomic():
        entrenamiento_ml = EntrenamientoML.objects.create(
            n_registros=n,
            n_entrenamiento=int(resultados["estrategia"].get("n_entrenamiento") or n),
            n_prueba=int(resultados["estrategia"].get("n_prueba") or 0),
            variables_usadas=variables_usadas,
            observaciones=resultados["criterio"].get("motivo"),
            ejecutado_por=usuario,
        )
        modelos = []
        for algoritmo in entrenamiento.NOMBRES:
            candidato = resultados["candidatos"][algoritmo]
            hiper = _hiperparametros(candidato, linea_base)
            hiper["hiperparametros"] = entrenamiento.hiperparametros_de(algoritmo)
            es_elegido = algoritmo == elegido
            modelos.append(ModeloML.objects.create(
                entrenamiento=entrenamiento_ml,
                algoritmo=algoritmo,
                version=str(version),
                mae=_decimal(candidato["mae"], 2),
                rmse=_decimal(candidato["rmse"], 2),
                r2=_decimal(candidato["r2"], 4),
                hiperparametros=hiper,
                archivo=nombre if es_elegido else None,
                contenido=(
                    contenido
                    if contenido is not None and es_elegido else None
                ),
                huella=(
                    huella_modelo
                    if contenido is not None and es_elegido else None
                ),
                versiones_librerias=(
                    guardado.versiones_librerias()
                    if contenido is not None and es_elegido else None
                ),
                activo=False,
            ))
        registrar_evento(
            usuario=usuario,
            accion="CREAR",
            modulo=MODULO_AUDITORIA,
            detalle={
                "tabla": "modelos_ml",
                "version": str(version),
                "algoritmo": elegido,
                "n_registros": n,
                "origen_datos": origen,
                "artefacto": "contenido" if contenido is not None
                else "archivo",
                "archivo": nombre,
            },
        )
        if activar:
            elegido_obj = next(
                m for m in modelos if m.algoritmo == elegido
            )
            activado = activar_modelo(elegido_obj, usuario, destino=destino)

    return {
        "seco": False,
        "n": n,
        "origen": origen,
        "elegido": elegido,
        "version": str(version),
        "huella": (
            huella_modelo if contenido is not None
            else guardado.huella_de(ruta_final)
        ),
        "variables": columnas,
        "entrenamiento": entrenamiento_ml,
        "modelos": modelos,
        "activado": activado,
    }


def activar_modelo(modelo, usuario, *, destino=None):
    """Un solo modelo activo; todo en una transacción (decisión 222)."""
    _exigir(usuario, PERMISO_ACTIVAR)
    if modelo.contenido:
        # Modelo en la BD (S23): la huella se verifica sobre los bytes
        bytea = bytes(modelo.contenido)
        huella = hashlib.sha256(bytea).hexdigest()
        if not modelo.huella or modelo.huella != huella:
            raise ErrorRegistro(
                f"La huella del contenido de {modelo} no coincide con la "
                "registrada: no se puede activar."
            )
        _cargar_tubo_bytes(bytea)
    elif modelo.archivo:
        ruta = guardado.carpeta(destino) / modelo.archivo
        if not ruta.exists():
            raise ErrorRegistro(
                f"No existe el archivo {modelo.archivo}: no se puede activar."
            )
        if not guardado.verificar(ruta, destino):
            raise ErrorRegistro(
                f"La huella de {modelo.archivo} no coincide con el manifiesto: "
                "no se puede activar."
            )
        _cargar_y_probar(ruta, destino)
    else:
        raise ErrorRegistro(
            f"El modelo {modelo} no tiene archivo asociado: solo puede "
            "activarse el modelo elegido por el criterio."
        )

    with transaction.atomic():
        desactivados = ModeloML.objects.filter(activo=True).exclude(
            pk=modelo.pk
        )
        for otro in desactivados:
            otro.activo = False
            otro.save(update_fields=["activo"])
            registrar_evento(
                usuario=usuario,
                accion="DESACTIVAR",
                modulo=MODULO_AUDITORIA,
                detalle={
                    "tabla": "modelos_ml",
                    "algoritmo": otro.algoritmo,
                    "version": otro.version,
                },
            )
        modelo.activo = True
        modelo.save(update_fields=["activo"])
        registrar_evento(
            usuario=usuario,
            accion="ACTIVAR",
            modulo=MODULO_AUDITORIA,
            detalle={
                "tabla": "modelos_ml",
                "algoritmo": modelo.algoritmo,
                "version": modelo.version,
            },
        )
    return modelo


def modelo_activo():
    """El modelo activo o None (lo consulta el servicio en cada petición)."""
    return ModeloML.objects.filter(activo=True).select_related(
        "entrenamiento"
    ).first()
