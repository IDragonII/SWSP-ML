"""Pruebas de la Semana 5: la API de los 8 catálogos y su comando.

Numeración del repositorio 54-67: 13 pruebas de la API (54-66) más la
67 —el comando cargar_catalogos— → 67 en total. La migración 0002 ya
siembra los 26 registros de referencia, así que las pruebas parten de
3 cultivos, 7 tipos de actividad, 8 tipos de incidencia y 8 unidades
(sin quintal: lo pone el comando).
"""
import json
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import (
    Agente,
    Cultivo,
    EtapaFenologica,
    Recurso,
    TipoActividad,
    TipoIncidencia,
    Unidad,
    Variedad,
)


class Semana5Base(TestCase):
    """Cuentas de los 3 roles y catálogo sembrado por la migración."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_cat",
            email="",
            password="AdminCat2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_cat",
            password="CoordCat2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_cat",
            password="TecCat2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )
        # Sembrados por la migración 0002
        self.quinua = Cultivo.objects.get(nombre="Quinua")
        self.canihua = Cultivo.objects.get(nombre="Cañihua")
        self.kg = Unidad.objects.get(nombre="Kilogramo")
        self.litro = Unidad.objects.get(nombre="Litro")
        self.riego = TipoActividad.objects.get(codigo="RIEGO")
        self.cosecha = TipoActividad.objects.get(codigo="COSECHA")
        self.helada = TipoIncidencia.objects.get(nombre="Helada")
        self.recurso = Recurso.objects.create(
            nombre="Semilla de Prueba", categoria="SEMILLA", tipo_unidad="MASA"
        )
        self.agente = Agente.objects.create(
            nombre="Pulgón de Prueba", tipo="PLAGA"
        )
        # Etapas de ejemplo (en producción las pone el comando)
        self.etapas_quinua = [
            EtapaFenologica.objects.create(
                cultivo=self.quinua, nombre=nombre, orden=orden
            )
            for orden, nombre in enumerate(
                ("Siembra", "Emergencia", "Floración", "Cosecha"), start=1
            )
        ]
        self.etapa_canihua = EtapaFenologica.objects.create(
            cultivo=self.canihua, nombre="Siembra", orden=1
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_cat", "AdminCat2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)


class CatalogoEscrituraTests(Semana5Base):
    """Pruebas 54-60: unicidad normalizada, reglas de negocio,
    listas controladas y protecciones de cada catálogo."""

    # ------------------------------------------------------------------ #
    # 54: unicidad normalizada (mayúsculas y espacios no duplican)
    # ------------------------------------------------------------------ #
    def test_54_unicidad_normalizada_de_cultivos(self):
        self._entrar_admin()
        repetido = self._api("post", "/api/cultivos/", {"nombre": "  quinua  "})
        self.assertEqual(repetido.status_code, 400)
        self.assertIn("ya existe", str(self._json(repetido)["nombre"]).lower())
        # El nombre se guarda limpio (sin espacios sobrantes)
        nuevo = self._api(
            "post", "/api/cultivos/", {"nombre": "  Lenteja   Negra "}
        )
        self.assertEqual(nuevo.status_code, 201)
        self.assertEqual(self._json(nuevo)["nombre"], "Lenteja Negra")
        # Y la variante con otras mayúsculas/espacios también duplica
        otro = self._api(
            "post", "/api/cultivos/", {"nombre": "LENTEJA  NEGRA"}
        )
        self.assertEqual(otro.status_code, 400)
        # También al editar
        lenteja = Cultivo.objects.get(nombre="Lenteja Negra")
        editar = self._api(
            "patch", f"/api/cultivos/{lenteja.pk}/", {"nombre": "quinua"}
        )
        self.assertEqual(editar.status_code, 400)
        # El propio nombre sin cambio sigue permitido
        mismo = self._api(
            "patch", f"/api/cultivos/{lenteja.pk}/", {"nombre": "Lenteja Negra"}
        )
        self.assertEqual(mismo.status_code, 200)

    # ------------------------------------------------------------------ #
    # 55: unicidad compuesta de variedades (cultivo + nombre)
    # ------------------------------------------------------------------ #
    def test_55_unicidad_compuesta_de_variedades(self):
        self._entrar_admin()
        en_quinua = self._api(
            "post",
            "/api/variedades/",
            {"cultivo": self.quinua.pk, "nombre": "Real"},
        )
        self.assertEqual(en_quinua.status_code, 201)
        # El mismo nombre en OTRO cultivo no es duplicado
        en_canihua = self._api(
            "post",
            "/api/variedades/",
            {"cultivo": self.canihua.pk, "nombre": "Real"},
        )
        self.assertEqual(en_canihua.status_code, 201)
        # En el mismo cultivo sí (aunque cambien espacios/mayúsculas)
        duplicado = self._api(
            "post",
            "/api/variedades/",
            {"cultivo": self.quinua.pk, "nombre": "  real "},
        )
        self.assertEqual(duplicado.status_code, 400)
        self.assertIn("para ese cultivo", str(self._json(duplicado)["nombre"]))
        # Y al editar otra variedad hacia ese nombre
        otra = Variedad.objects.create(cultivo=self.quinua, nombre="Amarilla")
        editar = self._api(
            "patch", f"/api/variedades/{otra.pk}/", {"nombre": "REAL"}
        )
        self.assertEqual(editar.status_code, 400)

    # ------------------------------------------------------------------ #
    # 56: reordenar es atómico (valor temporal) y valida el payload
    # ------------------------------------------------------------------ #
    def test_56_reordenamiento_atomico_de_etapas(self):
        self._entrar_admin()
        originales = [etapa.pk for etapa in self.etapas_quinua]
        # Del revés: sin valor temporal, uq_etapa_orden chocaría a mitad
        invertido = self._api(
            "post",
            "/api/etapas-fenologicas/reordenar/",
            {"cultivo": self.quinua.pk, "orden": list(reversed(originales))},
        )
        self.assertEqual(invertido.status_code, 200)
        self.assertEqual(self._json(invertido)[0]["id"], originales[-1])
        en_bd = list(
            EtapaFenologica.objects.filter(cultivo=self.quinua)
            .order_by("orden")
            .values_list("pk", flat=True)
        )
        self.assertEqual(en_bd, list(reversed(originales)))
        # Un id de OTRO cultivo: rechazo sin tocar nada
        malo = self._api(
            "post",
            "/api/etapas-fenologicas/reordenar/",
            {
                "cultivo": self.quinua.pk,
                "orden": originales + [self.etapa_canihua.pk],
            },
        )
        self.assertEqual(malo.status_code, 400)
        self.assertIn("orden", self._json(malo))
        en_bd = list(
            EtapaFenologica.objects.filter(cultivo=self.quinua)
            .order_by("orden")
            .values_list("pk", flat=True)
        )
        self.assertEqual(en_bd, list(reversed(originales)))
        # Ids repetidos e incompletos también se rechazan
        repetido = self._api(
            "post",
            "/api/etapas-fenologicas/reordenar/",
            {
                "cultivo": self.quinua.pk,
                "orden": [originales[0], originales[0], originales[1]],
            },
        )
        self.assertEqual(repetido.status_code, 400)
        incompleta = self._api(
            "post",
            "/api/etapas-fenologicas/reordenar/",
            {"cultivo": self.quinua.pk, "orden": originales[:2]},
        )
        self.assertEqual(incompleta.status_code, 400)

    # ------------------------------------------------------------------ #
    # 57: el factor de una unidad debe ser mayor que 0 (400, no 500)
    # ------------------------------------------------------------------ #
    def test_57_factor_de_unidad_mayor_que_cero(self):
        self._entrar_admin()
        cero = self._api(
            "post",
            "/api/unidades/",
            {
                "nombre": "Arroba",
                "simbolo": "arroba",
                "tipo": "MASA",
                "factor_a_base": 0,
                "es_base": False,
            },
        )
        self.assertEqual(cero.status_code, 400)
        self.assertIn("mayor que 0", str(self._json(cero)["factor_a_base"]))
        negativo = self._api(
            "post",
            "/api/unidades/",
            {
                "nombre": "Arroba",
                "simbolo": "arroba",
                "tipo": "MASA",
                "factor_a_base": -5,
                "es_base": False,
            },
        )
        self.assertEqual(negativo.status_code, 400)
        # Una edición a 0 también se rechaza sin tocar la fila
        editar = self._api(
            "patch", f"/api/unidades/{self.litro.pk}/", {"factor_a_base": 0}
        )
        self.assertEqual(editar.status_code, 400)
        self.litro.refresh_from_db()
        self.assertEqual(self.litro.factor_a_base, Decimal("0.001"))
        # Y una unidad válida sí se crea
        valido = self._api(
            "post",
            "/api/unidades/",
            {
                "nombre": "Quintal de Prueba",
                "simbolo": "qqp",
                "tipo": "MASA",
                "factor_a_base": 12.5,
                "es_base": False,
            },
        )
        self.assertEqual(valido.status_code, 201)

    # ------------------------------------------------------------------ #
    # 58: las unidades base no se crean ni se desactivan
    # ------------------------------------------------------------------ #
    def test_58_unidades_base_protegidas(self):
        self._entrar_admin()
        base = self._api(
            "post",
            "/api/unidades/",
            {
                "nombre": "Kilogramo Doble",
                "simbolo": "kg2",
                "tipo": "MASA",
                "factor_a_base": 1,
                "es_base": True,
            },
        )
        self.assertEqual(base.status_code, 400)
        self.assertIn("es_base", self._json(base))
        # No se desactiva la base (ni por /estado/ ni por edición)
        estado = self._api(
            "patch", f"/api/unidades/{self.kg.pk}/estado/", {"activo": False}
        )
        self.assertEqual(estado.status_code, 400)
        self.assertIn("base", str(self._json(estado)["activo"]))
        editar = self._api(
            "patch", f"/api/unidades/{self.kg.pk}/", {"activo": False}
        )
        self.assertEqual(editar.status_code, 400)
        # Ni se convierte una existente en base
        litro_a_base = self._api(
            "patch", f"/api/unidades/{self.litro.pk}/", {"es_base": True}
        )
        self.assertEqual(litro_a_base.status_code, 400)
        # Una unidad no base sí se desactiva y se reactiva
        off = self._api(
            "patch", f"/api/unidades/{self.litro.pk}/estado/", {"activo": False}
        )
        self.assertEqual(off.status_code, 200)
        self.assertFalse(self._json(off)["activo"])
        on = self._api(
            "patch", f"/api/unidades/{self.litro.pk}/estado/", {"activo": True}
        )
        self.assertEqual(on.status_code, 200)
        self.assertTrue(self._json(on)["activo"])

    # ------------------------------------------------------------------ #
    # 59: los tipos de actividad son fijos (código, altas y Cosecha)
    # ------------------------------------------------------------------ #
    def test_59_tipos_de_actividad_fijos(self):
        self._entrar_admin()
        listado = self._json(self._api("get", "/api/tipos-actividad/"))
        self.assertEqual(listado["count"], 7)
        # No se crean tipos nuevos
        nuevo = self._api(
            "post",
            "/api/tipos-actividad/",
            {"codigo": "NUEVO", "nombre": "Nuevo tipo"},
        )
        self.assertEqual(nuevo.status_code, 405)
        # El código no se modifica (no se envía ni se guarda)
        editar = self._api(
            "patch",
            f"/api/tipos-actividad/{self.riego.pk}/",
            {"codigo": "OTRO", "nombre": "Riego por goteo"},
        )
        self.assertEqual(editar.status_code, 200)
        self.assertEqual(self._json(editar)["codigo"], "RIEGO")
        self.riego.refresh_from_db()
        self.assertEqual(self.riego.codigo, "RIEGO")
        self.assertEqual(self.riego.nombre, "Riego por goteo")
        # Cosecha y Siembra no se desactivan (por /estado/ ni edición)
        estado = self._api(
            "patch",
            f"/api/tipos-actividad/{self.cosecha.pk}/estado/",
            {"activo": False},
        )
        self.assertEqual(estado.status_code, 400)
        editar = self._api(
            "patch",
            f"/api/tipos-actividad/{self.cosecha.pk}/",
            {"activo": False},
        )
        self.assertEqual(editar.status_code, 400)
        siembra = TipoActividad.objects.get(codigo="SIEMBRA")
        estado = self._api(
            "patch",
            f"/api/tipos-actividad/{siembra.pk}/estado/",
            {"activo": False},
        )
        self.assertEqual(estado.status_code, 400)
        # Otras actividades sí se desactivan
        off = self._api(
            "patch",
            f"/api/tipos-actividad/{self.riego.pk}/estado/",
            {"activo": False},
        )
        self.assertEqual(off.status_code, 200)
        self.assertFalse(self._json(off)["activo"])

    # ------------------------------------------------------------------ #
    # 60: los campos con lista cerrada rechazan en español
    # ------------------------------------------------------------------ #
    def test_60_listas_controladas_con_mensaje_en_espanol(self):
        self._entrar_admin()
        casos = [
            (
                "/api/recursos/",
                {
                    "nombre": "Guisante",
                    "categoria": "MAGICA",
                    "tipo_unidad": "MASA",
                },
                "categoria",
            ),
            (
                "/api/recursos/",
                {
                    "nombre": "Compost",
                    "categoria": "ABONO",
                    "tipo_unidad": "DINERO",
                },
                "tipo_unidad",
            ),
            (
                "/api/agentes/",
                {"nombre": "Virus de Prueba", "tipo": "ALIEN"},
                "tipo",
            ),
            (
                "/api/tipos-incidencia/",
                {"nombre": "X", "categoria": "NADA"},
                "categoria",
            ),
            (
                "/api/unidades/",
                {
                    "nombre": "Peseta",
                    "simbolo": "pta",
                    "tipo": "DINERO",
                    "factor_a_base": 1,
                },
                "tipo",
            ),
        ]
        for url, cuerpo, campo in casos:
            with self.subTest(url=url, campo=campo):
                respuesta = self._api("post", url, cuerpo)
                self.assertEqual(respuesta.status_code, 400)
                mensajes = str(self._json(respuesta)[campo])
                self.assertIn("no es una opción válida", mensajes)


class PermisosYConsultaTests(Semana5Base):
    """Pruebas 61-66: permisos por rol, desplegables ligeros, filtros y
    paginación de los 8 catálogos."""

    # ------------------------------------------------------------------ #
    # 61: 401 sin token; 403 para quien no tiene el permiso; 201 admin
    # ------------------------------------------------------------------ #
    def test_61_permisos_de_catalogos_por_rol(self):
        self.assertEqual(self._api("get", "/api/cultivos/").status_code, 401)
        # Coordinador: solo consulta (catalogos.ver)
        self._entrar("coord_cat", "CoordCat2026!")
        self.assertEqual(self._api("get", "/api/cultivos/").status_code, 200)
        self.assertEqual(
            self._api("post", "/api/cultivos/", {"nombre": "Nuevo"}).status_code,
            403,
        )
        self.assertEqual(
            self._api(
                "patch", f"/api/cultivos/{self.quinua.pk}/", {"nombre": "Cambio"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self._api(
                "patch",
                f"/api/cultivos/{self.quinua.pk}/estado/",
                {"activo": False},
            ).status_code,
            403,
        )
        self.assertEqual(
            self._api(
                "post",
                "/api/etapas-fenologicas/reordenar/",
                {"cultivo": self.quinua.pk, "orden": []},
            ).status_code,
            403,
        )
        # Técnico de campo: también solo consulta
        self._entrar("tec_cat", "TecCat2026!")
        self.assertEqual(self._api("get", "/api/cultivos/").status_code, 200)
        self.assertEqual(
            self._api("post", "/api/cultivos/", {"nombre": "Nuevo"}).status_code,
            403,
        )
        self.assertEqual(
            self._api(
                "patch",
                f"/api/cultivos/{self.quinua.pk}/estado/",
                {"activo": False},
            ).status_code,
            403,
        )
        # Administrador: todo
        self._entrar_admin()
        self.assertEqual(
            self._api(
                "post", "/api/cultivos/", {"nombre": "Nuevo Cultivo"}
            ).status_code,
            201,
        )
        self.assertEqual(
            self._api(
                "post",
                "/api/etapas-fenologicas/reordenar/",
                {
                    "cultivo": self.quinua.pk,
                    "orden": [e.pk for e in self.etapas_quinua],
                },
            ).status_code,
            200,
        )

    # ------------------------------------------------------------------ #
    # 62: los desplegables solo traen activos y sin paginar
    # ------------------------------------------------------------------ #
    def test_62_desplegables_solo_con_activos(self):
        self._entrar_admin()
        vieja = Variedad.objects.create(
            cultivo=self.quinua, nombre="Variedad Vieja", activo=False
        )
        tarwi = Cultivo.objects.get(nombre="Tarwi")
        nativa = Variedad.objects.create(cultivo=tarwi, nombre="Tarwi Nativa")
        etapa_tarwi = EtapaFenologica.objects.create(
            cultivo=tarwi, nombre="Preparación", orden=1
        )
        apagado = self._api(
            "patch", f"/api/cultivos/{tarwi.pk}/estado/", {"activo": False}
        )
        self.assertEqual(apagado.status_code, 200)
        # Desplegable de variedades: oculta la inactiva y la de Tarwi
        datos = self._json(self._api("get", "/api/variedades/?desplegable=1"))
        self.assertIsInstance(datos, list)
        ids = [fila["id"] for fila in datos]
        self.assertNotIn(vieja.pk, ids)
        self.assertNotIn(nativa.pk, ids)
        # El listado normal sí las trae (con paginación)
        listado = self._json(self._api("get", "/api/variedades/"))
        self.assertIn("results", listado)
        ids = [fila["id"] for fila in listado["results"]]
        self.assertIn(vieja.pk, ids)
        self.assertIn(nativa.pk, ids)
        # Etapas y cultivos del desplegable también ocultan el inactivo
        etapas = self._json(
            self._api("get", "/api/etapas-fenologicas/?desplegable=1")
        )
        self.assertNotIn(etapa_tarwi.pk, [f["id"] for f in etapas])
        cultivos = self._json(self._api("get", "/api/cultivos/?desplegable=1"))
        self.assertNotIn(tarwi.pk, [f["id"] for f in cultivos])
        # Una unidad desactivada tampoco aparece en su desplegable
        self._api(
            "patch", f"/api/unidades/{self.litro.pk}/estado/", {"activo": False}
        )
        unidades = self._json(self._api("get", "/api/unidades/?desplegable=1"))
        self.assertNotIn(self.litro.pk, [f["id"] for f in unidades])

    # ------------------------------------------------------------------ #
    # 63: un cultivo inactivo oculta sus hijas, las bloquea y las etapas
    #     no tienen endpoint de estado
    # ------------------------------------------------------------------ #
    def test_63_cultivo_inactivo_oculta_y_bloquea_sus_etapas(self):
        self._entrar_admin()
        tarwi = Cultivo.objects.get(nombre="Tarwi")
        etapa = EtapaFenologica.objects.create(
            cultivo=tarwi, nombre="Preparación", orden=1
        )
        self._api("patch", f"/api/cultivos/{tarwi.pk}/estado/", {"activo": False})
        # No se crean hijas de un cultivo inactivo
        variedad = self._api(
            "post", "/api/variedades/", {"cultivo": tarwi.pk, "nombre": "Nueva"}
        )
        self.assertEqual(variedad.status_code, 400)
        self.assertIn("inactivo", str(self._json(variedad)["cultivo"]))
        nueva_etapa = self._api(
            "post",
            "/api/etapas-fenologicas/",
            {"cultivo": tarwi.pk, "nombre": "Floración", "orden": 9},
        )
        self.assertEqual(nueva_etapa.status_code, 400)
        self.assertIn("inactivo", str(self._json(nueva_etapa)["cultivo"]))
        # Las etapas no tienen endpoint de estado (404)
        sin_estado = self._api(
            "patch",
            f"/api/etapas-fenologicas/{etapa.pk}/estado/",
            {"activo": False},
        )
        self.assertEqual(sin_estado.status_code, 404)
        # Siguen listándose para gestionarlas (filtro por cultivo)
        listado = self._json(
            self._api("get", f"/api/etapas-fenologicas/?cultivo={tarwi.pk}")
        )
        self.assertEqual(listado["count"], 1)

    # ------------------------------------------------------------------ #
    # 64: ningún catálogo ofrece DELETE (405) y nada se borra
    # ------------------------------------------------------------------ #
    def test_64_sin_delete_en_ningun_catalogo(self):
        self._entrar_admin()
        por_borrar = Variedad.objects.create(
            cultivo=self.quinua, nombre="Borrable"
        )
        urls = [
            f"/api/cultivos/{self.quinua.pk}/",
            f"/api/variedades/{por_borrar.pk}/",
            f"/api/etapas-fenologicas/{self.etapas_quinua[0].pk}/",
            f"/api/unidades/{self.kg.pk}/",
            f"/api/tipos-actividad/{self.riego.pk}/",
            f"/api/recursos/{self.recurso.pk}/",
            f"/api/tipos-incidencia/{self.helada.pk}/",
            f"/api/agentes/{self.agente.pk}/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self._api("delete", url).status_code, 405)
        self.assertTrue(Cultivo.objects.filter(pk=self.quinua.pk).exists())
        self.assertTrue(Variedad.objects.filter(pk=por_borrar.pk).exists())

    # ------------------------------------------------------------------ #
    # 65: filtros por clave, estado y búsqueda por nombre
    # ------------------------------------------------------------------ #
    def test_65_filtros_por_clave_estado_y_busqueda(self):
        self._entrar_admin()
        en_quinua = Variedad.objects.create(cultivo=self.quinua, nombre="Amarilla")
        en_canihua = Variedad.objects.create(cultivo=self.canihua, nombre="Blanca")
        # Por cultivo
        datos = self._json(
            self._api("get", f"/api/variedades/?cultivo={self.quinua.pk}")
        )
        ids = [fila["id"] for fila in datos["results"]]
        self.assertIn(en_quinua.pk, ids)
        self.assertNotIn(en_canihua.pk, ids)
        self.assertTrue(
            all(fila["cultivo"]["id"] == self.quinua.pk for fila in datos["results"])
        )
        # Por tipo de unidad
        datos = self._json(self._api("get", "/api/unidades/?tipo=MASA"))
        self.assertGreater(datos["count"], 0)
        self.assertTrue(all(fila["tipo"] == "MASA" for fila in datos["results"]))
        # Por categoría de recurso
        tractor = Recurso.objects.create(
            nombre="Alquiler de Tractor",
            categoria="MAQUINARIA",
            tipo_unidad="LABOR",
        )
        datos = self._json(self._api("get", "/api/recursos/?categoria=MAQUINARIA"))
        self.assertEqual([fila["id"] for fila in datos["results"]], [tractor.pk])
        # Por estado
        self._api(
            "patch", f"/api/cultivos/{self.quinua.pk}/estado/", {"activo": False}
        )
        datos = self._json(self._api("get", "/api/cultivos/?activo=false"))
        self.assertEqual([fila["nombre"] for fila in datos["results"]], ["Quinua"])
        # Estado mal escrito → 400 en español
        mal = self._api("get", "/api/cultivos/?activo=quizas")
        self.assertEqual(mal.status_code, 400)
        self.assertIn("Use true o false", str(self._json(mal)["activo"]))
        # Búsqueda por nombre (?busqueda=)
        datos = self._json(self._api("get", "/api/cultivos/?busqueda=quin"))
        self.assertEqual([fila["nombre"] for fila in datos["results"]], ["Quinua"])

    # ------------------------------------------------------------------ #
    # 66: el listado normal pagina y el desplegable es una lista corta
    # ------------------------------------------------------------------ #
    def test_66_paginacion_normal_y_campos_de_desplegables(self):
        self._entrar_admin()
        Recurso.objects.bulk_create(
            [
                Recurso(
                    nombre=f"Insumo de Prueba {i}",
                    categoria="FERTILIZANTE",
                    tipo_unidad="MASA",
                )
                for i in range(1, 26)
            ]
        )
        listado = self._json(self._api("get", "/api/recursos/"))
        tamano = settings.REST_FRAMEWORK["PAGE_SIZE"]
        self.assertEqual(listado["count"], 30)  # 25 + 4 de la S20 + setUp
        self.assertEqual(len(listado["results"]), min(tamano, 30))
        if tamano < 30:
            self.assertIsNotNone(listado["next"])
        # Sin paginar: lista cruda con los campos del desplegable (la
        # Semana 9 añade categoría y tipo de unidad a los recursos y el
        # factor a la base a las unidades, para el formulario de usos)
        datos = self._json(self._api("get", "/api/recursos/?desplegable=1"))
        self.assertIsInstance(datos, list)
        self.assertEqual(len(datos), 30)
        self.assertTrue(
            all(
                set(fila) == {"id", "nombre", "categoria", "tipo_unidad"}
                for fila in datos
            )
        )
        # Variedades y unidades traen sus campos extra
        variedad = Variedad.objects.create(cultivo=self.quinua, nombre="Prueba")
        datos = self._json(self._api("get", "/api/variedades/?desplegable=1"))
        self.assertEqual(set(datos[0]), {"id", "nombre", "cultivo"})
        self.assertIn(variedad.pk, [fila["id"] for fila in datos])
        unidades = self._json(self._api("get", "/api/unidades/?desplegable=1"))
        self.assertEqual(
            set(unidades[0]),
            {"id", "nombre", "simbolo", "tipo", "factor_a_base", "es_base"},
        )
        self.assertEqual(len(unidades), 8)


class ComandoCargarCatalogosTests(TestCase):
    """67: el comando cargar_catalogos (idempotente, sin pisar ediciones)."""

    def test_67_comando_cargar_catalogos(self):
        # Estado inicial: solo la migración 0002 (sin quintal, agentes ni etapas)
        self.assertEqual(Cultivo.objects.count(), 3)
        self.assertEqual(Unidad.objects.count(), 8)
        self.assertEqual(Agente.objects.count(), 0)
        self.assertEqual(EtapaFenologica.objects.count(), 0)

        salida = StringIO()
        call_command("cargar_catalogos", stdout=salida)
        texto = salida.getvalue()

        # Entran los datos de ejemplo del diseño (quintal, agentes, etapas)
        quintal = Unidad.objects.get(nombre="Quintal")
        self.assertEqual(quintal.simbolo, "qq")
        self.assertEqual(quintal.tipo, "MASA")
        self.assertEqual(quintal.factor_a_base, Decimal("46"))
        self.assertFalse(quintal.es_base)
        self.assertEqual(Unidad.objects.count(), 9)
        self.assertEqual(Agente.objects.count(), 5)
        self.assertIn("Pulgón", set(Agente.objects.values_list("nombre", flat=True)))
        self.assertEqual(
            set(EtapaFenologica.objects.values_list("nombre", flat=True)),
            {
                "Siembra",
                "Emergencia",
                "Desarrollo vegetativo",
                "Floración",
                "Maduración",
                "Cosecha",
            },
        )
        # Solo Quinua y Cañihua, con el orden 1..6 del diseño (Tarwi, no)
        quinua = Cultivo.objects.get(nombre="Quinua")
        ordenes = list(
            EtapaFenologica.objects.filter(cultivo=quinua)
            .order_by("orden")
            .values_list("orden", flat=True)
        )
        self.assertEqual(ordenes, [1, 2, 3, 4, 5, 6])
        self.assertEqual(
            EtapaFenologica.objects.filter(
                cultivo__nombre="Cañihua"
            ).count(),
            6,
        )
        self.assertEqual(
            EtapaFenologica.objects.filter(cultivo__nombre="Tarwi").count(),
            0,
        )

        # Informa de lo creado y de que es ejemplo hasta confirmar
        self.assertIn("Filas creadas: 18 · ya existían: 26", texto)
        self.assertIn(
            "unidades 9 · agentes 5 · etapas fenológicas 12", texto
        )
        self.assertIn("hasta confirmar", texto)

        # Segunda pasada: idempotente (no crea nada ni duplica)
        salida_2 = StringIO()
        call_command("cargar_catalogos", stdout=salida_2)
        self.assertIn("Filas creadas: 0", salida_2.getvalue())
        self.assertEqual(Unidad.objects.count(), 9)
        self.assertEqual(Agente.objects.count(), 5)
        self.assertEqual(EtapaFenologica.objects.count(), 12)

        # No pisa lo editado: cambio el factor del quintal y reejecuto
        quintal.factor_a_base = Decimal("50")
        quintal.save()
        call_command("cargar_catalogos", stdout=StringIO())
        quintal.refresh_from_db()
        self.assertEqual(quintal.factor_a_base, Decimal("50"))
