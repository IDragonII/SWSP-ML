"""Generación de los libros Excel con openpyxl (Semana 17, HU-143).

Dos hojas, sin fórmulas: «Resumen» (título, filtros, generado por,
fecha de Lima, número de filas, notas y resumen) y «Datos» (una fila
por registro con los tipos reales: números como números y fechas como
fechas). Encabezado congelado y autofiltro en «Datos», anchos de
columna razonables y todo texto que empiece con =, +, - o @ escrito
como cadena inofensiva —nunca como fórmula—.

El libro se construye en memoria (BytesIO) y no se guarda en disco.
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from . import catalogo, formato
from .consultas import fila_totales

_TITULO = Font(bold=True, size=14)
_CABECERA = Font(bold=True)


def generar_excel(reporte, datos, generado_por, generado_en):
    """Libro .xlsx en memoria: hoja «Resumen» y hoja «Datos»."""
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = "Resumen"
    _escribir_resumen(hoja_resumen, reporte, datos, generado_por, generado_en)
    hoja_datos = libro.create_sheet("Datos")
    _escribir_datos(hoja_datos, datos)
    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _celda(hoja, fila, columna, valor, negrita=False):
    celda = hoja.cell(row=fila, column=columna, value=valor)
    if negrita:
        celda.font = _CABECERA
    if formato.es_texto_de_formula(valor):
        # El texto riesgoso se guarda como cadena, jamás como fórmula
        celda.data_type = "s"
    return celda


def _escribir_resumen(hoja, reporte, datos, generado_por, generado_en):
    filas = [
        (reporte["nombre"], _TITULO),
        (f"Filtros: {datos['filtros_texto']}", None),
        (f"Generado por: {generado_por}", None),
        (
            f"Generado el: {formato.hora_larga(generado_en)} (hora de Lima)",
            None,
        ),
        (f"Filas: {len(datos['filas'])}", None),
        (catalogo.AVISO_PRIVACIDAD, None),
    ]
    if reporte.get("aviso"):
        # Semana 18: el de auditoría lleva su aviso de confidencialidad
        # en la hoja Resumen, en el pie del PDF y en la interfaz
        filas.append((reporte["aviso"], None))
    fila = 1
    for texto_fila, fuente in filas:
        celda = hoja.cell(row=fila, column=1, value=texto_fila)
        if fuente is not None:
            celda.font = fuente
        fila += 1
    for advertencia in datos["advertencias"]:
        hoja.cell(row=fila, column=1, value=f"Nota: {advertencia}")
        fila += 1
    fila += 1  # separación

    resumen = datos["resumen"]
    if reporte["tipo"] == "productores":
        valores = (
            ("Productores distintos", resumen["productores"]),
            ("Filas", resumen["filas"]),
            (
                "Superficie de parcelas (ha)",
                resumen["superficie_parcelas_ha"],
            ),
            ("Superficie sembrada (ha)", resumen["superficie_sembrada_ha"]),
        )
        for etiqueta, valor in valores:
            _celda(hoja, fila, 1, etiqueta, negrita=True)
            _celda(hoja, fila, 2, valor)
            fila += 1
    elif reporte["tipo"] == "actividades":
        valores = (
            ("Actividades", resumen["total"]),
            ("Campañas distintas", resumen["campanias_distintas"]),
            ("Productores distintos", resumen["productores_distintos"]),
            ("Con horas registradas", resumen["actividades_con_horas"]),
            ("Horas totales", resumen["horas_totales"]),
            ("Rango de fechas", _rango(resumen)),
        )
        for etiqueta, valor in valores:
            _celda(hoja, fila, 1, etiqueta, negrita=True)
            _celda(hoja, fila, 2, valor)
            fila += 1
        fila = _escribir_conteos(hoja, fila, "Tipo de actividad", resumen["por_tipo"])
    elif reporte["tipo"] == "auditoria":
        valores = (
            ("Eventos", resumen["total"]),
            ("Sin usuario", resumen["sin_usuario"]),
            ("Rango de fechas", _rango(resumen)),
        )
        for etiqueta, valor in valores:
            _celda(hoja, fila, 1, etiqueta, negrita=True)
            _celda(hoja, fila, 2, valor)
            fila += 1
        fila = _escribir_conteos(hoja, fila, "Acción", resumen["por_accion"])
        fila += 1
        _escribir_conteos(hoja, fila, "Módulo", resumen["por_modulo"])
    else:
        columnas = catalogo.COLUMNAS_RESUMEN_PRODUCTIVO
        for indice, columna in enumerate(columnas, start=1):
            _celda(hoja, fila, indice, columna["etiqueta"], negrita=True)
        fila += 1
        for fila_datos in resumen["por_cultivo"]:
            valores = formato.celda_excel(columnas, fila_datos)
            for indice, columna in enumerate(columnas, start=1):
                _celda(hoja, fila, indice, valores[columna["clave"]])
            fila += 1
        totales = fila_totales(resumen)
        valores = formato.celda_excel(columnas, totales)
        for indice, columna in enumerate(columnas, start=1):
            _celda(hoja, fila, indice, valores[columna["clave"]], negrita=True)
    _ajustar_anchos(hoja)


def _rango(resumen):
    """«dd/mm/aaaa – dd/mm/aaaa» del resumen (sin fechas → vacío)."""
    desde = formato.fecha_larga(resumen.get("fecha_min"))
    hasta = formato.fecha_larga(resumen.get("fecha_max"))
    if not desde and not hasta:
        return ""
    return f"{desde} – {hasta}"


def _escribir_conteos(hoja, fila, encabezado, conteos):
    """Tabla de dos columnas «encabezado | Actividades/Eventos»."""
    _celda(hoja, fila, 1, encabezado, negrita=True)
    _celda(hoja, fila, 2, "Cantidad", negrita=True)
    fila += 1
    for conteo in conteos:
        _celda(hoja, fila, 1, conteo["etiqueta"])
        _celda(hoja, fila, 2, conteo["cantidad"])
        fila += 1
    return fila


def _escribir_datos(hoja, datos):
    columnas = datos["columnas"]
    for indice, columna in enumerate(columnas, start=1):
        _celda(hoja, 1, indice, columna["etiqueta"], negrita=True)
    for numero_fila, datos_fila in enumerate(datos["filas"], start=2):
        valores = formato.celda_excel(columnas, datos_fila)
        for indice, columna in enumerate(columnas, start=1):
            _celda(hoja, numero_fila, indice, valores[columna["clave"]])
    hoja.freeze_panes = "A2"
    if datos["filas"]:
        ultima = get_column_letter(len(columnas))
        hoja.auto_filter.ref = f"A1:{ultima}{len(datos['filas']) + 1}"
    _ajustar_anchos(hoja)


def _ajustar_anchos(hoja):
    """Anchos razonables (10..45) según el contenido de cada columna."""
    for indice in range(1, hoja.max_column + 1):
        ancho = 10
        for fila in range(1, min(hoja.max_row, 200) + 1):
            valor = hoja.cell(row=fila, column=indice).value
            if valor is None:
                continue
            ancho = max(ancho, min(45, len(str(valor)) + 2))
        hoja.column_dimensions[get_column_letter(indice)].width = ancho
