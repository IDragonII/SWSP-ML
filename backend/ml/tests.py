"""Pruebas de la Semana 21: preparación de datos para Machine Learning.

Numeración 346-365 (20 pruebas → 365 en total; el repositorio cerró la
Semana 20 en 345). Cubren la exportación del dataset (permisos, ficha
técnica, auditoría, ruta y columnas), la vista con identificadores, el
catálogo de variables y su control de fuga, la carga del archivo, la
limpieza con su tabla de exclusiones, la imputación y transformaciones
dentro del pipeline, la validación agrupada y la línea base, y la
higiene final (notebooks sin salidas, 29 tablas y 25 triggers).

Los datos de estas pruebas son de demostración: ninguna cifra que salga
de aquí se presenta como resultado de la tesis.
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import Cultivo, Unidad, Variedad
from productores.models import Comunidad, Distrito, Parcela, Productor, Provincia
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

RUTA_VISTA = "vw_dataset_entrenamiento"


class MLBase(TestCase):
    """Base de la Semana 21: cuentas, geografía, cultivo y helpers para
    tocar la vista, la BD y la API como en el resto del proyecto."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin_ml", email="", password="AdminMl2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_ml", password="CoordMl2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.provincia = Provincia.objects.create(nombre="Prov S21")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S21"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S21"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua S21")
        self.variedad = Variedad.objects.create(
            cultivo=self.cultivo, nombre="Blanca S21"
        )
        self.kg = Unidad.objects.get(nombre="Kilogramo")
        self.periodo = "2026-2027"
        self.hoy = timezone.localdate()

    # ------------------------------------------------------------------ #
    # helpers de API (los mismos patrones que dashboard/tests.py)
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_ml", "AdminMl2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    # ------------------------------------------------------------------ #
    # helpers de datos (fixtures mínimas para la vista y el pipeline)
    # ------------------------------------------------------------------ #
    def _sql(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            cursor.execute(consulta, parametros or [])

    def _productor(self, dni="96000001", nombre="Uno", **extra):
        datos = {
            "nombres": nombre,
            "apellidos": "Prueba",
            "dni": dni,
            "comunidad": self.comunidad,
            "creado_por": self.admin,
        }
        datos.update(extra)
        return Productor.objects.create(**datos)

    def _parcela(self, productor, **extra):
        datos = {
            "productor": productor,
            "comunidad": productor.comunidad,
            "superficie_ha": "4.00",
            "altitud_msnm": 3900,
            "tipo_suelo": "FRANCO",
            "pendiente": "SUAVE",
            "disponibilidad_agua": "MEDIA",
            "sistema_riego": "GOTEO",
        }
        datos.update(extra)
        parcela = Parcela.objects.create(**datos)
        parcela.refresh_from_db()
        return parcela

    def _campania(self, parcela, **extra):
        datos = {
            "periodo": self.periodo,
            "parcela": parcela,
            "cultivo": self.cultivo,
            "variedad": self.variedad,
            "fecha_inicio": self.hoy - timedelta(days=60),
            "fecha_fin_prevista": self.hoy + timedelta(days=120),
            "estado": Campania.ESTADO_EN_PRODUCCION,
            "superficie_sembrada_ha": Decimal("1.50"),
        }
        datos.update(extra)
        campania = Campania.objects.create(**datos)
        campania.refresh_from_db()
        return campania

    def _producir(self, campania, superficie, kilos):
        """Producción por SQL crudo: los triggers calculan kg y
        rendimiento (mismo camino que la API)."""
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO producciones (campania_id, fecha_cosecha,"
                " superficie_cosechada_ha, cantidad_producida, unidad_id,"
                " produccion_kg, rendimiento_kg_ha, observaciones)"
                " VALUES (%s, %s, %s, %s, %s, 0, 0, '')",
                [
                    campania.pk, self.hoy - timedelta(days=5),
                    Decimal(superficie), Decimal(kilos), self.kg.pk,
                ],
            )
        campania.refresh_from_db()
        return campania

    def _cerrar(self, campania):
        self._sql(
            "UPDATE campanias SET estado = 'CERRADA' WHERE id = %s",
            [campania.pk],
        )
        campania.refresh_from_db()
        return campania

    # ------------------------------------------------------------------ #
    # helpers de la vista
    # ------------------------------------------------------------------ #
    def _columnas_vista(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name = %s ORDER BY ordinal_position",
                [RUTA_VISTA],
            )
            return [fila[0] for fila in cursor.fetchall()]

    def _filas_vista(self):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {RUTA_VISTA}")
            columnas = [col.name for col in cursor.description]
            return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


class VistaTests(MLBase):
    """Prueba 349: la vista nueva trae productor_id y parcela_id, su
    total coincide con la tarjeta «aptas» del dashboard y la migración
    es reversible."""

    def test_349_vista_con_identificadores_total_tarjeta_y_reversible(self):
        # Fixture: una sola campaña apta para entrenar
        p1 = self._productor(dni="96000001")
        parcela = self._parcela(p1)
        campania = self._campania(parcela)
        self._producir(campania, "1.50", "300")
        self._cerrar(campania)

        # Columnas: los dos identificadores internos, tras campania_id
        columnas = self._columnas_vista()
        self.assertIn("parcela_id", columnas)
        self.assertIn("productor_id", columnas)
        self.assertLess(
            columnas.index("campania_id"), columnas.index("parcela_id")
        )
        self.assertLess(
            columnas.index("parcela_id"), columnas.index("productor_id")
        )
        # Números internos, no datos personales (no hay DNI ni nombres)
        for prohibida in ("dni", "nombres", "apellidos", "telefono"):
            self.assertNotIn(prohibida, columnas)

        # Valores: los ids de la fila son los de la parcela y el productor
        filas = self._filas_vista()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["parcela_id"], parcela.pk)
        self.assertEqual(filas[0]["productor_id"], p1.pk)

        # Total idéntico a la tarjeta «aptas para entrenar» (admin)
        self._entrar_admin()
        resumen = self._json(
            self._api("get", "/api/dashboard/resumen/")
        )
        self.assertEqual(resumen["aptas_entrenar"], len(filas))

        # Reversibilidad: al volver a la Semana 20 desaparecen las
        # dos columnas (el WHERE no cambia: el total sigue en 1)
        executor = MigrationExecutor(connection)
        executor.migrate([("importaciones", "0002_vista_dataset")])
        sin_ids = self._columnas_vista()
        self.assertNotIn("parcela_id", sin_ids)
        self.assertNotIn("productor_id", sin_ids)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {RUTA_VISTA}")
            self.assertEqual(cursor.fetchone()[0], 1)

        # Y al reaplicar vuelven
        executor = MigrationExecutor(connection)
        executor.migrate([("importaciones", "0003_vista_dataset_ids")])
        con_ids = self._columnas_vista()
        self.assertIn("parcela_id", con_ids)
        self.assertIn("productor_id", con_ids)
