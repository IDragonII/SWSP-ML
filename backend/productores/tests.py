"""Pruebas de la Semana 3: ubicación y productores.

Numeración del repositorio 21-37 (14 obligatorias del plan —las 19-32 del
cuadro del spec, desplazadas porque la Semana 1/2 ya ocupó 01-20— y 3
extras: enmascarado, paginación/orden y comando de carga).
"""
import json
import tempfile
import time
from datetime import datetime
from io import StringIO

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import Comunidad, Distrito, Productor, Provincia


class ProductorApiTests(TestCase):
    """Pruebas 21-36: código automático, DNI, permisos, filtros, triggers
    y enmascarado en los 4 recursos de la API."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_pruebas", email="", password="AdminPruebas2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_pruebas", password="Coord2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_pruebas", password="Tec2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )
        self.provincia = Provincia.objects.create(nombre="Provincia Pruebas")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito Pruebas"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad Pruebas"
        )
        self.provincia_b = Provincia.objects.create(nombre="Provincia Pruebas B")
        self.distrito_b = Distrito.objects.create(
            provincia=self.provincia_b, nombre="Distrito Pruebas B"
        )
        self.comunidad_b = Comunidad.objects.create(
            distrito=self.distrito_b, nombre="Comunidad Pruebas B"
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_pruebas", "AdminPruebas2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _alta(self, **extra):
        datos = {
            "nombres": "Ana",
            "apellidos": "Zambrano",
            "dni": "11111111",
            "comunidad": self.comunidad.pk,
        }
        datos.update(extra)
        return self.client.post(
            "/api/productores/",
            data=json.dumps(datos),
            content_type="application/json",
        )

    def _patch(self, url, cuerpo):
        return self.client.patch(
            url, data=json.dumps(cuerpo), content_type="application/json"
        )

    def _ubicacion(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    # ------------------------------------------------------------------ #
    # 21-25: alta, código y validaciones del productor
    # ------------------------------------------------------------------ #
    def test_21_dos_productores_seguidos_reciben_codigos_consecutivos(self):
        # La secuencia no se reinicia entre pruebas: se comparan entre sí
        self._entrar_admin()
        primero = self._json(self._alta(nombres="Primero", apellidos="Alfa",
                                        dni="11111111"))
        segundo = self._json(self._alta(nombres="Segundo", apellidos="Beta",
                                        dni="22222222"))
        self.assertTrue(primero["codigo"].startswith("PROD-"))
        self.assertTrue(segundo["codigo"].startswith("PROD-"))
        n1 = int(primero["codigo"].split("-")[1])
        n2 = int(segundo["codigo"].split("-")[1])
        self.assertEqual(n2, n1 + 1)

    def test_22_el_codigo_no_se_puede_modificar_por_la_api(self):
        self._entrar_admin()
        original = self._json(self._alta())
        respuesta = self._patch(
            f"/api/productores/{original['id']}/", {"codigo": "PROD-9999"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self._json(respuesta)["codigo"], original["codigo"])
        actualizado = Productor.objects.get(pk=original["id"])
        self.assertEqual(actualizado.codigo, original["codigo"])

    def test_23_dni_invalido_se_rechaza(self):
        self._entrar_admin()
        for dni in ("123456", "123456789", "1234567a"):
            with self.subTest(dni=dni):
                respuesta = self._alta(dni=dni)
                self.assertEqual(respuesta.status_code, 400)
                mensajes = self._json(respuesta)["dni"]
                self.assertIn("exactamente 8 dígitos", mensajes[0])
        self.assertEqual(Productor.objects.count(), 0)

    def test_24_dni_duplicado_se_rechaza(self):
        self._entrar_admin()
        self.assertEqual(self._alta().status_code, 201)
        respuesta = self._alta(nombres="Otra", apellidos="Persona")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Ya existe", self._json(respuesta)["dni"][0])
        self.assertEqual(Productor.objects.count(), 1)

    def test_25_comunidad_es_obligatoria_debe_existir_y_estar_activa(self):
        self._entrar_admin()
        respuesta = self.client.post(
            "/api/productores/",
            data=json.dumps({"nombres": "Sin", "apellidos": "Comunidad",
                             "dni": "33333333"}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("obligatoria", self._json(respuesta)["comunidad"][0])

        inexistente = self._alta(dni="44444444", comunidad=999999)
        self.assertEqual(inexistente.status_code, 400)
        self.assertIn("no existe", self._json(inexistente)["comunidad"][0])

        inactiva = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad Cerrada", activo=False
        )
        respuesta = self._alta(dni="55555555", comunidad=inactiva.pk)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("inactiva", self._json(respuesta)["comunidad"][0])
        self.assertEqual(Productor.objects.count(), 0)

    # ------------------------------------------------------------------ #
    # 26-27: reglas de ubicación
    # ------------------------------------------------------------------ #
    def test_26_unicidad_compuesta_de_distritos_y_comunidades(self):
        self._entrar_admin()

        crear_distrito = lambda provincia: self._ubicacion(
            "post", "/api/ubicaciones/distritos/",
            {"nombre": "Distrito Repetido", "provincia": provincia},
        )
        self.assertEqual(crear_distrito(self.provincia.pk).status_code, 201)
        repetido = crear_distrito(self.provincia.pk)
        self.assertEqual(repetido.status_code, 400)
        self.assertIn("non_field_errors", self._json(repetido))
        # El mismo nombre sí cabe en otra provincia
        self.assertEqual(crear_distrito(self.provincia_b.pk).status_code, 201)

        distrito_nuevo = Distrito.objects.get(
            provincia=self.provincia, nombre="Distrito Repetido"
        )
        crear_comunidad = lambda distrito: self._ubicacion(
            "post", "/api/ubicaciones/comunidades/",
            {"nombre": "Comunidad Repetida", "distrito": distrito},
        )
        self.assertEqual(crear_comunidad(distrito_nuevo.pk).status_code, 201)
        self.assertEqual(crear_comunidad(distrito_nuevo.pk).status_code, 400)
        # y en otro distrito de la misma provincia, sí
        self.assertEqual(crear_comunidad(self.distrito_b.pk).status_code, 201)

    def test_27_desplegables_sin_inactivas_y_productor_conserva_la_suya(self):
        self._entrar_admin()
        productor = self._json(self._alta())
        cierre = self._patch(
            f"/api/ubicaciones/comunidades/{self.comunidad.pk}/estado/",
            {"activo": False},
        )
        self.assertEqual(cierre.status_code, 200)

        visibles = self._json(
            self._ubicacion("get", "/api/ubicaciones/comunidades/?activo=true")
        )
        self.assertNotIn(
            self.comunidad.pk, [c["id"] for c in visibles["results"]]
        )
        ocultas = self._json(
            self._ubicacion("get", "/api/ubicaciones/comunidades/?activo=false")
        )
        self.assertIn(self.comunidad.pk, [c["id"] for c in ocultas["results"]])

        ficha = self._json(
            self._ubicacion("get", f"/api/productores/{productor['id']}/")
        )
        self.assertEqual(ficha["comunidad"], self.comunidad.pk)
        listado = self._json(self._ubicacion("get", "/api/productores/"))
        self.assertEqual(
            listado["results"][0]["comunidad"]["nombre"], "Comunidad Pruebas"
        )
        en_bd = Productor.objects.get(pk=productor["id"])
        self.assertFalse(en_bd.comunidad.activo)

    # ------------------------------------------------------------------ #
    # 28-30: nada se borra y permisos por rol
    # ------------------------------------------------------------------ #
    def test_28_desactivar_conserva_datos_y_el_borrado_no_existe(self):
        self._entrar_admin()
        productor = self._json(self._alta())
        desactivado = self._json(self._patch(
            f"/api/productores/{productor['id']}/estado/",
            {"estado": "INACTIVO"},
        ))
        self.assertEqual(desactivado["estado"], "INACTIVO")

        ficha = self._json(
            self._ubicacion("get", f"/api/productores/{productor['id']}/")
        )
        for campo in ("nombres", "apellidos", "dni", "telefono", "comunidad",
                      "fecha_incorporacion", "creado_por", "creado_en"):
            self.assertIn(campo, ficha)

        borrado = self._ubicacion("delete", f"/api/productores/{productor['id']}/")
        self.assertEqual(borrado.status_code, 405)
        self.assertTrue(Productor.objects.filter(pk=productor["id"]).exists())

        reactivo = self._json(self._patch(
            f"/api/productores/{productor['id']}/estado/", {"estado": "ACTIVO"}
        ))
        self.assertEqual(reactivo["estado"], "ACTIVO")

    def test_29_sin_token_401_y_sin_permiso_403(self):
        self.assertEqual(
            self._ubicacion("get", "/api/productores/").status_code, 401
        )
        self.assertEqual(
            self._ubicacion("get", "/api/ubicaciones/provincias/").status_code,
            401,
        )
        self._entrar("coord_pruebas", "Coord2026!")
        self.assertEqual(self._alta().status_code, 403)
        productor = Productor.objects.create(
            codigo="PROD-0001", nombres="Puro", apellidos="Lectura",
            dni="66666666", comunidad=self.comunidad,
        )
        self.assertEqual(
            self._patch(
                f"/api/productores/{productor.pk}/", {"nombres": "No"}
            ).status_code,
            403,
        )

    def test_30_coordinador_consulta_pero_no_crea_ni_edita(self):
        self._entrar_admin()
        productor = self._json(self._alta())
        self.client.logout()
        self._entrar("coord_pruebas", "Coord2026!")

        listado = self._json(self._ubicacion("get", "/api/productores/"))
        self.assertEqual(listado["count"], 1)
        ficha = self._json(
            self._ubicacion("get", f"/api/productores/{productor['id']}/")
        )
        self.assertEqual(ficha["codigo"], productor["codigo"])
        self.assertEqual(self._alta(dni="77777777").status_code, 403)
        self.assertEqual(
            self._patch(
                f"/api/productores/{productor['id']}/", {"nombres": "No"}
            ).status_code,
            403,
        )

    # ------------------------------------------------------------------ #
    # 31-32: búsqueda y filtros
    # ------------------------------------------------------------------ #
    def test_31_busqueda_por_codigo_nombre_y_dni(self):
        self._entrar_admin()
        productor = self._json(self._alta(apellidos="Quispe Fernandez"))

        por_codigo = self._json(self._ubicacion(
            "get", f"/api/productores/?busqueda={productor['codigo']}"
        ))
        self.assertEqual(por_codigo["count"], 1)
        self.assertEqual(por_codigo["results"][0]["id"], productor["id"])

        por_nombre = self._json(self._ubicacion(
            "get", "/api/productores/?busqueda=Quispe"
        ))
        self.assertEqual(por_nombre["count"], 1)
        self.assertEqual(por_nombre["results"][0]["id"], productor["id"])

        por_dni = self._json(self._ubicacion(
            "get", "/api/productores/?busqueda=11111111"
        ))
        self.assertEqual(por_dni["count"], 1)
        self.assertEqual(por_dni["results"][0]["id"], productor["id"])

    def test_32_filtros_por_comunidad_distrito_provincia_y_estado(self):
        self._entrar_admin()
        p1 = self._json(self._alta())
        p2 = self._json(self._alta(nombres="Berta", apellidos="Acosta",
                                   dni="22222222",
                                   comunidad=self.comunidad_b.pk))

        por_comunidad = self._json(self._ubicacion(
            "get", f"/api/productores/?comunidad={self.comunidad.pk}"
        ))
        self.assertEqual([r["id"] for r in por_comunidad["results"]], [p1["id"]])

        por_distrito = self._json(self._ubicacion(
            "get", f"/api/productores/?distrito={self.distrito.pk}"
        ))
        self.assertEqual([r["id"] for r in por_distrito["results"]], [p1["id"]])

        por_provincia = self._json(self._ubicacion(
            "get", f"/api/productores/?provincia={self.provincia_b.pk}"
        ))
        self.assertEqual([r["id"] for r in por_provincia["results"]], [p2["id"]])

        self._patch(f"/api/productores/{p2['id']}/estado/",
                    {"estado": "INACTIVO"})
        inactivos = self._json(self._ubicacion(
            "get", "/api/productores/?estado=INACTIVO"
        ))
        self.assertEqual([r["id"] for r in inactivos["results"]], [p2["id"]])
        activos = self._json(self._ubicacion(
            "get", "/api/productores/?estado=ACTIVO"
        ))
        self.assertEqual([r["id"] for r in activos["results"]], [p1["id"]])

        malo = self._ubicacion("get", "/api/productores/?estado=MALO")
        self.assertEqual(malo.status_code, 400)
        self.assertIn("ACTIVO", str(self._json(malo)))

    # ------------------------------------------------------------------ #
    # 34: trazabilidad (la 33 vive en TriggerFechasTests: necesita
    # transacciones reales porque now() es el tiempo de la transacción)
    # ------------------------------------------------------------------ #
    def test_34_creado_por_es_el_usuario_autenticado_y_no_se_puede_forzar(self):
        self._entrar("tec_pruebas", "Tec2026!")
        productor = self._json(self._alta())
        self.assertEqual(productor["creado_por"], "tec_pruebas")

        # El campo ni siquiera se acepta en el cuerpo
        forzado = self._json(self._alta(
            dni="88888888", creado_por=self.admin.pk
        ))
        self.assertEqual(forzado["creado_por"], "tec_pruebas")

    # ------------------------------------------------------------------ #
    # 35-36: extras del spec («si sobra tiempo»)
    # ------------------------------------------------------------------ #
    def test_35_dni_y_telefono_se_enmascaran_segun_el_rol(self):
        self._entrar_admin()
        productor = self._json(self._alta(telefono="999888777"))
        admin_lista = self._json(self._ubicacion("get", "/api/productores/"))
        self.assertEqual(admin_lista["results"][0]["dni"], "11111111")

        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        tecnico_lista = self._json(self._ubicacion("get", "/api/productores/"))
        self.assertEqual(tecnico_lista["results"][0]["dni"], "11111111")

        self.client.logout()
        self._entrar("coord_pruebas", "Coord2026!")
        coord_lista = self._json(self._ubicacion("get", "/api/productores/"))
        fila = coord_lista["results"][0]
        self.assertEqual(fila["dni"], "****1111")
        coord_ficha = self._json(
            self._ubicacion("get", f"/api/productores/{productor['id']}/")
        )
        self.assertEqual(coord_ficha["dni"], "****1111")
        self.assertEqual(coord_ficha["telefono"], "****777")

    def test_36_listado_paginado_y_ordenado_por_apellidos(self):
        self._entrar_admin()
        self._alta(nombres="Zoe", apellidos="Zambrano", dni="10000001")
        self._alta(nombres="Alba", apellidos="Alfonso", dni="10000002")
        self._alta(nombres="Mario", apellidos="Mendoza", dni="10000003")

        listado = self._json(self._ubicacion("get", "/api/productores/"))
        for clave in ("count", "next", "previous", "results"):
            self.assertIn(clave, listado)
        self.assertEqual(listado["count"], 3)
        apellidos = [r["nombre_completo"].split(",")[0]
                     for r in listado["results"]]
        self.assertEqual(apellidos, sorted(apellidos))
        self.assertLessEqual(
            len(listado["results"]), settings.REST_FRAMEWORK["PAGE_SIZE"]
        )


class TriggerFechasTests(TransactionTestCase):
    """Prueba 33: actualizado_en cambia al editar y creado_en no.

    En PostgreSQL now() devuelve el instante de inicio de la transacción, y
    un TestCase ejecuta toda la prueba en una sola transacción: el trigger
    se dispararía con el mismo valor congelado. Se usan transacciones reales
    (TransactionTestCase) para que el UPDATE ocurra en otra transacción.
    El runner de Django agrupa los TestCase antes que los
    TransactionTestCase, así que esta prueba se ejecuta al final.
    """

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_pruebas", email="", password="AdminPruebas2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        provincia = Provincia.objects.create(nombre="Provincia Triggers")
        distrito = Distrito.objects.create(
            provincia=provincia, nombre="Distrito Triggers"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=distrito, nombre="Comunidad Triggers"
        )

    def test_33_actualizado_en_cambia_al_editar_y_creado_en_no(self):
        self.assertEqual(
            _post_login(self.client, "admin_pruebas", "AdminPruebas2026!"
                        ).status_code,
            200,
        )
        alta = self.client.post(
            "/api/productores/",
            data=json.dumps({"nombres": "Ana", "apellidos": "Zambrano",
                             "dni": "11111111", "comunidad": self.comunidad.pk}),
            content_type="application/json",
        )
        self.assertEqual(alta.status_code, 201)
        productor = json.loads(alta.content.decode("utf-8"))
        creado_antes = productor["creado_en"]
        actualizado_antes = productor["actualizado_en"]

        time.sleep(0.05)
        edicion = self.client.patch(
            f"/api/productores/{productor['id']}/",
            data=json.dumps({"telefono": "911222333"}),
            content_type="application/json",
        )
        self.assertEqual(edicion.status_code, 200)
        editado = json.loads(edicion.content.decode("utf-8"))

        self.assertEqual(editado["creado_en"], creado_antes)
        self.assertGreater(
            datetime.fromisoformat(editado["actualizado_en"]),
            datetime.fromisoformat(actualizado_antes),
        )


class ComandoCargaTests(TestCase):
    """Extra 37: el comando de carga es idempotente e informa los fallos
    sin detenerse (prueba del spec «si sobra tiempo»)."""

    def setUp(self):
        cache.clear()
        Provincia.objects.create(nombre="Provincia Pruebas")
        distrito = Distrito.objects.create(
            provincia=Provincia.objects.get(nombre="Provincia Pruebas"),
            nombre="Distrito Pruebas",
        )
        Comunidad.objects.create(distrito=distrito, nombre="Comunidad Pruebas")

    def _ejecutar(self, contenido):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as archivo:
            archivo.write(contenido)
            ruta = archivo.name
        salida = StringIO()
        call_command("cargar_ubicacion", archivo=ruta, stdout=salida)
        return salida.getvalue()

    def test_37_carga_idempotente_e_informe_de_fallidas(self):
        contenido = (
            "provincia,distrito,comunidad\n"
            "Provincia Comando Nueva,Distrito Comando,Comunidad Comando\n"
            "Provincia Pruebas,Distrito Pruebas,Comunidad Pruebas\n"
            ",Distrito Huerfano,Comunidad Huerfana\n"
        )
        primera = self._ejecutar(contenido)
        self.assertRegex(primera, r"Filas creadas:\s+1\b")
        self.assertRegex(primera, r"Filas ya existían:\s+1\b")
        self.assertRegex(primera, r"Filas fallidas:\s+1\b")
        self.assertIn("Fila 4: falta la provincia", primera)
        self.assertRegex(
            primera, r"provincias 1 · distritos 1 · comunidades 1"
        )
        self.assertTrue(
            Provincia.objects.filter(nombre="Provincia Comando Nueva").exists()
        )

        segunda = self._ejecutar(contenido)
        self.assertRegex(segunda, r"Filas creadas:\s+0\b")
        self.assertRegex(segunda, r"Filas ya existían:\s+2\b")
        self.assertRegex(segunda, r"Filas fallidas:\s+1\b")
        self.assertEqual(
            Provincia.objects.filter(nombre="Provincia Comando Nueva").count(), 1
        )
        self.assertEqual(Provincia.objects.count(), 2)
