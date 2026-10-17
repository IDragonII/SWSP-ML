import json
import time

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from auditoria.models import Auditoria

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
        # Semana 12: nombres y apellidos son obligatorios en el alta
        cuerpo = {
            "username": username,
            "password": "Productor2026!",
            "first_name": "Prueba",
            "last_name": "Api",
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

    def test_16_endpoint_con_permiso_devuelve_201(self):
        # Semana 12: el endpoint de prueba es ahora el CRUD completo
        self.assertEqual(_post_login(self.client, "admin_api", "AdminApi2026!").status_code, 200)
        respuesta = self._post_crear_usuario(username="creado_por_api")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["username"], "creado_por_api")
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


# ---------------------------------------------------------------------- #
# Semana 12: gestión de usuarios (pruebas 186 a 196)
# ---------------------------------------------------------------------- #
class GestionUsuariosApiTests(TestCase):
    """Pruebas 186 a 196: la API de gestión de usuarios — lista, alta,
    edición, desactivar/reactivar, restablecer contraseña, desbloquear y
    roles activos (HU-100 a HU-104), con las protecciones de la cuenta
    propia y del último gestor de roles."""

    def setUp(self):
        cache.clear()
        self.administrador = Rol.objects.get(nombre="Administrador")
        self.rol_coordinador = Rol.objects.get(nombre="Coordinador")
        self.admin = Usuario.objects.create_superuser(
            username="admin_gestion", email="admin@correo.test",
            password="AdminGestion2026!", rol=self.administrador,
        )
        self.admin.first_name = "Ana"
        self.admin.last_name = "Gestora"
        self.admin.save(update_fields=("first_name", "last_name"))
        self.coordinador = Usuario.objects.create_user(
            username="coord_gestion", password="Coord2026!",
            rol=self.rol_coordinador,
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_gestion", password="Tec2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )
        self.rol_vacio = Rol.objects.create(nombre="Rol vacío S12")
        self.ayudante = Usuario.objects.create_user(
            username="ayudante_gestion", password="Ayudante2026!",
            rol=self.rol_vacio,
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave, cliente=None):
        cliente = cliente or self.client
        self.assertEqual(_post_login(cliente, usuario, clave).status_code, 200)

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None, cliente=None):
        cliente = cliente or self.client
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(cliente, metodo)(url, **kwargs)

    def _datos_alta(self, **extra):
        datos = {
            "username": "nuevo_gestion",
            "password": "NuevaClave2026!",
            "first_name": "Nora",
            "last_name": "Nuevez",
            "rol": self.rol_coordinador.pk,
        }
        datos.update(extra)
        return datos

    # ------------------------------------------------------------------ #
    # 186-188: lista y alta
    # ------------------------------------------------------------------ #
    def test_186_lista_y_permisos(self):
        self.assertEqual(self._api("get", "/api/usuarios/").status_code, 401)
        self._entrar("ayudante_gestion", "Ayudante2026!")
        self.assertEqual(self._api("get", "/api/usuarios/").status_code, 403)

        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api("get", "/api/usuarios/")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = self._json(respuesta)
        self.assertEqual(cuerpo["count"], 4)
        fila = next(u for u in cuerpo["results"] if u["username"] == "admin_gestion")
        self.assertEqual(fila["nombre_completo"], "Ana Gestora")
        self.assertEqual(fila["rol"]["nombre"], "Administrador")
        self.assertFalse(fila["bloqueado"])
        self.assertTrue(fila["is_active"])

        # Búsqueda por nombre de usuario
        respuesta = self._api("get", "/api/usuarios/?busqueda=tec_gestion")
        cuerpo = self._json(respuesta)
        self.assertEqual(cuerpo["count"], 1)
        self.assertEqual(cuerpo["results"][0]["username"], "tec_gestion")

    def test_187_alta_valida_y_duplicado(self):
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api("post", "/api/usuarios/", self._datos_alta())
        self.assertEqual(respuesta.status_code, 201)
        cuerpo = self._json(respuesta)
        self.assertEqual(cuerpo["username"], "nuevo_gestion")
        self.assertEqual(cuerpo["nombre_completo"], "Nora Nuevez")
        self.assertEqual(cuerpo["rol"]["nombre"], "Coordinador")
        self.assertTrue(cuerpo["is_active"])
        self.assertNotIn("password", cuerpo)
        nuevo = Usuario.objects.get(username="nuevo_gestion")
        self.assertTrue(nuevo.check_password("NuevaClave2026!"))
        self.assertFalse(nuevo.check_password("NuevaClave2026"))

        # Duplicado: nombre y enlace al registro existente
        respuesta = self._api("post", "/api/usuarios/", self._datos_alta())
        self.assertEqual(respuesta.status_code, 400)
        cuerpo = self._json(respuesta)
        self.assertIn("Ya existe un usuario", str(cuerpo["username"]))
        existente = Usuario.objects.get(username="nuevo_gestion")
        self.assertEqual(cuerpo["usuario_existente"][0], str(existente.pk))
        self.assertEqual(Usuario.objects.count(), 5)

    def test_188_altas_invalidas(self):
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api(
            "post", "/api/usuarios/", self._datos_alta(first_name="")
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("nombres", str(self._json(respuesta)["first_name"]))

        respuesta = self._api(
            "post", "/api/usuarios/", self._datos_alta(password="123")
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("password", self._json(respuesta))

        respuesta = self._api(
            "post", "/api/usuarios/", self._datos_alta(rol=99999)
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("El rol indicado no existe", str(self._json(respuesta)["rol"]))

        inactivo = Rol.objects.create(nombre="Rol inactivo S12", activo=False)
        respuesta = self._api(
            "post", "/api/usuarios/", self._datos_alta(rol=inactivo.pk)
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("está inactivo", str(self._json(respuesta)["rol"]))
        self.assertEqual(Usuario.objects.count(), 4)

    # ------------------------------------------------------------------ #
    # 189-190: edición y desactivación
    # ------------------------------------------------------------------ #
    def test_189_edicion_username_inmutable_y_rol_propio(self):
        self._entrar("admin_gestion", "AdminGestion2026!")
        # El nombre de usuario no se modifica
        respuesta = self._api(
            "patch",
            f"/api/usuarios/{self.coordinador.pk}/",
            {"username": "otro_nombre"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "no se puede modificar", str(self._json(respuesta)["username"])
        )

        # Nadie cambia su propio rol
        respuesta = self._api(
            "patch",
            f"/api/usuarios/{self.admin.pk}/",
            {"rol": self.rol_coordinador.pk},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("tu propio rol", str(self._json(respuesta)["rol"]))

        # La contraseña no se toca por aquí
        respuesta = self._api(
            "patch",
            f"/api/usuarios/{self.coordinador.pk}/",
            {"password": "OtraClave2026!"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("restablecer-clave", str(self._json(respuesta)["password"]))

        # Edición válida de otro usuario (nombre y rol)
        respuesta = self._api(
            "patch",
            f"/api/usuarios/{self.coordinador.pk}/",
            {
                "first_name": "Carla",
                "last_name": "Coordina",
                "email": "carla@correo.test",
                "rol": self.administrador.pk,
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = self._json(respuesta)
        self.assertEqual(cuerpo["nombre_completo"], "Carla Coordina")
        self.assertEqual(cuerpo["rol"]["nombre"], "Administrador")
        self.assertEqual(cuerpo["username"], "coord_gestion")

        # Sin usuarios.editar: 403 (el Técnico no gestiona)
        self._entrar("tec_gestion", "Tec2026!")
        respuesta = self._api(
            "patch",
            f"/api/usuarios/{self.coordinador.pk}/",
            {"first_name": "Nadie"},
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_190_desactivar_no_afecta_la_cuenta_propia(self):
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api(
            "post", f"/api/usuarios/{self.admin.pk}/desactivar/"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "No puedes desactivar tu propia cuenta",
            str(self._json(respuesta)["estado"]),
        )

        respuesta = self._api(
            "post", f"/api/usuarios/{self.coordinador.pk}/desactivar/"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(self._json(respuesta)["is_active"])
        self.coordinador.refresh_from_db()
        self.assertFalse(self.coordinador.is_active)
        self.assertEqual(
            _post_login(self.client, "coord_gestion", "Coord2026!").status_code,
            401,
        )

        # Ya desactivada: 400
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api(
            "post", f"/api/usuarios/{self.coordinador.pk}/desactivar/"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("ya está desactivado", str(self._json(respuesta)["estado"]))

    # ------------------------------------------------------------------ #
    # 191-192: el último gestor de roles y la reactivación
    # ------------------------------------------------------------------ #
    def test_191_nunca_queda_sin_gestor_de_roles(self):
        # Un rol con permisos de gestión de usuarios pero SIN roles.gestionar:
        # es quien puede intentar dejar al sistema sin gestor.
        permisos = Permiso.objects.filter(
            codigo__in=('usuarios.ver', 'usuarios.editar', 'usuarios.desactivar')
        )
        rol_editor = Rol.objects.create(nombre="Editor de cuentas S12")
        rol_editor.permisos.set(permisos)
        editor = Usuario.objects.create_user(
            username="editor_gestion", password="Editor2026!", rol=rol_editor
        )
        self._entrar("editor_gestion", "Editor2026!")

        # El admin es el único activo con roles.gestionar: no se le puede
        # quitar el rol
        respuesta = self._api(
            "patch",
            f"/api/usuarios/{self.admin.pk}/",
            {"rol": self.rol_coordinador.pk},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "al menos un usuario activo con permiso para gestionar roles",
            str(self._json(respuesta)["estado"]),
        )
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol_id, self.administrador.pk)

        # ... ni desactivarlo
        respuesta = self._api(
            "post", f"/api/usuarios/{self.admin.pk}/desactivar/"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "al menos un usuario activo con permiso para gestionar roles",
            str(self._json(respuesta)["estado"]),
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

        # Con un segundo gestor activo la operación sí pasa
        Usuario.objects.create_user(
            username="admin2_gestion", password="Admin2Gestion2026!",
            rol=self.administrador,
        )
        respuesta = self._api(
            "post", f"/api/usuarios/{self.admin.pk}/desactivar/"
        )
        self.assertEqual(respuesta.status_code, 200)

        # El propio operador nunca se desactiva a sí mismo
        respuesta = self._api(
            "post", f"/api/usuarios/{editor.pk}/desactivar/"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "No puedes desactivar tu propia cuenta",
            str(self._json(respuesta)["estado"]),
        )

    def test_192_reactivar_una_cuenta(self):
        self._entrar("admin_gestion", "AdminGestion2026!")
        self._api("post", f"/api/usuarios/{self.tecnico.pk}/desactivar/")
        self.assertEqual(
            _post_login(self.client, "tec_gestion", "Tec2026!").status_code, 401
        )

        respuesta = self._api(
            "post", f"/api/usuarios/{self.tecnico.pk}/reactivar/"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self._json(respuesta)["is_active"])
        self.assertEqual(
            _post_login(self.client, "tec_gestion", "Tec2026!").status_code, 200
        )

        # Ya activa: 400
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api(
            "post", f"/api/usuarios/{self.tecnico.pk}/reactivar/"
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("ya está activo", str(self._json(respuesta)["estado"]))

    # ------------------------------------------------------------------ #
    # 193-194: restablecer contraseña y desbloquear
    # ------------------------------------------------------------------ #
    def test_193_restablecer_cierra_las_sesiones_abiertas(self):
        cliente_coord = Client()
        self._entrar("coord_gestion", "Coord2026!", cliente=cliente_coord)
        self.assertEqual(
            cliente_coord.get("/api/auth/me/").status_code, 200
        )
        self._entrar("admin_gestion", "AdminGestion2026!")

        # La cuenta propia no se restablece desde aquí (Sprint 7)
        respuesta = self._api(
            "post",
            f"/api/usuarios/{self.admin.pk}/restablecer-clave/",
            {"password": "Propia2026!"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("tu propia contraseña", str(self._json(respuesta)["password"]))

        # Contraseña débil: 400 (validadores de Django)
        respuesta = self._api(
            "post",
            f"/api/usuarios/{self.coordinador.pk}/restablecer-clave/",
            {"password": "123"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("password", self._json(respuesta))

        # Restablecer de otra cuenta: cierra sus sesiones y limpia bloqueos
        respuesta = self._api(
            "post",
            f"/api/usuarios/{self.coordinador.pk}/restablecer-clave/",
            {"password": "NuevaClave2026!"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Contraseña restablecida", respuesta.json()["detail"])
        self.assertEqual(
            cliente_coord.get("/api/auth/me/").status_code, 401
        )
        self.assertEqual(
            cliente_coord.post("/api/auth/refresh/").status_code, 401
        )
        self.assertEqual(
            _post_login(self.client, "coord_gestion", "Coord2026!").status_code,
            401,
        )
        self.assertEqual(
            _post_login(self.client, "coord_gestion", "NuevaClave2026!").status_code,
            200,
        )

    def test_194_desbloquear_el_acceso(self):
        for _ in range(settings.LOGIN_INTENTOS):
            _post_login(self.client, "coord_gestion", "ClaveQueNoEs")
        self.assertIsNotNone(ratelimit.segundos_de_bloqueo("coord_gestion"))
        self.assertEqual(
            _post_login(self.client, "coord_gestion", "Coord2026!").status_code,
            429,
        )

        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api(
            "post", f"/api/usuarios/{self.coordinador.pk}/desbloquear/"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("desbloqueado", respuesta.json()["detail"])
        self.assertIsNone(ratelimit.segundos_de_bloqueo("coord_gestion"))
        self.assertEqual(
            _post_login(self.client, "coord_gestion", "Coord2026!").status_code,
            200,
        )

        # Sin bloqueo activo: la respuesta lo aclara
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api(
            "post", f"/api/usuarios/{self.coordinador.pk}/desbloquear/"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("no estaba bloqueado", respuesta.json()["detail"])

    # ------------------------------------------------------------------ #
    # 195-196: roles desplegables y fin del CRUD
    # ------------------------------------------------------------------ #
    def test_195_roles_activos_para_el_desplegable(self):
        self.assertEqual(self._api("get", "/api/roles/").status_code, 401)
        self._entrar("ayudante_gestion", "Ayudante2026!")
        self.assertEqual(self._api("get", "/api/roles/").status_code, 403)

        Rol.objects.create(nombre="Rol oculto S12", activo=False)
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api("get", "/api/roles/")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = self._json(respuesta)
        # Sin paginación: la lista entera en la raíz
        nombres = [rol["nombre"] for rol in cuerpo]
        self.assertIn("Administrador", nombres)
        self.assertIn("Coordinador", nombres)
        self.assertIn("Técnico de campo", nombres)
        # El rol vacío está activo: aparece (asignable aunque no dé nada)
        self.assertIn("Rol vacío S12", nombres)
        self.assertNotIn("Rol oculto S12", nombres)

    def test_196_sin_borrado_y_sin_permiso(self):
        self._entrar("admin_gestion", "AdminGestion2026!")
        respuesta = self._api("delete", f"/api/usuarios/{self.tecnico.pk}/")
        self.assertEqual(respuesta.status_code, 405)

        # Sin usuarios.ver ni usuarios.editar: ni ficha ni edición
        self._entrar("ayudante_gestion", "Ayudante2026!")
        self.assertEqual(
            self._api("get", f"/api/usuarios/{self.admin.pk}/").status_code, 403
        )
        self.assertEqual(
            self._api(
                "patch", f"/api/usuarios/{self.admin.pk}/", {"first_name": "X"}
            ).status_code,
            403,
        )

        # Un usuario inexistente responde 404 (sin pistas)
        self._entrar("admin_gestion", "AdminGestion2026!")
        self.assertEqual(
            self._api("get", "/api/usuarios/99999/").status_code, 404
        )


# ---------------------------------------------------------------------- #
# Semana 13: cambio de contraseña propio (pruebas 211 a 220, RF-73)      #
# ---------------------------------------------------------------------- #
class CambioClaveApiTests(TestCase):
    """Pruebas 211-220: el cambio de la propia contraseña (HU-105 a
    HU-113) — cierra las sesiones abiertas, activa/desactiva la puerta
    debe_cambiar_clave del resto de la API y corta los intentos de prueba
    con un límite de 5 por hora."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_clave", email="", password="AdminClave2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_clave", password="CoordClave2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(_post_login(self.client, usuario, clave).status_code, 200)

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _marcar(self, usuario):
        usuario.debe_cambiar_clave = True
        usuario.save(update_fields=("debe_cambiar_clave",))

    def _cambiar(self, actual, nueva):
        return self._api(
            "post", "/api/auth/cambiar-clave/",
            {"password_actual": actual, "password_nueva": nueva},
        )

    # ------------------------------------------------------------------ #
    # 211: el cambio exitoso baja la marca, rota cookies y deja evento
    # ------------------------------------------------------------------ #
    def test_211_cambio_exitoso_baja_la_marca_cierra_sesiones_y_registra_evento(self):
        self._entrar("admin_clave", "AdminClave2026!")
        refresco_viejo = self.client.cookies["sigpa_refresh"].value
        self._marcar(self.admin)
        respuesta = self._cambiar("AdminClave2026!", "Cambiada2026!")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["detail"], "Contraseña actualizada.")
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.debe_cambiar_clave)
        self.assertTrue(self.admin.check_password("Cambiada2026!"))
        self.assertFalse(self.admin.check_password("AdminClave2026!"))
        # Cookies nuevas: la interfaz sigue dentro sin volver a entrar
        self.assertNotEqual(
            self.client.cookies["sigpa_refresh"].value, refresco_viejo
        )
        # El refresco anterior ya no sirve (marca de sesión)
        self.client.cookies["sigpa_refresh"] = refresco_viejo
        self.assertEqual(self.client.post("/api/auth/refresh/").status_code, 401)
        # Y la traza registra el cambio
        evento = Auditoria.objects.filter(accion="CAMBIAR_CLAVE").first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.usuario_id, self.admin.pk)
        self.assertEqual(evento.modulo, "usuarios")
        self.assertEqual(evento.tabla, "usuarios")
        self.assertEqual(evento.registro_id, self.admin.pk)

    # ------------------------------------------------------------------ #
    # 212: la contraseña actual no coincide -> 400 y nada cambia
    # ------------------------------------------------------------------ #
    def test_212_password_actual_incorrecta_no_cambia_nada(self):
        self._entrar("admin_clave", "AdminClave2026!")
        self._marcar(self.admin)
        respuesta = self._cambiar("ClaveQueNoEs", "Cambiada2026!")
        self.assertEqual(respuesta.status_code, 400)
        # El handler en español devuelve el mensaje suelto (decisión 12)
        self.assertEqual(
            respuesta.json()["password_actual"],
            "La contraseña actual no es correcta.",
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("AdminClave2026!"))
        self.assertTrue(self.admin.debe_cambiar_clave)
        self.assertFalse(
            Auditoria.objects.filter(accion="CAMBIAR_CLAVE").exists()
        )

    # ------------------------------------------------------------------ #
    # 213: la nueva pasa los validadores de Django (mensaje en español)
    # ------------------------------------------------------------------ #
    def test_213_la_nueva_contrasena_debe_pasar_los_validadores_de_django(self):
        self._entrar("admin_clave", "AdminClave2026!")
        self._marcar(self.admin)
        for invalida in ("1234", "123456789012", "password", "admin_clave123"):
            with self.subTest(clave=invalida):
                respuesta = self._cambiar("AdminClave2026!", invalida)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("password_nueva", respuesta.json())
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("AdminClave2026!"))
        self.assertTrue(self.admin.debe_cambiar_clave)

    # ------------------------------------------------------------------ #
    # 214: los dos campos son obligatorios
    # ------------------------------------------------------------------ #
    def test_214_los_dos_campos_son_obligatorios(self):
        self._entrar("admin_clave", "AdminClave2026!")
        respuesta = self._api("post", "/api/auth/cambiar-clave/", {})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["password_actual"],
            ["La contraseña actual es obligatoria."],
        )
        self.assertEqual(
            respuesta.json()["password_nueva"],
            ["La contraseña nueva es obligatoria."],
        )

    # ------------------------------------------------------------------ #
    # 215: 5 intentos por hora; el sexto recibe 429 con Retry-After
    # ------------------------------------------------------------------ #
    def test_215_maximo_cinco_intentos_por_hora_responde_429(self):
        self._entrar("admin_clave", "AdminClave2026!")
        for _ in range(5):
            self.assertEqual(
                self._cambiar("ClaveQueNoEs", "Cambiada2026!").status_code, 400
            )
        respuesta = self._cambiar("ClaveQueNoEs", "Cambiada2026!")
        self.assertEqual(respuesta.status_code, 429)
        cuerpo = respuesta.json()
        self.assertIn(
            "Demasiados intentos de cambio de contraseña", cuerpo["detail"]
        )
        self.assertGreater(cuerpo["retry_after"], 0)
        self.assertTrue(respuesta.get("Retry-After"))
        # Incluso con la contraseña correcta sigue cortado
        self.assertEqual(
            self._cambiar("AdminClave2026!", "Cambiada2026!").status_code, 429
        )

    # ------------------------------------------------------------------ #
    # 216: con la marca, la puerta cierra la API pero no la sesión
    # ------------------------------------------------------------------ #
    def test_216_con_la_marca_la_puerta_cierra_la_api_pero_no_la_sesion(self):
        self._entrar("admin_clave", "AdminClave2026!")
        self._marcar(self.admin)
        mensaje = "Debes cambiar tu contraseña antes de continuar."
        for url in (
            "/api/productores/",
            "/api/usuarios/",
            "/api/roles/",
            "/api/auditoria/",
            "/api/etapas-fenologicas/",
        ):
            with self.subTest(url=url):
                respuesta = self._api("get", url)
                self.assertEqual(respuesta.status_code, 403)
                self.assertEqual(respuesta.json()["detail"], mensaje)
        # La sesión sigue viva: /me y la renovación no se cortan
        me = self._json(self._api("get", "/api/auth/me/"))
        self.assertTrue(me["usuario"]["debe_cambiar_clave"])
        self.assertEqual(self.client.post("/api/auth/refresh/").status_code, 200)
        # cambiar-clave es la salida: no responde 403 (solo faltan los datos)
        self.assertEqual(
            self._api("post", "/api/auth/cambiar-clave/", {}).status_code, 400
        )
        self.assertEqual(
            self.client.post("/api/auth/logout/").status_code, 200
        )

    # ------------------------------------------------------------------ #
    # 217: tras cambiar la clave, la puerta se abre sin volver a entrar
    # ------------------------------------------------------------------ #
    def test_217_tras_cambiar_la_clave_la_puerta_se_abre(self):
        self._entrar("admin_clave", "AdminClave2026!")
        self._marcar(self.admin)
        self.assertEqual(self._api("get", "/api/productores/").status_code, 403)
        self.assertEqual(
            self._cambiar("AdminClave2026!", "Cambiada2026!").status_code, 200
        )
        self.assertEqual(self._api("get", "/api/productores/").status_code, 200)
        me = self._json(self._api("get", "/api/auth/me/"))
        self.assertFalse(me["usuario"]["debe_cambiar_clave"])

    # ------------------------------------------------------------------ #
    # 218: restablecer admin + cambio propio = el ciclo completo HU-112
    # ------------------------------------------------------------------ #
    def test_218_el_restablecimiento_admin_y_el_cambio_propio_completan_el_ciclo(self):
        self._entrar("admin_clave", "AdminClave2026!")
        self.assertEqual(
            self._api(
                "post",
                f"/api/usuarios/{self.coordinador.pk}/restablecer-clave/",
                {"password": "NuevaClave2026!"},
            ).status_code,
            200,
        )
        self.client.cookies.clear()
        # Primer ingreso con la clave nueva: entra, pero la API sigue cerrada
        entrada = _post_login(self.client, "coord_clave", "NuevaClave2026!")
        self.assertEqual(entrada.status_code, 200)
        self.assertTrue(entrada.json()["usuario"]["debe_cambiar_clave"])
        self.assertEqual(self._api("get", "/api/productores/").status_code, 403)
        # Cambia su contraseña y la API se abre (HU-113)
        self.assertEqual(
            self._cambiar("NuevaClave2026!", "PropiaClave2026!").status_code, 200
        )
        self.assertEqual(self._api("get", "/api/productores/").status_code, 200)
        self.coordinador.refresh_from_db()
        self.assertFalse(self.coordinador.debe_cambiar_clave)
        self.assertTrue(self.coordinador.check_password("PropiaClave2026!"))

    # ------------------------------------------------------------------ #
    # 219: login y /me exponen la marca; sin sesión, cambiar-clave es 401
    # ------------------------------------------------------------------ #
    def test_219_login_y_me_exponen_la_marca_y_sin_sesion_es_401(self):
        self._marcar(self.coordinador)
        entrada = _post_login(self.client, "coord_clave", "CoordClave2026!")
        self.assertEqual(entrada.status_code, 200)
        self.assertTrue(entrada.json()["usuario"]["debe_cambiar_clave"])
        self.assertTrue(
            self._json(self._api("get", "/api/auth/me/"))["usuario"][
                "debe_cambiar_clave"
            ]
        )
        self.coordinador.debe_cambiar_clave = False
        self.coordinador.save(update_fields=("debe_cambiar_clave",))
        self.assertFalse(
            self._json(self._api("get", "/api/auth/me/"))["usuario"][
                "debe_cambiar_clave"
            ]
        )
        # Sin sesión el endpoint pide autenticación (401, no 403)
        self.assertEqual(
            Client().post(
                "/api/auth/cambiar-clave/",
                data=json.dumps({}),
                content_type="application/json",
            ).status_code,
            401,
        )

    # ------------------------------------------------------------------ #
    # 220: un cambio exitoso limpia la ventana del límite de intentos
    # ------------------------------------------------------------------ #
    def test_220_un_cambio_exitoso_limpia_el_contador_del_limite(self):
        self._entrar("admin_clave", "AdminClave2026!")
        # Tres fallos y el cuarto intento (correcto) cabe en el límite de 5
        for _ in range(3):
            self.assertEqual(
                self._cambiar("ClaveQueNoEs", "Cambiada2026!").status_code, 400
            )
        self.assertEqual(
            self._cambiar("AdminClave2026!", "Cambiada2026!").status_code, 200
        )
        # El éxito limpia el contador: la siguiente petición vuelve a un
        # 400 normal (no un 429) y la ventana empieza de cero
        self.assertEqual(
            self._cambiar("ClaveQueNoEs", "OtraClave2026!").status_code, 400
        )
