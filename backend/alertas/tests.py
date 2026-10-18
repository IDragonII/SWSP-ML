"""Pruebas de la Semana 15: alertas y productores en riesgo (HU-124..HU-132).

Numeración del repositorio 242-262 (21 pruebas → 262 en total; el
repositorio llegaba a 241 con la matriz de calidad). Cubren la
evaluación (creación, cierre automático, reapertura, idempotencia, fecha
de Lima y evento resumen), la API (atender, reabrir, alcance y
privacidad del Técnico, 401/403, filtros, riesgo, resumen, evaluación
manual con límite y estado de atraso), los parámetros de la semana y las
restricciones de la tabla. Los ganchos on_commit se prueban con
captureOnCommitCallbacks (TestCase no confirma transacciones).
"""
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Variedad
from productores.models import (
    AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia,
)
from seguimiento.models import Actividad, Incidencia, TipoIncidencia
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import Alerta
from .servicio import evaluar_campania, evaluar_incidencia, evaluar_todo, fecha_hoy

_TZ_LIMA = ZoneInfo("America/Lima")


class AlertasBase(TestCase):
    """Cuentas, ubicación, cultivo, dos productores (el primero con
    asignación al Técnico), campañas con actividad antigua y reciente e
    helpers de API, servicio y datos por BD."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_alertas", email="", password="AdminAlertas2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_alertas", password="CoordAlertas2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_alertas", password="TecAlertas2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )
        self.provincia = Provincia.objects.create(nombre="Prov S15")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S15"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S15"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua S15")
        self.variedad = Variedad.objects.create(
            cultivo=self.cultivo, nombre="Real S15"
        )
        self.preparacion = TipoActividad.objects.get(codigo="PREPARACION")
        self.helada = TipoIncidencia.objects.get(nombre="Helada")
        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="93000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p2 = Productor.objects.create(
            nombres="Dos", apellidos="Beta", dni="93000002",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        AsignacionTecnico.objects.create(tecnico=self.tecnico, productor=self.p1)
        self.hoy = fecha_hoy()
        self.parcela = self._parcela_bd(self.p1, "2.00")
        self.parcela_fresca = self._parcela_bd(self.p1, "1.50")
        self.parcela_b = self._parcela_bd(self.p2, "3.00")
        # Campaña con última actividad antigua (45 días): genera
        # SIN_ACTIVIDAD con el umbral por defecto de 30
        self.campania_vieja = self._campania_bd(self.parcela)
        self._actividad_bd(self.campania_vieja, self.hoy - timedelta(days=45))
        # Campaña con actividad reciente: no genera alerta
        self.campania_fresca = self._campania_bd(self.parcela_fresca)
        self._actividad_bd(self.campania_fresca, self.hoy - timedelta(days=5))
        # Campaña del segundo productor (fuera del ámbito del Técnico),
        # con actividad reciente para que no genere su propia alerta
        self.campania_ajena = self._campania_bd(self.parcela_b)
        self._actividad_bd(self.campania_ajena, self.hoy - timedelta(days=3))

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_alertas", "AdminAlertas2026!")

    def _entrar_tecnico(self):
        self._entrar("tec_alertas", "TecAlertas2026!")

    def _entrar_coordinador(self):
        self._entrar("coord_alertas", "CoordAlertas2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _parcela_bd(self, productor, superficie):
        parcela = Parcela.objects.create(
            productor=productor, comunidad=self.comunidad,
            superficie_ha=superficie, altitud_msnm=3850,
            tipo_suelo="FRANCO", pendiente="SUAVE",
            disponibilidad_agua="MEDIA", sistema_riego="GOTEO",
        )
        parcela.refresh_from_db()
        return parcela

    def _campania_bd(self, parcela, **extra):
        datos = {
            "periodo": f"{self.hoy.year}-{self.hoy.year + 1}",
            "parcela": parcela,
            "cultivo": self.cultivo,
            "variedad": self.variedad,
            "fecha_inicio": self.hoy - timedelta(days=60),
            "fecha_fin_prevista": self.hoy + timedelta(days=120),
            "estado": Campania.ESTADO_EN_PRODUCCION,
            "superficie_sembrada_ha": Decimal("1.50"),
        }
        datos.update(extra)
        return Campania.objects.create(**datos)

    def _actividad_bd(self, campania, fecha):
        return Actividad.objects.create(
            campania=campania, tipo_actividad=self.preparacion,
            fecha=fecha, registrado_por=self.admin,
        )

    def _incidencia_bd(self, campania=None, **extra):
        datos = {
            "campania": campania or self.campania_fresca,
            "tipo_incidencia": self.helada,
            "fecha": self.hoy - timedelta(days=5),
            "severidad": Incidencia.ALTA,
            "descripcion": "Helada fuerte de la Semana 15",
            "registrado_por": self.admin,
        }
        datos.update(extra)
        return Incidencia.objects.create(**datos)

    def _alerta_bd(self, campania=None, **extra):
        campania = campania or self.campania_vieja
        datos = {
            "productor": campania.parcela.productor,
            "campania": campania,
            "tipo": Alerta.TIPO_SIN_ACTIVIDAD,
            "mensaje": f"La campaña {campania.periodo} no registra actividades.",
        }
        datos.update(extra)
        return Alerta.objects.create(**datos)

    def _datos_incidencia(self, **extra):
        datos = {
            "campania": self.campania_fresca.pk,
            "tipo_incidencia": self.helada.pk,
            "fecha": str(self.hoy - timedelta(days=5)),
            "severidad": "ALTA",
            "descripcion": "Helada severa por API",
        }
        datos.update(extra)
        return datos


class EvaluacionAlertasTests(AlertasBase):
    """Pruebas 242-250: la lógica de evaluación del servicio."""

    # ------------------------------------------------------------------ #
    # 242: incidencia severa crea una sola alerta (HU-124)
    # ------------------------------------------------------------------ #
    def test_242_incidencia_severa_crea_una_alerta_unica_por_incidencia(self):
        self._entrar_admin()
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self._api(
                "post", "/api/incidencias/", self._datos_incidencia()
            )
        self.assertEqual(respuesta.status_code, 201)
        incidencia = Incidencia.objects.get(pk=self._json(respuesta)["id"])
        alertas = Alerta.objects.filter(incidencia=incidencia)
        self.assertEqual(alertas.count(), 1)
        alerta = alertas.get()
        self.assertEqual(alerta.tipo, Alerta.TIPO_INCIDENCIA_SEVERA)
        self.assertEqual(alerta.productor, self.campania_fresca.parcela.productor)
        self.assertFalse(alerta.atendida)
        # Reevaluar (barrido) no duplica: una sola por incidencia (el
        # barrido sí puede crear la SIN_ACTIVIDAD de la campaña vieja)
        evaluar_todo(hoy=self.hoy)
        self.assertEqual(Alerta.objects.filter(incidencia=incidencia).count(), 1)

    # ------------------------------------------------------------------ #
    # 243: anular cierra; reactivar reabre; lo atendido a mano no se toca
    # ------------------------------------------------------------------ #
    def test_243_ciclo_de_reapertura_de_la_incidencia_severa(self):
        self._entrar_admin()
        with self.captureOnCommitCallbacks(execute=True):
            creada = self._api(
                "post", "/api/incidencias/", self._datos_incidencia()
            )
        incidencia = Incidencia.objects.get(pk=self._json(creada)["id"])
        alerta = Alerta.objects.get(incidencia=incidencia)
        # Anular → cierre automático (sin usuario)
        with self.captureOnCommitCallbacks(execute=True):
            self._api(
                "post", f"/api/incidencias/{incidencia.pk}/anular/",
                {"motivo": "Era un error de registro"},
            )
        alerta.refresh_from_db()
        self.assertTrue(alerta.atendida)
        self.assertIsNone(alerta.atendida_por)
        self.assertIsNone(alerta.nota_atencion)
        # Reactivar → se reabre sola
        with self.captureOnCommitCallbacks(execute=True):
            self._api(
                "post", f"/api/incidencias/{incidencia.pk}/reactivar/"
            )
        alerta.refresh_from_db()
        self.assertFalse(alerta.atendida)
        # Atendida a mano, anular ya no la cierra (queda como histórico)
        with self.captureOnCommitCallbacks(execute=True):
            self._api(
                "post", f"/api/alertas/{alerta.pk}/atender/", {"nota": "Vista"}
            )
        with self.captureOnCommitCallbacks(execute=True):
            self._api(
                "post", f"/api/incidencias/{incidencia.pk}/anular/",
                {"motivo": "Segunda anulación"},
            )
        alerta.refresh_from_db()
        self.assertTrue(alerta.atendida)
        self.assertIsNotNone(alerta.atendida_por)
        # Reactivar no reabre lo atendido a mano
        with self.captureOnCommitCallbacks(execute=True):
            self._api(
                "post", f"/api/incidencias/{incidencia.pk}/reactivar/"
            )
        alerta.refresh_from_db()
        self.assertTrue(alerta.atendida)

    # ------------------------------------------------------------------ #
    # 244: SIN_ACTIVIDAD con fecha inyectada (HU-129)
    # ------------------------------------------------------------------ #
    def test_244_sin_actividad_con_fecha_inyectada(self):
        resultado = evaluar_todo(hoy=self.hoy)
        self.assertEqual(resultado["creadas"], 1)
        alerta = Alerta.objects.get(tipo=Alerta.TIPO_SIN_ACTIVIDAD)
        self.assertEqual(alerta.campania, self.campania_vieja)
        self.assertFalse(alerta.atendida)
        # La fresca y la ajena no generan (actividad reciente)
        self.assertEqual(
            Alerta.objects.filter(campania__in=[
                self.campania_fresca, self.campania_ajena
            ]).count(),
            0,
        )
        # Un día antes del umbral no habría creado nada: la campaña
        # vieja tiene 45 días de inactividad; con umbral 90 no alerta
        parametro = self._parametro("dias_sin_actividad")
        parametro.valor = "90"
        parametro.save(update_fields=("valor",))
        Alerta.objects.all().delete()
        resultado = evaluar_todo(hoy=self.hoy)
        self.assertEqual(resultado["creadas"], 0)

    # ------------------------------------------------------------------ #
    # 245: una pendiente por campaña+tipo y gracia tras atención manual
    # ------------------------------------------------------------------ #
    def test_245_una_pendiente_por_campania_y_gracia_tras_atender(self):
        resultado = evaluar_todo(hoy=self.hoy)
        self.assertEqual(resultado["creadas"], 1)
        # Segunda evaluación: idempotente, no duplica
        resultado = evaluar_todo(hoy=self.hoy)
        self.assertEqual(resultado["creadas"], 0)
        alerta = Alerta.objects.get(campania=self.campania_vieja)
        # Atención manual
        alerta.atendida = True
        alerta.atendida_por = self.admin
        alerta.atendida_en = timezone.now()
        alerta.save(update_fields=("atendida", "atendida_por", "atendida_en"))
        # Dentro de la gracia (30 días): no reaparece
        resultado = evaluar_todo(hoy=self.hoy)
        self.assertEqual(resultado["creadas"], 0)
        # Pasada la gracia: reaparece como fila nueva
        alerta.atendida_en = timezone.now() - timedelta(days=31)
        alerta.save(update_fields=("atendida_en",))
        resultado = evaluar_todo(hoy=self.hoy)
        self.assertEqual(resultado["creadas"], 1)
        self.assertEqual(
            Alerta.objects.filter(
                campania=self.campania_vieja, atendida=False
            ).count(),
            1,
        )

    # ------------------------------------------------------------------ #
    # 246: actividad nueva cierra la pendiente (hook de la API)
    # ------------------------------------------------------------------ #
    def test_246_actividad_nueva_cierra_la_pendiente(self):
        evaluar_todo(hoy=self.hoy)
        alerta = Alerta.objects.get(campania=self.campania_vieja)
        self._entrar_admin()
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self._api(
                "post", "/api/actividades/",
                {
                    "campania": self.campania_vieja.pk,
                    "tipo_actividad": self.preparacion.pk,
                    "fecha": str(self.hoy),
                    "metodo": "Control de malezas",
                },
            )
        self.assertEqual(respuesta.status_code, 201)
        alerta.refresh_from_db()
        self.assertTrue(alerta.atendida)
        self.assertIsNone(alerta.atendida_por)  # cierre automático
        self.assertIsNone(alerta.nota_atencion)

    # ------------------------------------------------------------------ #
    # 247: cancelar la campaña cierra sus pendientes (HU-130)
    # ------------------------------------------------------------------ #
    def test_247_cancelar_campania_cierra_sus_pendientes(self):
        evaluar_todo(hoy=self.hoy)
        alerta = Alerta.objects.get(campania=self.campania_vieja)
        self._entrar_admin()
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self._api(
                "post", f"/api/campanias/{self.campania_vieja.pk}/cancelar/",
                {"motivo": "El productor se retiró"},
            )
        self.assertEqual(respuesta.status_code, 200)
        alerta.refresh_from_db()
        self.assertTrue(alerta.atendida)
        self.assertIsNone(alerta.atendida_por)
        self.campania_vieja.refresh_from_db()
        self.assertEqual(self.campania_vieja.estado, Campania.ESTADO_CANCELADA)

    # ------------------------------------------------------------------ #
    # 248: el comando es idempotente y dry-run no escribe (HU-131)
    # ------------------------------------------------------------------ #
    def test_248_comando_idempotente_y_dry_run(self):
        call_command("evaluar_alertas")
        self.assertEqual(Alerta.objects.filter(atendida=False).count(), 1)
        # Segunda corrida: nada nuevo
        call_command("evaluar_alertas")
        self.assertEqual(Alerta.objects.filter(atendida=False).count(), 1)
        # Dry-run sobre un escenario nuevo no escribe
        Alerta.objects.all().delete()
        call_command("evaluar_alertas", "--dry-run")
        self.assertEqual(Alerta.objects.count(), 0)
        # Y sin dry-run sí crea
        call_command("evaluar_alertas")
        self.assertEqual(Alerta.objects.count(), 1)

    # ------------------------------------------------------------------ #
    # 249: fecha de Lima en el mensaje; --hoy solo con DEBUG
    # ------------------------------------------------------------------ #
    def test_249_fecha_de_lima_y_hoy_solo_en_debug(self):
        evaluar_todo(hoy=self.hoy)
        alerta = Alerta.objects.get(tipo=Alerta.TIPO_SIN_ACTIVIDAD)
        referencia = self.hoy - timedelta(days=45)
        self.assertIn(str(referencia), alerta.mensaje)
        # --hoy es de prueba y solo con DEBUG
        with self.assertRaises(CommandError):
            call_command("evaluar_alertas", "--hoy", "2026-01-15")
        with override_settings(DEBUG=True):
            with patch("alertas.servicio.fecha_hoy", return_value=self.hoy):
                call_command("evaluar_alertas", "--hoy", str(self.hoy))
        # La fecha de Lima manda sobre la UTC cuando difieren
        self.assertEqual(
            fecha_hoy(), timezone.now().astimezone(_TZ_LIMA).date()
        )

    # ------------------------------------------------------------------ #
    # 250: evento resumen de la evaluación en auditoría (HU-132)
    # ------------------------------------------------------------------ #
    def test_250_evento_resumen_de_evaluacion(self):
        from auditoria.models import Auditoria

        evaluar_todo(hoy=self.hoy)
        evento = (
            Auditoria.objects.filter(
                modulo="alertas", tabla="alertas", detalle__resumen=True
            )
            .order_by("-fecha")
            .first()
        )
        self.assertIsNotNone(evento)
        self.assertEqual(evento.accion, "MODIFICAR")
        self.assertIsNone(evento.usuario)
        self.assertEqual(evento.detalle["creadas"], 1)
        self.assertEqual(evento.detalle["cerradas"], 0)
        # El dry-run no registra evento nuevo (los eventos son
        # inmutables: no se borra nada para comprobarlo)
        eventos_previos = Auditoria.objects.filter(tabla="alertas").count()
        evaluar_todo(hoy=self.hoy, dry_run=True)
        self.assertEqual(
            Auditoria.objects.filter(tabla="alertas").count(), eventos_previos
        )

    # ------------------------------------------------------------------ #
    # helpers internos
    # ------------------------------------------------------------------ #
    def _parametro(self, clave):
        from sistema.models import ParametroSistema

        return ParametroSistema.objects.get(clave=clave)


class ApiAlertasTests(AlertasBase):
    """Pruebas 251-259: la API de alertas."""

    def setUp(self):
        super().setUp()
        self.alerta = self._alerta_bd()  # pendiente de la campaña vieja

    # ------------------------------------------------------------------ #
    # 251: atender con permiso, nota y auditoría (HU-125)
    # ------------------------------------------------------------------ #
    def test_251_atender_con_permiso_y_auditoria(self):
        from auditoria.models import Auditoria

        self._entrar_admin()
        respuesta = self._api(
            "post", f"/api/alertas/{self.alerta.pk}/atender/",
            {"nota": "Se llamó al productor; agendará visita."},
        )
        self.assertEqual(respuesta.status_code, 200)
        datos = self._json(respuesta)
        self.assertTrue(datos["atendida"])
        self.assertEqual(
            datos["nota_atencion"], "Se llamó al productor; agendará visita."
        )
        evento = Auditoria.objects.filter(
            modulo="alertas", tabla="alertas", registro_id=self.alerta.pk
        ).order_by("-fecha").first()
        self.assertIsNotNone(evento)
        # Doble atender: 400 en español
        segunda = self._api(
            "post", f"/api/alertas/{self.alerta.pk}/atender/", {}
        )
        self.assertEqual(segunda.status_code, 400)
        self.assertIn("atendida", self._json(segunda)["estado"])

    # ------------------------------------------------------------------ #
    # 252: reabrir solo lo atendido a mano; lo automático no (HU-125)
    # ------------------------------------------------------------------ #
    def test_252_reabrir_solo_lo_mano(self):
        self._entrar_admin()
        # Lo automático no se reabre a mano
        self.alerta.atendida = True
        self.alerta.atendida_en = timezone.now()
        self.alerta.save(update_fields=("atendida", "atendida_en"))
        automatica = self._api(
            "post", f"/api/alertas/{self.alerta.pk}/reabrir/"
        )
        self.assertEqual(automatica.status_code, 400)
        self.assertIn(
            "automáticamente", self._json(automatica)["estado"]
        )
        # De vuelta a pendiente: lo atendido a mano sí se reabre
        self.alerta.atendida = False
        self.alerta.atendida_en = None
        self.alerta.save(update_fields=("atendida", "atendida_en"))
        self._api(
            "post", f"/api/alertas/{self.alerta.pk}/atender/",
            {"nota": "Revisado"},
        )
        reabierta = self._api(
            "post", f"/api/alertas/{self.alerta.pk}/reabrir/"
        )
        self.assertEqual(reabierta.status_code, 200)
        datos = self._json(reabierta)
        self.assertFalse(datos["atendida"])
        self.assertIsNone(datos["nota_atencion"])
        # Reabrir una pendiente: 400
        otra = self._api("post", f"/api/alertas/{self.alerta.pk}/reabrir/")
        self.assertEqual(otra.status_code, 400)

    # ------------------------------------------------------------------ #
    # 253: alcance del Técnico y privacidad del atendiente (HU-128)
    # ------------------------------------------------------------------ #
    def test_253_alcance_del_tecnico_y_privacidad(self):
        ajena = self._alerta_bd(campania=self.campania_ajena)
        self._entrar_admin()
        self._api(
            "post", f"/api/alertas/{ajena.pk}/atender/",
            {"nota": "Coordinador interviene"},
        )
        # El Técnico solo ve la suya
        self._entrar_tecnico()
        listado = self._json(self._api("get", "/api/alertas/"))
        ids = [f["id"] for f in listado["results"]]
        self.assertIn(self.alerta.pk, ids)
        self.assertNotIn(ajena.pk, ids)
        # El detalle ajeno responde 404, nunca 403
        ajeno = self._api("get", f"/api/alertas/{ajena.pk}/")
        self.assertEqual(ajeno.status_code, 404)
        # Privacidad: el Técnico no ve quién atendió
        self._api("post", f"/api/alertas/{self.alerta.pk}/atender/", {})
        detalle = self._json(self._api("get", f"/api/alertas/{self.alerta.pk}/"))
        self.assertIsNone(detalle["atendida_por_nombre"])
        # El Administrador sí lo ve (quien la atendió fue el Técnico,
        # sin nombre completo → username)
        self._entrar_admin()
        detalle = self._json(self._api("get", f"/api/alertas/{self.alerta.pk}/"))
        self.assertEqual(detalle["atendida_por_nombre"], "tec_alertas")

    # ------------------------------------------------------------------ #
    # 254: 401 sin sesión y 403 sin permiso (HU-125)
    # ------------------------------------------------------------------ #
    def test_254_sin_sesion_401_y_sin_permiso_403(self):
        sin_sesion = self._api("get", "/api/alertas/")
        self.assertEqual(sin_sesion.status_code, 401)
        self._entrar_coordinador()  # tiene alertas.ver, no alertas.atender
        self.assertEqual(self._api("get", "/api/alertas/").status_code, 200)
        atender = self._api(
            "post", f"/api/alertas/{self.alerta.pk}/atender/", {}
        )
        self.assertEqual(atender.status_code, 403)
        evaluar = self._api("post", "/api/alertas/evaluar/", {})
        self.assertEqual(evaluar.status_code, 403)

    # ------------------------------------------------------------------ #
    # 255: filtros y búsqueda del listado (HU-127)
    # ------------------------------------------------------------------ #
    def test_255_filtros_y_busqueda(self):
        atendida = self._alerta_bd(
            campania=self.campania_fresca,
            tipo=Alerta.TIPO_INCIDENCIA_SEVERA,
            incidencia=self._incidencia_bd(),
        )
        atendida.atendida = True
        atendida.atendida_en = timezone.now()
        atendida.atendida_por = self.admin
        atendida.save(
            update_fields=("atendida", "atendida_en", "atendida_por")
        )
        self._entrar_admin()
        # Por defecto solo pendientes
        listado = self._json(self._api("get", "/api/alertas/"))
        ids = [f["id"] for f in listado["results"]]
        self.assertEqual(ids, [self.alerta.pk])
        # ATENDIDAS
        listado = self._json(self._api("get", "/api/alertas/?estado=ATENDIDAS"))
        self.assertEqual(
            [f["id"] for f in listado["results"]], [atendida.pk]
        )
        # TODAS
        listado = self._json(self._api("get", "/api/alertas/?estado=TODAS"))
        self.assertEqual(listado["count"], 2)
        # Por tipo
        listado = self._json(
            self._api("get", "/api/alertas/?estado=TODAS&tipo=SIN_ACTIVIDAD")
        )
        self.assertEqual(listado["count"], 1)
        # Estado inválido: 400 en español
        mala = self._api("get", "/api/alertas/?estado=OTRA")
        self.assertEqual(mala.status_code, 400)
        self.assertIn("PENDIENTES", str(self._json(mala)["estado"]))
        # Búsqueda por código del productor
        listado = self._json(
            self._api("get", f"/api/alertas/?busqueda={self.p1.codigo}")
        )
        self.assertGreaterEqual(listado["count"], 1)

    # ------------------------------------------------------------------ #
    # 256: productores en riesgo (HU-126)
    # ------------------------------------------------------------------ #
    def test_256_productores_en_riesgo(self):
        evaluar_todo(hoy=self.hoy)  # crea la de la campaña vieja (p1)
        # La pendiente de p2 se crea después del barrido: la campaña
        # tiene actividad reciente y el barrido la cerraría
        self._alerta_bd(campania=self.campania_ajena)
        self._entrar_admin()
        datos = self._json(self._api("get", "/api/alertas/productores-en-riesgo/"))
        filas = {f["productor"]: f for f in datos["results"]}
        self.assertIn(self.p1.pk, filas)
        self.assertIn(self.p2.pk, filas)
        self.assertEqual(filas[self.p1.pk]["pendientes"], 1)
        self.assertEqual(filas[self.p1.pk]["tipos"], ["SIN_ACTIVIDAD"])
        self.assertEqual(filas[self.p2.pk]["pendientes"], 1)
        # El Técnico solo ve la fila de su productor
        self._entrar_tecnico()
        datos = self._json(self._api("get", "/api/alertas/productores-en-riesgo/"))
        self.assertEqual(
            [f["productor"] for f in datos["results"]], [self.p1.pk]
        )

    # ------------------------------------------------------------------ #
    # 257: resumen de la insignia (HU-127)
    # ------------------------------------------------------------------ #
    def test_257_resumen_de_pendientes(self):
        self._alerta_bd(campania=self.campania_ajena)
        self._entrar_admin()
        datos = self._json(self._api("get", "/api/alertas/resumen/"))
        self.assertEqual(datos["pendientes"], 2)
        self._entrar_tecnico()
        datos = self._json(self._api("get", "/api/alertas/resumen/"))
        self.assertEqual(datos["pendientes"], 1)

    # ------------------------------------------------------------------ #
    # 258: evaluación manual con límite de una cada 5 minutos (HU-131)
    # ------------------------------------------------------------------ #
    def test_258_evaluacion_manual_con_limite(self):
        # Sin la pendiente del setUp para que el barrido cree una nueva
        self.alerta.delete()
        self._entrar_admin()
        primera = self._api("post", "/api/alertas/evaluar/", {})
        self.assertEqual(primera.status_code, 200)
        datos = self._json(primera)
        self.assertEqual(datos["creadas"], 1)
        self.assertFalse(datos["dry_run"])
        self.assertEqual(Alerta.objects.filter(atendida=False).count(), 1)
        # Segunda en la ventana: 429 con el mensaje propio (hallazgo de
        # F6: el manejador global de Throttled lo habría sobrescrito)
        segunda = self._api("post", "/api/alertas/evaluar/", {})
        self.assertEqual(segunda.status_code, 429)
        cuerpo = self._json(segunda)
        self.assertIn("5 minutos", cuerpo["detail"])
        self.assertGreater(cuerpo["retry_after"], 0)
        self.assertTrue(segunda.get("Retry-After"))
        # Dry-run admite el parámetro (tras limpiar la caché)
        cache.clear()
        seca = self._api(
            "post", "/api/alertas/evaluar/", {"dry_run": True}
        )
        self.assertEqual(seca.status_code, 200)
        self.assertTrue(self._json(seca)["dry_run"])

    # ------------------------------------------------------------------ #
    # 259: estado de la evaluación y atraso de 36 horas (HU-132)
    # ------------------------------------------------------------------ #
    def test_259_estado_de_evaluacion_y_atraso(self):
        self._entrar_admin()
        # Sin eventos: atrasada
        estado = self._json(self._api("get", "/api/alertas/evaluacion/"))
        self.assertTrue(estado["atrasada"])
        self.assertIsNone(estado["ultima_evaluacion"])
        self.assertEqual(estado["umbral_horas"], 36)
        # Un evento de hace 40 horas sigue marcando atraso (INSERT
        # directo permitido: el trigger solo bloquea UPDATE/DELETE)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO auditoria "
                "(usuario_id, accion, modulo, tabla, detalle, fecha) "
                "VALUES (NULL, %s, %s, %s, %s, now() - interval '40 hours')",
                [
                    "MODIFICAR",
                    "alertas",
                    "alertas",
                    '{"resumen": true, "creadas": 0, "cerradas": 0}',
                ],
            )
        estado = self._json(self._api("get", "/api/alertas/evaluacion/"))
        self.assertTrue(estado["atrasada"])
        # Tras evaluar (evento nuevo): al día
        evaluar_todo(hoy=self.hoy)
        estado = self._json(self._api("get", "/api/alertas/evaluacion/"))
        self.assertFalse(estado["atrasada"])
        self.assertIsNotNone(estado["ultima_evaluacion"])


class ParametrosYCalidadTests(AlertasBase):
    """Pruebas 260-262: parámetros de la semana y restricciones de la
    tabla alertas."""

    # ------------------------------------------------------------------ #
    # 260: dias_sin_actividad es entero 1-365 y avisa del cambio
    # ------------------------------------------------------------------ #
    def test_260_dias_sin_actividad_entero_y_aviso(self):
        self._entrar_admin()

        def _cambiar(valor):
            return self._api(
                "patch", "/api/parametros/dias_sin_actividad/",
                {"valor": valor},
            )

        ok = _cambiar("45")
        self.assertEqual(ok.status_code, 200)
        self.assertIn("aviso", self._json(ok))
        self.assertIn("siguiente evaluación", self._json(ok)["aviso"])
        for malo in ("0", "366", "30.5", "treinta"):
            respuesta = _cambiar(malo)
            self.assertEqual(respuesta.status_code, 400, malo)
        # La regla no rompe los demás parámetros (helada admite negativos)
        helada = self._api(
            "patch", "/api/parametros/umbral_helada_c/", {"valor": "-2"}
        )
        self.assertEqual(helada.status_code, 200)

    # ------------------------------------------------------------------ #
    # 261: mensajes sin datos personales y RENDIMIENTO_BAJO no se genera
    # ------------------------------------------------------------------ #
    def test_261_mensajes_sin_personales_y_rendimiento_bajo(self):
        evaluar_todo(hoy=self.hoy)
        evaluar_incidencia(self._incidencia_bd())
        mensajes = " ".join(Alerta.objects.values_list("mensaje", flat=True))
        self.assertNotIn(self.p1.dni, mensajes)
        self.assertNotIn("Uno", mensajes)
        self.assertNotIn("Alfa", mensajes)
        # RENDIMIENTO_BAJO se permite en la tabla pero no se genera aún
        self.assertFalse(
            Alerta.objects.filter(tipo=Alerta.TIPO_RENDIMIENTO_BAJO).exists()
        )
        self._alerta_bd(tipo=Alerta.TIPO_RENDIMIENTO_BAJO)  # la tabla lo admite
        self.assertEqual(
            Alerta.objects.filter(tipo=Alerta.TIPO_RENDIMIENTO_BAJO).count(), 1
        )

    # ------------------------------------------------------------------ #
    # 262: restricciones de la tabla y triggers intactos
    # ------------------------------------------------------------------ #
    def test_262_restricciones_de_la_tabla_y_triggers(self):
        campania = self.campania_vieja
        productor_id = campania.parcela.productor_id
        campania_id = campania.pk
        # ck_alerta_incidencia: severa exige incidencia…
        self._sql_debe_fallar(
            "INSERT INTO alertas (productor_id, campania_id, tipo, mensaje) "
            "VALUES (%s, %s, 'INCIDENCIA_SEVERA', 'Sin incidencia')",
            [productor_id, campania_id],
        )
        # …y las demás no pueden llevarla
        incidencia = self._incidencia_bd()
        self._sql_debe_fallar(
            "INSERT INTO alertas (productor_id, campania_id, incidencia_id, "
            "tipo, mensaje) VALUES (%s, %s, %s, 'SIN_ACTIVIDAD', 'Con incidencia')",
            [productor_id, campania_id, incidencia.pk],
        )
        # uq_alerta_pendiente_campania_tipo: una pendiente por campaña+tipo
        self._alerta_bd()
        self._sql_debe_fallar(
            "INSERT INTO alertas (productor_id, campania_id, tipo, mensaje) "
            "VALUES (%s, %s, 'SIN_ACTIVIDAD', 'Duplicada')",
            [productor_id, campania_id],
        )
        # ck_alerta_nota: la nota solo si está atendida
        self._sql_debe_fallar(
            "INSERT INTO alertas (productor_id, campania_id, tipo, mensaje, "
            "nota_atencion) VALUES (%s, %s, 'SIN_ACTIVIDAD', 'Nota huérfana', "
            "'Apunta sin atender')",
            [productor_id, campania_id],
        )
        # La tabla alertas no tiene triggers (decisión de la Semana 15:
        # la lógica vive en la aplicación)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid = 'alertas'::regclass"
            )
            self.assertEqual(cursor.fetchone()[0], 0)
            # Y los triggers de seguridad de las tablas de negocio siguen
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                "AND tgname IN ('trg_incidencias_fecha', "
                "'trg_incidencias_superficie', 'trg_actividades_fecha', "
                "'trg_campanias_actualizado', 'trg_auditoria_inmutable')"
            )
            self.assertEqual(cursor.fetchone()[0], 5)

    # ------------------------------------------------------------------ #
    # helpers internos
    # ------------------------------------------------------------------ #
    def _sql_debe_fallar(self, consulta, parametros=None):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(consulta, parametros or [])
