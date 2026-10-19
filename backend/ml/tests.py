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
import hashlib
import io
import json
import os
import statistics
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase
from django.utils import timezone

from auditoria.models import Auditoria
from campanias.models import Campania
from catalogos.models import Cultivo, Unidad, Variedad
from productores.models import Comunidad, Distrito, Parcela, Productor, Provincia
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from ml import (
    catalogo,
    columnas,
    exportacion,
    linea_base,
    limpieza,
    preparacion,
    validacion,
)
from ml.carga import ErrorCarga, cargar

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


# ---------------------------------------------------------------------- #
# Fase 2: columna fija, carga, catálogo y control de fuga (350-355)
# ---------------------------------------------------------------------- #
def fila_valida(**extra):
    """Fila completa y válida para los CSV de prueba (datos inventados)."""
    fila = {
        "campania_id": 1,
        "parcela_id": 1,
        "productor_id": 1,
        "periodo": "2026-2027",
        "anio_campania": 2026,
        "cultivo": "Quinua",
        "variedad": "Blanca",
        "superficie_sembrada_ha": 1.5,
        "altitud_msnm": 3900,
        "tipo_suelo": "FRANCO",
        "pendiente": "SUAVE",
        "sistema_riego": "GOTEO",
        "origen": "SISTEMA",
        "precipitacion_acum_mm": 450.0,
        "temp_prom_c": 12.5,
        "humedad_prom_pct": 60.0,
        "n_heladas": 3,
        "dias_con_clima": 100,
        "dias_ventana_clima": 100,
        "semilla_kg_ha": 45.0,
        "fertilizante_kg_ha": 120.0,
        "jornales_ha": 30.0,
        "agua_m3_ha": 200.0,
        "n_incidencias": 1,
        "severidad_max": 2,
        "n_aplicaciones": 3,
        "dias_ciclo": 120,
        "rendimiento_kg_ha": 200.0,
    }
    fila.update(extra)
    return fila


class CSVBase(MLBase):
    """Base con un CSV temporal y helpers para escribirlo."""

    def setUp(self):
        super().setUp()
        self._carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self._carpeta.cleanup)
        self.ruta = Path(self._carpeta.name) / "dataset.csv"

    def _escribir_csv(self, filas, ruta=None):
        destino = ruta or self.ruta
        pd.DataFrame(filas).to_csv(destino, index=False, encoding="utf-8-sig")
        return destino


class ColumnasTests(CSVBase):
    """Prueba 350: la lista de columnas exportadas es fija y no contiene
    datos personales."""

    def test_350_lista_fija_de_columnas_sin_datos_personales(self):
        # La consulta se construye desde la lista: exactamente esas
        # columnas, nunca SELECT * y nunca otra
        seleccion = columnas.columnas_seleccionadas()
        self.assertEqual(seleccion, columnas.COLUMNAS_EXPORTADAS)
        self.assertNotIn("*", [c.strip() for c in seleccion])
        self.assertNotIn("SELECT *", columnas.consulta_exportacion().upper())

        # Toda columna de la lista existe en la vista
        vista = set(self._columnas_vista())
        self.assertTrue(set(seleccion) <= vista)

        # Ni la lista ni la vista llevan nombres, DNI ni teléfonos
        for prohibida in columnas.COLUMNAS_PROHIBIDAS:
            self.assertNotIn(prohibida, columnas.COLUMNAS_EXPORTADAS)
            self.assertNotIn(prohibida, vista)

        # Una columna nueva en la vista no sale sin declararse: no está
        # en la lista, y la consulta (hecha desde la lista) no la pide
        vista_con_nueva = vista | {"clave_nueva"}
        self.assertNotIn("clave_nueva", columnas.COLUMNAS_EXPORTADAS)
        self.assertTrue(set(seleccion) < vista_con_nueva)


class CargaTests(CSVBase):
    """Prueba 351: la carga rechaza columnas faltantes o tipos inválidos e
    informa las columnas desconocidas."""

    def test_351_columnas_faltantes_desconocidas_y_tipos_invalidos(self):
        # Válido de principio a fin (con cobertura de clima completa)
        self._escribir_csv([fila_valida()])
        datos = cargar(self.ruta)
        self.assertEqual(len(datos), 1)
        self.assertEqual(
            list(datos.columns), list(columnas.COLUMNAS_EXPORTADAS)
        )
        self.assertEqual(datos["rendimiento_kg_ha"].iloc[0], 200.0)
        # Clima con cobertura del 100 %: no se vacía
        self.assertEqual(datos["precipitacion_acum_mm"].iloc[0], 450.0)

        # Faltante declarada
        incompleta = fila_valida()
        del incompleta["altitud_msnm"]
        self._escribir_csv([incompleta])
        with self.assertRaises(ErrorCarga) as capturada:
            cargar(self.ruta)
        self.assertIn("altitud_msnm", str(capturada.exception))
        self.assertIn("Faltan columnas", str(capturada.exception))

        # Desconocida: se informa su nombre y no pasa
        con_extra = dict(fila_valida(), dato_raro=1)
        self._escribir_csv([con_extra])
        with self.assertRaises(ErrorCarga) as capturada:
            cargar(self.ruta)
        self.assertIn("dato_raro", str(capturada.exception))
        self.assertIn("desconocidas", str(capturada.exception))

        # Tipo inválido en una numérica (texto donde va un número)
        self._escribir_csv([fila_valida(), fila_valida(
            superficie_sembrada_ha="no_es_numero"
        )])
        with self.assertRaises(ErrorCarga) as capturada:
            cargar(self.ruta)
        self.assertIn("superficie_sembrada_ha", str(capturada.exception))
        self.assertIn("fila", str(capturada.exception))

        # Identificador vacío
        self._escribir_csv([fila_valida(productor_id="")])
        with self.assertRaises(ErrorCarga) as capturada:
            cargar(self.ruta)
        self.assertIn("productor_id", str(capturada.exception))


class CatalogoTests(CSVBase):
    """Pruebas 352-355: catálogo completo, control de fuga, conjuntos y
    cobertura de clima, y umbral de faltantes."""

    def test_352_toda_columna_de_la_vista_esta_clasificada(self):
        vista = self._columnas_vista()
        # Ni sobran en la vista ni faltan en el catálogo (una columna
        # nueva en la vista hace fallar esta prueba hasta declararla)
        self.assertEqual(sorted(catalogo.CATALOGO), sorted(vista))
        self.assertEqual(catalogo.sin_clasificar(vista), [])

    def test_353_los_conjuntos_excluyen_fuga_identificadores_y_metadatos(self):
        nunca = (
            "dias_ciclo",                      # fuga (fecha de cosecha)
            "campania_id", "parcela_id", "productor_id",  # identificadores
            "origen", "periodo", "anio_campania",         # metadatos
            "dias_con_clima", "dias_ventana_clima",       # cobertura
            "rendimiento_kg_ha",                # objetivo
            "n_incidencias", "severidad_max", "n_aplicaciones",  # C3
        )
        for conjunto in catalogo.CONJUNTOS:
            usadas = catalogo.columnas_conjunto(conjunto)
            for columna in nunca:
                self.assertNotIn(
                    columna, usadas,
                    f"{columna} no debe estar en el conjunto {conjunto}",
                )
            # Ninguna usada está declarada como no-predictora
            for columna in usadas:
                self.assertEqual(
                    catalogo.rol_de(columna), catalogo.ROL_PREDICTOR
                )
        # Control de fuga puntual
        self.assertTrue(catalogo.es_excluida_de_entrenamiento("dias_ciclo"))
        self.assertTrue(
            catalogo.es_excluida_de_entrenamiento("rendimiento_kg_ha")
        )
        self.assertFalse(catalogo.es_excluida_de_entrenamiento("cultivo"))

    def test_354_conjunto1_sin_clima_y_conjunto2_solo_con_cobertura(self):
        plan = catalogo.columnas_conjunto(catalogo.CONJUNTO_PLAN)
        con_clima = catalogo.columnas_conjunto(catalogo.CONJUNTO_CLIMA)

        # El plan no lleva clima; el comparativo sí, las 4 variables
        for columna in catalogo.COLUMNAS_CLIMA:
            self.assertNotIn(columna, plan)
            self.assertIn(columna, con_clima)
        # El plan es subconjunto del comparativo
        self.assertTrue(set(plan) <= set(con_clima))

        # Cobertura <80 % → el clima de esa campaña queda vacío;
        # ≥80 % → se conserva. Aplicado en la carga (CSV con ambas).
        completa = fila_valida()                       # 100/100
        escasa = fila_valida(                          # 70/100
            dias_con_clima=70,
            precipitacion_acum_mm=300.0,
            temp_prom_c=11.0,
            humedad_prom_pct=55.0,
            n_heladas=2,
        )
        limite = fila_valida(                          # 80/100 = 80 %
            dias_con_clima=80,
            precipitacion_acum_mm=400.0,
        )
        self._escribir_csv([completa, escasa, limite])
        datos = cargar(self.ruta)
        clima = list(catalogo.COLUMNAS_CLIMA)
        self.assertFalse(datos.loc[0, clima].isna().any())   # completa
        self.assertTrue(datos.loc[1, clima].isna().all())    # escasa
        self.assertFalse(datos.loc[2, clima].isna().any())   # en el límite
        # Las columnas de cobertura se conservan para auditar
        self.assertEqual(datos.loc[1, "dias_con_clima"], 70)

    def test_355_variables_con_mas_del_40_por_ciento_de_faltantes_fuera(self):
        filas = []
        for i in range(10):
            filas.append(fila_valida(
                campania_id=i + 1,
                altitud_msnm=None if i >= 5 else 3900,   # 50 % vacío
                pendiente=None if i >= 6 else "SUAVE",    # 40 % vacío
                variedad="Blanca",
            ))
        datos = pd.DataFrame(filas)
        fuera = catalogo.descartadas_por_faltantes(datos)
        # 50 % > 40 % → sale; exactamente 40 % no supera el umbral
        self.assertIn("altitud_msnm", fuera)
        self.assertAlmostEqual(fuera["altitud_msnm"], 0.5)
        self.assertNotIn("pendiente", fuera)
        self.assertNotIn("cultivo", fuera)
        # Lo que sale NO está en las columnas del conjunto elegido
        disponibles = [
            c for c in catalogo.columnas_conjunto(catalogo.CONJUNTO_PLAN)
            if c not in fuera
        ]
        self.assertNotIn("altitud_msnm", disponibles)
        self.assertIn("superficie_sembrada_ha", disponibles)


# ---------------------------------------------------------------------- #
# Fase 3: exportar_dataset con permisos, ficha y auditoría (346-348)
# ---------------------------------------------------------------------- #
class ExportarTests(MLBase):
    """Pruebas 346-348: el comando exportar_dataset escribe el CSV con
    su ficha técnica y deja un evento de auditoría sin contenido."""

    def setUp(self):
        super().setUp()
        # Una sola campaña apta en la vista (cerrada y con producción)
        p1 = self._productor(dni="96000001")
        parcela = self._parcela(p1)
        campania = self._campania(parcela)
        self._producir(campania, "1.50", "300")
        self._cerrar(campania)

    def _exportar(self, *argumentos, carpeta):
        with patch.dict(os.environ, {"ML_EXPORT_DIR": carpeta}):
            salida = io.StringIO()
            call_command(
                "exportar_dataset",
                "--usuario",
                "admin_ml",
                "--origen-datos",
                "demostracion",
                *argumentos,
                stdout=salida,
            )
        return salida.getvalue()

    def test_346_permisos_ruta_y_ensayo_sin_cambios(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"ML_EXPORT_DIR": carpeta}):
                # Argumentos obligatorios
                with self.assertRaises(CommandError) as ctx:
                    call_command("exportar_dataset")
                self.assertIn("Faltan", str(ctx.exception))

                # Usuario inexistente
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "exportar_dataset",
                        "--usuario",
                        "fantasma",
                        "--origen-datos",
                        "real",
                    )
                self.assertIn("No existe", str(ctx.exception))

                # Sin el permiso ml.entrenar (solo lo tiene Administrador)
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "exportar_dataset",
                        "--usuario",
                        "coord_ml",
                        "--origen-datos",
                        "real",
                    )
                self.assertIn("ml.entrenar", str(ctx.exception))

                # Cuenta inactiva
                inactivo = Usuario.objects.create_user(
                    username="inactivo_ml",
                    password="InactivoMl2026!",
                    rol=Rol.objects.get(nombre="Administrador"),
                    is_active=False,
                )
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "exportar_dataset",
                        "--usuario",
                        inactivo.username,
                        "--origen-datos",
                        "real",
                    )
                self.assertIn("inactivo", str(ctx.exception))

                # Sin carpeta de destino
                with patch.dict(os.environ, {"ML_EXPORT_DIR": ""}):
                    with self.assertRaises(CommandError) as ctx:
                        call_command(
                            "exportar_dataset",
                            "--usuario",
                            "admin_ml",
                            "--origen-datos",
                            "real",
                        )
                    self.assertIn("ML_EXPORT_DIR", str(ctx.exception))

                # Carpeta DENTRO del repositorio: prohibida
                dentro = Path(__file__).resolve().parent
                with patch.dict(os.environ, {"ML_EXPORT_DIR": str(dentro)}):
                    with self.assertRaises(CommandError) as ctx:
                        call_command(
                            "exportar_dataset",
                            "--usuario",
                            "admin_ml",
                            "--origen-datos",
                            "real",
                        )
                    self.assertIn("FUERA", str(ctx.exception))

                # Ensayo: informa filas y columnas sin escribir ni auditar
                salida = io.StringIO()
                call_command(
                    "exportar_dataset",
                    "--usuario",
                    "admin_ml",
                    "--origen-datos",
                    "demostracion",
                    "--dry-run",
                    stdout=salida,
                )
                texto = salida.getvalue()
                self.assertIn("Dry-run", texto)
                self.assertIn("filas", texto)
                self.assertIn("columnas", texto)
                self.assertEqual(list(Path(carpeta).iterdir()), [])
                self.assertEqual(Auditoria.objects.count(), 0)
                self.assertEqual(
                    list(Path(dentro).glob("dataset_*.csv")), []
                )

    def test_347_ficha_tecnica_con_fecha_lima_y_huella(self):
        with tempfile.TemporaryDirectory() as carpeta:
            self._exportar(carpeta=carpeta)

            csvs = list(Path(carpeta).glob("dataset_*.csv"))
            fichas = list(Path(carpeta).glob("ficha_dataset_*.json"))
            self.assertEqual(len(csvs), 1)
            self.assertEqual(len(fichas), 1)

            contenido = csvs[0].read_bytes()
            ficha = json.loads(fichas[0].read_text(encoding="utf-8"))

            # Filas = las de la vista, columnas = la lista fija en orden
            filas_vista = len(self._filas_vista())
            self.assertEqual(ficha["filas"], filas_vista)
            self.assertEqual(
                ficha["columnas"], list(columnas.COLUMNAS_EXPORTADAS)
            )

            # Huella = SHA-256 de los bytes exactos del archivo
            self.assertEqual(
                ficha["sha256"], hashlib.sha256(contenido).hexdigest()
            )

            # Fecha de Lima (UTC-5), origen declarado y semilla fija
            self.assertTrue(ficha["fecha"].endswith("-05:00"))
            self.assertEqual(ficha["origen_datos"], "demostracion")
            self.assertEqual(ficha["semilla"], exportacion.SEMILLA)

            # El CSV se abre con tildes y ñ, y trae encabezado + filas
            texto = contenido.decode("utf-8-sig")
            lineas = texto.strip().splitlines()
            self.assertEqual(
                lineas[0].split(",")[:3],
                ["campania_id", "parcela_id", "productor_id"],
            )
            self.assertEqual(len(lineas), 1 + filas_vista)

    def test_348_auditoria_sin_contenido_y_no_archivo_si_falla(self):
        with tempfile.TemporaryDirectory() as carpeta:
            self._exportar(carpeta=carpeta)

            # Un solo evento: EXPORTAR del módulo Machine Learning
            evento = Auditoria.objects.get(
                accion="EXPORTAR", modulo="Machine Learning"
            )
            self.assertEqual(evento.usuario, self.admin)
            self.assertIsNone(evento.tabla)

            # Detalle: filas, origen y huella — nada de contenido del
            # dataset (ni cultivo, ni valores, ni identificadores)
            detalle = evento.detalle
            self.assertEqual(
                set(detalle), {"filas", "origen_datos", "sha256"}
            )
            self.assertEqual(
                detalle["filas"], len(self._filas_vista())
            )
            self.assertEqual(detalle["origen_datos"], "demostracion")
            texto = json.dumps(detalle)
            for contenido_en_detalle in (
                "Quinua",
                "96000001",
                "rendimiento",
                "2026-2027",
            ):
                self.assertNotIn(contenido_en_detalle, texto)

        # Si la auditoría FALLA, NO se escribe el archivo
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"ML_EXPORT_DIR": carpeta}):
                with patch(
                    "sistema.management.commands.exportar_dataset."
                    "registrar_evento",
                    side_effect=RuntimeError("sin base"),
                ):
                    with self.assertRaises(CommandError) as ctx:
                        call_command(
                            "exportar_dataset",
                            "--usuario",
                            "admin_ml",
                            "--origen-datos",
                            "demostracion",
                            stdout=io.StringIO(),
                        )
                self.assertIn("auditoría", str(ctx.exception))
                self.assertEqual(list(Path(carpeta).iterdir()), [])


# ---------------------------------------------------------------------- #
# Fase 4: limpieza con tabla de exclusiones e imputación sin fuga (356-359)
# ---------------------------------------------------------------------- #
class LimpiezaTests(TestCase):
    """Pruebas 356-357: la tabla de exclusiones está completa, excluye
    lo que debe y su resumen solo lleva conteos."""

    def test_356_tabla_de_exclusiones_completa_y_efectiva(self):
        casos = {
            "Sin identificadores": (
                {
                    "campania_id": None,
                    "parcela_id": None,
                    "productor_id": None,
                },
                {"campania_id": 1, "parcela_id": 2, "productor_id": 3},
            ),
            "Superficie sin sentido": (
                {"superficie_sembrada_ha": 0},
                {"superficie_sembrada_ha": 1.5},
            ),
            "Altitud fuera de rango": (
                {"altitud_msnm": -50},
                {"altitud_msnm": 3900},
            ),
            "Sin objetivo": (
                {"rendimiento_kg_ha": 0.0},
                {"rendimiento_kg_ha": 200.0},
            ),
        }
        motivos = []
        for regla in limpieza.EXCLUSIONES:
            # La tabla está completa: motivo, condición, columnas y máscara
            self.assertTrue(regla["motivo"].strip())
            self.assertTrue(regla["condicion"].strip())
            self.assertTrue(regla["columnas"])
            self.assertTrue(callable(regla["mascara"]))

            motivo = regla["motivo"]
            motivos.append(motivo)
            self.assertIn(motivo, casos)
            mala, buena = casos[motivo]

            # La fila que incumple ESA regla se excluye con SU motivo
            limpio, resumen = limpieza.limpiar(pd.DataFrame([mala]))
            self.assertEqual(len(limpio), 0)
            self.assertEqual(resumen["por_motivo"], {motivo: 1})

            # La fila conforme a esa regla sobrevive
            limpio, resumen = limpieza.limpiar(pd.DataFrame([buena]))
            self.assertEqual(len(limpio), 1)
            self.assertEqual(resumen["por_motivo"], {})

        # Motivos únicos: cada exclusión tiene su etiqueta propia
        self.assertEqual(len(set(motivos)), len(motivos))

        # Una altitud imposible por ARRIBA también se excluye
        _, resumen = limpieza.limpiar(pd.DataFrame([{"altitud_msnm": 7000}]))
        self.assertEqual(
            resumen["por_motivo"], {"Altitud fuera de rango": 1}
        )

    def test_357_resumen_cuadra_y_no_llevar_contenido(self):
        base = {
            "campania_id": 1,
            "parcela_id": 2,
            "productor_id": 3,
            "superficie_sembrada_ha": 1.5,
            "altitud_msnm": 3900,
            "rendimiento_kg_ha": 200.0,
            "cultivo": "Quinua",
        }
        filas = [
            dict(base),
            {**base, "parcela_id": 4},
            # Doble falta: gana la primera regla de la tabla (superficie)
            {**base, "superficie_sembrada_ha": 0, "rendimiento_kg_ha": 0},
            {**base, "altitud_msnm": -50},
            {**base, "rendimiento_kg_ha": float("nan")},
            {**base, "campania_id": None},
        ]
        limpio, resumen = limpieza.limpiar(pd.DataFrame(filas))

        # Cuadra: entrada = salida + excluidas, y motivos = excluidas
        self.assertEqual(resumen["filas_entrada"], 6)
        self.assertEqual(resumen["filas_salida"], 2)
        self.assertEqual(resumen["filas_excluidas"], 4)
        self.assertEqual(
            resumen["por_motivo"],
            {
                "Sin identificadores": 1,
                "Superficie sin sentido": 1,
                "Altitud fuera de rango": 1,
                "Sin objetivo": 1,
            },
        )
        self.assertEqual(
            sum(resumen["por_motivo"].values()),
            resumen["filas_excluidas"],
        )

        # Solo conteos: nada del contenido de las filas sale en el resumen
        texto = json.dumps(resumen, ensure_ascii=False)
        self.assertNotIn("Quinua", texto)
        for valor in resumen["por_motivo"].values():
            self.assertIsInstance(valor, int)

        # Y lo que sobrevive son exactamente las dos filas válidas
        self.assertEqual(len(limpio), 2)
        self.assertTrue((limpio["rendimiento_kg_ha"] == 200.0).all())


class PreparacionTests(TestCase):
    """Pruebas 358-359: imputación y transformaciones dentro del
    pipeline, con la mediana aprendida solo en el entrenamiento."""

    def _datos(self, *sobrescrituras):
        filas = []
        for extra in sobrescrituras:
            fila = fila_valida()
            fila.update(extra)
            filas.append(fila)
        return pd.DataFrame(filas)

    def test_358_imputacion_con_mediana_del_entrenamiento_sin_fuga(self):
        datos = self._datos(
            {"altitud_msnm": 3900},
            {"altitud_msnm": 4000},
            {"altitud_msnm": 4100},
            {"altitud_msnm": None},
            {"altitud_msnm": 5000},
        )
        X, y, pipeline, fuera = preparacion.preparar(
            datos, catalogo.CONJUNTO_PLAN
        )

        # Sin descartes (1 vacío de 5 = 20 % < umbral del 40 %)
        self.assertEqual(fuera, {})
        # El objetivo se separa: se predice, no se imputa ni se usa
        self.assertNotIn("rendimiento_kg_ha", X.columns)
        self.assertEqual(
            list(X.columns),
            list(catalogo.columnas_conjunto(catalogo.CONJUNTO_PLAN)),
        )
        self.assertEqual(y.name, "rendimiento_kg_ha")

        # Ajuste SOLO con las tres primeras filas (mediana y media 4000)
        X_train, X_test = X.iloc[:3], X.iloc[3:]
        pipeline.fit(X_train)
        numericas, _ = preparacion.columnas_del_pipeline(list(X.columns))
        pos = numericas.index("altitud_msnm")
        pasos = pipeline.named_transformers_["numerico"].named_steps
        self.assertEqual(float(pasos["imputar"].statistics_[pos]), 4000.0)
        self.assertEqual(float(pasos["escalar"].mean_[pos]), 4000.0)

        # El vacío de prueba se rellena con la mediana del ENTRENAMIENTO
        # (si hubiera fuga, la mediana conjunta daría 4050)
        salida = pipeline.transform(X_test)
        self.assertFalse(bool(pd.isna(salida).any()))
        self.assertEqual(float(salida[0, pos]), 0.0)

    def test_359_categoria_desconocida_ignorada_y_objetivo_fuera(self):
        datos = self._datos(
            {"cultivo": "Quinua", "altitud_msnm": 3900},
            {"cultivo": "Arroz", "altitud_msnm": 4000},
            {"cultivo": "Quinua", "altitud_msnm": 4100},
            {"cultivo": "Maiz", "altitud_msnm": 4200},
        )
        X, y, pipeline, fuera = preparacion.preparar(datos)
        X_train, X_test = X.iloc[:3], X.iloc[3:]
        pipeline.fit(X_train)
        nombres = [str(n) for n in pipeline.get_feature_names_out()]

        # El objetivo y los identificadores no se codifican
        self.assertNotIn("rendimiento_kg_ha", nombres)
        for identificador in ("campania_id", "parcela_id", "productor_id"):
            self.assertNotIn(identificador, nombres)

        # One-hot con las categorías vistas en ENTRENAMIENTO
        self.assertIn("cultivo_Quinua", nombres)
        self.assertIn("cultivo_Arroz", nombres)
        self.assertNotIn("cultivo_Maiz", nombres)

        salida = pipeline.transform(X_test)
        self.assertFalse(bool(pd.isna(salida).any()))
        cultivo = [
            i for i, n in enumerate(nombres) if n.startswith("cultivo_")
        ]
        # «Maiz» es desconocida: sus columnas quedan en 0, no se inventa
        self.assertEqual(float(salida[0, cultivo].sum()), 0.0)

        # El escalado aprendió solo del entrenamiento: su media es 0
        salida_train = pipeline.transform(X_train)
        i_altitud = nombres.index("altitud_msnm")
        self.assertAlmostEqual(
            float(salida_train[:, i_altitud].mean()), 0.0, places=9
        )


# ---------------------------------------------------------------------- #
# Fase 5: validación agrupada y línea base (360-362)
# ---------------------------------------------------------------------- #
class ValidacionTests(TestCase):
    """Pruebas 360-361: ningún productor se reparte entre entrenamiento
    y prueba, y la semilla fija hace el corte reproducible."""

    def _datos(self, n=12, n_productores=3):
        filas = []
        for i in range(n):
            fila = fila_valida()
            fila["productor_id"] = 100 + (i % n_productores)
            fila["rendimiento_kg_ha"] = 100.0 + i
            filas.append(fila)
        return pd.DataFrame(filas)

    def test_360_sin_productor_compartido_y_prueba_de_todos_una_vez(self):
        datos = self._datos()
        pliegues = validacion.particiones(datos, n_pliegues=3)
        self.assertEqual(len(pliegues), 3)

        pasadas_por_prueba = []
        for entrenamiento, prueba in pliegues:
            # Un productor entero en UN solo lado del corte
            grupos_train = set(datos["productor_id"].iloc[entrenamiento])
            grupos_test = set(datos["productor_id"].iloc[prueba])
            self.assertTrue(grupos_train)
            self.assertTrue(grupos_test)
            self.assertEqual(grupos_train & grupos_test, set())

            # Índices posicionales, disjuntos y dentro del rango
            self.assertEqual(
                sorted(set(entrenamiento) & set(prueba)), []
            )
            pasadas_por_prueba.extend(int(i) for i in prueba)

        # Cada fila pasa por prueba exactamente una vez
        self.assertEqual(
            sorted(pasadas_por_prueba), list(range(len(datos)))
        )

    def test_361_misma_semilla_mismo_corte_y_grupos_suficientes(self):
        datos = self._datos()
        uno = validacion.particiones(datos, n_pliegues=3)
        dos = validacion.particiones(datos, n_pliegues=3)

        # Misma semilla → el mismo corte, fila por fila (reproducible)
        for (train_a, test_a), (train_b, test_b) in zip(uno, dos):
            self.assertTrue((train_a == train_b).all())
            self.assertTrue((test_a == test_b).all())

        # Ningún pliegue de prueba queda vacío
        self.assertTrue(all(len(prueba) > 0 for _, prueba in uno))

        # Pediendo más pliegues que productores, avisa en vez de fallar
        with self.assertRaises(ValueError) as ctx:
            validacion.particiones(datos, n_pliegues=10)
        self.assertIn("productores", str(ctx.exception))

        # Sin productor en los datos tampoco se presta a confusión
        sin_grupo = datos.drop(columns=["productor_id"])
        with self.assertRaises(ValueError) as ctx:
            validacion.particiones(sin_grupo, n_pliegues=3)
        self.assertIn("productor_id", str(ctx.exception))


class LineaBaseTests(TestCase):
    """Prueba 362: la línea base predice la media del ENTRENAMIENTO y
    se evalúa en la escala del objetivo (kg/ha)."""

    def _datos(self):
        filas = []
        for productor, rendimientos in (
            (100, (100.0, 200.0)),
            (101, (300.0, 400.0)),
        ):
            for rendimiento in rendimientos:
                fila = fila_valida()
                fila["productor_id"] = productor
                fila["rendimiento_kg_ha"] = rendimiento
                filas.append(fila)
        return pd.DataFrame(filas)

    def test_362_linea_base_predice_la_media_del_entrenamiento(self):
        # La media del entrenamiento es la predicción, sin trampa
        self.assertEqual(
            linea_base.predecir_media([100.0, 200.0, 300.0]), 200.0
        )
        # Una constante en entrenamiento se predice tal cual, y el
        # error frente a lo que sea en prueba sale de evaluar()
        constante = linea_base.predecir_media([250.0, 250.0, 250.0])
        self.assertEqual(constante, 250.0)
        metricas = linea_base.evaluar([0.0, 999.0], [constante, constante])
        self.assertEqual(metricas["mae"], 499.5)
        self.assertEqual(metricas["filas"], 2)

        # Errores conocidos: mae = rmse = 100 para [100, 300] vs 200
        conocidas = linea_base.evaluar([100.0, 300.0], [200.0, 200.0])
        self.assertEqual(conocidas["mae"], 100.0)
        self.assertEqual(conocidas["rmse"], 100.0)

        # Sin objetivo que predecir, el error es claro
        with self.assertRaises(ValueError):
            linea_base.predecir_media([])

        # Por cada pliegue agrupado: la media SOLO del entrenamiento
        # de ese pliegue (la prueba no decide la predicción)
        datos = self._datos()
        pliegues = validacion.particiones(datos, n_pliegues=2)
        objetivos = datos["rendimiento_kg_ha"]
        vistos = 0
        for entrenamiento, prueba in pliegues:
            y_train = objetivos.iloc[entrenamiento]
            y_test = objetivos.iloc[prueba]
            predicho = linea_base.predecir_media(y_train)
            self.assertEqual(predicho, statistics.mean(y_train))
            metricas = linea_base.evaluar(
                y_test, [predicho] * len(y_test)
            )
            self.assertEqual(metricas["filas"], len(prueba))
            vistos += len(prueba)
        self.assertEqual(vistos, len(datos))
