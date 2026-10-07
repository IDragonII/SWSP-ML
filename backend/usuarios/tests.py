import json
import time

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from . import ratelimit
from .models import Permiso, Rol, RolPermiso, Usuario


class SemillaTests(TestCase):
    def test_datos_iniciales(self):
        self.assertEqual(Permiso.objects.count(), 55)
        self.assertEqual(Rol.objects.count(), 3)

        self.assertEqual(Permiso.objects.get(codigo="usuarios.ver").descripcion, "Ver usuarios")
        self.assertEqual(Permiso.objects.get(codigo="produccion.crear").modulo, "Producción")
        self.assertEqual(Permiso.objects.get(codigo="ml.predecir").modulo, "Machine Learning")

        tecnico = Rol.objects.get(nombre="Técnico de campo")
        self.assertTrue(tecnico.es_sistema)
        self.assertTrue(tecnico.limita_a_asignados)
        coordinador = Rol.objects.get(nombre="Coordinador")
        self.assertFalse(coordinador.limita_a_asignados)

    def test_asignaciones_iniciales(self):
        self.assertEqual(RolPermiso.objects.count(), 101)

        administrador = Rol.objects.get(nombre="Administrador")
        tecnico = Rol.objects.get(nombre="Técnico de campo")
        coordinador = Rol.objects.get(nombre="Coordinador")
        self.assertEqual(administrador.permisos.count(), 55)
        self.assertEqual(tecnico.permisos.count(), 32)
        self.assertEqual(coordinador.permisos.count(), 14)

        codigos_tecnico = set(tecnico.permisos.values_list("codigo", flat=True))
        self.assertIn("productores.crear", codigos_tecnico)
        self.assertNotIn("usuarios.crear", codigos_tecnico)
        self.assertNotIn("roles.gestionar", codigos_tecnico)

        codigos_coordinador = set(coordinador.permisos.values_list("codigo", flat=True))
        self.assertIn("productores.ver", codigos_coordinador)
        self.assertNotIn("productores.crear", codigos_coordinador)
        self.assertNotIn("alertas.atender", codigos_coordinador)


class ReglasDeNegocioTests(TestCase):
    def test_trigger_protege_rol_del_sistema(self):
        mensaje = 'El rol "Administrador" es un rol del sistema y no se puede eliminar.'
        with self.assertRaises(DatabaseError) as ctx:
            with transaction.atomic():
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM roles WHERE nombre = 'Administrador'")
        self.assertIn(mensaje, str(ctx.exception))
        self.assertTrue(Rol.objects.filter(nombre="Administrador").exists())

    def test_rol_normal_se_puede_eliminar(self):
        rol = Rol.objects.create(nombre="TMP temporal", es_sistema=False)
        rol.delete()
        self.assertFalse(Rol.objects.filter(nombre="TMP temporal").exists())

    def test_rol_con_usuarios_no_se_puede_eliminar(self):
        rol = Rol.objects.create(nombre="TMP con usuario", es_sistema=False)
        Usuario.objects.create(username="tecnico_tmp", rol=rol)
        with self.assertRaises(ProtectedError):
            rol.delete()
        self.assertTrue(Rol.objects.filter(nombre="TMP con usuario").exists())

    def test_usuario_requiere_rol(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create(username="sin_rol")

    def test_permiso_duplicado_en_rol(self):
        rol = Rol.objects.create(nombre="TMP permiso", es_sistema=False)
        permiso = Permiso.objects.get(codigo="dashboard.ver")
        RolPermiso.objects.create(rol=rol, permiso=permiso)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RolPermiso.objects.create(rol=rol, permiso=permiso)


class PanelAdminTests(TestCase):
    def test_panel_admin(self):
        administrador = Rol.objects.get(nombre="Administrador")
        usuario = Usuario.objects.create_superuser(
            username="admin_prueba", email="", password="ClaveDePrueba123", rol=administrador
        )
        self.client.force_login(usuario)

        for nombre_url in (
            "admin:index",
            "admin:usuarios_usuario_changelist",
            "admin:usuarios_usuario_add",
            "admin:usuarios_usuario_change",
            "admin:usuarios_rol_changelist",
            "admin:usuarios_rol_change",
            "admin:usuarios_permiso_changelist",
            "admin:usuarios_rolpermiso_changelist",
        ):
            args = [usuario.pk] if nombre_url == "admin:usuarios_usuario_change" else (
                [administrador.pk] if nombre_url == "admin:usuarios_rol_change" else []
            )
            respuesta = self.client.get(reverse(nombre_url, args=args))
            self.assertEqual(respuesta.status_code, 200, nombre_url)

        # En un rol del sistema el campo nombre aparece solo lectura
        respuesta = self.client.get(reverse("admin:usuarios_rol_change", args=[administrador.pk]))
        self.assertIn("nombre", respuesta.context["adminform"].readonly_fields)


def _post_login(client, username, password):
    return client.post(
        "/api/auth/login/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )


class AutenticacionApiTests(TestCase):
    """Pruebas 9 a 14 y 18 de la Semana 2: login, renovación, me y logout."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_api", email="", password="AdminApi2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )

    def test_09_login_correcto_devuelve_tokens_rol_y_permisos(self):
        respuesta = _post_login(self.client, "admin_api", "AdminApi2026!")
        self.assertEqual(respuesta.status_code, 200)
        # Los tokens viajan en cookies httpOnly
        self.assertIn("sigpa_access", respuesta.cookies)
        self.assertIn("sigpa_refresh", respuesta.cookies)
        self.assertTrue(respuesta.cookies["sigpa_access"]["httponly"])
        self.assertTrue(respuesta.cookies["sigpa_refresh"]["httponly"])
        # y el cuerpo trae usuario, rol y permisos
        usuario = respuesta.json()["usuario"]
        self.assertEqual(usuario["rol"]["nombre"], "Administrador")
        self.assertEqual(len(usuario["permisos"]), 55)
        self.assertIn("usuarios.crear", usuario["permisos"])

    def test_10_password_incorrecta_y_usuario_inexistente_dan_el_mismo_mensaje(self):
        clave_mala = _post_login(self.client, "admin_api", "ClaveQueNoEs")
        inexistente = _post_login(self.client, "nadie_tiene_este_usuario", "ClaveQueNoEs")
        self.assertEqual(clave_mala.status_code, 401)
        self.assertEqual(inexistente.status_code, 401)
        self.assertEqual(clave_mala.json(), inexistente.json())
        self.assertEqual(clave_mala.json(), {"detail": "Credenciales incorrectas."})

    def test_11_usuario_desactivado_no_inicia_sesion(self):
        usuario = Usuario.objects.create_user(
            username="desactivado_api", password="Desactivado2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        usuario.is_active = False
        usuario.save()
        respuesta = _post_login(self.client, "desactivado_api", "Desactivado2026!")
        self.assertEqual(respuesta.status_code, 401)
        # Misma respuesta que cualquier otra credencial fallida
        self.assertEqual(respuesta.json(), {"detail": "Credenciales incorrectas."})

    def test_12_renovacion_con_token_valido_funciona(self):
        _post_login(self.client, "admin_api", "AdminApi2026!")
        refresh_original = self.client.cookies["sigpa_refresh"].value
        respuesta = self.client.post("/api/auth/refresh/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.json())
        # Con rotación activa también llega un refresh nuevo
        self.assertIn("refresh", respuesta.json())
        self.assertIn("sigpa_refresh", respuesta.cookies)
        self.assertNotEqual(respuesta.cookies["sigpa_refresh"].value, refresh_original)

    def test_13_renovacion_invalida_o_ya_cerrada_se_rechaza(self):
        # Token inválido (basura)
        self.client.cookies["sigpa_refresh"] = "token-basura"
        respuesta = self.client.post("/api/auth/refresh/")
        self.assertEqual(respuesta.status_code, 401)
        # Token ya usado (rotado en una renovación anterior)
        _post_login(self.client, "admin_api", "AdminApi2026!")
        viejo = self.client.cookies["sigpa_refresh"].value
        renovado = self.client.post("/api/auth/refresh/")
        self.assertEqual(renovado.status_code, 200)
        self.client.cookies["sigpa_refresh"] = viejo
        respuesta = self.client.post("/api/auth/refresh/")
        self.assertEqual(respuesta.status_code, 401)

    def test_14_datos_del_usuario_sin_token_devuelven_401(self):
        respuesta = self.client.get("/api/auth/me/")
        self.assertEqual(respuesta.status_code, 401)

    def test_18_cerrar_sesion_invalida_el_token(self):
        _post_login(self.client, "admin_api", "AdminApi2026!")
        refresh = self.client.cookies["sigpa_refresh"].value
        cierre = self.client.post("/api/auth/logout/")
        self.assertEqual(cierre.status_code, 200)
        self.assertEqual(cierre.json(), {"detail": "Sesión cerrada."})
        # El refresh recién cerrado ya no sirve
        self.client.cookies["sigpa_refresh"] = refresh
        respuesta = self.client.post("/api/auth/refresh/")
        self.assertEqual(respuesta.status_code, 401)
        # Cerrar de nuevo con esa sesión también es 401
        respuesta = self.client.post("/api/auth/logout/")
        self.assertEqual(respuesta.status_code, 401)


class PermisosApiTests(TestCase):
    """Pruebas 15 y 16 (y la extra 20): la clase TienePermiso en acción."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_api", email="", password="AdminApi2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_api", password="Coordinador2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )

    def _post_crear_usuario(self, username="nuevo_prueba"):
        cuerpo = {
            "username": username,
            "password": "Productor2026!",
            "rol": Rol.objects.get(nombre="Coordinador").pk,
        }
        return self.client.post(
            "/api/usuarios/", data=json.dumps(cuerpo), content_type="application/json"
        )

    def test_15_endpoint_protegido_sin_permiso_devuelve_403(self):
        self.assertEqual(_post_login(self.client, "coord_api", "Coordinador2026!").status_code, 200)
        respuesta = self._post_crear_usuario()
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("No tienes permiso", respuesta.json()["detail"])
        # Sin sesión, el mismo endpoint responde 401
        self.assertEqual(Client().post(
            "/api/usuarios/",
            data=json.dumps({"username": "x", "password": "Productor2026!", "rol": 1}),
            content_type="application/json",
        ).status_code, 401)

    def test_16_endpoint_con_permiso_devuelve_200(self):
        self.assertEqual(_post_login(self.client, "admin_api", "AdminApi2026!").status_code, 200)
        respuesta = self._post_crear_usuario(username="creado_por_api")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["usuario"]["username"], "creado_por_api")
        self.assertTrue(Usuario.objects.filter(username="creado_por_api").exists())

    def test_20_cambio_de_permisos_se_refleja_en_la_siguiente_consulta(self):
        # Extra: los permisos no viajan en el token, así que /me siempre está al día
        self.assertEqual(_post_login(self.client, "coord_api", "Coordinador2026!").status_code, 200)
        permisos = self.client.get("/api/auth/me/").json()["usuario"]["permisos"]
        self.assertNotIn("ml.predecir", permisos)
        self.coordinador.rol.permisos.add(Permiso.objects.get(codigo="ml.predecir"))
        permisos = self.client.get("/api/auth/me/").json()["usuario"]["permisos"]
        self.assertIn("ml.predecir", permisos)
        self.coordinador.rol.permisos.remove(Permiso.objects.get(codigo="ml.predecir"))


class RateLimitTests(TestCase):
    """Prueba 17 (y la extra 19): límite de intentos y bloqueo temporal."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_api", email="", password="AdminApi2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )

    def test_17_tras_superar_el_limite_el_login_devuelve_429(self):
        for _ in range(settings.LOGIN_INTENTOS - 1):
            respuesta = _post_login(self.client, "admin_api", "ClaveQueNoEs")
            self.assertEqual(respuesta.status_code, 401)
        respuesta = _post_login(self.client, "admin_api", "ClaveQueNoEs")
        self.assertEqual(respuesta.status_code, 429)
        self.assertIn("minuto", respuesta.json()["detail"])
        self.assertGreater(respuesta.json()["retry_after"], 0)
        self.assertTrue(respuesta.get("Retry-After"))
        # Incluso con la contraseña correcta sigue bloqueada
        respuesta = _post_login(self.client, "admin_api", "AdminApi2026!")
        self.assertEqual(respuesta.status_code, 429)

    def test_19_el_bloqueo_se_levanta_con_el_tiempo(self):
        # Extra: bloqueamos y simulamos el paso de LOGIN_BLOQUEO_MINUTOS
        for _ in range(settings.LOGIN_INTENTOS):
            _post_login(self.client, "admin_api", "ClaveQueNoEs")
        self.assertIsNotNone(ratelimit.segundos_de_bloqueo("admin_api"))
        # La fecha de desbloqueo almacenada queda en el pasado = tiempo cumplido
        cache.set(
            ratelimit.PREFIJO_BLOQUEO + "admin_api",
            time.time() - 1,
            timeout=60,
        )
        self.assertIsNone(ratelimit.segundos_de_bloqueo("admin_api"))
        respuesta = _post_login(self.client, "admin_api", "AdminApi2026!")
        self.assertEqual(respuesta.status_code, 200)
