"""Pruebas de la Semana 4: parcelas, asignaciones y filtro «solo mis productores».

Numeración del repositorio 38-53 (16 pruebas nuevas → 53 en total ≥ 48).
Mapeo spec → repositorio (decisión 10 de docs/decisiones_semana4.md):
33→38, 34→39, 35→40, 36→41, 37→42, 38→43, 39→44, 40→45, 41→46,
42→47, 43→48, 44→49, 45→50, 46→51, 47→52, 48→53.
"""
import json

from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.test import TestCase
from django.utils import timezone

from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia


class Semana4Base(TestCase):
    """Datos comunes: las 3 cuentas, ubicación y dos productores."""

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
        self.provincia = Provincia.objects.create(nombre="Prov S4")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S4"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S4"
        )
        self.distrito_b = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S4 B"
        )
        self.comunidad_b = Comunidad.objects.create(
            distrito=self.distrito_b, nombre="Comunidad S4 B"
        )
        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="51000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p2 = Productor.objects.create(
            nombres="Dos", apellidos="Beta", dni="51000002",
            comunidad=self.comunidad_b, creado_por=self.admin,
        )
        # El trigger de código rellena codigo después del INSERT
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()

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

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _datos_parcela(self, **extra):
        datos = {
            "productor": self.p1.pk,
            "comunidad": self.comunidad.pk,
            "superficie_ha": "2.00",
            "altitud_msnm": 3850,
            "latitud": "-15.123456",
            "longitud": "-70.987654",
            "tipo_suelo": "FRANCO",
            "pendiente": "SUAVE",
            "disponibilidad_agua": "MEDIA",
            "sistema_riego": "GOTEO",
        }
        datos.update(extra)
        return datos

    def _parcela(self, **extra):
        """Alta de parcela por la API (debe estar logueado el admin)."""
        return self._api("post", "/api/parcelas/", self._datos_parcela(**extra))

    def _parcela_bd(self, productor=None, comunidad=None, superficie="2.00"):
        parcela = Parcela.objects.create(
            productor=productor or self.p1,
            comunidad=comunidad or self.comunidad,
            superficie_ha=superficie,
            altitud_msnm=3850,
            tipo_suelo="FRANCO",
            pendiente="SUAVE",
            disponibilidad_agua="MEDIA",
            sistema_riego="GOTEO",
        )
        parcela.refresh_from_db()  # el trigger rellena codigo
        return parcela

    def _asignar_bd(self, productor=None, tecnico=None):
        return AsignacionTecnico.objects.create(
            tecnico=tecnico or self.tecnico, productor=productor or self.p1
        )

    def _asignar_api(self, productor=None, tecnico=None):
        return self._api(
            "post",
            "/api/asignaciones/",
            {
                "tecnico": (tecnico or self.tecnico).pk,
                "productor": (productor or self.p1).pk,
            },
        )


class ParcelaApiTests(Semana4Base):
    """Pruebas 38-44: alta y trazabilidad, validaciones, vida, filtros,
    permisos y trigger de código de las parcelas."""

    # ------------------------------------------------------------------ #
    # 38 (spec 33): alta válida, código automático y trazabilidad
    # ------------------------------------------------------------------ #
    def test_38_alta_valida_con_codigo_automatico_y_trazabilidad(self):
        self._entrar_admin()
        respuesta = self._parcela()
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        self.assertRegex(fila["codigo"], r"^P-\d{3}$")
        self.assertEqual(fila["estado"], "ACTIVA")
        self.assertEqual(fila["creado_por"], "admin_pruebas")
        self.assertIn("creado_en", fila)
        self.assertIn("actualizado_en", fila)
        self.assertIsInstance(fila["superficie_ha"], str)

        # El código es solo lectura por la API
        editada = self._api(
            "patch",
            f"/api/parcelas/{fila['id']}/",
            {"codigo": "P-999", "referencia_ubicacion": "Junto al canal"},
        )
        self.assertEqual(editada.status_code, 200)
        self.assertEqual(self._json(editada)["codigo"], fila["codigo"])
        self.assertEqual(
            Parcela.objects.get(pk=fila["id"]).codigo, fila["codigo"]
        )
        self.assertEqual(
            self._json(editada)["referencia_ubicacion"], "Junto al canal"
        )

    # ------------------------------------------------------------------ #
    # 39 (spec 34): validaciones de parcela
    # ------------------------------------------------------------------ #
    def test_39_validaciones_de_parcela(self):
        self._entrar_admin()

        casos = [
            ({"superficie_ha": "0"}, "superficie_ha", "mayor que 0"),
            ({"superficie_ha": "-1.50"}, "superficie_ha", "mayor que 0"),
            ({"altitud_msnm": 7000}, "altitud_msnm", "entre 0 y 6500"),
            ({"altitud_msnm": -1}, "altitud_msnm", "entre 0 y 6500"),
            ({"tipo_suelo": "PLANO"}, "tipo_suelo", "tipo de suelo"),
            ({"latitud": "91.000000"}, "latitud", "La latitud"),
            ({"longitud": "181.000000"}, "longitud", "La longitud"),
        ]
        for datos, campo, texto in casos:
            with self.subTest(campo=campo, valor=datos[campo]):
                respuesta = self._parcela(**datos)
                self.assertEqual(respuesta.status_code, 400)
                cuerpo = self._json(respuesta)
                self.assertIn(campo, cuerpo)
                self.assertIn(texto, str(cuerpo[campo]))

        # Listas cerradas: los campos existen y responden 400
        for campo, valor in (
            ("pendiente", "INCLINADA"),
            ("disponibilidad_agua", "ENORME"),
            ("sistema_riego", "TUBERIA"),
        ):
            with self.subTest(campo=campo):
                respuesta = self._parcela(**{campo: valor})
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(campo, self._json(respuesta))

        # Coordenadas: las dos o ninguna (ck_parcela_coordenadas)
        sin_longitud = {
            k: v for k, v in self._datos_parcela().items() if k != "longitud"
        }
        respuesta = self._api("post", "/api/parcelas/", sin_longitud)
        self.assertEqual(respuesta.status_code, 400)
        texto = str(self._json(respuesta)).replace("í", "i")
        self.assertIn("dos vacias", texto)

        # Sin coordenadas a la vez: sí se admite
        sin_coordenadas = {
            k: v
            for k, v in self._datos_parcela().items()
            if k not in ("latitud", "longitud")
        }
        self.assertEqual(
            self._api("post", "/api/parcelas/", sin_coordenadas).status_code,
            201,
        )

        # Campos obligatorios
        vacia = self._api("post", "/api/parcelas/", {})
        self.assertEqual(vacia.status_code, 400)
        cuerpo = self._json(vacia)
        self.assertIn("El productor es obligatorio.", str(cuerpo["productor"]))
        self.assertIn("La comunidad es obligatoria.", str(cuerpo["comunidad"]))
        self.assertIn(
            "La superficie es obligatoria.", str(cuerpo["superficie_ha"])
        )
        self.assertIn("La altitud es obligatoria.", str(cuerpo["altitud_msnm"]))
        self.assertEqual(Parcela.objects.count(), 1)

    # ------------------------------------------------------------------ #
    # 40 (spec 35): productor ACTIVO y reglas de edición
    # ------------------------------------------------------------------ #
    def test_40_productor_inactivo_rechazado_y_productor_inmutable(self):
        self._entrar_admin()
        self._api(
            "patch",
            f"/api/productores/{self.p2.pk}/estado/",
            {"estado": "INACTIVO"},
        )
        respuesta = self._parcela(productor=self.p2.pk)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "no admite parcelas nuevas",
            str(self._json(respuesta)["productor"]),
        )
        self._api(
            "patch",
            f"/api/productores/{self.p2.pk}/estado/",
            {"estado": "ACTIVO"},
        )

        parcela = self._json(self._parcela())

        # PUT completo: el productor no cambia, la comunidad sí
        editada = self._api(
            "put",
            f"/api/parcelas/{parcela['id']}/",
            self._datos_parcela(
                productor=self.p2.pk,
                comunidad=self.comunidad_b.pk,
                superficie_ha="3.00",
            ),
        )
        self.assertEqual(editada.status_code, 200)
        fila = self._json(editada)
        self.assertEqual(fila["productor"]["id"], self.p1.pk)
        self.assertEqual(fila["comunidad"]["id"], self.comunidad_b.pk)
        self.assertEqual(fila["superficie_ha"], "3.00")

        # PUT sin comunidad: obligatoria
        sin_comunidad = {
            k: v
            for k, v in self._datos_parcela().items()
            if k != "comunidad"
        }
        respuesta = self._api(
            "put", f"/api/parcelas/{parcela['id']}/", sin_comunidad
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "La comunidad es obligatoria.",
            str(self._json(respuesta)["comunidad"]),
        )

    # ------------------------------------------------------------------ #
    # 41 (spec 36): nada se borra (405) y estado sin perder datos
    # ------------------------------------------------------------------ #
    def test_41_sin_delete_y_estado_activa_inactiva(self):
        self._entrar_admin()
        parcela = self._json(self._parcela())

        self.assertEqual(
            self._api("delete", f"/api/parcelas/{parcela['id']}/").status_code,
            405,
        )

        r = self._api(
            "patch",
            f"/api/parcelas/{parcela['id']}/estado/",
            {"estado": "INACTIVA"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._json(r)["estado"], "INACTIVA")
        self.assertEqual(
            Parcela.objects.get(pk=parcela["id"]).estado, "INACTIVA"
        )
        # Sigue existiendo y es visible filtrando por estado
        inactivas = self._json(
            self._api("get", "/api/parcelas/?estado=INACTIVA")
        )
        self.assertIn(parcela["id"], [f["id"] for f in inactivas["results"]])

        r = self._api(
            "patch",
            f"/api/parcelas/{parcela['id']}/estado/",
            {"estado": "ACTIVA"},
        )
        self.assertEqual(self._json(r)["estado"], "ACTIVA")

        r = self._api(
            "patch",
            f"/api/parcelas/{parcela['id']}/estado/",
            {"estado": "X"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("Use ACTIVA o INACTIVA", str(self._json(r)))
        self.assertEqual(Parcela.objects.count(), 1)

    # ------------------------------------------------------------------ #
    # 42 (spec 37): filtros y búsqueda
    # ------------------------------------------------------------------ #
    def test_42_filtros_y_busqueda_de_parcelas(self):
        self._entrar_admin()
        pa1 = self._json(self._parcela())
        pa2 = self._json(self._parcela(productor=self.p2.pk,
                                       comunidad=self.comunidad_b.pk))

        por_productor = self._json(
            self._api("get", f"/api/parcelas/?productor={self.p1.pk}")
        )
        self.assertEqual(
            [f["id"] for f in por_productor["results"]], [pa1["id"]]
        )

        por_comunidad = self._json(
            self._api("get", f"/api/parcelas/?comunidad={self.comunidad.pk}")
        )
        self.assertIn(pa1["id"], [f["id"] for f in por_comunidad["results"]])
        self.assertNotIn(pa2["id"], [f["id"] for f in por_comunidad["results"]])

        por_distrito = self._json(
            self._api("get", f"/api/parcelas/?distrito={self.distrito.pk}")
        )
        self.assertEqual(
            [f["id"] for f in por_distrito["results"]], [pa1["id"]]
        )

        por_provincia = self._json(
            self._api("get", f"/api/parcelas/?provincia={self.provincia.pk}")
        )
        self.assertEqual(
            sorted(f["id"] for f in por_provincia["results"]),
            sorted([pa1["id"], pa2["id"]]),
        )

        self._api(
            "patch",
            f"/api/parcelas/{pa2['id']}/estado/",
            {"estado": "INACTIVA"},
        )
        inactivas = self._json(
            self._api("get", "/api/parcelas/?estado=INACTIVA")
        )
        self.assertIn(pa2["id"], [f["id"] for f in inactivas["results"]])
        self.assertNotIn(pa1["id"], [f["id"] for f in inactivas["results"]])

        por_busqueda = self._json(self._api("get", "/api/parcelas/?busqueda=Alfa"))
        self.assertEqual(
            [f["id"] for f in por_busqueda["results"]], [pa1["id"]]
        )

        respuesta = self._api("get", "/api/parcelas/?distrito=abc")
        self.assertEqual(respuesta.status_code, 400)
        texto = str(self._json(respuesta)).replace("é", "e")
        self.assertIn("id numerico", texto)

        respuesta = self._api("get", "/api/parcelas/?estado=RARO")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Use ACTIVA o INACTIVA", str(self._json(respuesta)))

    # ------------------------------------------------------------------ #
    # 43 (spec 38): permisos por rol
    # ------------------------------------------------------------------ #
    def test_43_permisos_de_parcelas(self):
        self._entrar_admin()
        parcela = self._json(self._parcela())

        self.client.logout()
        self._entrar("coord_pruebas", "Coord2026!")
        self.assertEqual(self._api("get", "/api/parcelas/").status_code, 200)
        self.assertEqual(
            self._api("post", "/api/parcelas/", self._datos_parcela()).status_code,
            403,
        )
        self.assertEqual(
            self._api(
                "patch",
                f"/api/parcelas/{parcela['id']}/estado/",
                {"estado": "INACTIVA"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self._api(
                "patch",
                f"/api/parcelas/{parcela['id']}/",
                {"referencia_ubicacion": "x"},
            ).status_code,
            403,
        )

        # El técnico crea su productor (auto-asignación) y su parcela
        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        propio = self._json(
            self._api(
                "post",
                "/api/productores/",
                {
                    "nombres": "Tec",
                    "apellidos": "Propio",
                    "dni": "52000001",
                    "comunidad": self.comunidad.pk,
                },
            )
        )
        propia = self._api(
            "post",
            "/api/parcelas/",
            self._datos_parcela(productor=propio["id"], superficie_ha="1.00"),
        )
        self.assertEqual(propia.status_code, 201)
        self.assertEqual(
            self._api(
                "patch",
                f"/api/parcelas/{self._json(propia)['id']}/",
                {"referencia_ubicacion": "Editada"},
            ).status_code,
            200,
        )
        # Sin parcelas.desactivar: 403 en estado, igual con id inexistente
        self.assertEqual(
            self._api(
                "patch",
                f"/api/parcelas/{self._json(propia)['id']}/estado/",
                {"estado": "INACTIVA"},
            ).status_code,
            403,
        )

        self.client.logout()
        self.assertEqual(self._api("get", "/api/parcelas/").status_code, 401)

    # ------------------------------------------------------------------ #
    # 44 (spec 39): el trigger genera el código en la base de datos
    # ------------------------------------------------------------------ #
    def test_44_trigger_genera_codigos_consecutivos_en_bd(self):
        self._entrar_admin()
        primero = self._json(self._parcela())
        segundo = self._json(self._parcela())
        self.assertRegex(primero["codigo"], r"^P-\d{3}$")
        self.assertRegex(segundo["codigo"], r"^P-\d{3}$")
        n1 = int(primero["codigo"].split("-")[1])
        n2 = int(segundo["codigo"].split("-")[1])
        self.assertEqual(n2, n1 + 1)

        # También con INSERT directo (fuera de la API) y refresh_from_db
        bd = self._parcela_bd(productor=self.p2, comunidad=self.comunidad_b)
        self.assertRegex(bd.codigo, r"^P-\d{3}$")
        n3 = int(bd.codigo.split("-")[1])
        self.assertEqual(n3, n2 + 1)
        # El ORM no lo sabe hasta que se relee
        self.assertEqual(Parcela.objects.get(pk=bd.pk).codigo, bd.codigo)


class AsignacionApiTests(Semana4Base):
    """Pruebas 45-49: alta, rechazos (API y trigger), permisos, vida y
    auto-asignación."""

    # ------------------------------------------------------------------ #
    # 45 (spec 40): alta válida
    # ------------------------------------------------------------------ #
    def test_45_alta_valida_de_asignacion(self):
        self._entrar_admin()
        respuesta = self._asignar_api()
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        self.assertIn("id", fila)
        self.assertIs(fila["activo"], True)
        self.assertEqual(fila["fecha_asignacion"], timezone.localdate().isoformat())
        self.assertEqual(fila["tecnico"]["username"], "tec_pruebas")
        self.assertEqual(fila["tecnico"]["nombre_completo"], "tec_pruebas")
        self.assertEqual(fila["productor"]["id"], self.p1.pk)
        self.assertEqual(fila["productor"]["codigo"], self.p1.codigo)
        self.assertEqual(fila["productor"]["nombre_completo"], "Alfa, Uno")

        recuperada = self._json(
            self._api("get", f"/api/asignaciones/{fila['id']}/")
        )
        self.assertEqual(recuperada["id"], fila["id"])
        self.assertEqual(
            [f["id"] for f in self._json(
                self._api("get", f"/api/asignaciones/?productor={self.p1.pk}")
            )["results"]],
            [fila["id"]],
        )

    # ------------------------------------------------------------------ #
    # 46 (spec 41): rechazos de la API en español + red del trigger
    # ------------------------------------------------------------------ #
    def test_46_rechazos_en_espanol_y_red_del_trigger(self):
        self._entrar_admin()

        # Rol sin limita_a_asignados (decisión 8: la API valida antes)
        r = self._asignar_api(tecnico=self.admin)
        self.assertEqual(r.status_code, 400)
        self.assertIn(
            "no tiene un rol que trabaje",
            str(self._json(r)["tecnico"]),
        )

        # Productor inexistente
        r = self._api(
            "post", "/api/asignaciones/",
            {"tecnico": self.tecnico.pk, "productor": 999999},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("no existe", str(self._json(r)["productor"]))

        # Campos requeridos
        r = self._api("post", "/api/asignaciones/", {"productor": self.p1.pk})
        self.assertEqual(r.status_code, 400)
        texto = str(self._json(r)["tecnico"]).replace("é", "e")
        self.assertIn("El tecnico es obligatorio", texto)

        # Duplicada (uq_asignacion): se reactiva, no se duplica
        self.assertEqual(self._asignar_api().status_code, 201)
        r = self._asignar_api()
        self.assertEqual(r.status_code, 400)
        mensaje = str(self._json(r))
        self.assertIn("ya existe", mensaje)
        # El mensaje de usuario no revela rutas ni verbos HTTP (seguridad)
        self.assertNotIn("/api/", mensaje)
        self.assertNotIn("PATCH", mensaje)
        self.assertEqual(
            AsignacionTecnico.objects.filter(
                tecnico=self.tecnico, productor=self.p1
            ).count(),
            1,
        )

        # Red de seguridad: el trigger rechaza en SQL crudo lo mismo
        with self.assertRaises(DatabaseError) as fallo:
            with transaction.atomic():
                AsignacionTecnico.objects.create(
                    tecnico=self.coordinador, productor=self.p1
                )
        self.assertIn("no tiene un rol que trabaje", str(fallo.exception))
        self.assertFalse(
            AsignacionTecnico.objects.filter(
                tecnico=self.coordinador, productor=self.p1
            ).exists()
        )

    # ------------------------------------------------------------------ #
    # 47 (spec 42): permisos
    # ------------------------------------------------------------------ #
    def test_47_permisos_de_asignaciones(self):
        self.assertEqual(self._api("get", "/api/asignaciones/").status_code, 401)

        self._entrar("coord_pruebas", "Coord2026!")
        self.assertEqual(self._api("get", "/api/asignaciones/").status_code, 403)
        self.assertEqual(self._asignar_api().status_code, 403)
        self.assertEqual(
            self._api("get", "/api/asignaciones/tecnicos-disponibles/").status_code,
            403,
        )

        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        self.assertEqual(self._api("get", "/api/asignaciones/").status_code, 403)
        self.assertEqual(self._asignar_api().status_code, 403)
        self.assertEqual(
            self._api("get", "/api/asignaciones/tecnicos-disponibles/").status_code,
            403,
        )

        self.client.logout()
        self._entrar_admin()
        self.assertEqual(self._api("get", "/api/asignaciones/").status_code, 200)
        disponibles = self._json(
            self._api("get", "/api/asignaciones/tecnicos-disponibles/")
        )
        nombres = [u["username"] for u in disponibles]
        self.assertIn("tec_pruebas", nombres)
        self.assertNotIn("admin_pruebas", nombres)
        self.assertNotIn("coord_pruebas", nombres)
        for usuario in disponibles:
            self.assertIn("nombre_completo", usuario)

    # ------------------------------------------------------------------ #
    # 48 (spec 43): vida de la asignación (decisión 5)
    # ------------------------------------------------------------------ #
    def test_48_desactivar_reactivar_sin_edicion_ni_borrado(self):
        self._entrar_admin()
        asignacion = self._json(self._asignar_api())

        r = self._api(
            "patch",
            f"/api/asignaciones/{asignacion['id']}/estado/",
            {"activo": False},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIs(self._json(r)["activo"], False)
        self.assertIs(
            AsignacionTecnico.objects.get(pk=asignacion["id"]).activo, False
        )

        r = self._api(
            "patch",
            f"/api/asignaciones/{asignacion['id']}/estado/",
            {"activo": True},
        )
        self.assertIs(self._json(r)["activo"], True)

        r = self._api(
            "patch",
            f"/api/asignaciones/{asignacion['id']}/estado/",
            {"activo": "si"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("Debe ser true o false", str(self._json(r)))

        # Sin PUT/PATCH completos ni DELETE: reasignar = desactivar + crear
        cuerpo = {"tecnico": self.tecnico.pk, "productor": self.p2.pk}
        self.assertEqual(
            self._api("put", f"/api/asignaciones/{asignacion['id']}/", cuerpo).status_code,
            405,
        )
        self.assertEqual(
            self._api("patch", f"/api/asignaciones/{asignacion['id']}/", cuerpo).status_code,
            405,
        )
        self.assertEqual(
            self._api("delete", f"/api/asignaciones/{asignacion['id']}/").status_code,
            405,
        )
        self.assertEqual(AsignacionTecnico.objects.count(), 1)

    # ------------------------------------------------------------------ #
    # 49 (spec 44): auto-asignación atómica (decisión 4)
    # ------------------------------------------------------------------ #
    def test_49_alta_de_productor_por_el_tecnico_se_auto_asigna(self):
        self._entrar("tec_pruebas", "Tec2026!")
        respuesta = self._api(
            "post",
            "/api/productores/",
            {
                "nombres": "Auto",
                "apellidos": "Tecnico",
                "dni": "53000001",
                "comunidad": self.comunidad.pk,
            },
        )
        self.assertEqual(respuesta.status_code, 201)
        nuevo = self._json(respuesta)
        self.assertTrue(
            AsignacionTecnico.objects.filter(
                tecnico=self.tecnico, productor=nuevo["id"], activo=True
            ).exists()
        )
        visibles = self._json(self._api("get", "/api/productores/"))
        self.assertIn(nuevo["id"], [f["id"] for f in visibles["results"]])

        # Si lo crea el Administrador no se asigna a nadie
        self.client.logout()
        self._entrar_admin()
        respuesta = self._api(
            "post",
            "/api/productores/",
            {
                "nombres": "Sin",
                "apellidos": "Asignar",
                "dni": "53000002",
                "comunidad": self.comunidad.pk,
            },
        )
        self.assertEqual(respuesta.status_code, 201)
        otro = self._json(respuesta)
        self.assertFalse(
            AsignacionTecnico.objects.filter(productor=otro["id"]).exists()
        )


class FiltroAsignadosTests(Semana4Base):
    """Pruebas 50-53: filtro «solo mis productores», pérdida de acceso,
    ficha ampliada y 404 en español (decisiones 6, 7 y 11)."""

    # ------------------------------------------------------------------ #
    # 50 (spec 45): el técnico solo ve y edita los suyos (404, no 403)
    # ------------------------------------------------------------------ #
    def test_50_tecnico_solo_ve_los_suyos_y_ajenos_son_404(self):
        self._entrar_admin()
        pa1 = self._parcela_bd()
        pa2 = self._parcela_bd(productor=self.p2, comunidad=self.comunidad_b)
        self._asignar_api()

        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")

        visibles = self._json(self._api("get", "/api/productores/"))
        ids = [f["id"] for f in visibles["results"]]
        self.assertIn(self.p1.pk, ids)
        self.assertNotIn(self.p2.pk, ids)

        self.assertEqual(
            self._api("get", f"/api/productores/{self.p1.pk}/").status_code,
            200,
        )
        ajeno = self._api("get", f"/api/productores/{self.p2.pk}/")
        self.assertEqual(ajeno.status_code, 404)
        self.assertEqual(self._json(ajeno), {"detail": "No encontrado."})
        self.assertEqual(
            self._api(
                "patch",
                f"/api/productores/{self.p2.pk}/",
                {"referencia_ubicacion": "x"},
            ).status_code,
            404,
        )

        parcelas = self._json(self._api("get", "/api/parcelas/"))
        ids_pa = [f["id"] for f in parcelas["results"]]
        self.assertIn(pa1.pk, ids_pa)
        self.assertNotIn(pa2.pk, ids_pa)
        pa_ajeno = self._api("get", f"/api/parcelas/{pa2.pk}/")
        self.assertEqual(pa_ajeno.status_code, 404)
        self.assertEqual(self._json(pa_ajeno), {"detail": "No encontrado."})

        # Sin filtro para el coordinador (limita_a_asignados = False)
        self.client.logout()
        self._entrar("coord_pruebas", "Coord2026!")
        visibles = self._json(self._api("get", "/api/productores/"))
        ids = [f["id"] for f in visibles["results"]]
        self.assertIn(self.p1.pk, ids)
        self.assertIn(self.p2.pk, ids)

    # ------------------------------------------------------------------ #
    # 51 (spec 46): desactivar la asignación hace perder el acceso
    # ------------------------------------------------------------------ #
    def test_51_desactivar_asignacion_quita_el_acceso_y_reactivar_lo_devuelve(self):
        self._entrar_admin()
        asignacion = self._json(self._asignar_api())

        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        self.assertEqual(
            self._api("get", f"/api/productores/{self.p1.pk}/").status_code,
            200,
        )

        self.client.logout()
        self._entrar_admin()
        r = self._api(
            "patch",
            f"/api/asignaciones/{asignacion['id']}/estado/",
            {"activo": False},
        )
        self.assertEqual(r.status_code, 200)

        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        ajeno = self._api("get", f"/api/productores/{self.p1.pk}/")
        self.assertEqual(ajeno.status_code, 404)
        self.assertEqual(self._json(ajeno), {"detail": "No encontrado."})
        visibles = self._json(self._api("get", "/api/productores/"))
        self.assertNotIn(
            self.p1.pk, [f["id"] for f in visibles["results"]]
        )

        # Reactivar → vuelve el acceso
        self.client.logout()
        self._entrar_admin()
        self._api(
            "patch",
            f"/api/asignaciones/{asignacion['id']}/estado/",
            {"activo": True},
        )
        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        self.assertEqual(
            self._api("get", f"/api/productores/{self.p1.pk}/").status_code,
            200,
        )

    # ------------------------------------------------------------------ #
    # 52 (spec 47): ficha ampliada (decisión 7)
    # ------------------------------------------------------------------ #
    def test_52_ficha_ampliada_con_parcelas_resumen_y_tecnicos(self):
        self._entrar_admin()
        self._parcela_bd(superficie="2.00")
        self._parcela_bd(superficie="1.50")
        self._asignar_api()

        self.client.logout()
        self._entrar("tec_pruebas", "Tec2026!")
        ficha = self._json(
            self._api("get", f"/api/productores/{self.p1.pk}/")
        )
        self.assertNotIn("tecnicos_asignados", ficha)
        self.assertEqual(len(ficha["parcelas"]), 2)
        codigos = {p["codigo"] for p in ficha["parcelas"]}
        self.assertTrue(all(c.startswith("P-") for c in codigos))
        self.assertEqual(ficha["resumen"]["parcelas_activas"], 2)
        self.assertEqual(float(ficha["resumen"]["superficie_total_ha"]), 3.5)

        self.client.logout()
        self._entrar_admin()
        ficha = self._json(
            self._api("get", f"/api/productores/{self.p1.pk}/")
        )
        asignados = ficha["tecnicos_asignados"]
        self.assertEqual(len(asignados), 1)
        self.assertEqual(asignados[0]["username"], "tec_pruebas")
        self.assertIn("fecha_asignacion", asignados[0])

        self.client.logout()
        self._entrar("coord_pruebas", "Coord2026!")
        ficha = self._json(
            self._api("get", f"/api/productores/{self.p1.pk}/")
        )
        self.assertIn("tecnicos_asignados", ficha)
        self.assertEqual(ficha["tecnicos_asignados"][0]["username"], "tec_pruebas")

    # ------------------------------------------------------------------ #
    # 53 (spec 48): 404 en español y filtros de asignaciones (extras)
    # ------------------------------------------------------------------ #
    def test_53_404_en_espanol_y_filtros_de_asignaciones(self):
        self._entrar_admin()
        for url in (
            "/api/productores/999999/",
            "/api/parcelas/999999/",
            "/api/asignaciones/999999/",
        ):
            with self.subTest(url=url):
                respuesta = self._api("get", url)
                self.assertEqual(respuesta.status_code, 404)
                self.assertEqual(
                    self._json(respuesta), {"detail": "No encontrado."}
                )

        asignacion = self._json(self._asignar_api())
        por_productor = self._json(
            self._api("get", f"/api/asignaciones/?productor={self.p1.pk}")
        )
        self.assertEqual(
            [f["id"] for f in por_productor["results"]], [asignacion["id"]]
        )
        por_tecnico = self._json(
            self._api("get", f"/api/asignaciones/?tecnico={self.tecnico.pk}")
        )
        self.assertIn(
            asignacion["id"], [f["id"] for f in por_tecnico["results"]]
        )
        sin_asignacion = self._json(
            self._api("get", f"/api/asignaciones/?productor={self.p2.pk}")
        )
        self.assertEqual(sin_asignacion["count"], 0)

        respuesta = self._api("get", "/api/asignaciones/?tecnico=abc")
        self.assertEqual(respuesta.status_code, 400)
        texto = str(self._json(respuesta)).replace("é", "e")
        self.assertIn("id numerico", texto)
