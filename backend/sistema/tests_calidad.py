"""Pruebas de la Semana 14: matriz de reglas de calidad (HU-121/HU-122).

Numeración del repositorio 236-241 (6 pruebas → 241 en total; el
repositorio llegaba a 235 con los tests de roles). Cada prueba cruza una
familia de reglas RN-01…RN-16 a nivel de API y de base de datos (los
mismos triggers/ CHECKs del diseño en DB_sql), de modo que la matriz de
docs/matriz_reglas_calidad.md se apoya en código ejecutable y no solo en
el diseño. No duplican casos pormenorizados (eso lo hacen las pruebas de
cada semana): aquí se confirma que ambas redes de seguridad existen y
siguen vivas.
"""
import json
import re
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver

from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Unidad, Variedad
from productores.models import (
    Comunidad, Distrito, Parcela, Productor, Provincia,
)
from seguimiento.models import Clima, Incidencia, TipoIncidencia
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login


class CalidadBase(TestCase):
    """Datos comunes de la matriz: admin, ubicación, cultivo, dos
    productores, parcelas, campañas en los estados que usan las reglas
    (PLANIFICADA, EN_PRODUCCION con siembra, EN_PRODUCCION sin siembra) y
    helpers de API y de SQL directo."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_calidad", email="", password="AdminCalidad2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.provincia = Provincia.objects.create(nombre="Prov S14")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S14"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S14"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua S14")
        self.variedad = Variedad.objects.create(
            cultivo=self.cultivo, nombre="Real S14"
        )
        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="91000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p1.refresh_from_db()
        self.parcela = self._parcela_bd("2.00")
        self.parcela_b = self._parcela_bd("3.00")
        self.preparacion = TipoActividad.objects.get(codigo="PREPARACION")
        self.helada = TipoIncidencia.objects.get(nombre="Helada")
        self.quintal = Unidad.objects.create(
            nombre="Quintal", simbolo="qq", tipo="MASA",
            factor_a_base=Decimal("46"), es_base=False,
        )
        # Campaña en producción con siembra (la carga histórica permite
        # INSERT en EN_PRODUCCION; la fecha se fija a mano como en S8)
        self.campania = self._campania_bd(
            self.parcela, estado="EN_PRODUCCION",
            fecha_siembra=date(2025, 10, 1),
            superficie_sembrada_ha=Decimal("2.00"),
        )
        # Campaña planificada para duplicados y estados que no producen
        self.planificada = self._campania_bd(
            self.parcela_b, periodo="2026-2027",
            fecha_inicio=date(2026, 9, 1), fecha_fin_prevista=date(2027, 5, 31),
        )
        # Campaña en producción sin siembra registrada (RN-07)
        self.sin_siembra = self._campania_bd(
            self._parcela_bd("1.50"), estado="EN_PRODUCCION",
            fecha_siembra=None, superficie_sembrada_ha=Decimal("1.50"),
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar_admin(self):
        self.assertEqual(
            _post_login(self.client, "admin_calidad", "AdminCalidad2026!"
                        ).status_code,
            200,
        )

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _parcela_bd(self, superficie):
        parcela = Parcela.objects.create(
            productor=self.p1, comunidad=self.comunidad,
            superficie_ha=superficie, altitud_msnm=3850,
            tipo_suelo="FRANCO", pendiente="SUAVE",
            disponibilidad_agua="MEDIA", sistema_riego="GOTEO",
        )
        parcela.refresh_from_db()  # el trigger rellena codigo
        return parcela

    def _campania_bd(self, parcela, **extra):
        datos = {
            "periodo": "2025-2026",
            "parcela": parcela,
            "cultivo": self.cultivo,
            "variedad": self.variedad,
            "fecha_inicio": date(2025, 9, 1),
            "fecha_fin_prevista": date(2026, 5, 31),
            "superficie_sembrada_ha": Decimal("1.50"),
        }
        datos.update(extra)
        return Campania.objects.create(**datos)

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

    def _datos_campania(self, **extra):
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

    def _datos_produccion(self, **extra):
        datos = {
            "campania": self.campania.pk,
            "fecha_cosecha": "2026-04-15",
            "superficie_cosechada_ha": "2.00",
            "cantidad_producida": "70",
            "unidad": self.quintal.pk,
        }
        datos.update(extra)
        return datos

    def _datos_clima(self, parcela, fecha, **extra):
        datos = {
            "parcela": parcela.pk,
            "fecha": fecha,
            "temp_min": "5.0",
            "temp_max": "15.0",
        }
        datos.update(extra)
        return datos

    def _sql(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            if parametros:
                cursor.execute(consulta, parametros)
            else:
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


class MatrizReglasCalidadTests(CalidadBase):
    """Pruebas 236-241."""

    # ------------------------------------------------------------------ #
    # 236 (RN-01, RN-02, RN-12): superficies > 0 y topes por campaña
    # ------------------------------------------------------------------ #
    def test_236_superficies_mayores_que_cero_y_techos_en_la_base(self):
        self._entrar_admin()

        # RN-01: parcela > 0 (API y CHECK)
        cero = self._api("post", "/api/parcelas/", self._datos_parcela(superficie_ha="0"))
        self.assertEqual(cero.status_code, 400)
        self.assertIn("mayor que 0", str(self._json(cero)["superficie_ha"]))
        self._sql_debe_fallar(
            "INSERT INTO parcelas (productor_id, comunidad_id, superficie_ha, "
            "altitud_msnm, tipo_suelo, pendiente, disponibilidad_agua, "
            "sistema_riego, estado, creado_por, creado_en, actualizado_en) "
            "VALUES (%s, %s, 0, 3850, 'FRANCO', 'SUAVE', 'MEDIA', 'GOTEO', "
            "'ACTIVA', %s, now(), now())",
            [self.p1.pk, self.comunidad.pk, self.admin.pk],
        )

        # RN-02: superficie sembrada > 0 y ≤ parcela (API y trigger)
        sembrada_cero = self._api(
            "post", "/api/campanias/", self._datos_campania(superficie_sembrada_ha="0")
        )
        self.assertEqual(sembrada_cero.status_code, 400)
        self.assertIn(
            "mayor que 0", str(self._json(sembrada_cero)["superficie_sembrada_ha"])
        )
        sembrada_alta = self._api(
            "post", "/api/campanias/", self._datos_campania(superficie_sembrada_ha="2.50")
        )
        self.assertEqual(sembrada_alta.status_code, 400)
        self.assertIn(
            "no puede superar la superficie de la parcela",
            str(self._json(sembrada_alta)["superficie_sembrada_ha"]),
        )
        self._sql_debe_fallar(
            "UPDATE campanias SET superficie_sembrada_ha = 9.00 WHERE id = %s",
            [self.campania.pk],
        )

        # RN-02: superficie cosechada > 0 y ≤ sembrada (API y trigger)
        cosechada_cero = self._api(
            "post", "/api/producciones/", self._datos_produccion(superficie_cosechada_ha="0")
        )
        self.assertEqual(cosechada_cero.status_code, 400)
        self.assertIn(
            "mayor que 0",
            str(self._json(cosechada_cero)["superficie_cosechada_ha"]),
        )
        cosechada_alta = self._api(
            "post", "/api/producciones/", self._datos_produccion(superficie_cosechada_ha="2.50")
        )
        self.assertEqual(cosechada_alta.status_code, 400)
        self.assertIn(
            "no puede superar la sembrada",
            str(self._json(cosechada_alta)["superficie_cosechada_ha"]),
        )
        produccion = self._json(
            self._api("post", "/api/producciones/", self._datos_produccion())
        )
        self._sql_debe_fallar(
            "UPDATE producciones SET superficie_cosechada_ha = 3.00 WHERE id = %s",
            [produccion["id"]],
        )

        # RN-12: superficie afectada ≥ 0 y ≤ sembrada (API y trigger)
        afectada_alta = self._api(
            "post", "/api/incidencias/",
            {
                "campania": self.campania.pk,
                "tipo_incidencia": self.helada.pk,
                "fecha": "2025-10-05",
                "severidad": "MEDIA",
                "descripcion": "Helada tardía",
                "superficie_afectada_ha": "2.50",
            },
        )
        self.assertEqual(afectada_alta.status_code, 400)
        self.assertIn(
            "supera la sembrada",
            str(self._json(afectada_alta)["superficie_afectada_ha"]),
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                Incidencia.objects.create(
                    campania=self.campania, tipo_incidencia=self.helada,
                    fecha=date(2025, 10, 6), severidad="MEDIA",
                    descripcion="SQL crudo", superficie_afectada_ha=Decimal("3.00"),
                )

    # ------------------------------------------------------------------ #
    # 237 (RN-07, RN-08, RN-09): fechas de cosecha, período de campaña y
    #     estados cerrados/cancelados que no admiten registros
    # ------------------------------------------------------------------ #
    def test_237_fechas_y_estados_que_no_admiten_registros(self):
        self._entrar_admin()

        # RN-07: la cosecha no es anterior a la siembra registrada
        anterior = self._json(
            self._api(
                "post", "/api/producciones/",
                self._datos_produccion(fecha_cosecha="2025-09-15"),
            )
        )
        self.assertIn("anterior a la fecha de siembra", anterior["fecha_cosecha"][0])

        # RN-07: sin siembra registrada no hay cosecha (ni en la API…)
        sin_siembra = self._json(
            self._api(
                "post", "/api/producciones/",
                self._datos_produccion(campania=self.sin_siembra.pk),
            )
        )
        self.assertIn("no tiene siembra registrada", sin_siembra["campania"][0])
        # …ni en la base: el trigger compara la cosecha con la siembra
        parcela_d = self._parcela_bd("2.00")
        campania_d = self._campania_bd(
            parcela_d, estado="EN_PRODUCCION", fecha_siembra=date(2025, 10, 1),
            superficie_sembrada_ha=Decimal("2.00"),
        )
        with self.assertRaises(DatabaseError) as falla:
            with transaction.atomic():
                self._sql(
                    "INSERT INTO producciones (campania_id, fecha_cosecha, "
                    "superficie_cosechada_ha, cantidad_producida, unidad_id) "
                    "VALUES (%s, '2025-09-15', 1.50, 50, %s)",
                    [campania_d.pk, self.quintal.pk],
                )
        self.assertIn("anterior a la fecha de siembra", str(falla.exception))

        # RN-08: la actividad debe caer dentro del período de la campaña
        fuera = self._json(
            self._api(
                "post", "/api/actividades/",
                {
                    "campania": self.campania.pk,
                    "tipo_actividad": self.preparacion.pk,
                    "fecha": "2025-08-31",
                    "metodo": "Arado de disco",
                },
            )
        )
        self.assertIn("fuera del período", fuera["fecha"][0])
        # Lo mismo en la base (fn_validar_fecha_campania)
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self._sql(
                    "INSERT INTO actividades (campania_id, tipo_actividad_id, "
                    "fecha, metodo, anulada, registrado_por, creado_en, "
                    "actualizado_en) VALUES (%s, %s, '2025-08-30', 'SQL crudo', "
                    "false, %s, now(), now())",
                    [self.campania.pk, self.preparacion.pk, self.admin.pk],
                )

        # RN-08/RN-09: la campaña cerrada no admite cosecha ni actividades
        producida = self._json(
            self._api("post", "/api/producciones/", self._datos_produccion())
        )
        self.assertEqual(producida["campania"]["estado"], "COSECHADA")
        self.assertEqual(
            self._api(
                "post", f"/api/campanias/{self.campania.pk}/cerrar/"
            ).status_code,
            200,
        )
        actividad_cerrada = self._json(
            self._api(
                "post", "/api/actividades/",
                {
                    "campania": self.campania.pk,
                    "tipo_actividad": self.preparacion.pk,
                    "fecha": "2025-10-02",
                    "metodo": "Arado de disco",
                },
            )
        )
        self.assertIn(
            "La campaña está CERRADA y no admite nuevos registros.",
            actividad_cerrada["campania"],
        )
        cosecha_cerrada = self._json(
            self._api(
                "post", "/api/producciones/",
                self._datos_produccion(fecha_cosecha="2026-04-20"),
            )
        )
        self.assertIn(
            "La campaña está CERRADA y no admite nuevos registros.",
            cosecha_cerrada["campania"],
        )

        # RN-09: la campaña cancelada tampoco admite nada
        self.assertEqual(
            self._api(
                "post", f"/api/campanias/{self.planificada.pk}/cancelar/",
                {"motivo": "Sin presupuesto"},
            ).status_code,
            200,
        )
        en_cancelada = self._json(
            self._api(
                "post", "/api/actividades/",
                {
                    "campania": self.planificada.pk,
                    "tipo_actividad": self.preparacion.pk,
                    "fecha": "2026-09-10",
                    "metodo": "Arado de disco",
                },
            )
        )
        self.assertIn("CANCELADA", en_cancelada["campania"][0])

    # ------------------------------------------------------------------ #
    # 238 (RN-10, RN-11): una campaña activa por parcela, un cultivo por
    #     parcela y período, y DNI único de 8 dígitos
    # ------------------------------------------------------------------ #
    def test_238_unicidades_por_indice_y_por_api(self):
        self._entrar_admin()

        # RN-10: un cultivo por parcela y período (API y índice único)
        duplicada = self._json(
            self._api("post", "/api/campanias/", self._datos_campania())
        )
        self.assertIn("Ya existe una campaña", duplicada["parcela"][0])
        self._sql_debe_fallar(
            "INSERT INTO campanias (periodo, parcela_id, cultivo_id, "
            "variedad_id, fecha_inicio, fecha_fin_prevista, "
            "superficie_sembrada_ha, estado, creado_por, creado_en, "
            "actualizado_en) VALUES ('2025-2026', %s, %s, %s, '2025-09-01', "
            "'2026-05-31', 1.00, 'PLANIFICADA', %s, now(), now())",
            [self.parcela.pk, self.cultivo.pk, self.variedad.pk, self.admin.pk],
        )

        # RN-10: una sola campaña activa por parcela (índice parcial)
        parcela_c = self._parcela_bd("4.00")
        activa = self._api(
            "post", "/api/campanias/",
            self._datos_campania(
                periodo="2026-2027", parcela=parcela_c.pk,
                fecha_inicio="2026-09-01", fecha_fin_prevista="2027-05-31",
            ),
        )
        self.assertEqual(activa.status_code, 201)
        segunda = self._json(
            self._api(
                "post", "/api/campanias/",
                self._datos_campania(
                    periodo="2027-2028", parcela=parcela_c.pk,
                    fecha_inicio="2027-09-01", fecha_fin_prevista="2028-05-31",
                ),
            )
        )
        self.assertIn("campaña activa", segunda["parcela"][0])

        # RN-11: DNI de 8 dígitos y único (API y CHECK)
        corto = self._json(
            self._api(
                "post", "/api/productores/",
                {
                    "nombres": "Corto", "apellidos": "DNI", "dni": "1234567",
                    "comunidad": self.comunidad.pk,
                },
            )
        )
        self.assertIn("exactamente 8 dígitos", corto["dni"][0])
        repetido = self._json(
            self._api(
                "post", "/api/productores/",
                {
                    "nombres": "Repetido", "apellidos": "DNI", "dni": "91000001",
                    "comunidad": self.comunidad.pk,
                },
            )
        )
        self.assertIn("Ya existe un productor con ese DNI", repetido["dni"][0])
        self._sql_debe_fallar(
            "INSERT INTO productores (nombres, apellidos, dni, comunidad_id, "
            "creado_por, creado_en, actualizado_en) VALUES ('Crudo', 'SQL', "
            "'1234567', %s, %s, now(), now())",
            [self.comunidad.pk, self.admin.pk],
        )

    # ------------------------------------------------------------------ #
    # 239 (RN-04, RN-05, RN-06): rangos de clima y coordenadas de parcela
    # ------------------------------------------------------------------ #
    def test_239_rangos_de_clima_y_coordenadas_de_parcela(self):
        self._entrar_admin()

        # RN-04: precipitación ≥ 0 y humedad 0-100 (API y CHECK)
        precip = self._json(
            self._api(
                "post", "/api/clima/",
                self._datos_clima(self.parcela, "2025-10-01", precipitacion_mm="-1"),
            )
        )
        self.assertIn("negativa", precip["precipitacion_mm"][0])
        humeda = self._json(
            self._api(
                "post", "/api/clima/",
                self._datos_clima(self.parcela, "2025-10-02", humedad_pct="150"),
            )
        )
        self.assertIn("entre 0 y 100", humeda["humedad_pct"][0])
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                Clima.objects.create(
                    parcela=self.parcela, fecha=date(2025, 10, 7),
                    temp_min=Decimal("5.0"), temp_max=Decimal("15.0"),
                    humedad_pct=Decimal("150"),
                )

        # RN-05: rangos de temperatura y mínima ≤ máxima (API y CHECK)
        fuera_rango = self._json(
            self._api(
                "post", "/api/clima/",
                self._datos_clima(self.parcela, "2025-10-03", temp_min="50.0"),
            )
        )
        self.assertIn("entre -30 y 45", fuera_rango["temp_min"][0])
        invertidas = self._json(
            self._api(
                "post", "/api/clima/",
                self._datos_clima(
                    self.parcela, "2025-10-04", temp_min="20.0", temp_max="10.0"
                ),
            )
        )
        self.assertIn("máxima", invertidas["temp_min"][0])
        self._sql_debe_fallar(
            "INSERT INTO clima (parcela_id, fecha, temp_min, temp_max, "
            "registrado_por, creado_en, actualizado_en) VALUES (%s, '2025-10-08', "
            "20.0, 10.0, %s, now(), now())",
            [self.parcela.pk, self.admin.pk],
        )

        # RN-06: latitud y longitud, las dos o ninguna (API y CHECK)
        solo_lat = {k: v for k, v in self._datos_parcela().items() if k != "longitud"}
        rechazo = self._api("post", "/api/parcelas/", solo_lat)
        self.assertEqual(rechazo.status_code, 400)
        texto = str(self._json(rechazo)).replace("í", "i")
        self.assertIn("dos vacias", texto)
        self._sql_debe_fallar(
            "UPDATE parcelas SET latitud = -15.5, longitud = NULL WHERE id = %s",
            [self.parcela.pk],
        )

    # ------------------------------------------------------------------ #
    # 240 (RN-03, RN-13, RN-14, RN-15): rendimiento calculado en el
    #     servidor, 0 kg con marca de revisión y cierre bloqueado
    # ------------------------------------------------------------------ #
    def test_240_rendimiento_calculado_revision_y_cierre(self):
        self._entrar_admin()

        # RN-14: los campos calculados no los escribe el cliente
        calculada = self._json(
            self._api(
                "post", "/api/producciones/",
                self._datos_produccion(
                    produccion_kg="999", rendimiento_kg_ha="999"
                ),
            )
        )
        self.assertEqual(calculada["produccion_kg"], "3220.00")
        self.assertEqual(calculada["rendimiento_kg_ha"], "1610.00")
        editada = self._json(
            self._api(
                "patch", f"/api/producciones/{calculada['id']}/",
                {"produccion_kg": "1", "rendimiento_kg_ha": "1"},
            )
        )
        self.assertEqual(editada["produccion_kg"], "3220.00")

        # RN-14: la base recalcula con su propio trigger
        self._sql(
            "UPDATE producciones SET cantidad_producida = 140 WHERE id = %s",
            [calculada["id"]],
        )
        kg, rendimiento = self._consulta(
            "SELECT produccion_kg, rendimiento_kg_ha FROM producciones WHERE id = %s",
            [calculada["id"]],
        )[0]
        self.assertEqual(kg, Decimal("6440.00"))
        self.assertEqual(rendimiento, Decimal("3220.00"))

        # RN-03/RN-15: 0 kg se acepta y queda marcada para revisión
        parcela_c = self._parcela_bd("2.00")
        campania_c = self._campania_bd(
            parcela_c, estado="EN_PRODUCCION", fecha_siembra=date(2025, 10, 1),
            superficie_sembrada_ha=Decimal("2.00"),
        )
        cero = self._json(
            self._api(
                "post", "/api/producciones/",
                self._datos_produccion(
                    campania=campania_c.pk, cantidad_producida="0",
                    superficie_cosechada_ha="2.00",
                ),
            )
        )
        self.assertEqual(cero["produccion_kg"], "0.00")
        self.assertTrue(cero["requiere_revision"])
        self.assertIn("Rendimiento atípico", cero["motivo_revision"])

        # RN-13: la revisión pendiente bloquea el cierre
        self.assertEqual(
            self._api(
                "post", f"/api/campanias/{campania_c.pk}/cerrar/"
            ).status_code,
            400,
        )
        cierre = self._json(
            self._api("post", f"/api/campanias/{campania_c.pk}/cerrar/")
        )
        self.assertIn("requiere revisión pendiente", str(cierre))
        # Revisada la producción, el cierre ya pasa
        self.assertEqual(
            self._api(
                "post", f"/api/producciones/{cero['id']}/revisar/",
                {"nota": "Revisado con el productor", "incluir_en_entrenamiento": True},
            ).status_code,
            200,
        )
        self.assertEqual(
            self._api(
                "post", f"/api/campanias/{campania_c.pk}/cerrar/"
            ).status_code,
            200,
        )

    # ------------------------------------------------------------------ #
    # 241 (RN-16): ninguna ruta de la API acepta DELETE (lista de
    #     excepciones vacía: deshacer-cosecha es un POST con motivo)
    # ------------------------------------------------------------------ #
    def test_241_ninguna_ruta_de_la_api_acepta_delete(self):
        self._entrar_admin()
        excepciones = []  # debe quedarse vacía: no hay DELETE en la API

        rutas = []
        for patron in get_resolver().url_patterns:
            if isinstance(patron, URLResolver):
                prefijo = getattr(patron.pattern, "_route", None) or str(
                    patron.pattern.regex.pattern
                )
                if not prefijo.startswith("api/"):
                    continue
                for sub in patron.url_patterns:
                    ruta = getattr(sub.pattern, "_route", None) or str(
                        sub.pattern.regex.pattern
                    )
                    rutas.append(prefijo + ruta)
            elif isinstance(patron, URLPattern):
                ruta = getattr(patron.pattern, "_route", None) or str(
                    patron.pattern.regex.pattern
                )
                if ruta.startswith("api/"):
                    rutas.append(ruta)

        # Al menos las nueve colecciones conocidas deben estar presentes
        self.assertGreaterEqual(len(rutas), 40)

        probadas = 0
        for ruta in rutas:
            concreta = re.sub(r"\(\?P<\w+>\[\^/\]\+\)", "1", ruta)
            concreta = re.sub(r"\(\?P<\w+>\\d\+\)", "1", concreta)
            if "(" in concreta:
                continue  # red rara: se omite en vez de fingir cobertura
            with self.subTest(ruta="/" + concreta):
                respuesta = self.client.delete("/" + concreta)
                probadas += 1
                if concreta.rstrip("/") in excepciones:
                    return
                # El método no puede existir: ni 2xx/3xx ni un DELETE
                # enseñado a un cliente (403 sin permiso)
                self.assertIn(respuesta.status_code, (405, 404, 403))

        # La lista de excepciones de la matriz sigue vacía
        self.assertEqual(excepciones, [])
        self.assertGreaterEqual(probadas, 30)
