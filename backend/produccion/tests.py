"""Pruebas de la Semana 8: producción, rendimiento y cierre de campañas
(HU-56 a HU-66).

Numeración del repositorio 103-120 (18 pruebas → 120 en total; el
repositorio llegaba a 102 al cerrar la Semana 7).
"""
import importlib
import json
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db import DatabaseError, connection, transaction
from django.test import TestCase

from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Unidad, Variedad
from productores.models import AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import Produccion


class Semana8Base(TestCase):
    """Datos comunes: las 3 cuentas, ubicación, cultivos, dos productores
    (el primero asignado al técnico), parcelas, unidades (con quintal a
    46 kg creado aquí: la migración no lo siembra) y dos campañas en
    producción con siembra registrada."""

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
        self.provincia = Provincia.objects.create(nombre="Prov S8")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S8"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S8"
        )
        self.distrito_b = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S8 B"
        )
        self.comunidad_b = Comunidad.objects.create(
            distrito=self.distrito_b, nombre="Comunidad S8 B"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua S8")
        self.cultivo_b = Cultivo.objects.create(nombre="Maíz S8")
        self.variedad = Variedad.objects.create(cultivo=self.cultivo, nombre="Real S8")
        self.variedad_b = Variedad.objects.create(
            cultivo=self.cultivo_b, nombre="Blanca S8"
        )
        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="81000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p2 = Productor.objects.create(
            nombres="Dos", apellidos="Beta", dni="81000002",
            comunidad=self.comunidad_b, creado_por=self.admin,
        )
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.parcela = self._parcela_bd(self.p1, self.comunidad, "2.00")
        self.parcela_b = self._parcela_bd(self.p2, self.comunidad_b, "3.00")
        AsignacionTecnico.objects.create(tecnico=self.tecnico, productor=self.p1)
        self.preparacion = TipoActividad.objects.get(codigo="PREPARACION")

        self.kg = Unidad.objects.get(nombre="Kilogramo")
        self.tonelada = Unidad.objects.get(nombre="Tonelada")
        self.hectarea = Unidad.objects.get(nombre="Hectárea")
        self.quintal = Unidad.objects.create(
            nombre="Quintal", simbolo="qq", tipo="MASA",
            factor_a_base=Decimal("46"), es_base=False,
        )

        # Campañas en producción con siembra (la actividad de siembra es
        # de la Semana 7; aquí se fija el estado y la fecha a mano porque
        # el trigger permite INSERT en EN_PRODUCCION para cargas históricas)
        self.campania = self._campania_bd(
            self.parcela, self.cultivo, self.variedad,
            estado="EN_PRODUCCION", fecha_siembra=date(2025, 10, 1),
            superficie_sembrada_ha=Decimal("2.00"),
        )
        self.campania_b = self._campania_bd(
            self.parcela_b, self.cultivo_b, self.variedad_b,
            estado="EN_PRODUCCION", fecha_siembra=date(2025, 10, 2),
            superficie_sembrada_ha=Decimal("2.50"),
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

    def _campania_bd(self, parcela, cultivo, variedad, **extra):
        datos = {
            "periodo": "2025-2026",
            "parcela": parcela,
            "cultivo": cultivo,
            "variedad": variedad,
            "fecha_inicio": date(2025, 9, 1),
            "fecha_fin_prevista": date(2026, 5, 31),
            "superficie_sembrada_ha": Decimal("1.50"),
        }
        datos.update(extra)
        return Campania.objects.create(**datos)

    def _datos(self, **extra):
        datos = {
            "campania": self.campania.pk,
            "fecha_cosecha": "2026-04-15",
            "superficie_cosechada_ha": "2.00",
            "cantidad_producida": "70",
            "unidad": self.quintal.pk,
        }
        datos.update(extra)
        return datos

    def _crear(self, **extra):
        return self._api("post", "/api/producciones/", self._datos(**extra))

    def _revisar(self, produccion_id, **extra):
        cuerpo = {"nota": "Revisado con el productor"}
        cuerpo.update(extra)
        return self._api(
            "post", f"/api/producciones/{produccion_id}/revisar/", cuerpo
        )

    def _deshacer(self, produccion_id, motivo="Error de registro"):
        return self._api(
            "post",
            f"/api/producciones/{produccion_id}/deshacer-cosecha/",
            {"motivo": motivo},
        )

    def _cerrar(self, campania_id):
        return self._api("post", f"/api/campanias/{campania_id}/cerrar/")

    def _sql(self, consulta, parametros=None):
        """Ejecuta SQL directo (red de seguridad de la base de datos)."""
        with connection.cursor() as cursor:
            if parametros:
                cursor.execute(consulta, parametros)
            else:
                # Sin parámetros: el texto puede contener '%' (funciones)
                cursor.execute(consulta)

    def _sql_debe_fallar(self, consulta, parametros=None):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self._sql(consulta, parametros)

    def _consulta(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            if parametros:
                cursor.execute(consulta, parametros)
            else:
                cursor.execute(consulta)
            return cursor.fetchall()


class ProduccionApiTests(Semana8Base):
    """Pruebas 103-120."""

    # ------------------------------------------------------------------ #
    # 103: conversión a kg y rendimiento; la campaña pasa a COSECHADA
    # ------------------------------------------------------------------ #
    def test_103_calcula_kg_y_rendimiento_y_pasa_la_campania_a_cosechada(self):
        self._entrar_admin()
        respuesta = self._crear()
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        # 70 qq × 46 kg = 3220 kg en 2.00 ha → 1610 kg/ha (en el rango
        # plausible de los parámetros: sin marca de revisión)
        self.assertEqual(fila["produccion_kg"], "3220.00")
        self.assertEqual(fila["rendimiento_kg_ha"], "1610.00")
        self.assertFalse(fila["requiere_revision"])
        self.assertIsNone(fila["motivo_revision"])
        self.assertEqual(fila["unidad"]["nombre"], "Quintal")
        self.assertEqual(fila["campania"]["estado"], "COSECHADA")
        self.assertEqual(fila["registrado_por"], "admin_pruebas")

        self.campania.refresh_from_db()
        self.assertEqual(self.campania.estado, "COSECHADA")

        # La base recalcula también en UPDATE (red de seguridad)
        self._sql(
            "UPDATE producciones SET cantidad_producida = 35 WHERE id = %s",
            [fila["id"]],
        )
        kg, rendimiento = self._consulta(
            "SELECT produccion_kg, rendimiento_kg_ha FROM producciones WHERE id = %s",
            [fila["id"]],
        )[0]
        self.assertEqual(kg, Decimal("1610.00"))
        self.assertEqual(rendimiento, Decimal("805.00"))

    # ------------------------------------------------------------------ #
    # 104: kg, rendimiento, marca, inclusión y registrado por son del
    #     servidor: lo que mande el cliente se sobrescribe
    # ------------------------------------------------------------------ #
    def test_104_campos_calculados_no_los_escribe_el_cliente(self):
        self._entrar_admin()
        fila = self._json(
            self._crear(
                cantidad_producida="1",
                produccion_kg=99999,
                rendimiento_kg_ha=99999,
                requiere_revision=False,
                incluir_en_entrenamiento=False,
                registrado_por=self.coordinador.pk,
            )
        )
        self.assertEqual(fila["produccion_kg"], "46.00")
        self.assertEqual(fila["rendimiento_kg_ha"], "23.00")
        # 23 kg/ha es atípico: la marca no se puede desactivar desde fuera
        self.assertTrue(fila["requiere_revision"])
        self.assertIn("Rendimiento atípico", fila["motivo_revision"])
        self.assertTrue(fila["incluir_en_entrenamiento"])
        self.assertEqual(fila["registrado_por"], "admin_pruebas")

    # ------------------------------------------------------------------ #
    # 105: la unidad debe ser de masa y activa; el factor de una unidad
    #     con producciones no se puede cambiar
    # ------------------------------------------------------------------ #
    def test_105_unidades_de_masa_activas_y_factor_protegido(self):
        self._entrar_admin()
        superficie = self._json(self._crear(unidad=self.hectarea.pk))
        self.assertIn("masa", superficie["unidad"][0])

        gramo = Unidad.objects.get(nombre="Gramo")
        gramo.activo = False
        gramo.save(update_fields=("activo",))
        inactiva = self._json(self._crear(unidad=gramo.pk))
        self.assertIn("masa", inactiva["unidad"][0])

        self._json(self._crear())  # quintal ya tiene producciones
        cambio = self._json(
            self._api(
                "patch", f"/api/unidades/{self.quintal.pk}/",
                {"factor_a_base": "50"},
            )
        )
        self.assertIn("ya tiene producciones", cambio["factor_a_base"])

        otro = self._api(
            "patch", f"/api/unidades/{self.tonelada.pk}/",
            {"factor_a_base": "900"},
        )
        self.assertEqual(otro.status_code, 200)
        self.assertEqual(self._json(otro)["factor_a_base"], "900.000000")

    # ------------------------------------------------------------------ #
    # 106: superficie cosechada mayor que 0 y sin superar la sembrada
    # ------------------------------------------------------------------ #
    def test_106_superficie_cosechada_valida_y_red_de_seguridad(self):
        self._entrar_admin()
        cero = self._json(self._crear(superficie_cosechada_ha="0"))
        self.assertIn("mayor que 0", cero["superficie_cosechada_ha"][0])

        exceso = self._json(self._crear(superficie_cosechada_ha="2.50"))
        self.assertIn(
            "no puede superar la sembrada", exceso["superficie_cosechada_ha"][0]
        )

        creada = self._json(self._crear())
        self._sql_debe_fallar(
            "UPDATE producciones SET superficie_cosechada_ha = 3.00 WHERE id = %s",
            [creada["id"]],
        )

    # ------------------------------------------------------------------ #
    # 107: rendimiento 0 marca la producción para revisión
    # ------------------------------------------------------------------ #
    def test_107_rendimiento_cero_requiere_revision(self):
        self._entrar_admin()
        fila = self._json(self._crear(cantidad_producida="0"))
        self.assertEqual(fila["produccion_kg"], "0.00")
        self.assertEqual(fila["rendimiento_kg_ha"], "0.00")
        self.assertTrue(fila["requiere_revision"])
        self.assertIn("Rendimiento atípico", fila["motivo_revision"])

    # ------------------------------------------------------------------ #
    # 108: la fecha de cosecha no es anterior a la siembra; sin siembra
    #     registrada no hay producción; la futura queda pendiente (H)
    # ------------------------------------------------------------------ #
    def test_108_fechas_validas_y_campania_sin_siembra(self):
        self._entrar_admin()
        anterior = self._json(self._crear(fecha_cosecha="2025-09-15"))
        self.assertIn("anterior a la fecha de siembra", anterior["fecha_cosecha"][0])

        parcela_c = self._parcela_bd(self.p1, self.comunidad, "2.00")
        sin_siembra = self._campania_bd(
            parcela_c, self.cultivo, self.variedad,
            estado="EN_PRODUCCION", superficie_sembrada_ha=Decimal("2.00"),
        )
        rechazo = self._json(self._crear(campania=sin_siembra.pk))
        self.assertIn("campania", rechazo)
        self.assertIn("no tiene siembra registrada", rechazo["campania"][0])

        # Decisión H pendiente del responsable: la fecha futura se admite
        futura = (date.today() + timedelta(days=30)).isoformat()
        ok = self._crear(fecha_cosecha=futura)
        self.assertEqual(ok.status_code, 201)

    # ------------------------------------------------------------------ #
    # 109: solo las campañas en producción o cosechadas admiten registro
    # ------------------------------------------------------------------ #
    def test_109_estados_que_no_admiten_produccion(self):
        self._entrar_admin()
        parcela_c = self._parcela_bd(self.p1, self.comunidad, "2.00")
        planificada = self._campania_bd(
            parcela_c, self.cultivo, self.variedad,
            superficie_sembrada_ha=Decimal("2.00"),
        )
        plan = self._json(self._crear(campania=planificada.pk))
        self.assertIn(
            "La campaña está PLANIFICADA y no admite nuevos registros.",
            plan["campania"],
        )

        parcela_d = self._parcela_bd(self.p1, self.comunidad, "2.00")
        cancelada = self._campania_bd(
            parcela_d, self.cultivo, self.variedad,
            estado="EN_PRODUCCION", superficie_sembrada_ha=Decimal("2.00"),
        )
        self._sql(
            "UPDATE campanias SET estado = 'CANCELADA' WHERE id = %s",
            [cancelada.pk],
        )
        cancel = self._json(self._crear(campania=cancelada.pk))
        self.assertIn("CANCELADA", cancel["campania"][0])

        self._sql_debe_fallar(
            "INSERT INTO producciones (campania_id, fecha_cosecha,"
            " superficie_cosechada_ha, cantidad_producida, unidad_id,"
            " produccion_kg, rendimiento_kg_ha, observaciones)"
            " VALUES (%s, %s, %s, %s, %s, 0, 0, '')",
            [
                planificada.pk, date(2026, 4, 15), Decimal("1.00"),
                Decimal("10"), self.quintal.pk,
            ],
        )

    # ------------------------------------------------------------------ #
    # 110: una sola producción por campaña (API y UNIQUE de la base)
    # ------------------------------------------------------------------ #
    def test_110_unicidad_de_produccion_por_campania(self):
        self._entrar_admin()
        creada = self._json(self._crear())
        duplicada = self._json(self._crear())
        self.assertIn(
            f"Ya existe una producción para esta campaña (id {creada['id']}).",
            duplicada["campania"],
        )
        self._sql_debe_fallar(
            "INSERT INTO producciones (campania_id, fecha_cosecha,"
            " superficie_cosechada_ha, cantidad_producida, unidad_id,"
            " produccion_kg, rendimiento_kg_ha, observaciones)"
            " VALUES (%s, %s, %s, %s, %s, 0, 0, '')",
            [
                self.campania.pk, date(2026, 4, 20), Decimal("1.00"),
                Decimal("10"), self.quintal.pk,
            ],
        )

    # ------------------------------------------------------------------ #
    # 111: la edición recalcula y reevalúa la marca; la campaña no cambia
    # ------------------------------------------------------------------ #
    def test_111_edicion_recalcula_reevalua_y_no_cambia_campania(self):
        self._entrar_admin()
        creada = self._json(self._crear(cantidad_producida="1"))
        self.assertTrue(creada["requiere_revision"])

        # Editar campos que no son kg ni superficie conserva la marca
        observada = self._json(
            self._api(
                "patch", f"/api/producciones/{creada['id']}/",
                {"observaciones": "Revisar con el productor"},
            )
        )
        self.assertTrue(observada["requiere_revision"])

        corregida = self._json(
            self._api(
                "patch", f"/api/producciones/{creada['id']}/",
                {"cantidad_producida": "70"},
            )
        )
        self.assertEqual(corregida["produccion_kg"], "3220.00")
        self.assertEqual(corregida["rendimiento_kg_ha"], "1610.00")
        self.assertFalse(corregida["requiere_revision"])
        self.assertIsNone(corregida["motivo_revision"])
        self.assertEqual(corregida["campania"]["estado"], "COSECHADA")

        otra = self._json(
            self._api(
                "patch", f"/api/producciones/{creada['id']}/",
                {"campania": self.campania_b.pk},
            )
        )
        self.assertIn("no se puede cambiar", otra["campania"][0])

    # ------------------------------------------------------------------ #
    # 112: rendimientos atípicos por debajo y por encima del umbral
    # ------------------------------------------------------------------ #
    def test_112_rendimientos_atipicos_bajos_y_altos(self):
        self._entrar_admin()
        baja = self._json(self._crear(cantidad_producida="1"))
        self.assertTrue(baja["requiere_revision"])
        self.assertIn("23.00 kg/ha", baja["motivo_revision"])

        alta = self._json(
            self._crear(
                campania=self.campania_b.pk,
                fecha_cosecha="2026-04-20",
                cantidad_producida="600",
            )
        )
        self.assertTrue(alta["requiere_revision"])
        self.assertIn("13800.00 kg/ha", alta["motivo_revision"])

    # ------------------------------------------------------------------ #
    # 113: revisar/ quita la marca, conserva el motivo y decide inclusión
    # ------------------------------------------------------------------ #
    def test_113_revisar_quita_la_marca_y_conserva_el_motivo(self):
        self._entrar_admin()
        creada = self._json(self._crear(cantidad_producida="1"))

        sin_nota = self._json(self._api("post", f"/api/producciones/{creada['id']}/revisar/", {}))
        self.assertIn("nota", sin_nota)

        no_bool = self._json(
            self._api(
                "post", f"/api/producciones/{creada['id']}/revisar/",
                {"nota": "x", "incluir_en_entrenamiento": "si"},
            )
        )
        self.assertIn("incluir_en_entrenamiento", no_bool)

        revisada = self._json(self._revisar(creada["id"], incluir_en_entrenamiento=False))
        self.assertFalse(revisada["requiere_revision"])
        self.assertIn("Rendimiento atípico", revisada["motivo_revision"])
        self.assertIn("Revisión: Revisado con el productor", revisada["motivo_revision"])
        self.assertFalse(revisada["incluir_en_entrenamiento"])

        segunda = self._json(self._revisar(creada["id"]))
        self.assertIn("no requiere revisión", segunda["estado"])

        self._entrar_tecnico()
        self.assertEqual(self._revisar(creada["id"]).status_code, 403)

    # ------------------------------------------------------------------ #
    # 114: deshacer-cosecha borra la fila y devuelve la campaña a
    #     producción; en cerrada no se puede
    # ------------------------------------------------------------------ #
    def test_114_deshacer_cosecha_devuelve_la_campania(self):
        self._entrar_admin()
        creada = self._json(self._crear())

        sin_motivo = self._json(
            self._api("post", f"/api/producciones/{creada['id']}/deshacer-cosecha/", {})
        )
        self.assertIn("motivo", sin_motivo)

        hecha = self._json(self._deshacer(creada["id"]))
        self.assertEqual(hecha["campania"], self.campania.pk)
        self.assertEqual(hecha["estado"], "EN_PRODUCCION")
        self.assertEqual(Produccion.objects.filter(pk=creada["id"]).count(), 0)
        self.campania.refresh_from_db()
        self.assertEqual(self.campania.estado, "EN_PRODUCCION")

        otra = self._json(self._crear())
        self.assertIn("id", otra)

        self._json(self._cerrar(self.campania.pk))
        cerrada = self._json(self._deshacer(otra["id"]))
        self.assertIn("la campaña está cerrada", cerrada["estado"])

        self._entrar_tecnico()
        self.assertEqual(self._deshacer(otra["id"]).status_code, 403)

    # ------------------------------------------------------------------ #
    # 115: cerrar la campaña exige cosechada, producción y sin revisión
    # ------------------------------------------------------------------ #
    def test_115_cerrar_campania_con_todas_las_condiciones(self):
        self._entrar_admin()
        self._sql(
            "UPDATE campanias SET estado = 'COSECHADA' WHERE id = %s",
            [self.campania_b.pk],
        )
        sin_produccion = self._json(self._cerrar(self.campania_b.pk))
        self.assertIn("no tiene producción registrada", sin_produccion["estado"])

        planificada = self._campania_bd(
            self._parcela_bd(self.p1, self.comunidad, "2.00"),
            self.cultivo, self.variedad,
            superficie_sembrada_ha=Decimal("2.00"),
        )
        no_cosechada = self._json(self._cerrar(planificada.pk))
        self.assertIn("Solo se puede cerrar una campaña cosechada.", no_cosechada["estado"])

        creada = self._json(self._crear(cantidad_producida="1"))
        marcada = self._json(self._cerrar(self.campania.pk))
        self.assertIn("requiere revisión pendiente", marcada["estado"])

        self._json(self._revisar(creada["id"], incluir_en_entrenamiento=True))
        cerrada = self._json(self._cerrar(self.campania.pk))
        self.assertEqual(cerrada["estado"], "CERRADA")
        bloque_produccion = cerrada["produccion"]
        self.assertEqual(bloque_produccion["produccion_kg"], 46.0)
        self.assertFalse(bloque_produccion["requiere_revision"])

        doble = self._json(self._cerrar(self.campania.pk))
        self.assertIn("Solo se puede cerrar una campaña cosechada.", doble["estado"])

        editada = self._json(
            self._api(
                "patch", f"/api/producciones/{creada['id']}/",
                {"observaciones": "Ya cerrada"},
            )
        )
        self.assertIn(
            "La campaña cerrada no admite cambios en la producción.",
            editada["non_field_errors"][0],
        )

        actividad = self._json(
            self._api(
                "post", "/api/actividades/",
                {
                    "campania": self.campania.pk,
                    "tipo_actividad": self.preparacion.pk,
                    "fecha": "2026-04-20",
                    "metodo": "Arado de disco",
                },
            )
        )
        self.assertIn("no admite nuevos registros", str(actividad))

        self._entrar_coordinador()
        self.assertEqual(self._cerrar(self.campania_b.pk).status_code, 403)
        self._entrar_tecnico()
        self.assertEqual(self._cerrar(self.campania_b.pk).status_code, 403)

    # ------------------------------------------------------------------ #
    # 116: parámetros del sistema: solo admin, validación y sin
    #     reevaluación de producciones existentes
    # ------------------------------------------------------------------ #
    def test_116_parametros_del_sistema(self):
        self._entrar_admin()
        listado = self._json(self.client.get("/api/parametros/"))
        self.assertEqual(listado["count"], 5)
        self.assertEqual(
            {p["clave"] for p in listado["results"]},
            {
                "dias_sin_actividad", "umbral_rendimiento_bajo",
                "rendimiento_min_plausible", "rendimiento_max_plausible",
                "umbral_helada_c",
            },
        )

        no_num = self._json(
            self._api(
                "patch", "/api/parametros/rendimiento_min_plausible/",
                {"valor": "abc"},
            )
        )
        self.assertIn("número mayor que 0", no_num["valor"][0])
        cero = self._json(
            self._api(
                "patch", "/api/parametros/rendimiento_min_plausible/", {"valor": "0"}
            )
        )
        self.assertIn("número mayor que 0", cero["valor"][0])

        incoherente = self._json(
            self._api(
                "patch", "/api/parametros/rendimiento_min_plausible/",
                {"valor": "6000"},
            )
        )
        self.assertIn(
            "El rendimiento mínimo debe ser menor que el máximo.",
            incoherente["valor"],
        )
        inverso = self._json(
            self._api(
                "patch", "/api/parametros/rendimiento_max_plausible/",
                {"valor": "50"},
            )
        )
        self.assertIn(
            "El rendimiento mínimo debe ser menor que el máximo.",
            inverso["valor"],
        )

        creada = self._json(self._crear(cantidad_producida="1"))
        self.assertTrue(creada["requiere_revision"])
        cambiado = self._json(
            self._api(
                "patch", "/api/parametros/rendimiento_min_plausible/", {"valor": "1"}
            )
        )
        self.assertEqual(cambiado["valor"], "1")
        # El cambio de umbral NO reevalúa lo ya marcado (solo INSERT/UPDATE)
        marcada = self._json(self._api("get", f"/api/producciones/{creada['id']}/"))
        self.assertTrue(marcada["requiere_revision"])

        self._json(
            self._api(
                "post",
                "/api/producciones/",
                self._datos(
                    campania=self.campania_b.pk,
                    fecha_cosecha="2026-04-20",
                    cantidad_producida="1",
                ),
            )
        )
        nueva = self._consulta(
            "SELECT requiere_revision FROM producciones WHERE campania_id = %s",
            [self.campania_b.pk],
        )[0][0]
        self.assertFalse(nueva)

        self.assertEqual(
            self._api("get", "/api/parametros/inexistente/").status_code, 404
        )
        self.assertEqual(
            self._api("post", "/api/parametros/", {"valor": "1"}).status_code, 405
        )
        self.assertEqual(
            self._api("delete", "/api/parametros/dias_sin_actividad/").status_code,
            405,
        )

        self._entrar_coordinador()
        self.assertEqual(
            self.client.get("/api/parametros/").status_code, 403
        )
        self._entrar_tecnico()
        self.assertEqual(
            self.client.get("/api/parametros/").status_code, 403
        )

    # ------------------------------------------------------------------ #
    # 117: las transiciones de estado solo las permite la base
    # ------------------------------------------------------------------ #
    def test_117_transiciones_de_estado_en_la_base(self):
        self._entrar_admin()
        self._sql_debe_fallar(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [self.campania.pk],
        )
        self._sql_debe_fallar(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [self.campania_b.pk],
        )
        self._sql(
            "UPDATE campanias SET estado = 'COSECHADA' WHERE id = %s",
            [self.campania_b.pk],
        )
        self._sql_debe_fallar(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [self.campania_b.pk],
        )
        self._sql(
            "UPDATE campanias SET estado = 'EN_PRODUCCION' WHERE id = %s",
            [self.campania_b.pk],
        )

        # El estado no es escribible por la API
        self._json(
            self._api(
                "patch", f"/api/campanias/{self.campania.pk}/",
                {"estado": "CERRADA"},
            )
        )
        self.campania.refresh_from_db()
        self.assertEqual(self.campania.estado, "EN_PRODUCCION")

    # ------------------------------------------------------------------ #
    # 118: ámbitos y permisos por rol; DELETE 405 y sin sesión 401
    # ------------------------------------------------------------------ #
    def test_118_ambitos_y_permisos_por_rol(self):
        self._entrar_admin()
        propia = self._json(self._crear())
        ajena = self._json(
            self._crear(
                campania=self.campania_b.pk,
                fecha_cosecha="2026-04-20",
                cantidad_producida="50",
            )
        )

        self._entrar_tecnico()
        listado = self._json(self.client.get("/api/producciones/"))
        self.assertEqual(listado["count"], 1)
        self.assertEqual(listado["results"][0]["id"], propia["id"])

        detalle_ajeno = self._json(
            self._api("get", f"/api/producciones/{ajena['id']}/")
        )
        self.assertEqual(detalle_ajeno["detail"], "No encontrado.")

        fuera_de_ambito = self._json(self._crear(campania=self.campania_b.pk))
        self.assertIn("La campaña indicada no existe.", fuera_de_ambito["campania"])

        propia_tecnico = self._json(
            self._api("get", f"/api/producciones/{propia['id']}/")
        )
        self.assertNotIn("registrado_por", propia_tecnico)

        self._entrar_coordinador()
        self.assertEqual(self.client.get("/api/producciones/").status_code, 200)
        self.assertEqual(self._crear().status_code, 403)
        self.assertEqual(
            self._api(
                "patch", f"/api/producciones/{propia['id']}/",
                {"observaciones": "x"},
            ).status_code,
            403,
        )
        self.assertEqual(self._revisar(propia["id"]).status_code, 403)
        self.assertEqual(self._deshacer(propia["id"]).status_code, 403)
        self.assertEqual(
            self._api("delete", f"/api/producciones/{propia['id']}/").status_code,
            405,
        )

        self.client.logout()
        self.assertEqual(
            self._api("get", "/api/producciones/").status_code, 401
        )

    # ------------------------------------------------------------------ #
    # 119: desplegable de campañas para el formulario; búsqueda y filtros
    # ------------------------------------------------------------------ #
    def test_119_desplegable_busqueda_y_filtros(self):
        self._entrar_admin()
        parcela_c = self._parcela_bd(self.p1, self.comunidad, "2.00")
        planificada = self._campania_bd(
            parcela_c, self.cultivo, self.variedad,
            superficie_sembrada_ha=Decimal("2.00"),
        )
        parcela_d = self._parcela_bd(self.p1, self.comunidad, "2.00")
        sin_siembra = self._campania_bd(
            parcela_d, self.cultivo, self.variedad,
            estado="EN_PRODUCCION", superficie_sembrada_ha=Decimal("2.00"),
        )

        def desplegable():
            respuesta = self.client.get("/api/campanias/?desplegable=1&produccion=1")
            return {c["id"] for c in self._json(respuesta)}

        self.assertEqual(
            desplegable(), {self.campania.pk, self.campania_b.pk}
        )

        self._json(self._crear())
        self.assertEqual(desplegable(), {self.campania_b.pk})

        self._json(
            self._crear(
                campania=self.campania_b.pk,
                fecha_cosecha="2026-04-20",
                cantidad_producida="1",
            )
        )
        self.assertEqual(desplegable(), set())
        self.assertNotIn(planificada.pk, desplegable())
        self.assertNotIn(sin_siembra.pk, desplegable())

        def ids(respuesta):
            return {p["id"] for p in self._json(respuesta)["results"]}

        id_propia = Produccion.objects.get(campania=self.campania).id
        id_ajena = Produccion.objects.get(campania=self.campania_b).id

        self.assertEqual(
            ids(
                self.client.get(
                    f"/api/producciones/?busqueda={self.parcela_b.codigo}"
                )
            ),
            {id_ajena},
        )
        self.assertEqual(
            ids(self.client.get("/api/producciones/?busqueda=Beta")), {id_ajena}
        )
        self.assertEqual(
            ids(self.client.get("/api/producciones/?busqueda=Maíz S8")), {id_ajena}
        )

        self.assertEqual(
            ids(self.client.get(f"/api/producciones/?campania={self.campania.pk}")),
            {id_propia},
        )
        self.assertEqual(
            ids(self.client.get(f"/api/producciones/?productor={self.p2.pk}")),
            {id_ajena},
        )
        self.assertEqual(
            len(ids(self.client.get(f"/api/producciones/?parcela={self.parcela_b.pk}"))), 1
        )
        self.assertEqual(
            len(ids(self.client.get(f"/api/producciones/?cultivo={self.cultivo_b.pk}"))), 1
        )
        self.assertEqual(
            len(ids(self.client.get("/api/producciones/?periodo=2025-2026"))), 2
        )
        self.assertEqual(
            len(ids(self.client.get(f"/api/producciones/?distrito={self.distrito_b.pk}"))), 1
        )
        self.assertEqual(
            len(ids(self.client.get(f"/api/producciones/?provincia={self.provincia.pk}"))), 2
        )
        self.assertEqual(
            len(ids(self.client.get("/api/producciones/?estado=COSECHADA"))), 2
        )
        self.assertEqual(
            len(ids(self.client.get("/api/producciones/?requiere_revision=true"))), 1
        )
        self.assertEqual(
            len(ids(self.client.get("/api/producciones/?requiere_revision=false"))), 1
        )
        self.assertEqual(
            len(ids(self.client.get("/api/producciones/?fecha_desde=2026-04-16"))), 1
        )
        self.assertEqual(
            len(ids(self.client.get("/api/producciones/?fecha_hasta=2026-04-15"))), 1
        )

        estado = self._json(self.client.get("/api/producciones/?estado=RARA"))
        self.assertIn("estado", estado)
        marca = self._json(
            self.client.get("/api/producciones/?requiere_revision=quizas")
        )
        self.assertIn("requiere_revision", marca)
        campania_mala = self._json(self.client.get("/api/producciones/?campania=abc"))
        self.assertIn("campania", campania_mala)

    # ------------------------------------------------------------------ #
    # 120: los 22 triggers del proyecto (15 de la S8 + 3 de uso_recursos
    #     de la S9 + 1 de clima de la S10 + 3 de incidencias de la S11)
    #     y la reversibilidad del SQL
    # ------------------------------------------------------------------ #
    def test_120_triggers_y_reversibilidad_de_las_migraciones(self):
        triggers = {
            fila[0]
            for fila in self._consulta(
                "SELECT tgname FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid IN (SELECT oid FROM pg_class "
                "WHERE relnamespace = 'public'::regnamespace)"
            )
        }
        # 15 al cerrar la Semana 8; la Semana 9 añade los 3 de
        # uso_recursos, la Semana 10 el de actualizado de clima y la
        # Semana 11 los 3 de incidencias
        self.assertEqual(len(triggers), 22)
        self.assertLessEqual(
            {
                "trg_producciones_validar",
                "trg_producciones_post",
                "trg_producciones_actualizado",
            },
            triggers,
        )
        self.assertLessEqual(
            {"trg_parametros_sistema_actualizado", "trg_clima_actualizado"},
            triggers,
        )

        prosrc = {
            fila[0]: fila[1]
            for fila in self._consulta(
                "SELECT proname, prosrc FROM pg_proc "
                "WHERE proname IN ('fn_validar_campania', 'fn_validar_produccion',"
                " 'fn_produccion_post')"
            )
        }
        self.assertIn("'CERRADA'", prosrc["fn_validar_campania"])
        self.assertIn("producciones", prosrc["fn_validar_campania"])
        self.assertIn("parametros_sistema", prosrc["fn_validar_produccion"])
        self.assertIn("'COSECHADA'", prosrc["fn_produccion_post"])

        # Reversibilidad real: la reversión de 0003 restaura la versión
        # parcial y el avance vuelve a instalar la completa
        mig_campanias = importlib.import_module(
            "campanias.migrations.0003_fn_validar_campania_completa"
        )
        for consulta in mig_campanias.Migration.operations[0].reverse_sql:
            self._sql(consulta)
        parcial = self._consulta(
            "SELECT prosrc FROM pg_proc WHERE proname = 'fn_validar_campania'"
        )[0][0]
        self.assertNotIn("'CERRADA'", parcial)
        for consulta in mig_campanias.Migration.operations[0].sql:
            self._sql(consulta)
        completa = self._consulta(
            "SELECT prosrc FROM pg_proc WHERE proname = 'fn_validar_campania'"
        )[0][0]
        self.assertIn("'CERRADA'", completa)

        mig_produccion = importlib.import_module(
            "produccion.migrations.0002_funciones_y_triggers"
        )
        for consulta in mig_produccion.Migration.operations[0].reverse_sql:
            self._sql(consulta)
        restantes = self._consulta(
            "SELECT count(*) FROM pg_trigger "
            "WHERE NOT tgisinternal AND tgrelid = 'producciones'::regclass"
        )[0][0]
        self.assertEqual(restantes, 0)
        for consulta in mig_produccion.Migration.operations[0].sql:
            self._sql(consulta)
        restaurados = {
            fila[0]
            for fila in self._consulta(
                "SELECT tgname FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid = 'producciones'::regclass"
            )
        }
        self.assertEqual(
            restaurados,
            {
                "trg_producciones_validar",
                "trg_producciones_post",
                "trg_producciones_actualizado",
            },
        )
