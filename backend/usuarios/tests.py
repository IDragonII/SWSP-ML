from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

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
