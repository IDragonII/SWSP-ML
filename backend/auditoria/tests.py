"""Pruebas de la Semana 13: auditoría (RF-71/RF-72).

Numeración del repositorio 198-210 (13 pruebas): el registro de eventos
en los endpoints que escriben, la API de consulta con filtros, la
inmutabilidad garantizada por trigger y la separación entre lectura y
escritura. Las 10 pruebas de cambio de contraseña propio (211-220) viven
en usuarios/tests.py.
"""
import json
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, connection, transaction
from django.test import Client, TestCase
from django.utils import timezone

from catalogos.models import Cultivo, EtapaFenologica
from productores.models import (
    AsignacionTecnico,
    Comunidad,
    Distrito,
    Productor,
    Provincia,
)
from seguimiento.tests import Semana9Base
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import Auditoria
from .registrar import registrar_evento


class AuditoriaApiTests(TestCase):
    """Pruebas 198-209: eventos en los endpoints, la API de consulta y
    las reglas de inmutabilidad."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_aud", email="", password="AdminAud2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_aud", password="CoordAud2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_aud", password="TecAud2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )
        self.provincia = Provincia.objects.create(nombre="Prov AUD")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito AUD"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad AUD"
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar_admin(self):
        self.assertEqual(
            _post_login(self.client, "admin_aud", "AdminAud2026!").status_code,
            200,
        )

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _productor_bd(self, dni="88000001", nombres="Alta", apellidos="Aud"):
        productor = Productor.objects.create(
            nombres=nombres, apellidos=apellidos, dni=dni,
            comunidad=self.comunidad, creado_por=self.admin,
        )
        productor.refresh_from_db()
        return productor

    def _ultimo(self, **filtros):
        return Auditoria.objects.filter(**filtros).order_by("-id").first()

    def _hoy_lima(self):
        return timezone.now().astimezone(ZoneInfo("America/Lima")).date()

    # ------------------------------------------------------------------ #
    # 198: alta de productor -> CREAR con usuario, tabla, id e IP
    # ------------------------------------------------------------------ #
    def test_198_alta_de_productor_registra_evento_crear(self):
        self._entrar_admin()
        respuesta = self._api(
            "post", "/api/productores/",
            {"nombres": "Ana", "apellidos": "Zambrano", "dni": "11111111",
             "comunidad": self.comunidad.pk},
        )
        self.assertEqual(respuesta.status_code, 201)
        productor_id = self._json(respuesta)["id"]
        evento = self._ultimo(accion="CREAR", tabla="productores")
        self.assertIsNotNone(evento)
        self.assertEqual(evento.usuario_id, self.admin.pk)
        self.assertEqual(evento.usuario.username, "admin_aud")
        self.assertEqual(evento.modulo, "productores")
        self.assertEqual(evento.registro_id, productor_id)
        self.assertEqual(str(evento.ip), "127.0.0.1")
        self.assertIsNone(evento.detalle)

    # ------------------------------------------------------------------ #
    # 199: estado del productor -> ACTIVAR/DESACTIVAR; sin cambio no duplica
    # ------------------------------------------------------------------ #
    def test_199_estado_del_productor_registra_activar_y_desactivar(self):
        productor = self._productor_bd()
        self._entrar_admin()
        self.assertEqual(
            self._api(
                "patch", f"/api/productores/{productor.pk}/estado/",
                {"estado": "INACTIVO"},
            ).status_code,
            200,
        )
        self.assertEqual(
            self._ultimo(tabla="productores", registro_id=productor.pk).accion,
            "DESACTIVAR",
        )
        total = Auditoria.objects.filter(
            tabla="productores", registro_id=productor.pk
        ).count()
        # El mismo estado de nuevo no genera un evento repetido
        self._api(
            "patch", f"/api/productores/{productor.pk}/estado/",
            {"estado": "INACTIVO"},
        )
        self.assertEqual(
            Auditoria.objects.filter(
                tabla="productores", registro_id=productor.pk
            ).count(),
            total,
        )
        self._api(
            "patch", f"/api/productores/{productor.pk}/estado/",
            {"estado": "ACTIVO"},
        )
        self.assertEqual(
            self._ultimo(tabla="productores", registro_id=productor.pk).accion,
            "ACTIVAR",
        )

    # ------------------------------------------------------------------ #
    # 200: login y logout dejan su rastro
    # ------------------------------------------------------------------ #
    def test_200_login_y_logout_registran_sus_eventos(self):
        self.assertEqual(
            _post_login(self.client, "coord_aud", "CoordAud2026!").status_code,
            200,
        )
        login = self._ultimo(accion="LOGIN")
        self.assertEqual(login.usuario_id, self.coordinador.pk)
        self.assertEqual(login.modulo, "usuarios")
        self.assertEqual(login.tabla, "usuarios")
        self.assertEqual(login.registro_id, self.coordinador.pk)

        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        logout = self._ultimo(accion="LOGOUT")
        self.assertEqual(logout.usuario_id, self.coordinador.pk)
        self.assertIsNone(logout.registro_id)

    # ------------------------------------------------------------------ #
    # 201: asignar y desasignar técnico
    # ------------------------------------------------------------------ #
    def test_201_asignacion_registra_asignar_y_desasignar(self):
        productor = self._productor_bd()
        self._entrar_admin()
        respuesta = self._api(
            "post", "/api/asignaciones/",
            {"tecnico": self.tecnico.pk, "productor": productor.pk},
        )
        self.assertEqual(respuesta.status_code, 201)
        asignacion_id = self._json(respuesta)["id"]
        evento = self._ultimo(accion="ASIGNAR", tabla="asignaciones_tecnico")
        self.assertEqual(evento.usuario_id, self.admin.pk)
        self.assertEqual(evento.registro_id, asignacion_id)
        self.assertEqual(evento.modulo, "asignaciones")

        self.assertEqual(
            self._api(
                "patch", f"/api/asignaciones/{asignacion_id}/estado/",
                {"activo": False},
            ).status_code,
            200,
        )
        self.assertEqual(
            self._ultimo(tabla="asignaciones_tecnico").accion, "DESASIGNAR"
        )
        self.assertTrue(
            AsignacionTecnico.objects.get(pk=asignacion_id).activo is False
        )

    # ------------------------------------------------------------------ #
    # 202: desactivar y reactivar una cuenta
    # ------------------------------------------------------------------ #
    def test_202_cuentas_registran_desactivar_y_reactivar(self):
        self._entrar_admin()
        self.assertEqual(
            self._api(
                "post", f"/api/usuarios/{self.coordinador.pk}/desactivar/"
            ).status_code,
            200,
        )
        evento = self._ultimo(accion="DESACTIVAR", tabla="usuarios")
        # El evento guarda quién actuó (admin) y a quién (registro_id)
        self.assertEqual(evento.usuario_id, self.admin.pk)
        self.assertEqual(evento.registro_id, self.coordinador.pk)
        self.coordinador.refresh_from_db()
        self.assertFalse(self.coordinador.is_active)

        self.assertEqual(
            self._api(
                "post", f"/api/usuarios/{self.coordinador.pk}/reactivar/"
            ).status_code,
            200,
        )
        self.assertEqual(
            self._ultimo(accion="ACTIVAR", tabla="usuarios").registro_id,
            self.coordinador.pk,
        )
        self.coordinador.refresh_from_db()
        self.assertTrue(self.coordinador.is_active)

    # ------------------------------------------------------------------ #
    # 203: restablecer la clave deja RESTABLECER_CLAVE y la marca de
    #     cambio obligatorio en el primer ingreso (HU-112)
    # ------------------------------------------------------------------ #
    def test_203_restablecer_clave_registra_evento_y_exige_cambio(self):
        self._entrar_admin()
        respuesta = self._api(
            "post", f"/api/usuarios/{self.coordinador.pk}/restablecer-clave/",
            {"password": "NuevaClaveAud2026!"},
        )
        self.assertEqual(respuesta.status_code, 200)
        evento = self._ultimo(accion="RESTABLECER_CLAVE", tabla="usuarios")
        self.assertEqual(evento.usuario_id, self.admin.pk)
        self.assertEqual(evento.registro_id, self.coordinador.pk)
        self.coordinador.refresh_from_db()
        self.assertTrue(self.coordinador.debe_cambiar_clave)
        # El primer ingreso con la clave nueva avisa de que hay que cambiarla
        self.client.cookies.clear()
        entrada = _post_login(self.client, "coord_aud", "NuevaClaveAud2026!")
        self.assertEqual(entrada.status_code, 200)
        self.assertTrue(entrada.json()["usuario"]["debe_cambiar_clave"])

    # ------------------------------------------------------------------ #
    # 204: bloqueo por intentos fallidos y desbloqueo administrativo
    # ------------------------------------------------------------------ #
    def test_204_bloqueo_y_desbloqueo_registran_eventos(self):
        for _ in range(settings.LOGIN_INTENTOS - 1):
            self.assertEqual(
                _post_login(self.client, "coord_aud", "ClaveQueNoEs").status_code,
                401,
            )
        respuesta = _post_login(self.client, "coord_aud", "ClaveQueNoEs")
        self.assertEqual(respuesta.status_code, 429)
        bloqueo = self._ultimo(accion="BLOQUEAR", tabla="usuarios")
        self.assertEqual(bloqueo.usuario_id, self.coordinador.pk)
        self.assertEqual(bloqueo.detalle, {"username": "coord_aud"})

        self._entrar_admin()
        self.assertEqual(
            self._api(
                "post", f"/api/usuarios/{self.coordinador.pk}/desbloquear/"
            ).json()["detail"],
            "Acceso desbloqueado.",
        )
        self.assertEqual(
            self._ultimo(accion="DESBLOQUEAR").registro_id, self.coordinador.pk
        )
        # Un segundo desbloqueo no repite el evento (no había bloqueo)
        self._api("post", f"/api/usuarios/{self.coordinador.pk}/desbloquear/")
        self.assertEqual(
            Auditoria.objects.filter(accion="DESBLOQUEAR").count(), 1
        )

    # ------------------------------------------------------------------ #
    # 205: la API de consulta exige auditoria.ver y pagina 20 por página
    # ------------------------------------------------------------------ #
    def test_205_consultar_auditoria_exige_permiso_y_pagina(self):
        # 21 eventos directos bastan para forzar una segunda página
        for indice in range(21):
            registrar_evento(
                usuario=self.admin, accion="MODIFICAR", modulo="pruebas",
                detalle={"n": indice},
            )
        self._entrar_admin()
        respuesta = self._api("get", "/api/auditoria/")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = self._json(respuesta)
        # 21 eventos directos + el LOGIN del admin = 22
        self.assertEqual(cuerpo["count"], 22)
        self.assertEqual(len(cuerpo["results"]), 20)
        segunda = self._json(self._api("get", "/api/auditoria/?page=2"))
        self.assertEqual(len(segunda["results"]), 2)
        fila = cuerpo["results"][0]
        self.assertEqual(
            set(fila),
            {"id", "fecha", "usuario", "accion", "modulo", "tabla",
             "registro_id", "detalle", "ip"},
        )
        self.assertEqual(fila["usuario"]["username"], "admin_aud")
        # El orden es del más reciente al más antiguo
        self.assertGreater(fila["id"], segunda["results"][0]["id"])

        # Sin auditoria.ver no se consulta la tabla (ni su existencia)
        self.client.cookies.clear()
        _post_login(self.client, "coord_aud", "CoordAud2026!")
        respuesta = self._api("get", "/api/auditoria/")
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("No tienes permiso", respuesta.json()["detail"])
        self.client.cookies.clear()
        _post_login(self.client, "tec_aud", "TecAud2026!")
        self.assertEqual(self._api("get", "/api/auditoria/").status_code, 403)
        self.assertEqual(Client().get("/api/auditoria/").status_code, 401)

    # ------------------------------------------------------------------ #
    # 206: filtros por usuario, módulo, acción, tabla, registro y fechas
    # ------------------------------------------------------------------ #
    def test_206_filtros_de_la_api_de_auditoria(self):
        self._entrar_admin()
        productor_id = self._json(
            self._api(
                "post", "/api/productores/",
                {"nombres": "Filtro", "apellidos": "Pruebas",
                 "dni": "11111122", "comunidad": self.comunidad.pk},
            )
        )["id"]
        self._api(
            "patch", f"/api/productores/{productor_id}/estado/",
            {"estado": "INACTIVO"},
        )
        hoy = self._hoy_lima()

        todo = self._json(self._api("get", "/api/auditoria/"))
        self.assertGreaterEqual(todo["count"], 3)

        por_accion = self._json(self._api("get", "/api/auditoria/?accion=LOGIN"))
        self.assertGreaterEqual(por_accion["count"], 1)
        self.assertTrue(
            all(f["accion"] == "LOGIN" for f in por_accion["results"])
        )

        por_modulo = self._json(
            self._api("get", "/api/auditoria/?modulo=productores")
        )
        self.assertGreaterEqual(por_modulo["count"], 2)
        self.assertTrue(
            all(f["modulo"] == "productores" for f in por_modulo["results"])
        )

        por_usuario = self._json(
            self._api("get", f"/api/auditoria/?usuario={self.admin.pk}")
        )
        self.assertGreaterEqual(por_usuario["count"], 3)
        sin_eventos = self._json(
            self._api("get", f"/api/auditoria/?usuario={self.tecnico.pk}")
        )
        self.assertEqual(sin_eventos["count"], 0)

        por_registro = self._json(
            self._api(
                "get",
                f"/api/auditoria/?tabla=productores&registro={productor_id}",
            )
        )
        self.assertEqual(por_registro["count"], 2)
        self.assertEqual(
            {f["accion"] for f in por_registro["results"]},
            {"CREAR", "DESACTIVAR"},
        )

        por_fecha = self._json(
            self._api("get", f"/api/auditoria/?fecha_desde={hoy}")
        )
        self.assertGreaterEqual(por_fecha["count"], 3)
        ayer = hoy - timedelta(days=1)
        sin_futuro = self._json(
            self._api("get", f"/api/auditoria/?fecha_hasta={ayer}")
        )
        self.assertEqual(sin_futuro["count"], 0)

        buscada = self._json(
            self._api("get", "/api/auditoria/?busqueda=usuarios")
        )
        self.assertGreaterEqual(buscada["count"], 1)
        self.assertTrue(
            all("usuarios" in (f["modulo"], f["tabla"]) for f in buscada["results"])
        )

        self.assertEqual(
            self._api("get", "/api/auditoria/?usuario=abc").status_code, 400
        )

    # ------------------------------------------------------------------ #
    # 207: ni UPDATE ni DELETE pasan el trigger inmutable
    # ------------------------------------------------------------------ #
    def test_207_los_eventos_no_se_pueden_modificar_ni_eliminar(self):
        registrar_evento(
            usuario=self.admin, accion="CREAR", modulo="pruebas",
            tabla="productores", registro_id=1,
        )
        evento_id = Auditoria.objects.latest("id").pk
        mensaje = (
            "Los registros de auditoría no se pueden modificar ni eliminar."
        )
        with self.assertRaises(DatabaseError) as ctx_mod:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE auditoria SET detalle = %s WHERE id = %s",
                        [json.dumps({"tocado": True}), evento_id],
                    )
        self.assertIn(mensaje, str(ctx_mod.exception))
        with self.assertRaises(DatabaseError) as ctx_del:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM auditoria WHERE id = %s", [evento_id]
                    )
        self.assertIn(mensaje, str(ctx_del.exception))
        evento = Auditoria.objects.get(pk=evento_id)
        self.assertIsNone(evento.detalle)

    # ------------------------------------------------------------------ #
    # 208: la API de auditoría es solo lectura
    # ------------------------------------------------------------------ #
    def test_208_la_api_de_auditoria_es_solo_lectura(self):
        registrar_evento(
            usuario=self.admin, accion="CREAR", modulo="pruebas"
        )
        evento_id = Auditoria.objects.latest("id").pk
        self._entrar_admin()
        self.assertEqual(self._api("get", f"/api/auditoria/{evento_id}/").status_code, 200)
        self.assertEqual(
            self._api("get", "/api/auditoria/99999999/").status_code, 404
        )
        self.assertEqual(self._api("post", "/api/auditoria/", {}).status_code, 405)
        for metodo, url in (
            ("patch", f"/api/auditoria/{evento_id}/"),
            ("put", f"/api/auditoria/{evento_id}/"),
            ("delete", f"/api/auditoria/{evento_id}/"),
        ):
            with self.subTest(metodo=metodo):
                self.assertEqual(self._api(metodo, url, {}).status_code, 405)

    # ------------------------------------------------------------------ #
    # 209: leer no deja eventos; la reescritura de etapas sí, con detalle
    # ------------------------------------------------------------------ #
    def test_209_las_lecturas_no_dejan_eventos_y_reordenar_registra_modificar(self):
        cultivo = Cultivo.objects.create(nombre="Quinua AUD")
        etapa_a = EtapaFenologica.objects.create(
            cultivo=cultivo, nombre="Siembra", orden=1
        )
        etapa_b = EtapaFenologica.objects.create(
            cultivo=cultivo, nombre="Floración", orden=2
        )
        self._entrar_admin()
        total = Auditoria.objects.count()
        for url in (
            "/api/productores/",
            "/api/cultivos/",
            "/api/auditoria/",
            f"/api/cultivos/{cultivo.pk}/",
        ):
            self.assertEqual(self._api("get", url).status_code, 200, url)
        self.assertEqual(Auditoria.objects.count(), total)

        respuesta = self._api(
            "post", "/api/etapas-fenologicas/reordenar/",
            {"cultivo": cultivo.pk, "orden": [etapa_b.pk, etapa_a.pk]},
        )
        self.assertEqual(respuesta.status_code, 200)
        evento = self._ultimo(accion="MODIFICAR", tabla="cultivos")
        self.assertEqual(evento.modulo, "catalogos")
        self.assertEqual(evento.registro_id, cultivo.pk)
        self.assertEqual(
            evento.detalle,
            {"cultivo": cultivo.pk, "orden": [etapa_b.pk, etapa_a.pk]},
        )


class AuditoriaSeguimientoTests(Semana9Base):
    """Prueba 210: anular con motivo y reactivar quedan en la traza."""

    def test_210_anular_y_reactivar_registran_eventos_con_el_motivo(self):
        self._entrar_admin()
        uso_id = self._json(self._crear_uso())["id"]
        self.assertEqual(self._anular_uso(uso_id, motivo="Duplicado").status_code, 200)
        evento = (
            Auditoria.objects.filter(accion="ANULAR")
            .order_by("-id")
            .first()
        )
        self.assertEqual(evento.modulo, "seguimiento")
        self.assertEqual(evento.registro_id, uso_id)
        self.assertEqual(evento.detalle, {"motivo": "Duplicado"})

        self.assertEqual(
            self._api(
                "post", f"/api/usos-recursos/{uso_id}/reactivar/", {}
            ).status_code,
            200,
        )
        self.assertEqual(
            Auditoria.objects.filter(accion="REACTIVAR")
            .order_by("-id")
            .first()
            .registro_id,
            uso_id,
        )
