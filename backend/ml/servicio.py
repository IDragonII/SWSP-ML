"""Servicio de predicción (Sprint 14, HU-173/HU-176, decisiones 225-238).

`fila_de_campania` arma las variables de una campaña con la MISMA
definición que la fila de la vista `vw_dataset_entrenamiento` (categorías
de recursos, por hectárea, unidades base; decisión 225) y `predecir` la
convierte en una predicción con el modelo activo. El modelo se carga en
cada petición verificando la huella contra el manifiesto y se recarga si
cambió (226); solo se predice en campañas PLANIFICADA o EN_PRODUCCION
(227; sin modelo activo el error es ErrorSinModelo → 409 en la API) y
`dias_ciclo` se guarda desde la fecha de siembra, o vacío si no hay
(238).

Resultado (230): rendimiento en kg/ha —un negativo se ajusta a 0 con
marca— y producción estimada = rendimiento × superficie sembrada; SIN
intervalo (las columnas quedan NULL: el intervalo de estos modelos no es
válido). Los valores planificados de semilla, fertilizante, mano de obra
y agua tienen prioridad sobre los registrados, se validan (≥ 0) y se
guardan con su origen dentro de `variables_entrada` (228), que también
guarda avisos y confiabilidad: faltantes imputadas con la mediana del
entrenamiento, categoría nunca vista que se ignora y valor fuera del
rango aprendido si se alcanzó; con 2 de las 4 variables de manejo
ausentes la confiabilidad es BAJA (229). Si el modelo activo viene de
datos de demostración la respuesta lo marca, con el texto fijo de
estimación y el MAE del modelo (231).

Cada predicción se guarda en una sola transacción con auditoría CREAR
sin variables de entrada (234). Al deshacer la cosecha,
`limpiar_comparacion` vacía el comparativo en la MISMA transacción
(236); si la producción se borra por SQL directo el trigger no corre y
el comparativo queda — limitación declarada (237).
"""
import math
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from auditoria.registrar import registrar_evento
from ml import guardado, registro
from ml.carga import COLUMNAS_NUMERICAS
from ml.models import Prediccion
from ml.registro import MODULO_AUDITORIA

TEXTO_ESTIMACION = (
    "Es una estimación basada en datos históricos, no una medición."
)
ELEGIBLES = ("PLANIFICADA", "EN_PRODUCCION")
CONFIA_BAJA_MINIMO = 2

# Campos que el cliente puede planificar (decisión 228) y la columna
# del dataset a la que corresponden.
CLAVES_PLANIFICADAS = {
    "semilla": "semilla_kg_ha",
    "fertilizante": "fertilizante_kg_ha",
    "mano_de_obra": "jornales_ha",
    "agua": "agua_m3_ha",
}
VARIABLES_MANEJO = tuple(CLAVES_PLANIFICADAS.values())
COLUMNAS_CAMPANIA = ("cultivo", "variedad", "superficie_sembrada_ha")
COLUMNAS_PARCELA = (
    "altitud_msnm", "tipo_suelo", "pendiente", "sistema_riego",
)

# Caché del tubo en memoria (226): se invalida sola porque la clave
# lleva la huella del archivo; limpiar_cache() la vacía para las pruebas.
_CACHE = {"clave": None, "tubo": None}


class ErrorServicio(Exception):
    """El servicio rechazó la operación; `estado` es el HTTP de la API."""

    estado = 400


class ErrorCampania(ErrorServicio):
    estado = 404


class ErrorEstado(ErrorServicio):
    estado = 400


class ErrorSinModelo(ErrorServicio):
    estado = 409


class ErrorModelo(ErrorServicio):
    estado = 409


class ErrorVariables(ErrorServicio):
    estado = 400


# ---------------------------------------------------------------------- #
# Carga del modelo activo (226)
# ---------------------------------------------------------------------- #
def limpiar_cache():
    """Vacía el tubo en memoria (lo usan las pruebas)."""
    _CACHE["clave"] = None
    _CACHE["tubo"] = None


def cargar_modelo(destino=None):
    """(modelo activo, tubo) con la huella verificada contra el manifiesto.

    Si el archivo del modelo activo cambió (otra huella) se recarga; si
    la huella no coincide con el manifiesto o el archivo falta, lanza
    ErrorModelo — nunca se carga un archivo alterado (decisión 226).
    """
    modelo = registro.modelo_activo()
    if modelo is None or not modelo.archivo:
        raise ErrorSinModelo(
            "No hay ningún modelo activo: activa un modelo antes de "
            "predecir."
        )
    ruta = guardado.carpeta(destino) / modelo.archivo
    try:
        huella = guardado.huella_de(ruta)
    except OSError as error:
        raise ErrorModelo(
            f"No se pudo leer el archivo del modelo activo: {error}"
        ) from error
    clave = (str(ruta), huella)
    if _CACHE["clave"] == clave and _CACHE["tubo"] is not None:
        return modelo, _CACHE["tubo"]
    try:
        tubo = guardado.cargar_verificado(ruta, destino)
    except guardado.ErrorManifiesto as error:
        raise ErrorModelo(str(error)) from error
    _CACHE["clave"] = clave
    _CACHE["tubo"] = tubo
    return modelo, tubo


# ---------------------------------------------------------------------- #
# Variables de la campaña (225)
# ---------------------------------------------------------------------- #
def _dos(decimales):
    return Decimal(f"{float(decimales):.2f}")


def _por_ha(total, superficie):
    """Total del ciclo / superficie, con el mismo redondeo que la vista."""
    if total is None or not superficie:
        return None
    return (Decimal(total) / Decimal(superficie)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _totales_por_categoria(campania):
    """Suma de cantidad_base por categoría (usos no anulados)."""
    totales = {}
    consulta = (
        campania.usos_recursos.filter(anulada=False)
        .values("recurso__categoria")
        .annotate(suma=Sum("cantidad_base"))
    )
    for fila in consulta:
        totales[fila["recurso__categoria"]] = fila["suma"]
    return totales


def _suma(totales, *categorias):
    encontrados = [totales[c] for c in categorias if c in totales]
    if not encontrados:
        return None
    return sum(encontrados, Decimal("0"))


def _validar_planificados(planificados):
    """{clave_api: valor ≥ 0} de lo que el usuario planificó (228)."""
    if not planificados:
        return {}
    if not isinstance(planificados, dict):
        raise ErrorVariables("Los valores planificados deben ser un objeto.")
    salida = {}
    for clave, valor in planificados.items():
        if clave not in CLAVES_PLANIFICADAS:
            raise ErrorVariables(
                f"Clave planificada desconocida: {clave}."
            )
        if valor is None:
            continue
        try:
            numero = Decimal(str(valor))
        except Exception as error:
            raise ErrorVariables(
                f"El valor planificado de {clave} no es un número."
            ) from error
        if not numero.is_finite():
            raise ErrorVariables(
                f"El valor planificado de {clave} no es un número finito."
            )
        if numero < 0:
            raise ErrorVariables(
                f"El valor planificado de {clave} no puede ser negativo."
            )
        salida[clave] = float(numero)
    return salida


def fila_de_campania(campania, *, planificados=None):
    """(fila, origenes) con la definición de la vista (decisión 225).

    La fila tiene los predictores del conjunto «plan»: lo que se sabe o
    se decide antes de cosechar. Los valores planificados tienen
    prioridad sobre los registrados y cambian el origen del dato.
    """
    superficie = campania.superficie_sembrada_ha
    totales = _totales_por_categoria(campania)
    parcela = campania.parcela
    fila = {
        "cultivo": campania.cultivo.nombre,
        "variedad": campania.variedad.nombre,
        "superficie_sembrada_ha": superficie,
        "altitud_msnm": parcela.altitud_msnm,
        "tipo_suelo": parcela.tipo_suelo,
        "pendiente": parcela.pendiente,
        "sistema_riego": parcela.sistema_riego,
        "semilla_kg_ha": _por_ha(_suma(totales, "SEMILLA"), superficie),
        "fertilizante_kg_ha": _por_ha(
            _suma(totales, "FERTILIZANTE", "ABONO"), superficie
        ),
        "jornales_ha": _por_ha(_suma(totales, "MANO_OBRA"), superficie),
        "agua_m3_ha": _por_ha(_suma(totales, "AGUA"), superficie),
    }
    origenes = {columna: "campaña" for columna in COLUMNAS_CAMPANIA}
    origenes.update({columna: "parcela" for columna in COLUMNAS_PARCELA})
    for columna in VARIABLES_MANEJO:
        origenes[columna] = "registrado" if fila[columna] is not None else "ausente"
    for clave, valor in _validar_planificados(planificados).items():
        fila[CLAVES_PLANIFICADAS[clave]] = valor
        origenes[CLAVES_PLANIFICADAS[clave]] = "planificado"
    return fila, origenes


# ---------------------------------------------------------------------- #
# Adaptación de la fila al tubo: imputación, avisos y rangos (229)
# ---------------------------------------------------------------------- #
def _estadisticas(tubo):
    """(medianas, categorías vistas) aprendidas dentro del pipeline."""
    medianas, vistas = {}, {}
    preparar = tubo.named_steps.get("preparar")
    if preparar is None:
        return medianas, vistas
    for nombre, transformador, columnas in getattr(preparar, "transformers_", []):
        if nombre == "numerico":
            imputar = getattr(transformador, "named_steps", {}).get("imputar")
            if imputar is not None and hasattr(imputar, "statistics_"):
                for columna, valor in zip(columnas, imputar.statistics_):
                    numero = float(valor)
                    if not math.isnan(numero):
                        medianas[columna] = numero
        elif nombre == "categorico":
            if hasattr(transformador, "categories_"):
                for columna, valores in zip(columnas, transformador.categories_):
                    vistas[columna] = [str(v) for v in valores]
    return medianas, vistas


def _columnas_del_tubo(tubo):
    try:
        return list(tubo.named_steps["preparar"].feature_names_in_)
    except (AttributeError, KeyError, TypeError) as error:
        raise ErrorModelo(
            "El archivo del modelo activo no es un pipeline del sistema."
        ) from error


def _preparar_entrada(fila, origenes, tubo):
    """(DataFrame de una fila, avisos, origenes) según lo aprendido.

    Numérico faltante → mediana del entrenamiento (aviso + origen
    «imputada»); categoría que no se vio → se ignora y se avisa; valor
    numérico fuera del rango visto en el entrenamiento (si el tubo lo
    trae) → se avisa sin bloquear (decisión 229).
    """
    columnas = _columnas_del_tubo(tubo)
    medianas, vistas = _estadisticas(tubo)
    rangos = getattr(tubo, "rangos_entrenamiento_", None) or {}
    avisos = []
    entrada = {}
    for columna in columnas:
        valor = fila.get(columna)
        if columna in COLUMNAS_NUMERICAS:
            if valor is None:
                entrada[columna] = medianas.get(columna, float("nan"))
                origenes[columna] = "imputada"
                avisos.append(
                    f"{columna}: sin valor, se imputó con la mediana del "
                    "entrenamiento."
                )
                continue
            numero = float(valor)
            entrada[columna] = numero
            rango = rangos.get(columna)
            if rango and (numero < rango["min"] or numero > rango["max"]):
                avisos.append(
                    f"{columna}: {numero:g} está fuera del rango de "
                    f"entrenamiento [{rango['min']:g}, {rango['max']:g}]."
                )
        else:
            texto = "" if valor is None else str(valor)
            entrada[columna] = texto
            if columna in vistas and texto not in vistas[columna]:
                avisos.append(
                    f"La categoría «{texto}» de {columna} no se vio en el "
                    "entrenamiento: se ignora."
                )
    return pd.DataFrame([entrada], columns=columnas), avisos, origenes


def _dias_desde_siembra(campania):
    """días_ciclo guardado en la propia predicción (decisión 238)."""
    if not campania.fecha_siembra:
        return None
    dias = (timezone.localdate() - campania.fecha_siembra).days
    return dias if dias >= 0 else None


# ---------------------------------------------------------------------- #
# Predecir (227, 230, 231, 234)
# ---------------------------------------------------------------------- #
def predecir(campania, usuario, *, planificados=None, destino=None):
    """Predice el rendimiento de la campaña y guarda la predicción.

    Devuelve un diccionario con la predicción guardada, el modelo
    usado, el resultado, los avisos, la confiabilidad y la marca de
    demostración. Lanza ErrorEstado si la campaña no está en un estado
    elegible, ErrorSinModelo si no hay modelo activo, ErrorModelo si el
    archivo del activo no pasa la huella y ErrorVariables si los
    valores planificados no son válidos.
    """
    if campania.estado not in ELEGIBLES:
        raise ErrorEstado(
            f"La campaña está {campania.estado}: solo se puede predecir "
            "con una campaña PLANIFICADA o EN_PRODUCCION."
        )
    modelo, tubo = cargar_modelo(destino)
    fila, origenes = fila_de_campania(campania, planificados=planificados)
    ausentes = sum(1 for columna in VARIABLES_MANEJO if fila[columna] is None)
    confiabilidad = (
        "BAJA" if ausentes >= CONFIA_BAJA_MINIMO else "ALTA"
    )
    entrada, avisos, origenes = _preparar_entrada(fila, origenes, tubo)
    bruto = float(tubo.predict(entrada)[0])
    if not math.isfinite(bruto):
        raise ErrorModelo("El modelo devolvió un valor no finito.")
    negativo = bruto < 0
    rendimiento = _dos(max(bruto, 0.0))
    if negativo:
        avisos.append("El rendimiento predicho era negativo: se ajustó a 0.")
    superficie = campania.superficie_sembrada_ha
    produccion = (
        (rendimiento * Decimal(superficie)).quantize(Decimal("0.01"))
        if superficie is not None
        else None
    )
    origen_datos = str(
        modelo.entrenamiento.variables_usadas.get("origen_datos") or ""
    )
    demostracion = "demostr" in origen_datos.lower()
    variables_entrada = {
        "valores": entrada.iloc[0].to_dict(),
        "origenes": origenes,
        # Validados y en float: el JSON del modelo no admite Decimal
        "planificados": {
            clave: float(valor)
            for clave, valor in _validar_planificados(planificados).items()
        },
        "avisos": avisos,
        "confiabilidad": confiabilidad,
        "negativo_ajustado": negativo,
    }
    with transaction.atomic():
        prediccion = Prediccion.objects.create(
            campania=campania,
            modelo=modelo,
            dias_ciclo=_dias_desde_siembra(campania),
            variables_entrada=variables_entrada,
            rendimiento_predicho=rendimiento,
            produccion_estimada_kg=produccion,
            creado_por=usuario,
        )
        registrar_evento(
            usuario=usuario,
            accion="CREAR",
            modulo=MODULO_AUDITORIA,
            detalle={
                "tabla": "predicciones",
                "campania": campania.pk,
                "modelo": f"{modelo.algoritmo} v{modelo.version}",
                "rendimiento_predicho": float(rendimiento),
            },
        )
    return {
        "prediccion": prediccion,
        "modelo": {
            "id": modelo.pk,
            "algoritmo": modelo.algoritmo,
            "version": modelo.version,
            "mae": str(modelo.mae),
            "rmse": str(modelo.rmse),
            "activo": True,
        },
        "rendimiento_predicho": prediccion.rendimiento_predicho,
        "produccion_estimada_kg": prediccion.produccion_estimada_kg,
        "dias_ciclo": prediccion.dias_ciclo,
        "intervalo_inferior": None,
        "intervalo_superior": None,
        "confiabilidad": confiabilidad,
        "avisos": avisos,
        "negativo_ajustado": negativo,
        "datos_demostracion": demostracion,
        "texto_estimacion": TEXTO_ESTIMACION,
        "variables_entrada": prediccion.variables_entrada,
    }


# ---------------------------------------------------------------------- #
# Comparación predicho vs real al cosechar (236, 237)
# ---------------------------------------------------------------------- #
def limpiar_comparacion(campania):
    """Vacía el comparativo de las predicciones de la campaña (236).

    Lo llama `deshacer-cosecha` dentro de su transacción: el trigger no
    corre al borrar la producción, así que el servicio limpia a mano.
    """
    return campania.predicciones.filter(
        rendimiento_real__isnull=False
    ).update(rendimiento_real=None, error_abs=None, error_pct=None)
