"""Generación de plantillas .xlsx para la importación histórica (S20).

Cada plantilla tiene la fila 1 con los encabezados que espera el
importador (más una columna opcional `marca` al principio) y la fila 2
con una fila EJEMPLO completa, alineada columna a columna y marcada en
`marca` con el valor EJEMPLO: el importador la ignora siempre, así quien
copia la plantilla no puede importar el ejemplo sin borrar la marca.

Los valores son inventados y no personales. Fuera del repositorio: la
ruta la decide quien ejecuta el comando --plantilla --salida. El .xlsx
se escribe con openpyxl (ya instalado; no hay pandas).
"""
from openpyxl import Workbook

# Columnas de datos por tipo (orden fijo = orden de las columnas en el
# archivo, justo después de la columna `marca`)
COLUMNAS = {
    "productores": (
        "nombres",
        "apellidos",
        "dni",
        "telefono",
        "comunidad",
        "referencia_ubicacion",
        "fecha_incorporacion",
    ),
    "parcelas": (
        "dni_productor",
        "comunidad",
        "referencia_ubicacion",
        "superficie_ha",
        "altitud_msnm",
        "latitud",
        "longitud",
        "tipo_suelo",
        "pendiente",
        "disponibilidad_agua",
        "sistema_riego",
    ),
    "campanias": (
        "dni_productor",
        "referencia_parcela",
        "cultivo",
        "variedad",
        "periodo",
        "fecha_inicio",
        "fecha_fin_prevista",
        "fecha_siembra",
        "superficie_sembrada_ha",
        "fecha_cosecha",
        "superficie_cosechada_ha",
        "produccion_kg",
        "semilla_kg",
        "fertilizante_kg",
        "jornales",
        "agua_m3",
        "observaciones",
    ),
}

# Columna opcional de control: si su valor es EJEMPLO, la fila se salta
COLUMNA_MARCA = "marca"
VALOR_EJEMPLO = "EJEMPLO"

# Fila EJEMPLO: la primera celda es la marca (COLUMNA_MARCA) y el resto
# son los valores de ejemplo de COLUMNAS, alineados uno a uno.
EJEMPLOS = {
    "productores": (
        VALOR_EJEMPLO,
        "Ana",
        "Ejemplo Lopez",
        "88000001",
        "999999999",
        "Comunidad de prueba",
        "Cerca del caserío",
        "01/01/2020",
    ),
    "parcelas": (
        VALOR_EJEMPLO,
        "88000001",
        "Comunidad de prueba",
        "Cerca del caserío",
        "1.50",
        "3800",
        "-15.500000",
        "-70.100000",
        "FRANCO",
        "SUAVE",
        "MEDIA",
        "GRAVEDAD",
    ),
    "campanias": (
        VALOR_EJEMPLO,
        "88000001",
        "Cerca del caserío",
        "Quinua",
        "Blanca",
        "2024-2025",
        "01/11/2024",
        "30/04/2025",
        "10/11/2024",
        "1.50",
        "20/05/2025",
        "1.50",
        "1200",
        "45",
        "120",
        "30",
        "200",
        "Campaña de ejemplo",
    ),
}


def encabezados(tipo):
    """Encabezados de la plantilla del tipo (marca + columnas de datos)."""
    return (COLUMNA_MARCA,) + COLUMNAS[tipo]


def generar_plantilla(tipo, ruta):
    """Escribe la plantilla .xlsx del tipo en la ruta indicada.

    Devuelve la ruta escrita (str). El tipo debe ser productores,
    parcelas o campanias (el comando lo valida antes).
    """
    libro = Workbook()
    hoja = libro.active
    hoja.title = tipo
    # Encabezados primero (fila 1) y la fila EJEMPLO alineada debajo
    hoja.append(list(encabezados(tipo)))
    hoja.append(list(EJEMPLOS[tipo]))
    libro.save(ruta)
    return ruta
