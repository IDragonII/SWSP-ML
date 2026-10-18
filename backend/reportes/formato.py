"""Presentación de los valores crudos en cada capa (Semana 17).

Una fila se construye con valores crudos (Decimal, date, bool, código
de estado) y cada capa la presenta:

- vista previa: el texto que devuelve la API (decimales con 2 cifras,
  fechas dd/mm/aaaa, estados con su etiqueta, Sí/No);
- Excel: números reales y fechas reales (la hoja se formatea según la
  configuración regional del usuario);
- PDF: formato habitual en Perú —punto decimal y coma de miles— con 2
  decimales para hectáreas y kg/ha y sin decimales para kilos.

Además, todo texto que empiece con =, +, - o @ se trata como texto
inelástico: el escritor de Excel lo guarda como cadena, nunca como
fórmula (protección contra inyección de fórmulas).
"""
from campanias.models import Campania
from dashboard.consultas import cuantizar, texto
from productores.models import Productor

ESTADOS_PRODUCTOR = dict(Productor.ESTADOS)
ESTADOS_CAMPANIA = dict(Campania.ESTADOS)

_INICIOS_FORMULA = ("=", "+", "-", "@")


def es_texto_de_formula(valor):
    """True si un texto podría interpretarse como fórmula en una celda."""
    return isinstance(valor, str) and valor[:1] in _INICIOS_FORMULA


def fecha_larga(valor):
    """date/datetime a dd/mm/aaaa (None → cadena vacía)."""
    if valor is None:
        return ""
    return valor.strftime("%d/%m/%Y")


def hora_larga(valor):
    """date/datetime a dd/mm/aaaa HH:MM (None → cadena vacía)."""
    if valor is None:
        return ""
    return valor.strftime("%d/%m/%Y %H:%M")


def seguro(texto_pdf):
    """Carácter seguro para la fuente estándar del PDF: todo lo que no
    cubre (tildes, ñ, ¿ ¡ sí lo cubren) se reemplaza por «?»."""
    return str(texto_pdf).encode("cp1252", "replace").decode("cp1252")


def numero_pdf(valor, decimales=2):
    """Número al formato peruano (coma de miles, punto decimal)."""
    if valor is None:
        return ""
    return format(cuantizar(valor, decimales), f",.{decimales}f")


def _dec(columna):
    return columna.get("dec", 2)


def _preview(columna, valor):
    tipo = columna["tipo"]
    if valor is None:
        return ""
    if tipo in ("texto", "estado_productor", "estado_campania"):
        if tipo == "estado_productor":
            return seguro(ESTADOS_PRODUCTOR.get(valor, valor))
        if tipo == "estado_campania":
            return seguro(ESTADOS_CAMPANIA.get(valor, valor))
        return seguro(valor)
    if tipo == "numero":
        return texto(valor)
    if tipo == "entero":
        return str(int(valor))
    if tipo == "fecha":
        return fecha_larga(valor)
    if tipo == "booleano":
        return "Sí" if valor else "No"
    return str(valor)


def _excel(columna, valor):
    tipo = columna["tipo"]
    if valor is None:
        return None
    if tipo == "numero":
        return cuantizar(valor, _dec(columna))
    if tipo == "entero":
        return int(valor)
    if tipo == "fecha":
        return valor
    if tipo == "booleano":
        return "Sí" if valor else "No"
    if tipo == "estado_productor":
        return ESTADOS_PRODUCTOR.get(valor, valor)
    if tipo == "estado_campania":
        return ESTADOS_CAMPANIA.get(valor, valor)
    return str(valor)


def _pdf(columna, valor):
    tipo = columna["tipo"]
    if valor is None:
        return ""
    if tipo == "numero":
        return numero_pdf(valor, _dec(columna))
    if tipo == "entero":
        return format(int(valor), ",")
    if tipo == "fecha":
        return fecha_larga(valor)
    if tipo == "booleano":
        return "Sí" if valor else "No"
    if tipo == "estado_productor":
        return seguro(ESTADOS_PRODUCTOR.get(valor, valor))
    if tipo == "estado_campania":
        return seguro(ESTADOS_CAMPANIA.get(valor, valor))
    # Cualquier carácter fuera de la fuente del PDF se sustituye por uno seguro
    return seguro(valor)


def vista_preview(columnas, fila):
    """Fila tal cual responde la vista previa (texto de la API)."""
    return {c["clave"]: _preview(c, fila.get(c["clave"])) for c in columnas}


def celda_excel(columnas, fila):
    """Fila para la hoja «Datos»: números y fechas reales, texto seguro."""
    return {c["clave"]: _excel(c, fila.get(c["clave"])) for c in columnas}


def celda_pdf(columnas, fila):
    """Fila para la tabla del PDF: texto seguro y números con coma/punto."""
    return {c["clave"]: _pdf(c, fila.get(c["clave"])) for c in columnas}


def resumen_preview(tipo, resumen):
    """Resumen en el formato de la API (decimales como texto)."""
    if tipo == "productores":
        return {
            "productores": resumen["productores"],
            "filas": resumen["filas"],
            "superficie_parcelas_ha": texto(resumen["superficie_parcelas_ha"]),
            "superficie_sembrada_ha": texto(resumen["superficie_sembrada_ha"]),
        }
    return {
        "por_cultivo": [
            {
                **fila,
                "superficie_ha": texto(fila["superficie_ha"]),
                "produccion_kg": texto(fila["produccion_kg"]),
                "toneladas": texto(fila.get("toneladas")),
                "rendimiento_kg_ha": texto(fila["rendimiento_kg_ha"]),
                "rendimiento_promedio_kg_ha": texto(
                    fila["rendimiento_promedio_kg_ha"]
                ),
            }
            for fila in resumen["por_cultivo"]
        ],
        "totales": {
            "campanias": resumen["totales"]["campanias"],
            "superficie_ha": texto(resumen["totales"]["superficie_ha"]),
            "produccion_kg": texto(resumen["totales"]["produccion_kg"]),
            "rendimiento_kg_ha": texto(resumen["totales"]["rendimiento_kg_ha"]),
        },
        "campanias_provisionales": resumen["campanias_provisionales"],
        "excluidas_revision": resumen["excluidas_revision"],
    }
