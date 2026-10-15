"""Consulta al servicio meteorológico Open-Meteo (HU-84).

Adaptador sin dependencias nuevas (urllib): baja las lecturas diarias de un
punto para un rango pedido y devuelve una lista de días con None donde el
servicio no tenga dato. Las unidades se piden en las del modelo (°C, mm, %,
m/s y MJ/m²) para guardarlas sin conversiones. Las reglas del dominio (rangos,
unicidad, fuente) no viven aquí: las aplica la vista. Un fallo de red, de
HTTP o de JSON sube como ErrorServicioMeteorologico y la API lo responde
como 502 (nunca 500). Las pruebas lo ejercitan simulado (sin internet); la
consulta real solo se verifica con puntos públicos, nunca con datos reales
del proyecto.
"""
import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL_CONSULTA = "https://archive-api.open-meteo.com/v1/archive"
CAMPOS_DIARIOS = {
    "temperature_2m_min": "temp_min",
    "temperature_2m_max": "temp_max",
    "precipitation_sum": "precipitacion_mm",
    "relative_humidity_2m_mean": "humedad_pct",
    "wind_speed_10m_max": "viento_ms",
    "shortwave_radiation_sum": "radiacion_mj",
}
# Orden en que la vista espera las medidas de cada día (sin temp_prom: si el
# servicio la trae, el adaptador solo la entrega si cabe entre mínima y máxima;
# en otro caso el servidor calculará el punto medio como en el alta manual)
CLAVES_SALIDA = (
    "temp_min",
    "temp_max",
    "temp_prom",
    "precipitacion_mm",
    "humedad_pct",
    "viento_ms",
    "radiacion_mj",
)
TIEMPO_LIMITE_S = 15


class ErrorServicioMeteorologico(Exception):
    """El servicio meteorológico no respondió o respondió mal."""


def _medida(valor):
    """El modelo solo admite 1 decimal: lo que venga del servicio se
    cuantiza igual que el resto del proyecto (ROUND_HALF_UP), sin lo cual
    7.80 mm o 17.19 MJ/m² harían que el día entero se descartara."""
    if valor is None:
        return None
    return Decimal(str(valor)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def consultar_dias(latitud, longitud, fecha_desde, fecha_hasta):
    """Devuelve [{fecha, temp_min, temp_max, temp_prom, precipitacion_mm,
    humedad_pct, viento_ms, radiacion_mj}, ...] con None donde no haya dato.
    Las coordenadas llegan ya redondeadas (decisión de la Semana 10)."""
    parametros = urlencode(
        {
            "latitude": latitud,
            "longitude": longitud,
            "start_date": fecha_desde.isoformat(),
            "end_date": fecha_hasta.isoformat(),
            "daily": ",".join(CAMPOS_DIARIOS),
            "wind_speed_unit": "ms",
            "timezone": "America/Lima",
        }
    )
    solicitud = Request(
        f"{URL_CONSULTA}?{parametros}",
        headers={"User-Agent": "sigpa-ga/1.0"},
    )
    try:
        with urlopen(solicitud, timeout=TIEMPO_LIMITE_S) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
    except (URLError, TimeoutError, OSError) as exc:
        raise ErrorServicioMeteorologico("sin respuesta del servicio") from exc
    try:
        diario = json.loads(cuerpo)["daily"]
        fechas = diario["time"]
        columnas = {clave: diario[campo] for campo, clave in CAMPOS_DIARIOS.items()}
        promedios = diario.get("temperature_2m_mean")
    except (ValueError, KeyError, TypeError) as exc:
        raise ErrorServicioMeteorologico("respuesta ilegible del servicio") from exc
    dias = []
    for posicion, texto_fecha in enumerate(fechas):
        minima = _medida(columnas["temp_min"][posicion])
        maxima = _medida(columnas["temp_max"][posicion])
        promedio = _medida(promedios[posicion]) if promedios else None
        # El promedio del servicio solo se confía si cabe entre mínima y
        # máxima; si ERA5 lo trae fuera de ruido fuera de rango, el servidor
        # calcula el punto medio en vez de descartar el día completo
        if (
            promedio is not None
            and minima is not None
            and maxima is not None
            and not minima <= promedio <= maxima
        ):
            promedio = None
        dias.append(
            {
                "fecha": date.fromisoformat(texto_fecha),
                "temp_min": minima,
                "temp_max": maxima,
                "temp_prom": promedio,
                "precipitacion_mm": _medida(columnas["precipitacion_mm"][posicion]),
                "humedad_pct": _medida(columnas["humedad_pct"][posicion]),
                "viento_ms": _medida(columnas["viento_ms"][posicion]),
                "radiacion_mj": _medida(columnas["radiacion_mj"][posicion]),
            }
        )
    return dias
