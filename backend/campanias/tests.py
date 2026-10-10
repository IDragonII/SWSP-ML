"""Pruebas de la Semana 6: campañas (HU-38 a HU-46).

Numeración del repositorio 68-86 (19 pruebas nuevas → 86 en total ≥ 84;
el repositorio llegaba a 67 al cerrar la Semana 5). Las 17 del enunciado
son 68-84 y 85-86 son los extras «si sobra tiempo»: la ficha no expone
creado_por y la campaña conserva su cultivo aunque éste se desactive.
"""
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.db import DatabaseError, connection, transaction
from django.test import TestCase

from catalogos.models import Cultivo, Variedad
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from productores.models import AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia

from .models import Campania


class Semana6Base(TestCase):
    """Datos comunes: las 3 cuentas, ubicación, dos cultivos variedades,
    dos productores (el primero asignado al técnico) y sus parcelas."""

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
        self.provincia = Provincia.objects.create(nombre="Prov S6")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S6"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S6"
        )
        self.distrito_b = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S6 B"
        )
        self.comunidad_b = Comunidad.objects.create(
            distrito=self.distrito_b, nombre="Comunidad S6 B"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua S6")
        self.cultivo_b = Cultivo.objects.create(nombre="Maíz S6")
        self.variedad = Variedad.objects.create(cultivo=self.cultivo, nombre="Real S6")
        self.variedad_b = Variedad.objects.create(
            cultivo=self.cultivo_b, nombre="Blanca S6"
        )
        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="71000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p2 = Productor.objects.create(
            nombres="Dos", apellidos="Beta", dni="71000002",
            comunidad=self.comunidad_b, creado_por=self.admin,
        )
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.parcela = self._parcela_bd(self.p1, self.comunidad, "2.00")
        self.parcela_b = self._parcela_bd(self.p2, self.comunidad_b, "3.00")
        AsignacionTecnico.objects.create(tecnico=self.tecnico, productor=self.p1)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_pruebas", "AdminPruebas2026!")

    def _entrar_tecnico(self):
        self._entrar("tec_pruebas", "Tec2026!")

    def _entrar_coordinador(self):
        self._entrar("coord_pruebas", "Coord2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _parcela_bd(self, productor, comunidad, superficie):
        parcela = Parcela.objects.create(
            productor=productor,
            comunidad=comunidad,
            superficie_ha=superficie,
            altitud_msnm=3850,
            tipo_suelo="FRANCO",
            pendiente="SUAVE",
            disponibilidad_agua="MEDIA",
            sistema_riego="GOTEO",
        )
        parcela.refresh_from_db()  # el trigger rellena codigo
        return parcela

    def _datos(self, **extra):
        datos = {
            "periodo": "2025-2026",
            "parcela": self.parcela.pk,
            "cultivo": self.cultivo.pk,
            "variedad": self.variedad.pk,
            "fecha_inicio": "2025-09-01",
            "fecha_fin_prevista": "2026-05-31",
            "superficie_sembrada_ha": "1.50",
        }
        datos.update(extra)
        return datos

    def _crear(self, **extra):
        return self._api("post", "/api/campanias/", self._datos(**extra))

    def _iniciar(self, campania_id):
        return self._api("post", f"/api/campanias/{campania_id}/iniciar/")

    def _cancelar(self, campania_id, motivo="Sin datos"):
        return self._api(
            "post", f"/api/campanias/{campania_id}/cancelar/", {"motivo": motivo}
        )

    def _sql(self, consulta, parametros=None):
        """Ejecuta SQL directo (red de seguridad de la base de datos)."""
        with connection.cursor() as cursor:
            cursor.execute(consulta, parametros or [])

    def _sql_debe_fallar(self, consulta, parametros=None):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self._sql(consulta, parametros)


class CampaniaApiTests(Semana6Base):
    """Pruebas 68-86."""

    # ------------------------------------------------------------------ #
    # 68: clave compuesta (variedad del cultivo correcto)
    # ------------------------------------------------------------------ #
    def test_68_alta_valida_nace_planificada_y_variedad_de_otro_cultivo_se_rechaza(self):
        self._entrar_admin()
        respuesta = self._crear()
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        self.assertEqual(fila["estado"], "PLANIFICADA")
        self.assertEqual(fila["creado_por"], "admin_pruebas")
        self.assertIsNone(fila["fecha_siembra"])

        # API: una variedad de otro cultivo se rechaza en español
        rechazo = self._json(self._crear(variedad=self.variedad_b.pk))
        self.assertIn("variedad", rechazo)
        self.assertIn(
            "La variedad indicada no pertenece al cultivo elegido.",
            rechazo["variedad"],
        )

        # Base: la clave compuesta fk_campania_variedad_cultivo lo rechaza
        self._sql_debe_fallar(
            "INSERT INTO campanias (periodo, parcela_id, cultivo_id, variedad_id,"
            " fecha_inicio, fecha_fin_prevista, superficie_sembrada_ha)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                "2025-2026",
                self.parcela_b.pk,
                self.cultivo.pk,
                self.variedad_b.pk,
                date(2025, 9, 1),
                date(2026, 5, 31),
                Decimal("1.00"),
            ],
        )

    # ------------------------------------------------------------------ #
    # 69: formato y años consecutivos del período
    # ------------------------------------------------------------------ #
    def test_69_periodo_con_formato_invalido_o_anios_no_consecutivos(self):
        self._entrar_admin()
        formato = self._json(self._crear(periodo="2025/2026"))
        self.assertIn("periodo", formato)
        self.assertIn("formato AAAA-AAAA", formato["periodo"][0])

        consecutivos = self._json(self._crear(periodo="2025-2027"))
        self.assertIn("periodo", consecutivos)
        self.assertIn("uno más que el primero", consecutivos["periodo"][0])

        # La base también lo rechaza (ck_campania_periodo)
        self._sql_debe_fallar(
            "INSERT INTO campanias (periodo, parcela_id, cultivo_id, variedad_id,"
            " fecha_inicio, fecha_fin_prevista, superficie_sembrada_ha)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                "2025-2027",
                self.parcela_b.pk,
                self.cultivo.pk,
                self.variedad.pk,
                date(2025, 9, 1),
                date(2027, 5, 31),
                Decimal("1.00"),
            ],
        )

    # ------------------------------------------------------------------ #
    # 70: fin previsto >= inicio y fechas dentro del período
    # ------------------------------------------------------------------ #
    def test_70_fechas_invertidas_o_fuera_del_periodo_se_rechazan(self):
        self._entrar_admin()
        invertidas = self._json(
            self._crear(fecha_inicio="2026-06-01", fecha_fin_prevista="2026-05-31")
        )
        self.assertIn("fecha_fin_prevista", invertidas)
        self.assertIn("no puede ser anterior", invertidas["fecha_fin_prevista"][0])

        inicio_fuera = self._json(self._crear(fecha_inicio="2019-01-10"))
        self.assertIn("fecha_inicio", inicio_fuera)
        self.assertIn("2025-2026", inicio_fuera["fecha_inicio"][0])

        fin_fuera = self._json(self._crear(fecha_fin_prevista="2027-01-10"))
        self.assertIn("fecha_fin_prevista", fin_fuera)
        self.assertIn("2025-2026", fin_fuera["fecha_fin_prevista"][0])

    # ------------------------------------------------------------------ #
    # 71: superficie > 0 y <= superficie de la parcela (API y trigger)
    # ------------------------------------------------------------------ #
    def test_71_superficie_invalida_se_rechaza_en_la_api_y_en_la_base(self):
        self._entrar_admin()
        cero = self._json(self._crear(superficie_sembrada_ha="0.00"))
        self.assertIn("mayor que 0", cero["superficie_sembrada_ha"][0])

        negativa = self._json(self._crear(superficie_sembrada_ha="-1.00"))
        self.assertIn("mayor que 0", negativa["superficie_sembrada_ha"][0])

        mayor = self._json(self._crear(superficie_sembrada_ha="3.00"))
        self.assertIn("no puede superar", mayor["superficie_sembrada_ha"][0])
        self.assertIn("2.00", mayor["superficie_sembrada_ha"][0])

        # El trigger también defiende la regla con SQL directo
        campania = self._json(self._crear())
        self._sql_debe_fallar(
            "UPDATE campanias SET superficie_sembrada_ha = 9.00 WHERE id = %s",
            [campania["id"]],
        )

    # ------------------------------------------------------------------ #
    # 72: una campaña activa por parcela; cancelada libera la parcela
    # ------------------------------------------------------------------ #
    def test_72_una_sola_campania_activa_por_parcela_y_traduccion_del_choque(self):
        self._entrar_admin()
        primera = self._json(self._crear())
        rechazo = self._json(self._crear())
        self.assertEqual(rechazo["campania_existente"], [str(primera["id"])])
        self.assertIn(f"(id {primera['id']})", rechazo["parcela"][0])

        # Cancelar la primera libera la parcela
        cancelada = self._json(self._cancelar(primera["id"]))
        self.assertEqual(cancelada["estado"], "CANCELADA")
        segunda = self._json(self._crear())
        self.assertEqual(segunda["estado"], "PLANIFICADA")

        # Carrera: la validación no ve el duplicado, la base sí y la vista
        # lo traduce a un 400 que nombra la campaña existente (prueba 84
        # cubre el camino completo; aquí se fuerza el choque real)
        with patch(
            "campanias.serializers.CampaniaEscrituraSerializer._duplicada_activa",
            return_value=None,
        ), patch(
            "campanias.serializers.CampaniaEscrituraSerializer._duplicada_periodo",
            return_value=None,
        ):
            choque = self._json(self._crear())
        self.assertEqual(choque["campania_existente"], str(segunda["id"]))
        self.assertIn("parcela", choque)

    # ------------------------------------------------------------------ #
    # 73: un cultivo por parcela y período; la cancelada no cuenta
    # ------------------------------------------------------------------ #
    def test_73_un_cultivo_por_parcela_y_periodo_sin_contar_las_canceladas(self):
        self._entrar_admin()
        quinua = self._json(self._crear())
        # Misma parcela y período con otro cultivo: nombra la existente
        rechazo = self._json(
            self._crear(cultivo=self.cultivo_b.pk, variedad=self.variedad_b.pk)
        )
        self.assertEqual(rechazo["campania_existente"], [str(quinua["id"])])
        self.assertIn("Quinua S6", rechazo["parcela"][0])

        # La cancelada no cuenta: ahora sí se puede repetir el período
        self._cancelar(quinua["id"])
        segunda = self._json(
            self._crear(cultivo=self.cultivo_b.pk, variedad=self.variedad_b.pk)
        )
        self.assertEqual(segunda["estado"], "PLANIFICADA")

        # La base también lo defiende (índice uq_campania_parcela_periodo)
        self._sql_debe_fallar(
            "INSERT INTO campanias (periodo, parcela_id, cultivo_id, variedad_id,"
            " fecha_inicio, fecha_fin_prevista, superficie_sembrada_ha)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                "2025-2026",
                self.parcela.pk,
                self.cultivo.pk,
                self.variedad.pk,
                date(2025, 9, 1),
                date(2026, 5, 31),
                Decimal("1.00"),
            ],
        )

        # Carrera sobre el índice de período
        with patch(
            "campanias.serializers.CampaniaEscrituraSerializer._duplicada_activa",
            return_value=None,
        ), patch(
            "campanias.serializers.CampaniaEscrituraSerializer._duplicada_periodo",
            return_value=None,
        ):
            choque = self._json(self._crear())
        self.assertEqual(choque["campania_existente"], str(segunda["id"]))

    # ------------------------------------------------------------------ #
    # 74: sin campañas en parcelas o productores inactivos
    # ------------------------------------------------------------------ #
    def test_74_no_se_crean_campanias_en_parcelas_ni_productores_inactivos(self):
        self._entrar_admin()
        self.parcela.estado = Parcela.ESTADO_INACTIVA
        self.parcela.save(update_fields=("estado",))
        en_parcela_inactiva = self._json(self._crear())
        self.assertIn("parcela", en_parcela_inactiva)
        self.assertIn(
            "no existe o está inactiva", en_parcela_inactiva["parcela"][0]
        )

        self.parcela.estado = Parcela.ESTADO_ACTIVA
        self.parcela.save(update_fields=("estado",))
        self.p1.estado = Productor.ESTADO_INACTIVO
        self.p1.save(update_fields=("estado",))
        de_productor_inactivo = self._json(self._crear())
        self.assertIn("parcela", de_productor_inactivo)
        self.assertIn("productor", de_productor_inactivo["parcela"][0])

    # ------------------------------------------------------------------ #
    # 75: iniciar y cancelar; cosechada/cerrada no existen aún
    # ------------------------------------------------------------------ #
    def test_75_estados_iniciar_cancelar_y_estado_no_forzable(self):
        self._entrar_admin()
        # El estado que mande el cliente se ignora en el alta
        campania = self._json(self._crear(estado="EN_PRODUCCION"))
        self.assertEqual(campania["estado"], "PLANIFICADA")

        respuesta = self._json(
            self._api(
                "patch",
                f"/api/campanias/{campania['id']}/",
                {"estado": "CANCELADA"},
            )
        )
        self.assertEqual(respuesta["estado"], "PLANIFICADA")

        iniciada = self._json(self._iniciar(campania["id"]))
        self.assertEqual(iniciada["estado"], "EN_PRODUCCION")
        repetido = self._json(self._iniciar(campania["id"]))
        self.assertIn("Solo se puede iniciar", str(repetido["estado"]))

        # Cosechada y cerrada: ni a mano (trigger) ni por la API
        self._sql_debe_fallar(
            "UPDATE campanias SET estado = 'COSECHADA' WHERE id = %s",
            [campania["id"]],
        )
        self._sql_debe_fallar(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [campania["id"]],
        )
        self._sql_debe_fallar(
            "INSERT INTO campanias (periodo, parcela_id, cultivo_id, variedad_id,"
            " fecha_inicio, fecha_fin_prevista, superficie_sembrada_ha, estado)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, 'COSECHADA')",
            [
                "2026-2027",
                self.parcela_b.pk,
                self.cultivo.pk,
                self.variedad.pk,
                date(2026, 9, 1),
                date(2027, 5, 31),
                Decimal("1.00"),
            ],
        )
        # Sí se puede cancelar (con motivo) desde en producción
        cancelada = self._json(self._cancelar(campania["id"], "Temporada perdida"))
        self.assertEqual(cancelada["estado"], "CANCELADA")
        self.assertIn("Temporada perdida", cancelada["observaciones"])

    # ------------------------------------------------------------------ #
    # 76: edición condicionada al estado
    # ------------------------------------------------------------------ #
    def test_76_campos_bloqueados_segun_el_estado(self):
        self._entrar_admin()
        campania = self._json(self._crear())

        # En planificada sí se puede cambiar la parcela
        cambiada = self._json(
            self._api(
                "patch",
                f"/api/campanias/{campania['id']}/",
                {"parcela": self.parcela_b.pk},
            )
        )
        self.assertEqual(cambiada["parcela"]["id"], self.parcela_b.pk)
        # ...y volver a la original para el resto de la prueba
        self._api(
            "patch",
            f"/api/campanias/{campania['id']}/",
            {"parcela": self.parcela.pk},
        )
        self._json(self._iniciar(campania["id"]))

        bloqueados = {
            "parcela": self.parcela_b.pk,
            "cultivo": self.cultivo_b.pk,
            "variedad": self.variedad_b.pk,
            "periodo": "2026-2027",
            "fecha_inicio": "2025-10-01",
        }
        for campo, valor in bloqueados.items():
            rechazo = self._json(
                self._api(
                    "patch", f"/api/campanias/{campania['id']}/", {campo: valor}
                )
            )
            self.assertIn(campo, rechazo, campo)
            self.assertIn("bloqueado", str(rechazo[campo]), campo)

        # En producción sí se permite: fin prevista, superficie y observaciones
        permitida = self._json(
            self._api(
                "patch",
                f"/api/campanias/{campania['id']}/",
                {
                    "fecha_fin_prevista": "2026-05-15",
                    "superficie_sembrada_ha": "1.80",
                    "observaciones": "Riego programado",
                },
            )
        )
        self.assertEqual(permitida["superficie_sembrada_ha"], "1.80")
        self.assertEqual(permitida["observaciones"], "Riego programado")

        # Cancelada: no admite ningún cambio
        self._json(self._cancelar(campania["id"]))
        cancelada = self._json(
            self._api(
                "patch",
                f"/api/campanias/{campania['id']}/",
                {"observaciones": "Intento tardío"},
            )
        )
        self.assertIn("cancelada no admite", str(cancelada))

    # ------------------------------------------------------------------ #
    # 77: cancelar exige motivo y campanias.desactivar
    # ------------------------------------------------------------------ #
    def test_77_cancelar_exige_motivo_y_permiso_de_desactivar(self):
        self._entrar_admin()
        campania = self._json(self._crear())

        sin_resp = self._cancelar(campania["id"], "")
        sin_motivo = self._json(sin_resp)
        self.assertIn("motivo", sin_motivo)
        self.assertIn("obligatorio", str(sin_motivo["motivo"]))

        # El Técnico no cancela ni siquiera las suyas (sin campanias.desactivar)
        self._entrar_tecnico()
        self.assertEqual(self._cancelar(campania["id"]).status_code, 403)

        self._entrar_admin()
        cancelada = self._json(self._cancelar(campania["id"], "Lluvias tardías"))
        self.assertEqual(cancelada["estado"], "CANCELADA")
        self.assertIn("Lluvias tardías", cancelada["observaciones"])
        repetido = self._json(self._cancelar(campania["id"], "Otra vez"))
        self.assertIn("cancelada", str(repetido["estado"]))

    # ------------------------------------------------------------------ #
    # 78: no se desactiva una parcela con campaña activa (HU-45)
    # ------------------------------------------------------------------ #
    def test_78_parcela_con_campania_activa_no_se_desactiva(self):
        self._entrar_admin()
        campania = self._json(self._crear())
        rechazo = self._json(
            self._api(
                "patch",
                f"/api/parcelas/{self.parcela.pk}/estado/",
                {"estado": "INACTIVA"},
            )
        )
        self.assertIn("campaña activa", rechazo["estado"])
        self.assertIn(str(campania["id"]), rechazo["estado"])

        # Con solo campañas canceladas sí se puede
        self._cancelar(campania["id"])
        desactivada = self._json(
            self._api(
                "patch",
                f"/api/parcelas/{self.parcela.pk}/estado/",
                {"estado": "INACTIVA"},
            )
        )
        self.assertEqual(desactivada["estado"], "INACTIVA")
        reactivada = self._json(
            self._api(
                "patch",
                f"/api/parcelas/{self.parcela.pk}/estado/",
                {"estado": "ACTIVA"},
            )
        )
        self.assertEqual(reactivada["estado"], "ACTIVA")

    # ------------------------------------------------------------------ #
    # 79: no se desactiva un productor con campañas activas (HU-46; decisión
    #     pendiente de confirmar con el responsable)
    # ------------------------------------------------------------------ #
    def test_79_productor_con_campania_activa_no_se_desactiva(self):
        self._entrar_admin()
        campania = self._json(self._crear())
        rechazo = self._json(
            self._api(
                "patch",
                f"/api/productores/{self.p1.pk}/estado/",
                {"estado": "INACTIVO"},
            )
        )
        self.assertIn("campaña(s) activa(s)", rechazo["estado"])
        self.assertIn(str(campania["id"]), rechazo["estado"])

        self._cancelar(campania["id"])
        desactivado = self._json(
            self._api(
                "patch",
                f"/api/productores/{self.p1.pk}/estado/",
                {"estado": "INACTIVO"},
            )
        )
        self.assertEqual(desactivado["estado"], "INACTIVO")
        reactivado = self._json(
            self._api(
                "patch",
                f"/api/productores/{self.p1.pk}/estado/",
                {"estado": "ACTIVO"},
            )
        )
        self.assertEqual(reactivado["estado"], "ACTIVO")

    # ------------------------------------------------------------------ #
    # 80: el Técnico solo ve las campañas de sus productores (404)
    # ------------------------------------------------------------------ #
    def test_80_tecnico_solo_ve_las_suyas_y_las_ajenas_son_404(self):
        self._entrar_admin()
        ajena = self._json(self._crear(parcela=self.parcela_b.pk))
        propia = self._json(self._crear())

        self._entrar_tecnico()
        listado = self._json(self.client.get("/api/campanias/"))
        self.assertEqual(listado["count"], 1)
        self.assertEqual(listado["results"][0]["id"], propia["id"])

        self.assertEqual(
            self._api("get", f"/api/campanias/{ajena['id']}/").status_code, 404
        )
        self.assertEqual(
            self._api(
                "patch", f"/api/campanias/{ajena['id']}/", {"observaciones": "x"}
            ).status_code,
            404,
        )
        self.assertEqual(self._iniciar(ajena["id"]).status_code, 404)

        # Crear sobre una parcela ajena: el MISMO mensaje que si no existiera
        ajena_pk = self._json(self._crear(parcela=self.parcela_b.pk))
        inexistente = self._json(self._crear(parcela=999999))
        self.assertEqual(ajena_pk, inexistente)
        self.assertEqual(
            ajena_pk["parcela"], ["La parcela indicada no existe."]
        )

    # ------------------------------------------------------------------ #
    # 81: Administrador y Coordinador ven todas; el Coordinador solo lee
    # ------------------------------------------------------------------ #
    def test_81_administrador_y_coordinador_lo_todocoordinador_no_edita(self):
        self._entrar_admin()
        self._json(self._crear())
        self._json(self._crear(parcela=self.parcela_b.pk))

        listado = self._json(self.client.get("/api/campanias/"))
        self.assertEqual(listado["count"], 2)

        self._entrar_coordinador()
        listado = self._json(self.client.get("/api/campanias/"))
        self.assertEqual(listado["count"], 2)
        campania_id = listado["results"][0]["id"]
        self.assertEqual(self._crear().status_code, 403)
        self.assertEqual(
            self._api(
                "patch", f"/api/campanias/{campania_id}/", {"observaciones": "x"}
            ).status_code,
            403,
        )
        self.assertEqual(self._iniciar(campania_id).status_code, 403)
        self.assertEqual(self._cancelar(campania_id).status_code, 403)

    # ------------------------------------------------------------------ #
    # 82: búsqueda general y filtros
    # ------------------------------------------------------------------ #
    def test_82_busqueda_y_filtros(self):
        self._entrar_admin()
        una = self._json(self._crear())
        otra = self._json(
            self._crear(
                parcela=self.parcela_b.pk,
                cultivo=self.cultivo_b.pk,
                variedad=self.variedad_b.pk,
                periodo="2026-2027",
                fecha_inicio="2026-09-01",
                fecha_fin_prevista="2027-05-31",
                superficie_sembrada_ha="2.50",
            )
        )
        self._json(self._iniciar(otra["id"]))

        def ids(respuesta):
            return {c["id"] for c in self._json(respuesta)["results"]}

        # Búsqueda general: código de parcela, apellidos, cultivo y variedad
        self.assertEqual(
            ids(self.client.get(f"/api/campanias/?busqueda={otra['parcela']['codigo']}")),
            {otra["id"]},
        )
        self.assertEqual(
            ids(self.client.get("/api/campanias/?busqueda=Beta")), {otra["id"]}
        )
        self.assertEqual(
            ids(self.client.get("/api/campanias/?busqueda=Quinua S6")), {una["id"]}
        )
        self.assertEqual(
            ids(self.client.get("/api/campanias/?busqueda=Blanca S6")), {otra["id"]}
        )

        # Filtros
        self.assertEqual(
            ids(self.client.get("/api/campanias/?estado=PLANIFICADA")), {una["id"]}
        )
        self.assertEqual(
            ids(self.client.get(f"/api/campanias/?cultivo={self.cultivo_b.pk}")),
            {otra["id"]},
        )
        self.assertEqual(
            ids(self.client.get("/api/campanias/?periodo=2026-2027")), {otra["id"]}
        )
        self.assertEqual(
            ids(self.client.get(f"/api/campanias/?distrito={self.distrito_b.pk}")),
            {otra["id"]},
        )
        self.assertEqual(
            ids(self.client.get(f"/api/campanias/?productor={self.p2.pk}")),
            {otra["id"]},
        )
        self.assertEqual(
            ids(self.client.get(f"/api/campanias/?parcela={self.parcela_b.pk}")),
            {otra["id"]},
        )
        invalido = self._json(self.client.get("/api/campanias/?estado=RARA"))
        self.assertIn("estado", invalido)

    # ------------------------------------------------------------------ #
    # 83: creado_por lo pone el servidor; estado/siembra no se fuerzan
    # ------------------------------------------------------------------ #
    def test_83_creado_por_del_servidor_y_campos_protegidos(self):
        self._entrar_admin()
        fila = self._json(
            self._crear(
                parcela=self.parcela_b.pk,
                estado="CANCELADA",
                fecha_siembra="2025-09-15",
                creado_por="coord_pruebas",
            )
        )
        self.assertEqual(fila["creado_por"], "admin_pruebas")
        self.assertEqual(fila["estado"], "PLANIFICADA")
        self.assertIsNone(fila["fecha_siembra"])

        self._entrar_tecnico()
        propia = self._json(self._crear())
        self.assertEqual(propia["creado_por"], "tec_pruebas")

    # ------------------------------------------------------------------ #
    # 84: los 2 triggers y la base rechazan con SQL directo
    # ------------------------------------------------------------------ #
    def test_84_triggers_indices_y_sql_directo(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tgname FROM pg_trigger "
                "WHERE tgrelid = 'campanias'::regclass AND NOT tgisinternal"
            )
            triggers = {fila[0] for fila in cursor.fetchall()}
        self.assertLessEqual(
            {"trg_campanias_validar", "trg_campanias_actualizado"}, triggers
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'campanias'"
            )
            indices = {fila[0] for fila in cursor.fetchall()}
        self.assertLessEqual(
            {"uq_campania_activa_por_parcela", "uq_campania_parcela_periodo"},
            indices,
        )

        self._entrar_admin()
        campania = self._json(self._crear())
        # Superficie mayor que la de la parcela
        self._sql_debe_fallar(
            "UPDATE campanias SET superficie_sembrada_ha = 9.00 WHERE id = %s",
            [campania["id"]],
        )
        # Transición no permitida (en producción no pasa a cerrada)
        self._sql_debe_fallar(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [campania["id"]],
        )
        # Estado inicial inválido
        self._sql_debe_fallar(
            "INSERT INTO campanias (periodo, parcela_id, cultivo_id, variedad_id,"
            " fecha_inicio, fecha_fin_prevista, superficie_sembrada_ha, estado)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, 'CERRADA')",
            [
                "2026-2027",
                self.parcela_b.pk,
                self.cultivo.pk,
                self.variedad.pk,
                date(2026, 9, 1),
                date(2027, 5, 31),
                Decimal("1.00"),
            ],
        )

    # ------------------------------------------------------------------ #
    # 85 (extra): la ficha del productor no expone creado_por ni técnicos
    # ------------------------------------------------------------------ #
    def test_85_ficha_del_productor_con_campanias_sin_datos_de_usuarios(self):
        self._entrar_admin()
        self._json(self._crear())
        ficha = self._json(self.client.get(f"/api/productores/{self.p1.pk}/"))
        self.assertEqual(len(ficha["campanias"]), 1)
        bloque = ficha["campanias"][0]
        self.assertEqual(
            set(bloque),
            {"id", "periodo", "cultivo", "variedad", "parcela", "estado"},
        )
        self.assertNotIn("creado_por", bloque)
        self.assertEqual(ficha["resumen"]["campanias_activas"], 1)

        self._entrar_tecnico()
        ficha_tecnico = self._json(self.client.get(f"/api/productores/{self.p1.pk}/"))
        self.assertIn("campanias", ficha_tecnico)
        self.assertNotIn("tecnicos_asignados", ficha_tecnico)

    # ------------------------------------------------------------------ #
    # 86 (extra): la campaña conserva su cultivo aunque se desactive
    # ------------------------------------------------------------------ #
    def test_86_campania_conserva_su_cultivo_si_se_desactiva_despues(self):
        self._entrar_admin()
        campania = self._json(self._crear())
        self.assertEqual(
            self._api(
                "patch",
                f"/api/cultivos/{self.cultivo.pk}/estado/",
                {"activo": False},
            ).status_code,
            200,
        )
        detalle = self._json(self._api("get", f"/api/campanias/{campania['id']}/"))
        self.assertEqual(detalle["cultivo"]["nombre"], "Quinua S6")
        listado = self._json(self.client.get("/api/campanias/"))
        self.assertEqual(listado["results"][0]["cultivo"]["nombre"], "Quinua S6")
        # Y la edición sigue funcionando en planificada
        self.assertEqual(
            self._api(
                "patch",
                f"/api/campanias/{campania['id']}/",
                {"observaciones": "Cultivo desactivado después"},
            ).status_code,
            200,
        )
