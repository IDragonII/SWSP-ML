"""Generación de los PDF con ReportLab (Semana 17, HU-144).

ReportLab es Python puro y no necesita componentes del sistema. Hoja A4
horizontal con: encabezado con el nombre del proyecto, el título del
reporte y «Generado por / Generado el» en hora de Lima en cada página;
pie con «Página X de Y»; filtros y aviso de privacidad al principio;
resumen y tabla de detalle con encabezado repetido en cada página y
texto que se ajusta (Paragraph) en lugar de cortarse.

Se genera sin compresión para poder verificar su contenido en las
pruebas y, como todo reporte, en memoria: nunca se guarda en disco.
"""
from functools import partial
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import catalogo, formato
from .consultas import fila_totales

PROYECTO = "SIGPA-GA"

ANCHURA, ALTURA = landscape(A4)
_MARGEN = 15 * mm
_USABLE = ANCHURA - 2 * _MARGEN

_ESTILO_TEXTO = ParagraphStyle(
    "reporte_texto", fontName="Helvetica", fontSize=9, leading=12
)
_ESTILO_NOTA = ParagraphStyle(
    "reporte_nota",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#444444"),
    spaceAfter=3,
)
_ESTILO_CELDA = ParagraphStyle(
    "reporte_celda", fontName="Helvetica", fontSize=7.5, leading=9
)
_ESTILO_CENTRO = ParagraphStyle(
    "reporte_centro", parent=_ESTILO_CELDA, alignment=TA_CENTER
)
_ESTILO_DERECHA = ParagraphStyle(
    "reporte_derecha", parent=_ESTILO_CELDA, alignment=TA_RIGHT
)
_ESTILO_CABECERA = ParagraphStyle(
    "reporte_cabecera",
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=9,
    textColor=colors.white,
)
_ESTILO_TOTAL = ParagraphStyle(
    "reporte_total", parent=_ESTILO_CELDA, fontName="Helvetica-Bold"
)

_ESTILO_TABLA = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#31516b")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#f3f5f7")],
        ),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
)


class _CanvasReporte(canvas.Canvas):
    """Lienzo con encabezado y pie «Página X de Y» (sin compresión)."""

    def __init__(self, *args, **kwargs):
        self._titulo = kwargs.pop("titulo", "")
        self._generado = kwargs.pop("generado", "")
        kwargs["pageCompression"] = 0
        super().__init__(*args, **kwargs)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._decorar(total)
            super().showPage()
        super().save()

    def _decorar(self, total):
        self.saveState()
        self.setLineWidth(0.5)
        self.line(_MARGEN, ALTURA - 19 * mm, ANCHURA - _MARGEN, ALTURA - 19 * mm)
        self.setFont("Helvetica-Bold", 11)
        self.drawString(_MARGEN, ALTURA - 13 * mm, formato.seguro(self._titulo))
        self.setFont("Helvetica", 8)
        self.drawString(_MARGEN, ALTURA - 17.5 * mm, formato.seguro(self._generado))
        self.setFont("Helvetica", 8)
        self.drawRightString(
            ANCHURA - _MARGEN, 9 * mm, f"Página {self._pageNumber} de {total}"
        )
        self.restoreState()


def generar_pdf(reporte, datos, generado_por, generado_en):
    """PDF en memoria con encabezado, resumen y tabla de detalle."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=_MARGEN,
        rightMargin=_MARGEN,
        topMargin=24 * mm,
        bottomMargin=15 * mm,
        title=reporte["nombre"],
        author=PROYECTO,
    )
    titulo = f"{PROYECTO} — {reporte['nombre']}"
    generado = (
        f"Generado por: {generado_por} · "
        f"Generado el: {formato.hora_larga(generado_en)} (hora de Lima)"
    )
    documento.build(
        _relato(reporte, datos),
        canvasmaker=partial(_CanvasReporte, titulo=titulo, generado=generado),
    )
    return buffer.getvalue()


def _relato(reporte, datos):
    relato = [
        Paragraph(
            f"Filtros: {formato.seguro(datos['filtros_texto'])}",
            _ESTILO_TEXTO,
        ),
        Paragraph(formato.seguro(catalogo.AVISO_PRIVACIDAD), _ESTILO_NOTA),
    ]
    for advertencia in datos["advertencias"]:
        relato.append(
            Paragraph(f"• {formato.seguro(advertencia)}", _ESTILO_NOTA)
        )
    relato.append(Spacer(1, 6))
    relato.append(_tabla_resumen(reporte, datos))
    relato.append(Spacer(1, 10))
    relato.append(_tabla_detalle(reporte, datos))
    return relato


def _parrafo(columna, valor, estilo=None):
    if estilo is None:
        tipo = columna["tipo"]
        if tipo in ("numero", "entero"):
            estilo = _ESTILO_DERECHA
        elif tipo in ("fecha", "booleano"):
            estilo = _ESTILO_CENTRO
        else:
            estilo = _ESTILO_CELDA
    return Paragraph(valor or "", estilo)


def _tabla_resumen(reporte, datos):
    resumen = datos["resumen"]
    if reporte["tipo"] == "productores":
        filas = [
            [Paragraph("Indicador", _ESTILO_CABECERA),
             Paragraph("Valor", _ESTILO_CABECERA)],
            ["Productores distintos", str(resumen["productores"])],
            ["Filas", str(resumen["filas"])],
            [
                "Superficie de parcelas (ha)",
                formato.numero_pdf(resumen["superficie_parcelas_ha"]),
            ],
            [
                "Superficie sembrada (ha)",
                formato.numero_pdf(resumen["superficie_sembrada_ha"]),
            ],
        ]
        filas = [
            fila if isinstance(fila[0], Paragraph) else
            [Paragraph(str(valor), _ESTILO_CELDA) for valor in fila]
            for fila in filas
        ]
        tabla = Table(
            filas, colWidths=[_USABLE * 0.7, _USABLE * 0.3], repeatRows=1
        )
    else:
        columnas = catalogo.COLUMNAS_RESUMEN_PRODUCTIVO
        cabecera = [
            Paragraph(formato.seguro(c["etiqueta"]), _ESTILO_CABECERA)
            for c in columnas
        ]
        filas = [cabecera]
        for fila_datos in [*resumen["por_cultivo"], fila_totales(resumen)]:
            valores = formato.celda_pdf(columnas, fila_datos)
            es_total = valores["etiqueta"] == "Totales"
            filas.append(
                [
                    _parrafo(
                        columna,
                        valores[columna["clave"]],
                        _ESTILO_TOTAL if es_total else None,
                    )
                    for columna in columnas
                ]
            )
        anchos = _anchos(columnas, _USABLE)
        tabla = Table(filas, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(_ESTILO_TABLA)
    return tabla


def _tabla_detalle(reporte, datos):
    columnas = reporte["columnas"]
    cabecera = [
        Paragraph(formato.seguro(columna["etiqueta"]), _ESTILO_CABECERA)
        for columna in columnas
    ]
    filas = [cabecera]
    for fila_datos in datos["filas"]:
        valores = formato.celda_pdf(columnas, fila_datos)
        filas.append(
            [
                _parrafo(columna, valores[columna["clave"]])
                for columna in columnas
            ]
        )
    tabla = Table(
        filas, colWidths=_anchos(columnas, _USABLE), repeatRows=1, hAlign="LEFT"
    )
    tabla.setStyle(_ESTILO_TABLA)
    return tabla


def _anchos(columnas, disponibles):
    """Reparto del ancho útil: lo numérico y fechas más estrecho, los
    nombres de productor/campaña más anchos."""
    pesos = []
    for columna in columnas:
        if columna["tipo"] in ("numero", "entero", "fecha", "booleano"):
            pesos.append(1.0)
        elif columna["clave"] in ("productor", "codigo_productor", "campania"):
            pesos.append(1.7)
        else:
            pesos.append(1.3)
    total = sum(pesos)
    return [disponibles * peso / total for peso in pesos]
