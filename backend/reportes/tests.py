"""Pruebas de los reportes descargables (Semanas 17 y 18).

Numeración 280-317 (38 pruebas → 317 en total; el repositorio llegaba a
279 con la Semana 16). La Semana 17 ocupa 280-299 en ReportesTests y la
Semana 18, 302-317 en ReportesSemana18Tests (300-301 viven en
auditoria/tests.py). Parten de los mismos datos que el panel
(DashboardBase) para poder comparar cifras con él.

Pruebas 280-299 (Semana 17): el catálogo con su doble permiso y el 404
de tipo desconocido; los 401/403 de las tres lecturas y el portón de
cambio de contraseña; el alcance del Técnico; los filtros comunes con
sus 400 y su eco; la granularidad y el orden del reporte de productores;
sus superficies (parcelas contadas una sola vez); el detalle productivo
con sus estados y marcas; la coincidencia de cifras con el panel; las
dos hojas del Excel; la protección contra fórmulas inyectadas; el PDF
con cabecera, pie, resumen y texto seguro; los límites de filas por
formato (400, sin truncar); la privacidad por diseño; la auditoría
EXPORTAR y el 503 sin archivo; las 20 exportaciones por hora; las
cabeceras y el nombre de archivo; la generación en memoria sin tocar
disco; la fecha de Lima cerca de la medianoche; la migración del CHECK
(reversible) con 29 tablas y 25 triggers; y el recorrido de rutas (405)
donde solo exportar registra eventos.

Pruebas 302-317 (Semana 18): los reportes nuevos de actividades (RF-68)
y auditoría (HU-155/HU-156) — catálogo sensible con su aviso y segunda
capa de permisos, columnas efectivas (sin costo/observaciones/motivo y
sin «responsable» para roles limitados), filas, orden, campaña
cancelada, alcance del Técnico, filtros con sus 400 y eco, estados y
resumen, responsable/densidad/método, Excel y PDF; el rango obligatorio
de auditoría con sus seis 400, hora de Lima, etiquetas, filtros
compartidos con la pantalla, detalle en blanco segura, resumen por
acción/módulo, Excel con aviso de confidencialidad y PDF con el aviso en
relato y pie; el evento EXPORTAR de los dos tipos; y los límites y el
formato compartidos.
"""
import builtins
import importlib
import json
import re
import tempfile
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.apps import apps as apps_reales
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.urls import get_resolver
from django.utils import timezone
from openpyxl import load_workbook
from reportlab.pdfbase import pdfmetrics

from auditoria.models import Auditoria
from campanias.models import Campania
from catalogos.models import TipoActividad
from dashboard.tests import _TABLAS_DJANGO, _TABLAS_PROPIAS, DashboardBase
from productores.models import Parcela, Productor
from produccion.models import Produccion
from reportes import catalogo, consultas
from reportes.formato import es_texto_de_formula
from seguimiento.models import Actividad
from usuarios.models import Permiso, Rol, RolPermiso, Usuario
from usuarios.ratelimit import PREFIJO_EXPORTACIONES

_TZ_LIMA = ZoneInfo("America/Lima")

_PROHIBIDOS = (
    "dni", "telefono", "teléfono", "registrado_por", "correo", "email",
    "clave",
)


class ReportesBase(DashboardBase):
    """Mismos datos que el panel (Semana 16) más helpers de las tres
    lecturas de /api/reportes/ y de roles con permisos a medida."""

    def _catalogo(self):
        return self._json(self._api("get", "/api/reportes/"))["reportes"]

    def _previa(self, tipo="productores", filtros=""):
        return self._api("get", f"/api/reportes/{tipo}/vista-previa/{filtros}")

    def _exportar(self, tipo="productores", formato="xlsx", filtros=""):
        return self._api(
            "post",
            f"/api/reportes/{tipo}/exportar/{filtros}",
            {"formato": formato},
        )

    def _usuario_con(self, username, nombre_rol, codigos):
        """Usuario con un rol de prueba que tiene exactamente esos permisos."""
        rol = Rol.objects.create(nombre=nombre_rol, es_sistema=False)
        for codigo in codigos:
            RolPermiso.objects.create(
                rol=rol, permiso=Permiso.objects.get(codigo=codigo)
            )
        usuario = Usuario.objects.create_user(
            username=username, password="Reportes2026!", rol=rol
        )
        usuario.debe_cambiar_clave = False
        usuario.save(update_fields=("debe_cambiar_clave",))
        return usuario

    def _texto_pdf(self, contenido):
        """Texto del PDF: resuelve los escapes octales de reportlab y
        devuelve los caracteres como los escribió la vista."""
        texto = contenido.decode("latin-1")
        texto = re.sub(
            r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), texto
        )
        texto = texto.replace("\\(", "(").replace("\\)", ")")
        return texto.encode("latin-1", "replace").decode("cp1252", "replace")

    def _columna(self, hoja, etiqueta):
        """Índice (1-based) de una columna por su etiqueta de cabecera."""
        cabeceras = [celda.value for celda in hoja[1]]
        return cabeceras.index(etiqueta) + 1


class ReportesTests(ReportesBase):
    """Pruebas 280-299."""

    # ------------------------------------------------------------------ #
    # 280: catálogo, segunda capa de permisos y 404 de tipo desconocido
    # ------------------------------------------------------------------ #
    def test_280_catalogo_con_doble_permiso_y_404_de_tipo(self):
        self._entrar_admin()
        catalogo_admin = self._catalogo()
        self.assertEqual(
            [r["tipo"] for r in catalogo_admin],
            ["productores", "productivo", "actividades", "auditoria"],
        )
        primero = catalogo_admin[0]
        self.assertEqual(primero["nombre"], "Reporte de productores")
        self.assertEqual(primero["filtros"][-1], "estado_productor")
        self.assertEqual(primero["formatos"], ["xlsx", "pdf"])
        self.assertEqual(primero["limites"], {"xlsx": 20000, "pdf": 1000})
        self.assertEqual(
            primero["aviso_privacidad"], catalogo.AVISO_PRIVACIDAD
        )
        self.assertIn("descripcion", primero)
        # Con reportes.ver pero sin produccion.ver: solo se lista el suyo
        self._usuario_con(
            "cat_modulo_s17", "Catálogo módulo S17",
            ["reportes.ver", "productores.ver"],
        )
        self._entrar("cat_modulo_s17", "Reportes2026!")
        parcial = self._catalogo()
        self.assertEqual([r["tipo"] for r in parcial], ["productores"])
        # Tipo inexistente en las dos lecturas con detalle → 404 del sistema
        self._entrar_admin()
        for respuesta in (
            self._previa("inexistente"),
            self._api(
                "post", "/api/reportes/inexistente/exportar/",
                {"formato": "xlsx"},
            ),
        ):
            self.assertEqual(respuesta.status_code, 404)
            self.assertEqual(
                self._json(respuesta), {"detail": "No encontrado."}
            )

    # ------------------------------------------------------------------ #
    # 281: primer capa, segunda capa, portón y 401
    # ------------------------------------------------------------------ #
    def test_281_doble_permiso_401_403_y_porton_de_clave(self):
        url_catalogo = "/api/reportes/"
        url_previa = "/api/reportes/productores/vista-previa/"
        url_exportar = "/api/reportes/productores/exportar/"
        # Sin sesión: 401 en las tres
        self.assertEqual(self._api("get", url_catalogo).status_code, 401)
        self.assertEqual(self._api("get", url_previa).status_code, 401)
        self.assertEqual(
            self._api("post", url_exportar, {"formato": "xlsx"}).status_code,
            401,
        )
        # Con ver pero sin exportar: 403 solo al exportar
        self._usuario_con(
            "sin_exportar_s17", "Sin exportar S17",
            ["reportes.ver", "productores.ver", "produccion.ver"],
        )
        self._entrar("sin_exportar_s17", "Reportes2026!")
        self.assertEqual(len(self._catalogo()), 2)
        self.assertEqual(self._previa().status_code, 200)
        exportar = self._exportar()
        self.assertEqual(exportar.status_code, 403)
        self.assertEqual(
            self._json(exportar),
            {"detail": "No tienes permiso para realizar esta acción."},
        )
        # Sin el ver del módulo: la segunda capa cierra las lecturas con
        # detalle y el reporte no llega ni al catálogo
        self._usuario_con(
            "sin_modulo_s17", "Sin módulo S17",
            ["reportes.ver", "reportes.exportar"],
        )
        self._entrar("sin_modulo_s17", "Reportes2026!")
        self.assertEqual(self._catalogo(), [])
        self.assertEqual(self._previa().status_code, 403)
        self.assertEqual(self._exportar().status_code, 403)
        # Sin reportes.ver: 403 en las tres (primera capa)
        self._usuario_con(
            "sin_reportes_s17", "Sin reportes S17",
            ["productores.ver", "produccion.ver"],
        )
        self._entrar("sin_reportes_s17", "Reportes2026!")
        self.assertEqual(
            self._api("get", url_catalogo).status_code, 403
        )
        self.assertEqual(self._api("get", url_previa).status_code, 403)
        self.assertEqual(
            self._api("post", url_exportar, {"formato": "xlsx"}).status_code,
            403,
        )
        # Portón de cambio obligatorio de contraseña (HU-112): 403
        self._entrar_admin()
        self.admin.debe_cambiar_clave = True
        self.admin.save(update_fields=("debe_cambiar_clave",))
        for url in (url_catalogo, url_previa, url_exportar):
            cuerpo = {"formato": "xlsx"} if url.endswith("exportar/") else None
            respuesta = self._api(
                "post" if cuerpo else "get", url, cuerpo
            )
            self.assertEqual(respuesta.status_code, 403, url)
            self.assertEqual(
                self._json(respuesta),
                {"detail": "Debes cambiar tu contraseña antes de continuar."},
            )

    # ------------------------------------------------------------------ #
    # 282: el Técnico solo ve SUS productores en los dos reportes
    # ------------------------------------------------------------------ #
    def test_282_alcance_del_tecnico_en_los_dos_reportes(self):
        self._entrar_admin()
        productores_admin = self._json(self._previa("productores"))
        productivo_admin = self._json(self._previa("productivo"))
        self.assertEqual(productores_admin["total_filas"], 8)
        self.assertEqual(productivo_admin["total_filas"], 7)
        self._entrar_tecnico()
        productores_tec = self._json(self._previa("productores"))
        productivo_tec = self._json(self._previa("productivo"))
        self.assertEqual(productores_tec["total_filas"], 7)
        self.assertEqual(productivo_tec["total_filas"], 6)
        self.assertEqual(
            {f["productor"] for f in productores_tec["filas"]}, {"Uno Alfa"}
        )
        self.assertNotIn("Dos Beta", str(productores_tec))
        self.assertEqual(
            {f["productor"] for f in productivo_tec["filas"]}, {"Uno Alfa"}
        )
        # El Coordinador no se limita: mismas cifras que el Admin
        self._entrar_coordinador()
        self.assertEqual(
            self._json(self._previa("productores"))["total_filas"], 8
        )
        self.assertEqual(
            self._json(self._previa("productivo"))["total_filas"], 7
        )

    # ------------------------------------------------------------------ #
    # 283: filtros comunes, sus 400 y el eco de la respuesta
    # ------------------------------------------------------------------ #
    def test_283_filtros_comunes_400_y_eco(self):
        self._entrar_admin()
        # 400 con mensaje claro: id no numérico, estado y estado de productor
        malo = self._previa("productores", "?cultivo=abc")
        self.assertEqual(malo.status_code, 400)
        self.assertEqual(
            self._json(malo), {"cultivo": "Debe ser un id numérico."}
        )
        malo = self._previa("productivo", "?estado=RARA")
        self.assertEqual(malo.status_code, 400)
        self.assertEqual(
            self._json(malo),
            {"estado": "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, "
                       "CERRADA o CANCELADA."},
        )
        malo = self._previa("productores", "?estado_productor=VAGO")
        self.assertEqual(malo.status_code, 400)
        self.assertEqual(
            self._json(malo),
            {"estado_productor": "Use ACTIVO, INACTIVO o TODOS."},
        )
        # Eco de filtros válidos (los nombres salen resueltos a texto)
        eco = self._json(
            self._previa(
                "productores",
                f"?periodo=2026-2027&cultivo={self.cultivo.pk}",
            )
        )
        self.assertEqual(
            eco["filtros"],
            {"periodo": "2026-2027", "cultivo": self.cultivo.pk},
        )
        self.assertEqual(
            eco["filtros_texto"], "Período: 2026-2027 · Cultivo: Quinua S16"
        )
        self.assertEqual(eco["total_filas"], 5)
        # Periodo sin campañas: 0 filas (no un error)
        vacio = self._json(self._previa("productores", "?periodo=2025-2026"))
        self.assertEqual(vacio["total_filas"], 0)
        self.assertEqual(vacio["filas"], [])
        # estado= filtra también el reporte de productores (solo cosechadas)
        cosechadas = self._json(
            self._previa("productores", "?estado=COSECHADA")
        )
        self.assertEqual(cosechadas["total_filas"], 5)
        # estado del productor: por defecto solo activos
        inactivos = self._json(
            self._previa("productores", "?estado_productor=INACTIVO")
        )
        self.assertEqual(inactivos["total_filas"], 1)
        self.assertEqual(inactivos["filas"][0]["productor"], "Tres Gama")
        self.assertEqual(inactivos["resumen"]["productores"], 1)
        todos = self._json(
            self._previa("productores", "?estado_productor=TODOS")
        )
        self.assertEqual(todos["total_filas"], 9)
        self.assertEqual(todos["resumen"]["productores"], 3)

    # ------------------------------------------------------------------ #
    # 284: una fila por productor y campaña, sin canceladas y con orden
    # ------------------------------------------------------------------ #
    def test_284_granularidad_y_orden_del_reporte_de_productores(self):
        Productor.objects.create(
            nombres="Nueve", apellidos="Zeta", dni="95000077",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self._entrar_admin()
        datos = self._json(self._previa("productores"))
        productos = [f["productor"] for f in datos["filas"]]
        # Una fila por campaña: 7 de Uno Alfa (c9 está cancelada) + 1 de
        # Dos Beta + 1 del productor sin campañas
        self.assertEqual(productos.count("Uno Alfa"), 7)
        self.assertEqual(productos.count("Dos Beta"), 1)
        self.assertEqual(productos.count("Nueve Zeta"), 1)
        self.assertEqual(datos["total_filas"], 9)
        self.assertNotIn(
            "2025-2026", str([f["campania"] for f in datos["filas"]])
        )
        # Sin campañas: fila con la campaña vacía (sin filtro de campaña)
        ultima = datos["filas"][-1]
        self.assertEqual(ultima["productor"], "Nueve Zeta")
        self.assertEqual(ultima["campania"], "")
        self.assertEqual(ultima["cultivo"], "")
        # Orden del servidor: apellidos ascendente y luego período; los
        # de Alfa antes que los de Beta y el sin campaña al final
        ultimo_alfa = max(
            i for i, nombre in enumerate(productos) if nombre == "Uno Alfa"
        )
        primero_beta = productos.index("Dos Beta")
        self.assertLess(ultimo_alfa, primero_beta)
        # Con filtro de campaña, un productor sin campañas no aparece
        con_filtro = self._json(
            self._previa("productores", f"?cultivo={self.cultivo_maiz.pk}")
        )
        self.assertEqual(con_filtro["total_filas"], 1)
        self.assertEqual(con_filtro["filas"][0]["productor"], "Dos Beta")

    # ------------------------------------------------------------------ #
    # 285: superficies: parcelas contadas una sola vez por productor
    # ------------------------------------------------------------------ #
    def test_285_superficies_y_resumen_de_productores(self):
        self._entrar_admin()
        resumen = self._json(self._previa("productores"))["resumen"]
        self.assertEqual(resumen["productores"], 2)
        self.assertEqual(resumen["filas"], 8)
        # 9 parcelas de 4 ha: 36.00 aunque las 7 filas de Uno Alfa
        # repitieran la misma superficie
        self.assertEqual(resumen["superficie_parcelas_ha"], "36.00")
        self.assertEqual(resumen["superficie_sembrada_ha"], "13.50")
        self._entrar_tecnico()
        resumen_tec = self._json(self._previa("productores"))["resumen"]
        self.assertEqual(resumen_tec["superficie_parcelas_ha"], "32.00")
        self.assertEqual(resumen_tec["superficie_sembrada_ha"], "12.00")
        # Una parcela desactivada deja de contar en la superficie
        self._entrar_admin()
        parcela = self.c4.parcela
        parcela.estado = Parcela.ESTADO_INACTIVA
        parcela.save(update_fields=("estado",))
        datos = self._json(self._previa("productores"))
        fila_beta = next(
            f for f in datos["filas"] if f["productor"] == "Dos Beta"
        )
        self.assertEqual(fila_beta["parcelas_activas"], "0")
        self.assertEqual(datos["resumen"]["superficie_parcelas_ha"], "32.00")
        self.assertEqual(datos["resumen"]["filas"], 8)

    # ------------------------------------------------------------------ #
    # 286: detalle productivo: estados, revisiones y marcas
    # ------------------------------------------------------------------ #
    def test_286_detalle_productivo_estados_y_marcas(self):
        self._entrar_admin()
        datos = self._json(self._previa("productivo"))
        # Cada producción es una fila; la de revisión viene marcada
        self.assertEqual(datos["total_filas"], Produccion.objects.count())
        self.assertEqual(datos["total_filas"], 7)
        revision = next(
            f for f in datos["filas"] if f["requiere_revision"] == "Sí"
        )
        self.assertIn(
            revision["estado_campania"], dict(Campania.ESTADOS).values()
        )
        advertencias = " · ".join(datos["advertencias"])
        self.assertIn("1 producción espera revisión", advertencias)
        self.assertIn(
            "4 campañas sin cerrar aparecen como provisionales", advertencias
        )
        self.assertIn("Cañihua S16, Maíz S16", advertencias)
        # Filtro de estado estricto en el detalle y el resumen
        cerradas = self._json(self._previa("productivo", "?estado=CERRADA"))
        self.assertEqual(cerradas["total_filas"], 2)
        self.assertEqual(
            {f["estado_campania"] for f in cerradas["filas"]}, {"Cerrada"}
        )
        totales = cerradas["resumen"]["totales"]
        self.assertEqual(totales["campanias"], 2)
        self.assertEqual(totales["superficie_ha"], "2.50")
        self.assertEqual(totales["produccion_kg"], "800.00")
        self.assertEqual(totales["rendimiento_kg_ha"], "320.00")
        cosechadas = self._json(
            self._previa("productivo", "?estado=COSECHADA")
        )
        self.assertEqual(cosechadas["total_filas"], 5)
        # El resumen excluye la producción en revisión (4 de 5)
        self.assertEqual(cosechadas["resumen"]["totales"]["campanias"], 4)
        self.assertEqual(cosechadas["resumen"]["excluidas_revision"], 1)
        self.assertEqual(cosechadas["resumen"]["campanias_provisionales"], 4)

    # ------------------------------------------------------------------ #
    # 287: mismos filtros, mismas cifras que el panel
    # ------------------------------------------------------------------ #
    def test_287_coincidencia_con_el_panel(self):
        claves = (
            "clave", "etiqueta", "campanias", "superficie_ha",
            "produccion_kg", "rendimiento_kg_ha",
            "rendimiento_promedio_kg_ha", "provisional", "pocos_datos",
        )

        def comparar(filtros=""):
            previa = self._json(self._previa("productivo", filtros))
            panel = self._json(
                self._api("get", f"/api/dashboard/produccion/{filtros}")
            )
            self.assertEqual(previa["resumen"]["totales"], panel["totales"])
            propias = previa["resumen"]["por_cultivo"]
            self.assertEqual(len(propias), len(panel["filas"]))
            for propia, del_panel in zip(propias, panel["filas"]):
                for clave in claves:
                    self.assertEqual(
                        propia[clave], del_panel[clave],
                        f"{clave}: {propia['etiqueta']}",
                    )

        self._entrar_admin()
        comparar()
        comparar(f"?cultivo={self.cultivo.pk}")
        # El alcance del Técnico también coincide entre las dos pantallas
        self._entrar_tecnico()
        comparar()

    # ------------------------------------------------------------------ #
    # 288: el Excel con su hoja de resumen y la de datos
    # ------------------------------------------------------------------ #
    def test_288_excel_resumen_y_datos(self):
        self._entrar_admin()
        respuesta = self._exportar("productores", "xlsx")
        self.assertEqual(respuesta.status_code, 200)
        libro = load_workbook(BytesIO(respuesta.content))
        self.assertEqual(libro.sheetnames, ["Resumen", "Datos"])
        resumen = libro["Resumen"]
        titulos = [celda.value for celda in resumen["A"] if celda.value]
        self.assertEqual(titulos[0], "Reporte de productores")
        self.assertIn("Filtros: ninguno", titulos)
        self.assertIn("Generado por: admin_dashboard", titulos)
        self.assertTrue(any(t.startswith("Filas: 8") for t in titulos))
        self.assertIn(catalogo.AVISO_PRIVACIDAD, titulos)
        datos = libro["Datos"]
        cabeceras = [celda.value for celda in datos[1]]
        self.assertEqual(
            cabeceras,
            [c["etiqueta"] for c in catalogo.COLUMNAS_PRODUCTORES],
        )
        self.assertEqual(datos.freeze_panes, "A2")
        self.assertEqual(datos.auto_filter.ref, "A1:M9")
        # Estados con su etiqueta y números como números (nunca textos)
        columna_estado = self._columna(datos, "Estado")
        estados = {
            datos.cell(row=fila, column=columna_estado).value
            for fila in range(2, datos.max_row + 1)
        }
        self.assertEqual(estados, {"Activo"})
        columna_superficie = self._columna(
            datos, "Superficie de parcelas (ha)"
        )
        celda = datos.cell(row=2, column=columna_superficie)
        self.assertIsInstance(celda.value, (int, float))
        self.assertNotIsInstance(celda.value, str)
        # El mismo libro en el reporte productivo, con resumen y fechas
        respuesta = self._exportar("productivo", "xlsx")
        self.assertEqual(respuesta.status_code, 200)
        libro = load_workbook(BytesIO(respuesta.content))
        resumen = libro["Resumen"]
        titulos = [celda.value for celda in resumen["A"] if celda.value]
        self.assertIn("Totales", titulos)
        datos = libro["Datos"]
        self.assertEqual(
            [celda.value for celda in datos[1]],
            [c["etiqueta"] for c in catalogo.COLUMNAS_PRODUCTIVO],
        )
        self.assertEqual(datos.auto_filter.ref, "A1:M8")
        columna_fecha = self._columna(datos, "Fecha de cosecha")
        self.assertIsInstance(
            datos.cell(row=2, column=columna_fecha).value, datetime
        )
        columna_kg = self._columna(datos, "Producción (kg)")
        valor_kg = datos.cell(row=2, column=columna_kg).value
        self.assertIsInstance(valor_kg, (int, float))

    # ------------------------------------------------------------------ #
    # 289: todo texto tipo fórmula se guarda como cadena, no como fórmula
    # ------------------------------------------------------------------ #
    def test_289_excel_sin_formulas_inyectadas(self):
        Productor.objects.create(
            nombres="=1+1", apellidos="-Zeta", dni="95000078",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self._entrar_admin()
        # La vista previa lo devuelve tal cual, como texto
        previa = self._json(self._previa("productores"))
        riesgoso = next(
            f for f in previa["filas"] if f["productor"].startswith("=")
        )
        self.assertEqual(riesgoso["productor"], "=1+1 -Zeta")
        # En el Excel la celda es de texto (data_type "s"), jamás fórmula
        respuesta = self._exportar("productores", "xlsx")
        self.assertEqual(respuesta.status_code, 200)
        libro = load_workbook(BytesIO(respuesta.content))
        datos = libro["Datos"]
        columna = self._columna(datos, "Productor")
        celdas_riesgo = [
            datos.cell(row=fila, column=columna)
            for fila in range(2, datos.max_row + 1)
            if es_texto_de_formula(datos.cell(row=fila, column=columna).value)
        ]
        self.assertEqual(len(celdas_riesgo), 1)
        self.assertEqual(celdas_riesgo[0].value, "=1+1 -Zeta")
        self.assertEqual(celdas_riesgo[0].data_type, "s")

    # ------------------------------------------------------------------ #
    # 290: el PDF con cabecera, pie, resumen y texto fuera de cp1252
    # ------------------------------------------------------------------ #
    def test_290_pdf_encabezado_tabla_y_texto_seguro(self):
        Productor.objects.create(
            nombres="日本語", apellidos="Prueba", dni="95000079",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        pdfmetrics.getFont("Helvetica")
        pdfmetrics.getFont("Helvetica-Bold")
        self._entrar_admin()
        respuesta = self._exportar("productores", "pdf")
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content
        self.assertTrue(contenido.startswith(b"%PDF"))
        # Sin compresión: los textos ASCII están a la vista en los bytes
        self.assertIn(b"Generado por: admin_dashboard", contenido)
        texto = self._texto_pdf(contenido)
        self.assertIn("SIGPA-GA — Reporte de productores", texto)
        self.assertIn("Filtros: ninguno", texto)
        self.assertIn(catalogo.AVISO_PRIVACIDAD, texto)
        self.assertRegex(texto, r"Página 1 de \d+")
        # Caracteres fuera de la fuente: sustituidos, nunca rompen
        self.assertNotIn("日本語", texto)
        self.assertIn("??? Prueba", texto)
        # Números en formato peruano y resumen con Totales
        respuesta = self._exportar("productivo", "pdf")
        self.assertEqual(respuesta.status_code, 200)
        texto = self._texto_pdf(respuesta.content)
        self.assertIn("SIGPA-GA — Reporte productivo", texto)
        self.assertIn("Totales", texto)
        self.assertIn("1,300", texto)
        self.assertIn("216.67", texto)
        self.assertIn("Sí", texto)

    # ------------------------------------------------------------------ #
    # 291: límites de filas por formato: 400 claro, sin truncar
    # ------------------------------------------------------------------ #
    def test_291_limites_de_filas_por_formato(self):
        self._entrar_admin()
        self.assertEqual(self._json(self._previa())["total_filas"], 8)
        with patch("reportes.catalogo.LIMITE_PDF_FILAS", 5):
            respuesta = self._exportar("productores", "pdf")
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(
                self._json(respuesta),
                {
                    "detail": (
                        "El reporte tiene 8 filas y el máximo para PDF es 5. "
                        "Descarga en Excel (admite más filas) o afina los "
                        "filtros."
                    )
                },
            )
            self.assertNotIn("Content-Disposition", respuesta)
            # La vista previa no se ve afectada por el límite de descarga
            self.assertEqual(self._json(self._previa())["total_filas"], 8)
        with patch("reportes.catalogo.LIMITE_EXCEL_FILAS", 3):
            respuesta = self._exportar("productores", "xlsx")
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(
                self._json(respuesta),
                {
                    "detail": (
                        "El reporte tiene 8 filas y el máximo para XLSX es 3. "
                        "Afina los filtros para reducir el número de filas."
                    )
                },
            )
            self.assertNotIn("Content-Disposition", respuesta)
        # Formato desconocido o ausente en el cuerpo → 400
        for cuerpo in ({"formato": "csv"}, {}):
            respuesta = self._api(
                "post", "/api/reportes/productores/exportar/", cuerpo
            )
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(
                self._json(respuesta), {"formato": "Use xlsx o pdf."}
            )

    # ------------------------------------------------------------------ #
    # 292: privacidad por diseño: sin DNI, teléfono ni registrado_por
    # ------------------------------------------------------------------ #
    def test_292_privacidad_por_diseno(self):
        self._entrar_admin()
        for tipo in ("productores", "productivo"):
            for columna in catalogo.obtener(tipo)["columnas"]:
                texto = f"{columna['clave']} {columna['etiqueta']}".lower()
                for prohibido in _PROHIBIDOS:
                    self.assertNotIn(prohibido, texto, f"{tipo}: {texto}")
        previa = self._json(self._previa("productores"))
        claves_esperadas = {
            c["clave"] for c in catalogo.obtener("productores")["columnas"]
        }
        for fila in previa["filas"]:
            self.assertEqual(set(fila), claves_esperadas)
        bruto = json.dumps(previa, ensure_ascii=False)
        self.assertNotIn("95000001", bruto)
        self.assertNotIn("95000002", bruto)
        # El aviso de privacidad acompaña siempre a la respuesta
        self.assertEqual(
            previa["aviso_privacidad"], catalogo.AVISO_PRIVACIDAD
        )
        # Ni en el detalle del evento de auditoría
        self._exportar("productores", "xlsx")
        evento = Auditoria.objects.get(accion="EXPORTAR")
        detalle = json.dumps(evento.detalle, ensure_ascii=False)
        self.assertNotIn("95000001", detalle)
        self.assertNotIn("registrado_por", detalle)

    # ------------------------------------------------------------------ #
    # 293: auditoría EXPORTAR antes de entregar; si falla → 503 sin archivo
    # ------------------------------------------------------------------ #
    def test_293_auditoria_exportar_y_503_sin_archivo(self):
        self._entrar_admin()
        base = Auditoria.objects.count()
        self.assertEqual(self._exportar().status_code, 200)
        self.assertEqual(Auditoria.objects.count(), base + 1)
        evento = Auditoria.objects.get(accion="EXPORTAR")
        self.assertEqual(evento.modulo, "reportes")
        self.assertEqual(evento.usuario, self.admin)
        self.assertEqual(
            evento.detalle,
            {"tipo": "productores", "formato": "xlsx", "filtros": {},
             "filas": 8},
        )
        self.assertEqual(evento.ip, "127.0.0.1")
        # Catálogo y vista previa no son exportación: sin eventos nuevos
        self._catalogo()
        self._previa()
        self.assertEqual(Auditoria.objects.count(), base + 1)
        # La auditoría va ANTES de la entrega: si falla, no hay archivo
        clave = PREFIJO_EXPORTACIONES + self.admin.username
        cache.set(
            clave,
            {"intentos": 19, "expira": time.time() + 3600},
            timeout=3600,
        )
        with patch(
            "reportes.views.registrar_evento",
            side_effect=RuntimeError("fallo de auditoría"),
        ):
            respuesta = self._exportar("productores", "pdf")
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(
            self._json(respuesta),
            {
                "detail": (
                    "No se pudo registrar la auditoría de la exportación; "
                    "no se entregó el archivo. Vuelve a intentarlo."
                )
            },
        )
        self.assertTrue(
            respuesta["Content-Type"].startswith("application/json")
        )
        self.assertNotIn("Content-Disposition", respuesta)
        self.assertEqual(Auditoria.objects.count(), base + 1)
        # Tampoco gastó la ventana de exportaciones
        self.assertEqual(cache.get(clave)["intentos"], 19)
        # Y sin la falla, la siguiente entrega sí sale con su evento
        self.assertEqual(
            self._exportar("productores", "pdf").status_code, 200
        )
        self.assertEqual(Auditoria.objects.count(), base + 2)

    # ------------------------------------------------------------------ #
    # 294: 20 exportaciones por hora y usuario; la vista previa no cuenta
    # ------------------------------------------------------------------ #
    def test_294_frecuencia_veinte_por_hora(self):
        self._entrar_admin()
        with patch("usuarios.ratelimit.EXPORTACIONES_POR_HORA", 2):
            self.assertEqual(self._exportar().status_code, 200)
            self.assertEqual(self._previa().status_code, 200)
            self.assertEqual(self._exportar().status_code, 200)
            self.assertEqual(self._previa().status_code, 200)
            bloqueo = self._exportar()
            self.assertEqual(bloqueo.status_code, 429)
            datos = self._json(bloqueo)
            self.assertGreaterEqual(datos["retry_after"], 1)
            self.assertIn("límite de exportaciones", datos["detail"])
            self.assertIn("Intenta de nuevo en", datos["detail"])
            self.assertEqual(bloqueo["Retry-After"], str(datos["retry_after"]))
            self.assertNotIn("Content-Disposition", bloqueo)
            # Cada usuario tiene su propia ventana
            self._entrar_coordinador()
            self.assertEqual(self._exportar().status_code, 200)
            # Pasada la ventana (marca expirada) vuelve a haber cupo
            cache.set(
                PREFIJO_EXPORTACIONES + self.admin.username,
                {"intentos": 2, "expira": time.time() - 1},
                timeout=60,
            )
            self._entrar_admin()
            self.assertEqual(self._exportar().status_code, 200)

    # ------------------------------------------------------------------ #
    # 295: cabeceras anti-caché y nombre de archivo con fecha de Lima
    # ------------------------------------------------------------------ #
    def test_295_cabeceras_y_nombre_de_archivo(self):
        self._entrar_admin()
        xlsx = self._exportar("productores", "xlsx")
        self.assertEqual(xlsx.status_code, 200)
        self.assertEqual(
            xlsx["Content-Type"],
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet",
        )
        self.assertRegex(
            xlsx["Content-Disposition"],
            r'^attachment; filename="reporte_productores_\d{8}-\d{4}'
            r'\.xlsx"$',
        )
        self.assertEqual(xlsx["Cache-Control"], "no-store")
        self.assertEqual(xlsx["X-Content-Type-Options"], "nosniff")
        self.assertTrue(xlsx.content.startswith(b"PK"))
        pdf = self._exportar("productivo", "pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertRegex(
            pdf["Content-Disposition"],
            r'^attachment; filename="reporte_productivo_\d{8}-\d{4}\.pdf"$',
        )
        self.assertEqual(pdf["Cache-Control"], "no-store")
        self.assertEqual(pdf["X-Content-Type-Options"], "nosniff")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    # ------------------------------------------------------------------ #
    # 296: la generación ocurre en memoria: el PDF sin tocar el sistema
    # de ficheros y Excel solo en el temporal que openpyxl borra solo
    # ------------------------------------------------------------------ #
    def test_296_generacion_en_memoria_sin_disco(self):
        self._entrar_admin()
        # Calentamiento: las fuentes del PDF y las cargas internas se
        # hacen una vez; a partir de ahí ninguna llamada abre archivos
        self.assertEqual(self._exportar("productores", "pdf").status_code, 200)
        self.assertEqual(
            self._exportar("productores", "xlsx").status_code, 200
        )
        pdfmetrics.getFont("Helvetica")
        pdfmetrics.getFont("Helvetica-Bold")
        with patch(
            "builtins.open",
            side_effect=AssertionError("la exportación abrió un archivo"),
        ):
            self.assertEqual(
                self._exportar("productores", "pdf").status_code, 200
            )
            self.assertEqual(
                self._exportar("productivo", "pdf").status_code, 200
            )
            self.assertEqual(self._previa().status_code, 200)
        # Excel: openpyxl escribe cada hoja en un temporal del sistema
        # (lo borra al volcarla en la memoria); anotamos cada apertura
        # para comprobar que solo toca ese temporal, nunca el repositorio
        abiertos = []
        abrir_real = builtins.open

        def espiar(ruta, *args, **kwargs):
            modo = (
                args[0]
                if args and isinstance(args[0], str)
                else kwargs.get("mode", "r")
            )
            abiertos.append((str(ruta), modo))
            return abrir_real(ruta, *args, **kwargs)

        with patch("builtins.open", side_effect=espiar):
            self.assertEqual(
                self._exportar("productores", "xlsx").status_code, 200
            )
            self.assertEqual(
                self._exportar("productivo", "xlsx").status_code, 200
            )
            self.assertEqual(self._previa().status_code, 200)
        self.assertTrue(abiertos)
        temporal = Path(tempfile.gettempdir()).resolve()
        raiz = Path(__file__).resolve().parents[2]
        for ruta, _modo in abiertos:
            destino = Path(ruta).resolve()
            self.assertTrue(
                destino.is_relative_to(temporal),
                f"archivo fuera del temporal del sistema: {ruta}",
            )
            self.assertFalse(
                destino.is_relative_to(raiz),
                f"archivo dentro del repositorio: {ruta}",
            )
            self.assertTrue(destino.name.startswith("openpyxl."), ruta)
        # openpyxl borra su temporal al terminar de escribir la hoja
        for ruta, _modo in abiertos:
            self.assertFalse(Path(ruta).exists(), f"temporal: {ruta}")

    # ------------------------------------------------------------------ #
    # 297: «Generado el» en hora de Lima, con casos de medianoche
    # ------------------------------------------------------------------ #
    def test_297_fecha_de_lima_cerca_de_medianoche(self):
        self._entrar_admin()
        ultima_hora = datetime(2025, 12, 31, 23, 59, tzinfo=_TZ_LIMA)
        with patch("reportes.views.ahora_lima", return_value=ultima_hora):
            xlsx = self._exportar("productores", "xlsx")
        self.assertEqual(
            xlsx["Content-Disposition"],
            'attachment; filename="reporte_productores_20251231-2359.xlsx"',
        )
        libro = load_workbook(BytesIO(xlsx.content))
        titulos = [
            celda.value for celda in libro["Resumen"]["A"] if celda.value
        ]
        self.assertIn(
            "Generado el: 31/12/2025 23:59 (hora de Lima)", titulos
        )
        primer_dia = datetime(2026, 1, 1, 0, 0, tzinfo=_TZ_LIMA)
        with patch("reportes.views.ahora_lima", return_value=primer_dia):
            pdf = self._exportar("productores", "pdf")
        self.assertEqual(
            pdf["Content-Disposition"],
            'attachment; filename="reporte_productores_20260101-0000.pdf"',
        )
        self.assertIn(b"Generado el: 01/01/2026 00:00", pdf.content)
        # El reloj de la API sigue huso de Lima
        from dashboard.consultas import ahora_lima

        self.assertEqual(ahora_lima().utcoffset(), timedelta(hours=-5))

    # ------------------------------------------------------------------ #
    # 298: migración del CHECK reversible, 29 tablas y 25 triggers
    # ------------------------------------------------------------------ #
    def test_298_migracion_check_29_tablas_y_25_triggers(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema = 'public'"
                " AND table_type = 'BASE TABLE'"
            )
            todas = {fila[0] for fila in cursor.fetchall()}
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"
            )
            triggers = cursor.fetchone()[0]
        propias = todas - _TABLAS_DJANGO
        self.assertEqual(propias, _TABLAS_PROPIAS)
        self.assertEqual(len(propias), 29)
        self.assertEqual(triggers, 25)
        # La app de reportes no crea tablas ni migraciones
        self.assertEqual([t for t in todas if t.startswith("reportes")], [])
        carpeta = Path(__file__).resolve().parent / "migrations"
        self.assertFalse(carpeta.exists())
        # El modelo y la migración están sincronizados
        try:
            call_command(
                "makemigrations", "--check", "--dry-run", verbosity=0
            )
        except SystemCheckError:
            self.fail("Hay cambios de modelo sin migrar")
        # Guarda de reversión: pasa mientras no haya eventos EXPORTAR
        # (los eventos no se pueden borrar, así que el orden importa)
        modulo = importlib.import_module(
            "auditoria.migrations.0003_accion_exportar"
        )
        modulo._antes_de_revertir(apps_reales, None)
        # Reversión real (el DDL de PostgreSQL es transaccional): al
        # volver al CHECK de 15 acciones, EXPORTAR ya no cabe
        executor = MigrationExecutor(connection)
        executor.migrate([("auditoria", "0002_fn_trg_auditoria")])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Auditoria.objects.create(
                    usuario=self.admin, accion="EXPORTAR", modulo="reportes"
                )
        # Al reaplicar, el CHECK de 16 vuelve: EXPORTAR cabe y PEPE no
        executor = MigrationExecutor(connection)
        executor.migrate([("auditoria", "0003_accion_exportar")])
        Auditoria.objects.create(
            usuario=self.admin, accion="EXPORTAR", modulo="reportes"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Auditoria.objects.create(
                    usuario=self.admin, accion="PEPE", modulo="reportes"
                )
        # Con eventos EXPORTAR presentes no se puede volver atrás
        with self.assertRaises(IrreversibleError) as capturada:
            modulo._antes_de_revertir(apps_reales, None)
        mensaje = str(capturada.exception)
        self.assertIn("No se puede revertir la migración", mensaje)
        self.assertIn("EXPORTAR", mensaje)

    # ------------------------------------------------------------------ #
    # 299: recorrido de rutas: 405 donde no toca y solo exportar registra
    # ------------------------------------------------------------------ #
    def test_299_recorrido_de_rutas_y_solo_exportar_registra(self):
        patrones = []

        def recorrer(patrones_hijos, prefijo=""):
            for patron in patrones_hijos:
                if hasattr(patron, "url_patterns"):
                    recorrer(
                        patron.url_patterns, prefijo + str(patron.pattern)
                    )
                else:
                    patrones.append(prefijo + str(patron.pattern))

        recorrer(get_resolver().url_patterns)
        # El pk se cambia primero (dentro de [^/.] hay un ^ que el
        # siguiente replace borraría) y solo después los anclajes
        rutas = [
            re.sub(r"\(\?P<pk>\[\^/\.\]\+\)", "productores", ruta)
            .replace("^", "")
            .replace("$", "")
            for ruta in patrones
            if "reportes" in ruta
        ]
        self.assertEqual(len(rutas), 3)
        self._entrar_admin()
        base = Auditoria.objects.count()
        for ruta in rutas:
            completa = f"/{ruta}"
            if ruta.endswith("exportar/"):
                self.assertEqual(
                    self._api("get", completa).status_code, 405, ruta
                )
                for metodo in ("put", "patch", "delete"):
                    self.assertEqual(
                        self._api(metodo, completa, {}).status_code, 405,
                        f"{metodo} {ruta}",
                    )
                # Solo aquí se genera (y se registra) un archivo
                self.assertEqual(
                    self._api(
                        "post", completa, {"formato": "xlsx"}
                    ).status_code,
                    200, ruta,
                )
            elif ruta.endswith("vista-previa/"):
                self.assertEqual(
                    self._api("get", completa).status_code, 200, ruta
                )
                for metodo in ("post", "put", "patch", "delete"):
                    self.assertEqual(
                        self._api(metodo, completa, {}).status_code, 405,
                        f"{metodo} {ruta}",
                    )
            elif ruta.rstrip("/").endswith("reportes"):
                self.assertEqual(
                    self._api("get", completa).status_code, 200, ruta
                )
                for metodo in ("post", "put", "patch", "delete"):
                    self.assertEqual(
                        self._api(metodo, completa, {}).status_code, 405,
                        f"{metodo} {ruta}",
                    )
            else:
                # Solo existen el catálogo, la vista previa y exportar
                self.fail(f"ruta inesperada: {ruta}")
        # El detalle no existe: el cliente no elige columnas ni registro
        self.assertEqual(
            self._api("get", "/api/reportes/productores/").status_code, 404
        )
        # El recorrido entero solo dejó el evento de la exportación
        self.assertEqual(Auditoria.objects.count(), base + 1)
        ultimo = Auditoria.objects.order_by("-id").first()
        self.assertEqual(ultimo.accion, "EXPORTAR")
        self.assertEqual(ultimo.modulo, "reportes")


class ReportesSemana18Tests(ReportesBase):
    """Pruebas 302-317 (Semana 18): los reportes de actividades (RF-68)
    y de auditoría (HU-155/HU-156), sus permisos, filtros, archivos y la
    confidencialidad del segundo."""

    def setUp(self):
        super().setUp()
        # El trigger de código rellena codigo en la base; el objeto en
        # memoria sigue con el '' inicial
        self.p1.refresh_from_db()
        self.preparacion = TipoActividad.objects.get(codigo="PREPARACION")
        self.siembra = TipoActividad.objects.get(codigo="SIEMBRA")
        # Actividades con fechas, tipos, horas y estados variados
        self.a1 = self._actividad(
            self.c1, self.hoy - timedelta(days=10), self.preparacion,
            horas="4.5", registrado_por=self.admin, metodo="Arado",
        )
        self.a2 = self._actividad(
            self.c1, self.hoy - timedelta(days=3), self.siembra,
            registrado_por=self.admin, densidad=("25", "KG_HA"),
        )
        self.a3 = self._actividad(
            self.c4, self.hoy - timedelta(days=5), self.preparacion,
            registrado_por=self.coordinador,
        )
        # La campaña se cancela DESPUÉS de registrar la actividad: los
        # triggers rechazan altas sobre campañas canceladas, y el reporte
        # debe seguir incluyéndola con su estado en la fila
        self.c_cancelada = self._campania(
            self.p1, self.cultivo, parcela="pa10"
        )
        self.a4 = self._actividad(
            self.c_cancelada, self.hoy - timedelta(days=8), self.preparacion,
            horas="2.0",
        )
        self._sql(
            "UPDATE campanias SET estado = 'CANCELADA' WHERE id = %s",
            [self.c_cancelada.pk],
        )
        self.a5 = self._actividad(
            self.c2, self.hoy - timedelta(days=2), self.siembra,
            horas="1.0", anulada=True, motivo="Lluvia persistente",
        )
        # Eventos de bitácora con formas variadas (los tres son
        # anteriores al LOGIN que deja cada inicio de sesión)
        ahora = timezone.now()
        self.ev_exportar = Auditoria.objects.create(
            usuario=self.admin, accion="EXPORTAR", modulo="reportes",
            tabla="auditoria", registro_id=77, ip="10.0.0.5",
            detalle={
                "tipo": "xlsx",
                "filtros": {"cultivo": 1},
                "filas": 12,
                "motivo": "Texto libre confidencial",
                "resumen": {"alertas": 3},
            },
            fecha=ahora - timedelta(hours=1),
        )
        self.ev_sin_usuario = Auditoria.objects.create(
            usuario=None, accion="LOGIN", modulo="sesiones_prueba",
            ip="10.0.0.9", fecha=ahora - timedelta(hours=2),
        )
        self.ev_crear = Auditoria.objects.create(
            usuario=self.coordinador, accion="CREAR", modulo="informes_esp",
            tabla="cosas", registro_id=5, ip="10.0.0.7",
            detalle={"estado": "ACTIVO", "nota": "No debe aparecer"},
            fecha=ahora - timedelta(hours=3),
        )
        self._desde = (self.hoy - timedelta(days=30)).isoformat()
        self._rango = f"?fecha_desde={self._desde}&fecha_hasta={self.hoy.isoformat()}"

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _actividad(
        self, campania, fecha, tipo, horas=None, registrado_por=None,
        anulada=False, metodo="", densidad=None, motivo=None,
    ):
        datos = {
            "campania": campania,
            "tipo_actividad": tipo,
            "fecha": fecha,
            "registrado_por": registrado_por,
            "metodo": metodo,
            "anulada": anulada,
        }
        if horas is not None:
            datos["horas"] = horas
        if densidad is not None:
            datos["densidad_siembra"], datos["densidad_unidad"] = densidad
        if motivo is not None:
            datos["motivo_anulacion"] = motivo
        return Actividad.objects.create(**datos)

    # ------------------------------------------------------------------ #
    # 302: catálogo de los tipos nuevos (sensible, aviso) y 2ª capa
    # ------------------------------------------------------------------ #
    def test_302_catalogo_nuevo_sensible_aviso_y_segunda_capa(self):
        self._entrar_admin()
        cat = {r["tipo"]: r for r in self._catalogo()}
        self.assertEqual(
            set(cat),
            {"productores", "productivo", "actividades", "auditoria"},
        )
        activ = cat["actividades"]
        self.assertFalse(activ["sensible"])
        self.assertIsNone(activ["aviso"])
        self.assertEqual(activ["filtros"], list(catalogo.FILTROS_ACTIVIDADES))
        self.assertEqual(len(activ["filtros"]), 10)
        aud = cat["auditoria"]
        self.assertTrue(aud["sensible"])
        self.assertEqual(aud["aviso"], catalogo.AVISO_CONFIDENCIALIDAD)
        self.assertEqual(aud["filtros"], list(catalogo.FILTROS_AUDITORIA))
        # Segunda capa: el ver del módulo decide qué reportes se usan
        self._usuario_con(
            "cap_s18a", "Cap S18 A",
            ["reportes.ver", "reportes.exportar", "actividades.ver"],
        )
        self._entrar("cap_s18a", "Reportes2026!")
        self.assertEqual([r["tipo"] for r in self._catalogo()], ["actividades"])
        self.assertEqual(self._previa("actividades").status_code, 200)
        self.assertEqual(self._previa("auditoria").status_code, 403)
        self.assertEqual(self._exportar("actividades", "xlsx").status_code, 200)
        denegado = self._exportar("auditoria", "xlsx")
        self.assertEqual(denegado.status_code, 403)
        self.assertEqual(
            self._json(denegado),
            {"detail": "No tienes permiso para realizar esta acción."},
        )
        # Con el ver de auditoría pero sin el rango: 400, no 403
        self._usuario_con(
            "cap_s18b", "Cap S18 B",
            ["reportes.ver", "reportes.exportar", "auditoria.ver"],
        )
        self._entrar("cap_s18b", "Reportes2026!")
        self.assertEqual([r["tipo"] for r in self._catalogo()], ["auditoria"])
        sin_rango = self._previa("auditoria")
        self.assertEqual(sin_rango.status_code, 400)
        self.assertEqual(
            self._json(sin_rango),
            {
                "fecha_desde": "El rango de fechas es obligatorio.",
                "fecha_hasta": "El rango de fechas es obligatorio.",
            },
        )

    # ------------------------------------------------------------------ #
    # 303: columnas efectivas (sin costo/observaciones ni responsable)
    # ------------------------------------------------------------------ #
    def test_303_columnas_efectivas_de_las_dos_vistas_previas(self):
        self._entrar_admin()
        previa = self._json(self._previa("actividades"))
        claves = [c["clave"] for c in previa["columnas"]]
        self.assertEqual(
            claves, [c["clave"] for c in catalogo.COLUMNAS_ACTIVIDADES]
        )
        self.assertEqual(len(claves), 13)
        # Privacidad por diseño: los tres campos de la ficha no salen
        self.assertNotIn("costo", claves)
        self.assertNotIn("observaciones", claves)
        self.assertNotIn("motivo_anulacion", claves)
        self.assertIn("responsable", claves)
        previa_aud = self._json(self._previa("auditoria", self._rango))
        self.assertEqual(
            [c["clave"] for c in previa_aud["columnas"]],
            [c["clave"] for c in catalogo.COLUMNAS_AUDITORIA],
        )
        self.assertEqual(
            previa_aud["columnas"][0],
            {"clave": "fecha", "etiqueta": "Fecha y hora"},
        )
        # Ninguna columna de los tipos nuevos nombra datos prohibidos
        for tipo in ("actividades", "auditoria"):
            for columna in catalogo.obtener(tipo)["columnas"]:
                texto_col = f"{columna['clave']} {columna['etiqueta']}".lower()
                for prohibido in _PROHIBIDOS:
                    self.assertNotIn(prohibido, texto_col, f"{tipo}: {texto_col}")
        # El rol limitado no recibe la columna «responsable»
        self._entrar_tecnico()
        previa_tec = self._json(self._previa("actividades"))
        claves_tec = [c["clave"] for c in previa_tec["columnas"]]
        self.assertNotIn("responsable", claves_tec)
        self.assertEqual(len(claves_tec), 12)
        # El Coordinador no se limita: la conserva
        self._entrar_coordinador()
        previa_coord = self._json(self._previa("actividades"))
        self.assertIn(
            "responsable", [c["clave"] for c in previa_coord["columnas"]]
        )

    # ------------------------------------------------------------------ #
    # 304: filas, orden, campaña cancelada incluida y alcance del Técnico
    # ------------------------------------------------------------------ #
    def test_304_actividades_filas_orden_cancelada_y_alcance(self):
        self._entrar_admin()
        datos = self._json(self._previa("actividades"))
        self.assertEqual(datos["total_filas"], 4)  # a5 anulada no cuenta
        fechas = [f["fecha"] for f in datos["filas"]]
        esperadas = [
            (self.hoy - timedelta(days=3)).strftime("%d/%m/%Y"),
            (self.hoy - timedelta(days=5)).strftime("%d/%m/%Y"),
            (self.hoy - timedelta(days=8)).strftime("%d/%m/%Y"),
            (self.hoy - timedelta(days=10)).strftime("%d/%m/%Y"),
        ]
        self.assertEqual(fechas, esperadas)
        # La campaña cancelada sí aparece, con su estado en la fila
        cancelada = datos["filas"][2]
        self.assertEqual(cancelada["campania"], self.c_cancelada.periodo)
        self.assertEqual(cancelada["estado_campania"], "Cancelada")
        self.assertEqual(cancelada["cultivo"], "Quinua S16")
        self.assertEqual(
            cancelada["productor"], f"{self.p1.codigo} · Uno Alfa"
        )
        self.assertEqual(cancelada["parcela"], self.c_cancelada.parcela.codigo)
        self.assertEqual(cancelada["distrito"], "Distrito S16")
        # El estado de campaña, cuando se pide, sí filtra
        solo_cancelada = self._json(
            self._previa("actividades", "?estado=CANCELADA")
        )
        self.assertEqual(solo_cancelada["total_filas"], 1)
        cosechadas = self._json(
            self._previa("actividades", "?estado=COSECHADA")
        )
        self.assertEqual(cosechadas["total_filas"], 3)  # a1, a2 y a3
        # Alcance del Técnico: solo sus productores (a1, a2 y a4)
        self._entrar_tecnico()
        tec = self._json(self._previa("actividades"))
        self.assertEqual(tec["total_filas"], 3)
        self.assertEqual(
            {f["productor"] for f in tec["filas"]},
            {f"{self.p1.codigo} · Uno Alfa"},
        )
        self.assertNotIn("Dos Beta", str(tec))

    # ------------------------------------------------------------------ #
    # 305: filtros con sus 400 y el eco resuelto a texto
    # ------------------------------------------------------------------ #
    def test_305_actividades_filtros_400_y_eco_de_texto(self):
        self._entrar_admin()
        casos = [
            (
                "?estado_actividad=LOCO",
                {"estado_actividad": "Use ACTIVAS, ANULADAS o TODAS."},
            ),
            (
                "?tipo_actividad=99999",
                {"tipo_actividad": "El tipo de actividad indicado no existe."},
            ),
            (
                "?tipo_actividad=abc",
                {"tipo_actividad": "Debe ser un id numérico."},
            ),
            (
                f"?fecha_actividad_desde={self.hoy.isoformat()}"
                f"&fecha_actividad_hasta={(self.hoy - timedelta(days=5)).isoformat()}",
                {"fecha_actividad_desde": "La fecha inicial no puede ser "
                                          "posterior a la final."},
            ),
            (
                "?fecha_actividad_desde=31-10-2026",
                {"fecha_actividad_desde": "La fecha no es válida: usa el "
                                          "formato AAAA-MM-DD."},
            ),
        ]
        for consulta, esperado in casos:
            respuesta = self._previa("actividades", consulta)
            self.assertEqual(respuesta.status_code, 400, consulta)
            self.assertEqual(self._json(respuesta), esperado, consulta)
        # Eco: fechas en dd/mm/aaaa y etiquetas resueltas
        desde = (self.hoy - timedelta(days=5)).isoformat()
        eco = self._json(
            self._previa(
                "actividades",
                f"?fecha_actividad_desde={desde}&estado_actividad=TODAS"
                f"&tipo_actividad={self.siembra.pk}",
            )
        )
        self.assertEqual(eco["filtros"]["fecha_actividad_desde"], desde)
        self.assertEqual(eco["filtros"]["estado_actividad"], "TODAS")
        texto_filtros = eco["filtros_texto"]
        self.assertIn(
            f"Actividad desde: {(self.hoy - timedelta(days=5)).strftime('%d/%m/%Y')}",
            texto_filtros,
        )
        self.assertIn("Estado de la actividad: todas", texto_filtros)
        self.assertIn(f"Tipo de actividad: {self.siembra.nombre}", texto_filtros)

    # ------------------------------------------------------------------ #
    # 306: estados, rango inclusivo y resumen completo
    # ------------------------------------------------------------------ #
    def test_306_actividades_estados_rango_y_resumen(self):
        self._entrar_admin()
        # Por defecto solo activas; anuladas y todas cambian el conteo
        self.assertEqual(
            self._json(self._previa("actividades"))["total_filas"], 4
        )
        anuladas = self._json(
            self._previa("actividades", "?estado_actividad=ANULADAS")
        )
        self.assertEqual(anuladas["total_filas"], 1)
        fila_anulada = anuladas["filas"][0]
        self.assertEqual(fila_anulada["estado_actividad"], "Anulada")
        self.assertEqual(
            set(fila_anulada),
            {c["clave"] for c in catalogo.COLUMNAS_ACTIVIDADES},
        )
        todas = self._json(
            self._previa("actividades", "?estado_actividad=TODAS")
        )
        self.assertEqual(todas["total_filas"], 5)
        # Rango inclusivo en los dos extremos
        desde = self._json(
            self._previa(
                "actividades",
                f"?fecha_actividad_desde={(self.hoy - timedelta(days=5)).isoformat()}",
            )
        )
        self.assertEqual(desde["total_filas"], 2)  # a3 (hoy-5) y a2 (hoy-3)
        hasta = self._json(
            self._previa(
                "actividades",
                f"?fecha_actividad_hasta={(self.hoy - timedelta(days=8)).isoformat()}",
            )
        )
        self.assertEqual(hasta["total_filas"], 2)  # a4 (hoy-8) y a1 (hoy-10)
        # Resumen: totales, por tipo ordenado y rango de fechas
        resumen = self._json(self._previa("actividades"))["resumen"]
        self.assertEqual(resumen["total"], 4)
        esperado = sorted(
            [
                {"etiqueta": self.preparacion.nombre, "cantidad": 3},
                {"etiqueta": self.siembra.nombre, "cantidad": 1},
            ],
            key=lambda fila: fila["etiqueta"],
        )
        self.assertEqual(resumen["por_tipo"], esperado)
        self.assertEqual(resumen["horas_totales"], "6.50")
        self.assertEqual(resumen["actividades_con_horas"], 2)
        self.assertEqual(resumen["campanias_distintas"], 3)
        self.assertEqual(resumen["productores_distintos"], 2)
        self.assertEqual(
            resumen["rango"],
            {
                "desde": (self.hoy - timedelta(days=10)).strftime("%d/%m/%Y"),
                "hasta": (self.hoy - timedelta(days=3)).strftime("%d/%m/%Y"),
            },
        )

    # ------------------------------------------------------------------ #
    # 307: responsable, densidad y método; ausente para el rol limitado
    # ------------------------------------------------------------------ #
    def test_307_actividades_responsable_densidad_y_metodo(self):
        self._entrar_admin()
        datos = self._json(self._previa("actividades"))
        por_fecha = {f["fecha"]: f for f in datos["filas"]}
        a1 = por_fecha[(self.hoy - timedelta(days=10)).strftime("%d/%m/%Y")]
        self.assertEqual(a1["responsable"], "admin_dashboard")
        self.assertEqual(a1["metodo"], "Arado")
        a3 = por_fecha[(self.hoy - timedelta(days=5)).strftime("%d/%m/%Y")]
        self.assertEqual(a3["responsable"], "coord_dashboard")
        a4 = por_fecha[(self.hoy - timedelta(days=8)).strftime("%d/%m/%Y")]
        self.assertEqual(a4["responsable"], "")  # registrado_por nulo
        a2 = por_fecha[(self.hoy - timedelta(days=3)).strftime("%d/%m/%Y")]
        self.assertEqual(a2["densidad"], "25.00 kg/ha")
        self.assertEqual(a2["metodo"], "")
        # El Técnico no recibe la columna ni en columnas ni en las filas
        self._entrar_tecnico()
        previa_tec = self._json(self._previa("actividades"))
        self.assertEqual(len(previa_tec["columnas"]), 12)
        for fila in previa_tec["filas"]:
            self.assertNotIn("responsable", fila)

    # ------------------------------------------------------------------ #
    # 308: Excel y PDF del reporte de actividades
    # ------------------------------------------------------------------ #
    def test_308_excel_y_pdf_de_actividades(self):
        self._entrar_admin()
        respuesta = self._exportar("actividades", "xlsx")
        self.assertEqual(respuesta.status_code, 200)
        libro = load_workbook(BytesIO(respuesta.content))
        self.assertEqual(libro.sheetnames, ["Resumen", "Datos"])
        resumen = libro["Resumen"]
        titulos = [celda.value for celda in resumen["A"] if celda.value]
        self.assertEqual(titulos[0], "Reporte de actividades")
        self.assertIn("Filtros: ninguno", titulos)
        self.assertIn("Generado por: admin_dashboard", titulos)
        self.assertIn("Actividades", titulos)
        self.assertIn("Tipo de actividad", titulos)
        self.assertIn(catalogo.AVISO_PRIVACIDAD, titulos)
        # El aviso de confidencialidad es exclusivo del reporte sensible
        self.assertNotIn(catalogo.AVISO_CONFIDENCIALIDAD, titulos)
        datos = libro["Datos"]
        self.assertEqual(
            [celda.value for celda in datos[1]],
            [c["etiqueta"] for c in catalogo.COLUMNAS_ACTIVIDADES],
        )
        cabeceras = [celda.value for celda in datos[1]]
        self.assertNotIn("Costo", cabeceras)
        self.assertNotIn("Observaciones", cabeceras)
        self.assertNotIn("Motivo de anulación", cabeceras)
        for prohibido in _PROHIBIDOS:
            for cabecera in cabeceras:
                self.assertNotIn(prohibido, str(cabecera).lower())
        # Fecha como fecha real y horas como número (nunca texto)
        columna_fecha = self._columna(datos, "Fecha")
        self.assertIsInstance(
            datos.cell(row=2, column=columna_fecha).value, datetime
        )
        columna_horas = self._columna(datos, "Horas")
        valores_horas = [
            datos.cell(row=fila, column=columna_horas).value
            for fila in range(2, datos.max_row + 1)
        ]
        self.assertIn(4.5, valores_horas)
        self.assertIn(2, valores_horas)
        # El PDF con su título, su tabla y sin el aviso confidencial
        pdf = self._exportar("actividades", "pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        texto = self._texto_pdf(pdf.content)
        self.assertIn("SIGPA-GA — Reporte de actividades", texto)
        self.assertIn("Tipo de actividad", texto)
        self.assertIn("Responsable", texto)
        self.assertIn(catalogo.AVISO_PRIVACIDAD, texto)
        self.assertNotIn("uso interno", texto)
        self.assertNotIn("95000001", texto)

    # ------------------------------------------------------------------ #
    # 309: el rango de auditoría es obligatorio y valida seis formas
    # ------------------------------------------------------------------ #
    def test_309_auditoria_rango_obligatorio_y_sus_400(self):
        self._entrar_admin()
        hoy = self.hoy.isoformat()
        casos = [
            (
                "",
                {
                    "fecha_desde": "El rango de fechas es obligatorio.",
                    "fecha_hasta": "El rango de fechas es obligatorio.",
                },
            ),
            (
                f"?fecha_desde={hoy}",
                {"fecha_hasta": "El rango de fechas es obligatorio."},
            ),
            (
                f"?fecha_hasta={hoy}",
                {"fecha_desde": "El rango de fechas es obligatorio."},
            ),
            (
                f"?fecha_desde={hoy}&fecha_hasta="
                f"{(self.hoy - timedelta(days=5)).isoformat()}",
                {"fecha_desde": "La fecha inicial no puede ser posterior "
                                "a la final."},
            ),
            (
                f"?fecha_desde={(self.hoy - timedelta(days=1)).isoformat()}"
                f"&fecha_hasta={(self.hoy + timedelta(days=1)).isoformat()}",
                {"fecha_hasta": "La fecha final no puede ser futura."},
            ),
            (
                f"?fecha_desde={(self.hoy - timedelta(days=400)).isoformat()}"
                f"&fecha_hasta={hoy}",
                {"fecha_hasta": "El rango admite como máximo 366 días."},
            ),
            (
                f"?fecha_desde=31-10-2026&fecha_hasta={hoy}",
                {"fecha_desde": "La fecha no es válida: usa el formato "
                                "AAAA-MM-DD."},
            ),
        ]
        for consulta, esperado in casos:
            respuesta = self._previa("auditoria", consulta)
            self.assertEqual(respuesta.status_code, 400, consulta)
            self.assertEqual(self._json(respuesta), esperado, consulta)
        # Frontera válida: exactamente 366 días (365 de diferencia)
        borde = self._previa(
            "auditoria",
            f"?fecha_desde={(self.hoy - timedelta(days=365)).isoformat()}"
            f"&fecha_hasta={hoy}",
        )
        self.assertEqual(borde.status_code, 200)

    # ------------------------------------------------------------------ #
    # 310: hora de Lima, «(sin usuario)», etiquetas y orden
    # ------------------------------------------------------------------ #
    def test_310_auditoria_filas_hora_lima_etiquetas_y_orden(self):
        self._entrar_admin()
        datos = self._json(self._previa("auditoria", self._rango))
        self.assertEqual(datos["total_filas"], 4)
        # La capa cruda devuelve la hora de Lima (la tabla guarda UTC)
        crudo = consultas.preparar(
            catalogo.obtener("auditoria"), self.admin,
            {
                "fecha_desde": self._desde,
                "fecha_hasta": self.hoy.isoformat(),
            },
        )
        fila_export = next(
            f for f in crudo["filas"] if f["registro_id"] == 77
        )
        evento = Auditoria.objects.get(pk=self.ev_exportar.pk)
        self.assertEqual(fila_export["fecha"], timezone.localtime(evento.fecha))
        self.assertEqual(fila_export["fecha"].tzinfo.key, "America/Lima")
        self.assertEqual(fila_export["fecha"].utcoffset(), timedelta(hours=-5))
        # Vista previa: dd/mm/aaaa HH:MM de Lima (entero → texto en la API)
        preview = next(f for f in datos["filas"] if f["registro_id"] == "77")
        self.assertEqual(
            preview["fecha"],
            timezone.localtime(evento.fecha).strftime("%d/%m/%Y %H:%M"),
        )
        # Evento sin usuario → «(sin usuario)» con su etiqueta
        sin_usuario = [
            f for f in datos["filas"] if f["usuario"] == "(sin usuario)"
        ]
        self.assertEqual(len(sin_usuario), 1)
        self.assertEqual(sin_usuario[0]["accion"], "Iniciar sesión")
        # Etiquetas de acción, nunca códigos crudos
        acciones = {f["accion"] for f in datos["filas"]}
        self.assertIn("Exportar", acciones)
        self.assertIn("Crear", acciones)
        self.assertNotIn("EXPORTAR", acciones)
        self.assertNotIn("CREAR", acciones)
        # Orden: el evento más reciente (el LOGIN de este test) primero
        self.assertEqual(datos["filas"][0]["usuario"], "admin_dashboard")
        self.assertEqual(datos["filas"][0]["accion"], "Iniciar sesión")

    # ------------------------------------------------------------------ #
    # 311: los filtros compartidos acotan igual en pantalla y en reporte
    # ------------------------------------------------------------------ #
    def test_311_auditoria_filtros_compartidos_coinciden_con_la_pantalla(self):
        self._entrar_admin()
        parejas = [
            f"usuario={self.coordinador.pk}",
            "accion=EXPORTAR",
            "tabla=cosas",
            "registro=77",
            "ip=10.0.0.7",
            "modulo=informes_esp",
        ]
        for filtro in parejas:
            pantalla = self._json(self._api("get", f"/api/auditoria/?{filtro}"))
            previa = self._json(
                self._previa("auditoria", f"{self._rango}&{filtro}")
            )
            self.assertGreater(pantalla["count"], 0, filtro)
            self.assertEqual(previa["total_filas"], pantalla["count"], filtro)
        # El mismo registro identificado en ambas capas
        pantalla = self._json(self._api("get", "/api/auditoria/?registro=77"))
        self.assertEqual(
            [f["registro_id"] for f in pantalla["results"]], [77]
        )
        previa = self._json(
            self._previa("auditoria", f"{self._rango}&registro=77")
        )
        self.assertEqual(
            [f["registro_id"] for f in previa["filas"]], ["77"]
        )

    # ------------------------------------------------------------------ #
    # 312: el detalle se reduce a un blanco seguro (sin valores libres)
    # ------------------------------------------------------------------ #
    def test_312_auditoria_detalle_blanco_segura(self):
        self._entrar_admin()
        datos = self._json(self._previa("auditoria", self._rango))
        por_registro = {
            f["registro_id"]: f for f in datos["filas"] if f["registro_id"]
        }
        # Claves seguras con su valor; texto libre y dicts solo con nombre
        self.assertEqual(
            por_registro["77"]["detalle"],
            "filas: 12 · tipo: xlsx · Campos: filtros, motivo",
        )
        self.assertEqual(
            por_registro["5"]["detalle"],
            "estado: ACTIVO · Campos: nota",
        )
        # «resumen» (barrido de alertas) jamás se muestra
        self.assertNotIn("alertas", por_registro["77"]["detalle"])
        bruto = json.dumps(datos, ensure_ascii=False)
        self.assertNotIn("Texto libre confidencial", bruto)
        self.assertNotIn("No debe aparecer", bruto)
        # Sin detalle → celda vacía
        sin_usuario = next(
            f for f in datos["filas"] if f["usuario"] == "(sin usuario)"
        )
        self.assertEqual(sin_usuario["detalle"], "")

    # ------------------------------------------------------------------ #
    # 313: resumen por acción y módulo, sin usuario y rango
    # ------------------------------------------------------------------ #
    def test_313_auditoria_resumen_por_accion_modulo_y_rango(self):
        self._entrar_admin()
        datos = self._json(self._previa("auditoria", self._rango))
        resumen = datos["resumen"]
        en_rango = Auditoria.objects.filter(
            fecha__date__gte=self._desde, fecha__date__lte=self.hoy.isoformat()
        )
        self.assertEqual(resumen["total"], en_rango.count())
        self.assertEqual(resumen["sin_usuario"], 1)
        self.assertEqual(
            resumen["sin_usuario"], en_rango.filter(usuario__isnull=True).count()
        )
        self.assertIn(
            {"etiqueta": "Exportar", "cantidad": 1}, resumen["por_accion"]
        )
        self.assertIn(
            {"etiqueta": "Crear", "cantidad": 1}, resumen["por_accion"]
        )
        # El LOGIN de este test y el evento sin usuario
        self.assertIn(
            {"etiqueta": "Iniciar sesión", "cantidad": 2},
            resumen["por_accion"],
        )
        self.assertIn(
            {"etiqueta": "informes_esp", "cantidad": 1}, resumen["por_modulo"]
        )
        self.assertIn(
            {"etiqueta": "sesiones_prueba", "cantidad": 1},
            resumen["por_modulo"],
        )
        minimo = timezone.localtime(en_rango.order_by("fecha").first().fecha)
        maximo = timezone.localtime(en_rango.order_by("-fecha").first().fecha)
        self.assertEqual(
            resumen["rango"]["desde"], minimo.strftime("%d/%m/%Y")
        )
        self.assertEqual(resumen["rango"]["hasta"], maximo.strftime("%d/%m/%Y"))

    # ------------------------------------------------------------------ #
    # 314: Excel de auditoría con su aviso y la hora de Lima
    # ------------------------------------------------------------------ #
    def test_314_excel_de_auditoria_con_aviso_y_hora_de_lima(self):
        self._entrar_admin()
        respuesta = self._exportar("auditoria", "xlsx", self._rango)
        self.assertEqual(respuesta.status_code, 200)
        libro = load_workbook(BytesIO(respuesta.content))
        self.assertEqual(libro.sheetnames, ["Resumen", "Datos"])
        resumen = libro["Resumen"]
        titulos = [celda.value for celda in resumen["A"] if celda.value]
        self.assertEqual(titulos[0], "Reporte de auditoría")
        self.assertIn(catalogo.AVISO_PRIVACIDAD, titulos)
        # El aviso de confidencialidad va en la hoja Resumen
        self.assertIn(catalogo.AVISO_CONFIDENCIALIDAD, titulos)
        self.assertIn("Eventos", titulos)
        self.assertIn("Sin usuario", titulos)
        self.assertIn("Rango de fechas", titulos)
        self.assertIn("Acción", titulos)
        self.assertIn("Módulo", titulos)
        datos = libro["Datos"]
        self.assertEqual(
            [celda.value for celda in datos[1]],
            [c["etiqueta"] for c in catalogo.COLUMNAS_AUDITORIA],
        )
        columna_fecha = self._columna(datos, "Fecha y hora")
        columna_ip = self._columna(datos, "IP")
        # Sin huso: openpyxl rechazaría los datetimes aware
        for fila in range(2, datos.max_row + 1):
            valor = datos.cell(row=fila, column=columna_fecha).value
            self.assertIsInstance(valor, datetime)
            self.assertIsNone(valor.tzinfo)
        fila_ev = next(
            fila
            for fila in range(2, datos.max_row + 1)
            if datos.cell(row=fila, column=columna_ip).value == "10.0.0.5"
        )
        evento = Auditoria.objects.get(pk=self.ev_exportar.pk)
        esperado = timezone.localtime(evento.fecha).replace(tzinfo=None)
        celda = datos.cell(row=fila_ev, column=columna_fecha).value
        self.assertLess(abs((celda - esperado).total_seconds()), 1)

    # ------------------------------------------------------------------ #
    # 315: PDF de auditoría con el aviso en el relato y en el pie
    # ------------------------------------------------------------------ #
    def test_315_pdf_de_auditoria_con_confidencialidad_en_relato_y_pie(self):
        self._entrar_admin()
        respuesta = self._exportar("auditoria", "pdf", self._rango)
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content
        self.assertTrue(contenido.startswith(b"%PDF"))
        texto = self._texto_pdf(contenido)
        self.assertIn("SIGPA-GA — Reporte de auditoría", texto)
        self.assertIn(catalogo.AVISO_CONFIDENCIALIDAD, texto)
        # Una vez en el relato y otra en el pie de cada página
        self.assertGreaterEqual(texto.count("uso interno"), 2)
        self.assertIn("(sin usuario)", texto)
        self.assertIn("Acción", texto)
        self.assertIn("Módulo", texto)
        self.assertRegex(texto, r"Página 1 de \d+")

    # ------------------------------------------------------------------ #
    # 316: exportar los tipos nuevos deja su evento con detalle seguro
    # ------------------------------------------------------------------ #
    def test_316_exportar_de_los_tipos_nuevos_registra_su_evento(self):
        self._entrar_admin()
        base = Auditoria.objects.count()
        for tipo in ("actividades", "auditoria"):
            filtros = self._rango if tipo == "auditoria" else ""
            respuesta = self._exportar(tipo, "xlsx", filtros)
            self.assertEqual(respuesta.status_code, 200, tipo)
        self.assertEqual(Auditoria.objects.count(), base + 2)
        nuevos = list(Auditoria.objects.order_by("-id")[:2])
        self.assertEqual(
            [e.accion for e in nuevos], ["EXPORTAR", "EXPORTAR"]
        )
        for evento in nuevos:
            self.assertEqual(evento.modulo, "reportes")
            self.assertEqual(evento.usuario_id, self.admin.pk)
        por_tipo = {e.detalle["tipo"]: e.detalle for e in nuevos}
        self.assertEqual(por_tipo["actividades"]["formato"], "xlsx")
        self.assertEqual(por_tipo["actividades"]["filtros"], {})
        self.assertEqual(por_tipo["auditoria"]["formato"], "xlsx")
        self.assertEqual(
            por_tipo["auditoria"]["filtros"],
            {"fecha_desde": self._desde, "fecha_hasta": self.hoy.isoformat()},
        )
        # Al re-exportarlo, su propio detalle es seguro y legible
        previa = self._json(self._previa("auditoria", self._rango))
        detalles = [
            f["detalle"]
            for f in previa["filas"]
            if f["detalle"] and "tipo: auditoria" in f["detalle"]
        ]
        self.assertEqual(len(detalles), 1)
        self.assertRegex(
            detalles[0],
            r"^filas: \d+ · formato: xlsx · tipo: auditoria · Campos: filtros$",
        )
        self.assertNotIn("cultivo", detalles[0])

    # ------------------------------------------------------------------ #
    # 317: límites de filas y formato también para los tipos nuevos
    # ------------------------------------------------------------------ #
    def test_317_limites_y_formato_compartidos_de_los_tipos_nuevos(self):
        self._entrar_admin()
        # Formato desconocido → 400 con el mensaje compartido
        for tipo in ("actividades", "auditoria"):
            respuesta = self._api(
                "post", f"/api/reportes/{tipo}/exportar/", {"formato": "csv"}
            )
            self.assertEqual(respuesta.status_code, 400, tipo)
            self.assertEqual(
                self._json(respuesta), {"formato": "Use xlsx o pdf."}, tipo
            )
        # Límite de filas del PDF también en auditoría (4 eventos > 2)
        with patch("reportes.catalogo.LIMITE_PDF_FILAS", 2):
            respuesta = self._exportar("auditoria", "pdf", self._rango)
            self.assertEqual(respuesta.status_code, 400)
            detalle = self._json(respuesta)["detail"]
            self.assertIn("El reporte tiene 4 filas", detalle)
            self.assertIn("máximo para PDF es 2", detalle)
            self.assertNotIn("Content-Disposition", respuesta)
            # La vista previa no se ve afectada por el límite de descarga
            self.assertEqual(
                self._previa("auditoria", self._rango).status_code, 200
            )
        # Límite de Excel también en actividades (4 filas > 1)
        with patch("reportes.catalogo.LIMITE_EXCEL_FILAS", 1):
            respuesta = self._exportar("actividades", "xlsx")
            self.assertEqual(respuesta.status_code, 400)
            detalle = self._json(respuesta)["detail"]
            self.assertIn("El reporte tiene 4 filas", detalle)
            self.assertIn("máximo para XLSX es 1", detalle)
            self.assertIn("Afina los filtros", detalle)
            self.assertNotIn("Content-Disposition", respuesta)
