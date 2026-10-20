"""Pruebas de la Semana 16: panel de indicadores (HU-133..HU-140).

Numeración 263-279 (17 pruebas → 279 en total; el repositorio llegaba a
262 con la Semana 15). Cubren las tarjetas del resumen y la franja de
alertas por tipo, la superficie de las campañas activas, la serie por
estado (y su coherencia con el endpoint de periodo), las aptas para
entrenar frente al SQL literal de vw_dataset_entrenamiento, la
producción agrupada por cultivo y distrito con el rendimiento
PONDERADO, el alcance del Técnico en las cuatro lecturas, las marcas de
provisional y pocos datos, el vacío sin datos (null, no cero), la
consistencia con el listado de producciones, la hora de Lima, el número
fijo de consultas, los 401/403/405 —incluido el portón de cambio
obligatorio de contraseña—, el recuento de 32 tablas y 25 triggers, el
recorrido de rutas del panel y los filtros con sus 400.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from campanias.models import Campania
from catalogos.models import Cultivo, Unidad, Variedad
from produccion.models import Produccion
from productores.models import (
    AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia,
)
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from alertas.models import Alerta

_TZ_LIMA = ZoneInfo("America/Lima")

# Número fijo de consultas por lectura (se mide en la prueba 275: todo
# ocurre en la vista; si un cambio de código añade una consulta, salta)
_CONSULTAS_RESUMEN = 12
_CONSULTAS_SERIE = 4
_CONSULTAS_PRODUCCION = 5
_CONSULTAS_FILTROS = 8

# Tablas propias del diseño (32): las de DB_sql menos las de Django, más
# la de la S20 y las 3 de Machine Learning de la S22
_TABLAS_PROPIAS = {
    "actividades", "agentes", "alertas", "asignaciones_tecnico", "auditoria",
    "campanias", "clima", "comunidades", "cultivos", "distritos",
    "entrenamientos_ml", "etapas_fenologicas", "importaciones", "incidencias",
    "modelos_ml", "parametros_sistema", "parcelas", "permisos", "predicciones",
    "producciones", "productores", "provincias",
    "recursos", "roles", "roles_permisos", "seguimiento_etapas",
    "tipos_actividad", "tipos_incidencia", "unidades", "uso_recursos",
    "usuarios", "variedades",
}

# Tablas que añade Django (no son del diseño)
_TABLAS_DJANGO = {
    "auth_group", "auth_group_permissions", "auth_permission",
    "django_admin_log", "django_content_type", "django_migrations",
    "django_session", "token_blacklist_blacklistedtoken",
    "token_blacklist_outstandingtoken",
}


class DashboardBase(TestCase):
    """Tres cuentas, dos provincias con sus distritos/comunidades, tres
    cultivos, dos productores (el Técnico tiene asignado solo al
    primero) y un parque de campañas con producciones calculadas por los
    mismos triggers de la base."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_dashboard", email="", password="AdminDash2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_dashboard", password="CoordDash2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_dashboard", password="TecDash2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )

        self.provincia = Provincia.objects.create(nombre="Prov S16")
        self.provincia_b = Provincia.objects.create(nombre="Prov S16-B")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S16"
        )
        self.distrito_b = Distrito.objects.create(
            provincia=self.provincia_b, nombre="Distrito S16-B"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S16"
        )
        self.comunidad_b = Comunidad.objects.create(
            distrito=self.distrito_b, nombre="Comunidad S16-B"
        )

        self.cultivo = Cultivo.objects.create(nombre="Quinua S16")
        self.cultivo_canihua = Cultivo.objects.create(nombre="Cañihua S16")
        self.cultivo_maiz = Cultivo.objects.create(nombre="Maíz S16")
        self.variedad = Variedad.objects.create(
            cultivo=self.cultivo, nombre="Real S16"
        )
        self.variedad_canihua = Variedad.objects.create(
            cultivo=self.cultivo_canihua, nombre="Blanca S16"
        )
        self.variedad_maiz = Variedad.objects.create(
            cultivo=self.cultivo_maiz, nombre="Dura S16"
        )
        self.kg = Unidad.objects.get(nombre="Kilogramo")

        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="95000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p2 = Productor.objects.create(
            nombres="Dos", apellidos="Beta", dni="95000002",
            comunidad=self.comunidad_b, creado_por=self.admin,
        )
        self.p3 = Productor.objects.create(
            nombres="Tres", apellidos="Gama", dni="95000003",
            comunidad=self.comunidad, creado_por=self.admin,
            estado=Productor.ESTADO_INACTIVO,
        )
        AsignacionTecnico.objects.create(tecnico=self.tecnico, productor=self.p1)

        self.periodo = "2026-2027"
        self.hoy = timezone_localdate()

        # Campañas del productor asignado (una por parcela: la activa
        # ocupa la parcela) — quinua con 3 cosechadas y 1 en revisión
        self.c1 = self._campania(self.p1, self.cultivo, parcela="pa1")
        self.c2 = self._campania(
            self.p1, self.cultivo, parcela="pa2",
            superficie_sembrada_ha=Decimal("3.00"),
        )
        self.c3 = self._campania(
            self.p1, self.cultivo, parcela="pa3",
            superficie_sembrada_ha=Decimal("2.00"),
        )
        self.c8 = self._campania(self.p1, self.cultivo, parcela="pa4")
        self.c5 = self._campania(
            self.p1, self.cultivo, parcela="pa5",
            estado=Campania.ESTADO_PLANIFICADA,
            superficie_sembrada_ha=Decimal("1.00"),
        )
        self.c9 = self._campania(
            self.p1, self.cultivo, parcela="pa6", periodo="2025-2026"
        )
        self.c6 = self._campania(self.p1, self.cultivo_canihua, parcela="pa7")
        self.c7 = self._campania(self.p1, self.cultivo_canihua, parcela="pa8")
        # Campaña del segundo productor: fuera del ámbito del Técnico
        self.c4 = self._campania(self.p2, self.cultivo_maiz, parcela="pa9")

        # Producciones: los triggers calculan kg, rendimiento y revisión
        self._producir(self.c1, "1.00", "150")   # 150.00 kg/ha
        self._producir(self.c2, "3.00", "750")   # 250.00 kg/ha
        self._producir(self.c3, "2.00", "400")   # 200.00 kg/ha
        self._producir(self.c8, "1.00", "50")    # 50.00 kg/ha → revisión
        self._producir(self.c6, "1.50", "500")   # 333.33 kg/ha
        self._producir(self.c7, "1.00", "300")   # 300.00 kg/ha
        self._producir(self.c4, "1.00", "300")   # 300.00 kg/ha (ajena)
        self.assertTrue(
            Produccion.objects.get(campania=self.c8).requiere_revision
        )
        # Cerradas: una apta para entrenar y otra excluida tras revisión
        self._sql(
            "UPDATE producciones SET incluir_en_entrenamiento = FALSE"
            " WHERE campania_id = %s", [self.c7.pk],
        )
        self._cerrar(self.c6)
        self._cerrar(self.c7)
        # Cancelada en otro período (aparece en la serie de estados)
        self._sql(
            "UPDATE campanias SET estado = 'CANCELADA' WHERE id = %s",
            [self.c9.pk],
        )

        # Alertas: 2 pendientes del productor asignado, 1 pendiente ajena
        # y 1 atendida (la insignia y la franja se prueban con ellas)
        self.a1 = self._alerta(self.c1, Alerta.TIPO_SIN_ACTIVIDAD)
        self.a2 = self._alerta(self.c2, Alerta.TIPO_RENDIMIENTO_BAJO)
        self.a4 = self._alerta(self.c3, Alerta.TIPO_SIN_ACTIVIDAD)
        self.a3 = self._alerta(self.c4, Alerta.TIPO_SIN_ACTIVIDAD)
        self.a4.atendida = True
        self.a4.save(update_fields=("atendida",))

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_dashboard", "AdminDash2026!")

    def _entrar_coordinador(self):
        self._entrar("coord_dashboard", "CoordDash2026!")

    def _entrar_tecnico(self):
        self._entrar("tec_dashboard", "TecDash2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _parcela(self, productor, clave):
        parcela = Parcela.objects.create(
            productor=productor, comunidad=productor.comunidad,
            superficie_ha="4.00", altitud_msnm=3900,
            tipo_suelo="FRANCO", pendiente="SUAVE",
            disponibilidad_agua="MEDIA", sistema_riego="GOTEO",
        )
        parcela.refresh_from_db()
        return parcela

    def _campania(self, productor, cultivo, parcela=None, **extra):
        variedades = {
            self.cultivo: self.variedad,
            self.cultivo_canihua: self.variedad_canihua,
            self.cultivo_maiz: self.variedad_maiz,
        }
        parcela = self._parcela(productor, parcela)
        datos = {
            "periodo": self.periodo,
            "parcela": parcela,
            "cultivo": cultivo,
            "variedad": variedades[cultivo],
            "fecha_inicio": self.hoy - timedelta(days=60),
            "fecha_fin_prevista": self.hoy + timedelta(days=120),
            "estado": Campania.ESTADO_EN_PRODUCCION,
            "superficie_sembrada_ha": Decimal("1.50"),
        }
        datos.update(extra)
        campania = Campania.objects.create(**datos)
        campania.refresh_from_db()
        return campania

    def _producir(self, campania, superficie, kilos):
        """Registro de producción por SQL crudo: los triggers de la base
        calculan kg, rendimiento y la marca de revisión, y pasan la
        campaña a COSECHADA (los mismos caminos que la API)."""
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO producciones (campania_id, fecha_cosecha,"
                " superficie_cosechada_ha, cantidad_producida, unidad_id,"
                " produccion_kg, rendimiento_kg_ha, observaciones)"
                " VALUES (%s, %s, %s, %s, %s, 0, 0, '')",
                [
                    campania.pk, self.hoy - timedelta(days=5),
                    Decimal(superficie), Decimal(kilos), self.kg.pk,
                ],
            )
        campania.refresh_from_db()
        return campania

    def _alerta(self, campania, tipo):
        return Alerta.objects.create(
            productor=campania.parcela.productor,
            campania=campania,
            tipo=tipo,
            mensaje=f"Alerta de prueba {tipo} · campaña {campania.pk}",
        )

    def _sql(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            cursor.execute(consulta, parametros or [])

    def _cerrar(self, campania):
        self._sql(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [campania.pk],
        )
        campania.refresh_from_db()

    def _panel(self, url, metodo="get"):
        return self._api(metodo, url)


def timezone_localdate():
    return datetime.now(_TZ_LIMA).date()


class ResumenTests(DashboardBase):
    """Pruebas 263-266: tarjetas, superficie, serie y aptas."""

    # ------------------------------------------------------------------ #
    # 263: tarjetas de productores, alertas del alcance y franja por tipo
    # ------------------------------------------------------------------ #
    def test_263_tarjetas_de_productores_superficie_y_alertas(self):
        self._entrar_admin()
        datos = self._json(self._panel("/api/dashboard/resumen/"))
        self.assertEqual(
            datos["productores"],
            {"activos": 2, "inactivos": 1, "con_campania_activa": 2},
        )
        self.assertEqual(datos["alertas"], {"total": 4, "pendientes": 3})
        self.assertEqual(datos["revisiones_pendientes"], 1)
        self.assertEqual(datos["aptas_entrenar"], 1)
        # Franja de alertas: el resumen de la insignia ahora clasifica
        # por tipo (los tres con ceros donde no hay)
        franja = self._json(self._panel("/api/alertas/resumen/"))
        self.assertEqual(franja["pendientes"], 3)
        self.assertEqual(
            franja["por_tipo"],
            {"INCIDENCIA_SEVERA": 0, "SIN_ACTIVIDAD": 2, "RENDIMIENTO_BAJO": 1},
        )

    # ------------------------------------------------------------------ #
    # 264: la superficie sembrada es la de las campañas ACTIVAS
    # ------------------------------------------------------------------ #
    def test_264_superficie_de_las_campanias_activas(self):
        self._entrar_admin()
        datos = self._json(self._panel("/api/dashboard/resumen/"))
        # c5 planificada (1.00) + c1 (1.50), c2 (3.00), c3 (2.00), c8
        # (1.50) y c4 (1.50) cosechadas: las cerradas (c6, c7) y la
        # cancelada (c9) no cuentan
        self.assertEqual(datos["superficie_sembrada_ha"], "10.50")
        self._entrar_tecnico()
        datos = self._json(self._panel("/api/dashboard/resumen/"))
        self.assertEqual(datos["superficie_sembrada_ha"], "9.00")

    # ------------------------------------------------------------------ #
    # 265: la serie por estado sale completa, con ceros, y el periodo filtra
    # ------------------------------------------------------------------ #
    def test_265_campanias_por_estado_con_ceros_y_periodo(self):
        self._entrar_admin()
        resumen = self._json(self._panel("/api/dashboard/resumen/"))
        serie = self._json(self._panel("/api/dashboard/campanias-estado/"))
        self.assertIsNone(serie["periodo"])
        self.assertEqual(
            serie["estados"],
            {"PLANIFICADA": 1, "EN_PRODUCCION": 0, "COSECHADA": 5,
             "CERRADA": 2, "CANCELADA": 1},
        )
        self.assertEqual(resumen["campanias_por_estado"], serie["estados"])
        # Con periodo: solo la cancelada del periodo viejo; los demás a cero
        con_periodo = self._json(
            self._panel("/api/dashboard/campanias-estado/?periodo=2025-2026")
        )
        self.assertEqual(con_periodo["periodo"], "2025-2026")
        self.assertEqual(
            con_periodo["estados"],
            {"PLANIFICADA": 0, "EN_PRODUCCION": 0, "COSECHADA": 0,
             "CERRADA": 0, "CANCELADA": 1},
        )
        # Periodo sin campañas: serie a cero, no error
        vacio = self._json(
            self._panel("/api/dashboard/campanias-estado/?periodo=1999-2000")
        )
        self.assertEqual(sum(vacio["estados"].values()), 0)

    # ------------------------------------------------------------------ #
    # 266: aptas para entrenar = el WHERE literal de la vista del diseño
    # ------------------------------------------------------------------ #
    def test_266_aptas_para_entrenar_igual_que_la_vista_literal(self):
        ruta = (
            Path(__file__).resolve().parents[2]
            / "DB_sql"
            / "02_reglas_y_vista.sql"
        )
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        marca = "CREATE VIEW vw_dataset_entrenamiento AS"
        inicio = texto.index(marca) + len(marca)
        fin = texto.index("COMMENT ON VIEW", inicio)
        consulta = texto[inicio:fin].strip().rstrip(";").strip()
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM ({consulta}) AS vista")
            filas_vista = cursor.fetchone()[0]
        self._entrar_admin()
        datos = self._json(self._panel("/api/dashboard/resumen/"))
        self.assertEqual(datos["aptas_entrenar"], filas_vista)
        self.assertEqual(datos["aptas_entrenar"], 1)
        self._entrar_tecnico()
        datos = self._json(self._panel("/api/dashboard/resumen/"))
        self.assertEqual(datos["aptas_entrenar"], 1)


class ProduccionTests(DashboardBase):
    """Pruebas 267-269 y 271-273: agrupaciones y consistencia."""

    # ------------------------------------------------------------------ #
    # 267: producción agrupada por cultivo
    # ------------------------------------------------------------------ #
    def test_267_produccion_agrupada_por_cultivo(self):
        self._entrar_admin()
        datos = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=cultivo")
        )
        self.assertEqual(datos["agrupar"], "cultivo")
        filas = {f["etiqueta"]: f for f in datos["filas"]}
        self.assertEqual(
            set(filas), {"Quinua S16", "Cañihua S16", "Maíz S16"}
        )
        quinua = filas["Quinua S16"]
        self.assertEqual(quinua["campanias"], 3)   # c8 está en revisión
        self.assertEqual(quinua["superficie_ha"], "6.00")
        self.assertEqual(quinua["produccion_kg"], "1300.00")
        self.assertEqual(datos["totales"]["campanias"], 6)
        self.assertEqual(datos["totales"]["produccion_kg"], "2400.00")

    # ------------------------------------------------------------------ #
    # 268: producción agrupada por distrito
    # ------------------------------------------------------------------ #
    def test_268_produccion_agrupada_por_distrito(self):
        self._entrar_admin()
        datos = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=distrito")
        )
        filas = {f["etiqueta"]: f for f in datos["filas"]}
        self.assertEqual(
            set(filas), {"Distrito S16", "Distrito S16-B"}
        )
        self.assertEqual(filas["Distrito S16"]["campanias"], 5)
        self.assertEqual(filas["Distrito S16"]["superficie_ha"], "8.50")
        self.assertEqual(filas["Distrito S16"]["produccion_kg"], "2100.00")
        self.assertEqual(filas["Distrito S16-B"]["campanias"], 1)

    # ------------------------------------------------------------------ #
    # 269: el rendimiento que manda es el PONDERADO, no la media simple
    # ------------------------------------------------------------------ #
    def test_269_rendimiento_ponderado_frente_a_media_simple(self):
        self._entrar_admin()
        datos = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=cultivo")
        )
        quinua = next(f for f in datos["filas"] if f["etiqueta"] == "Quinua S16")
        # 1300 kg ÷ 6.00 ha = 216.67 kg/ha; la media de 150/250/200 = 200
        self.assertEqual(quinua["rendimiento_kg_ha"], "216.67")
        self.assertEqual(quinua["rendimiento_promedio_kg_ha"], "200.00")
        self.assertNotEqual(
            quinua["rendimiento_kg_ha"], quinua["rendimiento_promedio_kg_ha"]
        )
        total = datos["totales"]
        self.assertEqual(total["superficie_ha"], "9.50")
        self.assertEqual(total["rendimiento_kg_ha"], "252.63")
        # El total también pondera: 2400 ÷ 9.50 = 252.63 (la media
        # simple de las 6 filas no daría ese número)

    # ------------------------------------------------------------------ #
    # 271: marcas de provisional y pocos datos
    # ------------------------------------------------------------------ #
    def test_271_marcas_de_provisional_y_pocos_datos(self):
        self._entrar_admin()
        datos = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=cultivo")
        )
        filas = {f["etiqueta"]: f for f in datos["filas"]}
        # Quinua: 3 campañas (no es «pocos datos») y ninguna cerrada
        self.assertFalse(filas["Quinua S16"]["pocos_datos"])
        self.assertTrue(filas["Quinua S16"]["provisional"])
        # Cañihua: 2 campañas (<3) pero las dos cerradas: dato final
        self.assertTrue(filas["Cañihua S16"]["pocos_datos"])
        self.assertFalse(filas["Cañihua S16"]["provisional"])
        self.assertTrue(filas["Maíz S16"]["pocos_datos"])

    # ------------------------------------------------------------------ #
    # 272: sin datos, los totales salen en null —no en cero—
    # ------------------------------------------------------------------ #
    def test_272_vacio_sin_datos_con_totales_null(self):
        self._entrar_admin()
        datos = self._json(
            self._panel(
                "/api/dashboard/produccion/"
                f"?cultivo={self.cultivo_maiz.pk}&distrito={self.distrito.pk}"
            )
        )
        self.assertEqual(datos["filas"], [])
        self.assertEqual(datos["totales"]["campanias"], 0)
        self.assertIsNone(datos["totales"]["superficie_ha"])
        self.assertIsNone(datos["totales"]["produccion_kg"])
        self.assertIsNone(datos["totales"]["rendimiento_kg_ha"])

    # ------------------------------------------------------------------ #
    # 273: los mismos filtros dan los mismos números que el listado
    # ------------------------------------------------------------------ #
    def test_273_consistencia_con_el_listado_de_producciones(self):
        self._entrar_admin()
        panel = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=cultivo")
        )
        respuesta_listado = self._api(
            "get", "/api/producciones/?requiere_revision=false"
        )
        self.assertEqual(
            respuesta_listado.status_code, 200, respuesta_listado.content[:400]
        )
        listado = self._json(respuesta_listado)
        self.assertEqual(panel["totales"]["campanias"], listado["count"])
        suma = sum(
            Decimal(f["produccion_kg"]) for f in listado["results"]
        )
        self.assertEqual(panel["totales"]["produccion_kg"], str(suma))
        # Filtro de distrito en común: la fila del panel y las filas del
        # listado coinciden
        panel_b = self._json(
            self._panel(
                f"/api/dashboard/produccion/?agrupar=cultivo"
                f"&distrito={self.distrito_b.pk}"
            )
        )
        listado_b = self._json(
            self._api(
                "get",
                f"/api/producciones/?distrito={self.distrito_b.pk}"
                "&requiere_revision=false",
            )
        )
        self.assertEqual(panel_b["totales"]["campanias"], listado_b["count"])
        self.assertEqual(len(panel_b["filas"]), len(listado_b["results"]))
        self.assertEqual(
            panel_b["filas"][0]["produccion_kg"],
            listado_b["results"][0]["produccion_kg"],
        )


class AlcanceTests(DashboardBase):
    """Pruebas 270, 274-276 y 278-279: quién ve qué, hora, consultas,
    permisos, recorrido y filtros."""

    # ------------------------------------------------------------------ #
    # 270: el Técnico solo agrega SUS productores en las cuatro lecturas
    # ------------------------------------------------------------------ #
    def test_270_alcance_del_tecnico_en_las_cuatro_lecturas(self):
        self._entrar_admin()
        resumen_admin = self._json(self._panel("/api/dashboard/resumen/"))
        # generado_en es el reloj del momento: fuera de la comparación
        # (el de la hora de Lima lo cubre la 274)
        resumen_admin.pop("generado_en")
        serie_admin = self._json(self._panel("/api/dashboard/campanias-estado/"))
        prod_admin = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=cultivo")
        )
        filtros_admin = self._json(self._panel("/api/dashboard/filtros/"))
        # El Coordinador no se limita: mismos números que el Admin
        self._entrar_coordinador()
        resumen_coord = self._json(self._panel("/api/dashboard/resumen/"))
        resumen_coord.pop("generado_en")
        self.assertEqual(resumen_coord, resumen_admin)
        self.assertEqual(
            self._json(self._panel("/api/dashboard/campanias-estado/")),
            serie_admin,
        )
        self._entrar_tecnico()
        resumen_tec = self._json(self._panel("/api/dashboard/resumen/"))
        self.assertEqual(
            resumen_tec["productores"],
            {"activos": 1, "inactivos": 0, "con_campania_activa": 1},
        )
        self.assertEqual(resumen_tec["alertas"], {"total": 3, "pendientes": 2})
        self.assertEqual(resumen_tec["superficie_sembrada_ha"], "9.00")
        serie_tec = self._json(self._panel("/api/dashboard/campanias-estado/"))
        self.assertEqual(
            serie_tec["estados"],
            {"PLANIFICADA": 1, "EN_PRODUCCION": 0, "COSECHADA": 4,
             "CERRADA": 2, "CANCELADA": 1},
        )
        prod_tec = self._json(
            self._panel("/api/dashboard/produccion/?agrupar=cultivo")
        )
        etiquetas_tec = {f["etiqueta"] for f in prod_tec["filas"]}
        self.assertNotIn("Maíz S16", etiquetas_tec)
        self.assertEqual(
            etiquetas_tec, {f["etiqueta"] for f in prod_admin["filas"]}
            - {"Maíz S16"}
        )
        filtros_tec = self._json(self._panel("/api/dashboard/filtros/"))
        self.assertEqual(
            [c["nombre"] for c in filtros_tec["comunidades"]],
            ["Comunidad S16"],
        )
        self.assertEqual(
            [c["nombre"] for c in filtros_admin["comunidades"]],
            ["Comunidad S16", "Comunidad S16-B"],
        )

    # ------------------------------------------------------------------ #
    # 274: generado_en es la hora de Lima, con su huso
    # ------------------------------------------------------------------ #
    def test_274_generado_en_es_la_hora_de_lima(self):
        self._entrar_admin()
        fija = datetime(2026, 1, 20, 10, 30, tzinfo=_TZ_LIMA)
        with patch("dashboard.views.ahora_lima", return_value=fija):
            datos = self._json(self._panel("/api/dashboard/resumen/"))
        self.assertEqual(datos["generado_en"], "2026-01-20T10:30:00-05:00")
        # Sin parchear: sigue llevando el huso de Lima
        datos = self._json(self._panel("/api/dashboard/resumen/"))
        instante = datetime.fromisoformat(datos["generado_en"])
        self.assertEqual(instante.utcoffset(), timedelta(hours=-5))
        self.assertEqual(instante.date(), datetime.now(_TZ_LIMA).date())

    # ------------------------------------------------------------------ #
    # 275: número fijo de consultas: todo ocurre en la vista, sin N+1
    # ------------------------------------------------------------------ #
    def test_275_numero_fijo_de_consultas(self):
        self._entrar_admin()
        with CaptureQueriesContext(connection) as resumen:
            self._panel("/api/dashboard/resumen/")
        self.assertEqual(len(resumen), _CONSULTAS_RESUMEN)
        with CaptureQueriesContext(connection) as serie:
            self._panel("/api/dashboard/campanias-estado/")
        self.assertEqual(len(serie), _CONSULTAS_SERIE)
        with CaptureQueriesContext(connection) as produccion:
            self._panel("/api/dashboard/produccion/?agrupar=distrito")
        self.assertEqual(len(produccion), _CONSULTAS_PRODUCCION)
        with CaptureQueriesContext(connection) as filtros:
            self._panel("/api/dashboard/filtros/")
        self.assertEqual(len(filtros), _CONSULTAS_FILTROS)

    # ------------------------------------------------------------------ #
    # 276: 401 sin sesión, 403 sin permiso o con clave por cambiar, 405
    # ------------------------------------------------------------------ #
    def test_276_401_403_405_y_porton_de_clave(self):
        urls = (
            "/api/dashboard/resumen/",
            "/api/dashboard/campanias-estado/",
            "/api/dashboard/produccion/",
            "/api/dashboard/filtros/",
        )
        for url in urls:
            self.assertEqual(self._panel(url).status_code, 401, url)
        # Rol sin dashboard.ver → 403 en cada lectura
        rol = Rol.objects.create(nombre="Sin panel S16", es_sistema=False)
        sin_panel = Usuario.objects.create_user(
            username="sin_panel_s16", password="SinPanel2026!", rol=rol
        )
        sin_panel.debe_cambiar_clave = False
        sin_panel.save(update_fields=("debe_cambiar_clave",))
        self._entrar("sin_panel_s16", "SinPanel2026!")
        for url in urls:
            self.assertEqual(self._panel(url).status_code, 403, url)
        # Portón de cambio obligatorio de contraseña (HU-112): 403
        self._entrar_admin()
        self.admin.debe_cambiar_clave = True
        self.admin.save(update_fields=("debe_cambiar_clave",))
        self.assertEqual(self._panel(urls[0]).status_code, 403)
        self.admin.debe_cambiar_clave = False
        self.admin.save(update_fields=("debe_cambiar_clave",))
        # Sin escritura: todos los verbos de mutación responden 405
        for url in urls:
            for metodo in ("post", "put", "patch", "delete"):
                respuesta = self._api(metodo, url, {})
                self.assertEqual(respuesta.status_code, 405, f"{metodo} {url}")

    # ------------------------------------------------------------------ #
    # 277: 32 tablas propias y 25 triggers, sin nada nuevo del panel
    # ------------------------------------------------------------------ #
    def test_277_recuento_de_tablas_propias_y_triggers(self):
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
        self.assertEqual(len(propias), 32)
        self.assertEqual(triggers, 25)
        # La app del panel no crea tablas: sigue sin migraciones propias
        self.assertEqual(
            [t for t in todas if t.startswith("dashboard")], []
        )

    # ------------------------------------------------------------------ #
    # 278: el recorrido de rutas del panel solo admite GET
    # ------------------------------------------------------------------ #
    def test_278_recorrido_de_rutas_del_panel(self):
        from django.urls import get_resolver

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
        # El router usa regex («^…$»): se limpian los anclajes y se
        # quedan solo las rutas del panel
        panel = [
            ruta.replace("^", "").replace("$", "")
            for ruta in patrones
            if "dashboard" in ruta
        ]
        self.assertEqual(len(panel), 4)
        # Cada ruta registrada: GET con sesión responde 200 y cualquier
        # escritura 405 (el verbo no existe en el ViewSet)
        self._entrar_admin()
        for ruta in panel:
            self.assertEqual(
                self._api("get", f"/{ruta}").status_code, 200, ruta
            )
            for metodo in ("post", "patch", "delete"):
                self.assertEqual(
                    self._api(metodo, f"/{ruta}", {}).status_code, 405,
                    f"{metodo} {ruta}",
                )

    # ------------------------------------------------------------------ #
    # 279: filtros del alcance, cascada y 400 claros
    # ------------------------------------------------------------------ #
    def test_279_filtros_cascada_y_400(self):
        self._entrar_admin()
        datos = self._json(self._panel("/api/dashboard/filtros/"))
        self.assertEqual(datos["periodos"], ["2025-2026", "2026-2027"])
        self.assertEqual(
            {c["nombre"] for c in datos["cultivos"]},
            {"Quinua S16", "Cañihua S16", "Maíz S16"},
        )
        self.assertEqual(len(datos["provincias"]), 2)
        # ?provincia= estrecha distritos y comunidades
        estrecho = self._json(
            self._panel(
                f"/api/dashboard/filtros/?provincia={self.provincia_b.pk}"
            )
        )
        self.assertEqual(
            [d["nombre"] for d in estrecho["distritos"]], ["Distrito S16-B"]
        )
        self.assertEqual(
            [c["nombre"] for c in estrecho["comunidades"]],
            ["Comunidad S16-B"],
        )
        # No numérico e inexistente → 400 con mensaje claro
        malo = self._api("get", "/api/dashboard/filtros/?provincia=abc")
        self.assertEqual(malo.status_code, 400)
        self.assertEqual(
            self._json(malo), {"provincia": "Debe ser un id numérico."}
        )
        inexistente = self._api(
            "get", "/api/dashboard/filtros/?provincia=99999"
        )
        self.assertEqual(inexistente.status_code, 400)
        self.assertEqual(
            self._json(inexistente),
            {"provincia": "La provincia indicada no existe."},
        )
        # El Técnico solo recibe la ubicación de SUS productores
        self._entrar_tecnico()
        datos = self._json(self._panel("/api/dashboard/filtros/"))
        self.assertEqual(len(datos["provincias"]), 1)
        self.assertEqual(
            [d["nombre"] for d in datos["distritos"]], ["Distrito S16"]
        )
        # agrupar inválido y ids no numéricos en producción → 400
        self._entrar_admin()
        malo = self._api(
            "get", "/api/dashboard/produccion/?agrupar=pais"
        )
        self.assertEqual(malo.status_code, 400)
        self.assertEqual(self._json(malo), {"agrupar": "Use cultivo o distrito."})
        malo = self._api("get", "/api/dashboard/produccion/?cultivo=abc")
        self.assertEqual(malo.status_code, 400)
        self.assertEqual(
            self._json(malo), {"cultivo": "Debe ser un id numérico."}
        )
