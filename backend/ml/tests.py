"""Pruebas de Machine Learning: Semana 21 (346-365) y Semana 22 (366-392).

Numeración Semana 21: 346-365 (20 pruebas → 365 en total; el
repositorio cerró la Semana 20 en 345). Cubren la exportación del
dataset (permisos, ficha técnica, auditoría, ruta y columnas), la vista
con identificadores, el catálogo de variables y su control de fuga, la
carga del archivo, la limpieza con su tabla de exclusiones, la
imputación y transformaciones dentro del pipeline, la validación
agrupada y la línea base, y la higiene final (notebooks sin salidas,
32 tablas de dominio y 25 triggers: 29 al cerrar la S21, más las 3 de
ML que añade la S22).

Numeración Semana 22: 366-392 (27 pruebas → 392 en total; base real
365). Cubren criterio de selección, entrenamiento reproducible,
serialización con manifiesto de huellas, registro/activación de
modelos, servicio de predicción, API, comparación con lo real,
permisos, migraciones (32 tablas / 25 triggers), recorrido completo y
higiene de la entrega.

Los datos de estas pruebas son de demostración: ninguna cifra que salga
de aquí se presenta como resultado de la tesis.
"""
import hashlib
import io
import json
import os
import statistics
import subprocess
import sys
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase
from django.utils import timezone

from rest_framework.throttling import ScopedRateThrottle

from auditoria.models import Auditoria
from campanias.models import Campania
from catalogos.models import Cultivo, Recurso, Unidad, Variedad
from productores.models import (
    AsignacionTecnico,
    Comunidad,
    Distrito,
    Parcela,
    Productor,
    Provincia,
)
from seguimiento.models import UsoRecurso
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from ml import (
    catalogo,
    columnas,
    criterio,
    entrenamiento,
    exportacion,
    guardado,
    linea_base,
    limpieza,
    preparacion,
    registro,
    servicio,
    validacion,
)
from ml.carga import ErrorCarga, cargar
from ml.models import EntrenamientoML, ModeloML, Prediccion
from ml.registro import ErrorRegistro
from ml.servicio import ErrorModelo, ErrorSinModelo, ErrorVariables

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


# ---------------------------------------------------------------------- #
# Fase 6: higiene final — esquema intacto y notebooks sin salidas (363-365)
# ---------------------------------------------------------------------- #
class HigieneTests(TestCase):
    """Pruebas 363-365: la Semana 21 no mueve el esquema (29 tablas de
    dominio entonces; 32 con las 3 de ML de la S22, 25 triggers) y los
    notebooks se versionan limpios."""

    def test_363_las_migraciones_siguen_creando_32_tablas_de_dominio(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM information_schema.tables"
                " WHERE table_schema = 'public'"
                " AND table_type = 'BASE TABLE'"
                " AND table_name NOT LIKE 'auth\\_%'"
                " AND table_name NOT LIKE 'django\\_%'"
                " AND table_name NOT LIKE 'token\\_%'"
            )
            tablas = cursor.fetchone()[0]
        self.assertEqual(
            tablas,
            32,
            "las migraciones deben seguir creando 32 tablas de dominio "
            "(29 de la S21 + 3 de ML de la S22)",
        )

    def test_364_las_migraciones_siguen_creando_25_triggers(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"
            )
            triggers = cursor.fetchone()[0]
        self.assertEqual(
            triggers,
            25,
            "las migraciones deben seguir creando 25 triggers",
        )

    def test_365_notebooks_versionados_sin_salidas(self):
        raiz = Path(__file__).resolve().parents[2]
        carpeta = raiz / "notebooks"
        gitignore = (raiz / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".ipynb_checkpoints", gitignore)

        for nombre in ("01_exploracion.ipynb", "02_preparacion.ipynb"):
            ruta = carpeta / nombre
            self.assertTrue(ruta.exists(), f"Falta el cuaderno {ruta}")
            cuaderno = json.loads(ruta.read_text(encoding="utf-8"))
            self.assertEqual(cuaderno["nbformat"], 4)

            partes = []
            for celda in cuaderno["cells"]:
                partes.append("".join(celda.get("source", [])))
                if celda["cell_type"] == "code":
                    self.assertEqual(
                        celda.get("outputs"), [],
                        f"{nombre}: celda con salidas guardadas",
                    )
                    self.assertIsNone(
                        celda.get("execution_count"),
                        f"{nombre}: celda con contador de ejecución",
                    )
            texto = "\n".join(partes)

            # Marca visible de datos de demostración
            self.assertIn("demostración", texto.lower())
            # Los datos salen de ML_EXPORT_DIR, nunca de una ruta del repo
            self.assertIn("ML_EXPORT_DIR", texto)
            self.assertNotIn("read_csv(", texto)


# ---------------------------------------------------------------------- #
# Semana 22 — Fase 1: criterio, entrenamiento y modelo guardado (366-368)
# ---------------------------------------------------------------------- #
def datos_sinteticos(n=36, grupos=7):
    """DataFrame inventado con productores agrupables (fila_valida)."""
    filas = []
    for i in range(n):
        filas.append(
            fila_valida(
                campania_id=i + 1,
                parcela_id=i + 1,
                productor_id=(i % grupos) + 1,
                cultivo="Quinua" if i % 3 else "Canihua",
                semilla_kg_ha=30 + (i % 7) * 5,
                fertilizante_kg_ha=80 + (i % 5) * 20,
                jornales_ha=20 + (i % 4) * 6,
                agua_m3_ha=150 + (i % 6) * 25,
                altitud_msnm=3600 + (i % 9) * 50,
                rendimiento_kg_ha=180 + (i % 11) * 22,
            )
        )
    return pd.DataFrame(filas)


class Bloque1Tests(TestCase):
    """Pruebas 366-368: el entrenamiento es reproducible, el criterio
    se aplica como está escrito y el modelo guardado se carga en un
    proceso limpio con su huella verificada."""

    def test_366_el_entrenamiento_es_reproducible_con_la_misma_semilla(self):
        datos = datos_sinteticos()
        plan = {
            "nombre": "prueba",
            "pliegues": 3,
            "repeticiones": 1,
            "holdout": None,
        }
        una = entrenamiento.evaluar(datos, estrategia=plan)
        dos = entrenamiento.evaluar(datos, estrategia=plan)
        for nombre in entrenamiento.NOMBRES:
            self.assertEqual(
                una["candidatos"][nombre]["rmse_pliegues"],
                dos["candidatos"][nombre]["rmse_pliegues"],
                f"{nombre}: la misma semilla debe dar el mismo RMSE por "
                "pliegue",
            )
            self.assertAlmostEqual(
                una["candidatos"][nombre]["rmse"],
                dos["candidatos"][nombre]["rmse"],
                places=8,
            )
        # Estrategia fijada de antemano según el tramo de datos
        self.assertEqual(
            entrenamiento.estrategia_de(13)["nombre"], "cv_agrupada"
        )
        self.assertEqual(
            entrenamiento.estrategia_de(40)["nombre"], "cv_repetida"
        )
        self.assertEqual(
            entrenamiento.estrategia_de(120)["nombre"],
            "holdout_final_20",
        )
        # Los tres candidatos y la línea base comparten los mismos cortes
        cortes = len(
            una["candidatos"]["RANDOM_FOREST"]["rmse_pliegues"]
        )
        self.assertEqual(
            cortes, len(una["linea_base"]["rmse_pliegues"])
        )
        self.assertEqual(cortes, 3)
        self.assertIn("por_cultivo", una["candidatos"]["REGRESION_LINEAL"])
        self.assertIn("Canihua", una["candidatos"]["REGRESION_LINEAL"]["por_cultivo"])

    def test_367_el_criterio_se_aplica_como_esta_escrito(self):
        # (a) gana el MENOR RMSE cuando la diferencia supera el desvío
        resuelto = criterio.elegir(
            {
                "REGRESION_LINEAL": {"rmse": 140.0, "desvio": 0.0},
                "RANDOM_FOREST": {"rmse": 90.0, "desvio": 5.0},
                "GRADIENT_BOOSTING": {"rmse": 95.0, "desvio": 0.0},
                criterio.LINEA_BASE: {"rmse": 120.0},
            }
        )
        self.assertEqual(resuelto["elegido"], "RANDOM_FOREST")
        self.assertIn("menor RMSE", resuelto["motivo"])

        # (b) un desvío de más de 15 «repara» al lineal por simplicidad
        desvio = criterio.elegir(
            {
                "REGRESION_LINEAL": {"rmse": 115.0},
                "RANDOM_FOREST": {"rmse": 100.0, "desvio": 20.0},
                "GRADIENT_BOOSTING": {"rmse": 130.0, "desvio": 0.0},
                criterio.LINEA_BASE: {"rmse": 125.0},
            }
        )
        self.assertEqual(desvio["elegido"], "REGRESION_LINEAL")
        self.assertEqual(desvio["sigma"], 20.0)
        self.assertIn("simplicidad", desvio["motivo"])

        # (c) dentro del desvío, gana el más simple (RF antes que GB)
        orden = criterio.elegir(
            {
                "REGRESION_LINEAL": {"rmse": 130.0, "desvio": 0.0},
                "RANDOM_FOREST": {"rmse": 100.0, "desvio": 20.0},
                "GRADIENT_BOOSTING": {"rmse": 99.0, "desvio": 10.0},
                criterio.LINEA_BASE: {"rmse": 150.0},
            }
        )
        self.assertEqual(orden["elegido"], "RANDOM_FOREST")

        # (d) nadie mejora a la línea base → no se elige ninguno
        base = criterio.elegir(
            {
                "REGRESION_LINEAL": {"rmse": 140.0, "desvio": 0.0},
                "RANDOM_FOREST": {"rmse": 100.0, "desvio": 5.0},
                "GRADIENT_BOOSTING": {"rmse": 110.0, "desvio": 0.0},
                criterio.LINEA_BASE: {"rmse": 90.0},
            }
        )
        self.assertIsNone(base["elegido"])
        self.assertIn("línea base", base["motivo"])

        # Faltan candidatos → error claro (nada se elige a ciegas)
        with self.assertRaises(criterio.ErrorCriterio):
            criterio.elegir({"RANDOM_FOREST": {"rmse": 1.0}})

        # El criterio aplicado a una corrida real devuelve su resolución
        corrida = entrenamiento.evaluar(
            datos_sinteticos(),
            estrategia={
                "nombre": "prueba",
                "pliegues": 3,
                "repeticiones": 1,
                "holdout": None,
            },
        )
        resolucion = entrenamiento.aplicar_criterio(corrida)
        self.assertIn("elegido", resolucion)
        self.assertIn("motivo", resolucion)
        if resolucion["elegido"]:
            self.assertIn(resolucion["elegido"], entrenamiento.NOMBRES)

    def test_368_el_modelo_guardado_se_carga_en_proceso_limpio(self):
        datos = datos_sinteticos(n=21, grupos=7)
        tubo, X, _ = entrenamiento.entrenar_completo(
            datos, "RANDOM_FOREST"
        )
        pred_padre = tubo.predict(X)

        with tempfile.TemporaryDirectory() as tmp:
            ruta = guardado.guardar(
                tubo, "RANDOM_FOREST", "t368", destino=tmp
            )
            huella = guardado.registrar_archivo(
                ruta,
                destino=tmp,
                algoritmo="RANDOM_FOREST",
                version="t368",
            )
            self.assertEqual(len(huella), 64)
            self.assertTrue(guardado.verificar(ruta, destino=tmp))

            # Proceso limpio: intérprete nuevo, fuera del ciclo de pruebas
            ruta_entrada = Path(tmp) / "entrada.joblib"
            joblib.dump(X, ruta_entrada)
            codigo = (
                "import sys, joblib\n"
                "tubo = joblib.load(sys.argv[1])\n"
                "X = joblib.load(sys.argv[2])\n"
                "print(','.join('%.12g' % v for v in tubo.predict(X)))\n"
            )
            proceso = subprocess.run(
                [sys.executable, "-c", codigo, str(ruta),
                 str(ruta_entrada)],
                capture_output=True,
                text=True,
                check=True,
            )
            hijo = [float(v) for v in proceso.stdout.strip().split(",")]
            np.testing.assert_allclose(hijo, pred_padre, rtol=1e-9)

            # Archivo alterado → la huella no coincide y NO se carga
            ruta.write_bytes(ruta.read_bytes() + b"\x00")
            self.assertFalse(guardado.verificar(ruta, destino=tmp))
            with self.assertRaises(guardado.ErrorManifiesto):
                guardado.cargar_verificado(ruta, destino=tmp)

            # Un archivo que nunca pasó por el manifiesto tampoco carga
            intruso = Path(tmp) / "intruso.joblib"
            joblib.dump(tubo, intruso)
            with self.assertRaises(guardado.ErrorManifiesto):
                guardado.cargar_verificado(intruso, destino=tmp)


# ---------------------------------------------------------------------- #
# Fase F2b: registro y activación de modelos (369-371)
# ---------------------------------------------------------------------- #
class Bloque2Base(MLBase):
    """Helpers compartidos de F2b y F2c (369-380): métricas de prueba
    válidas para registrar (candidatos, línea base y criterio) y tubos
    .joblib entrenados fuera del destino."""

    def _metricas(self, version, n=48, origen="real",
                  elegido="REGRESION_LINEAL"):
        candidatos = {
            "REGRESION_LINEAL": {
                "mae": 4.5, "rmse": 5.48, "desvio_rmse": 1.24,
                "r2": 0.94, "mape": 1.4,
            },
            "RANDOM_FOREST": {
                "mae": 8.9, "rmse": 11.17, "desvio_rmse": 2.2,
                "r2": 0.78, "mape": 2.8,
            },
            "GRADIENT_BOOSTING": {
                "mae": 7.2, "rmse": 8.78, "desvio_rmse": 1.8,
                "r2": 0.86, "mape": 2.2,
            },
        }
        return {
            "estrategia": {
                "nombre": "cv_repetida", "pliegues": 5, "repeticiones": 5,
                "holdout": None, "semilla": 42, "n_prueba": 0,
                "n_entrenamiento": n,
            },
            "candidatos": candidatos,
            "linea_base": {
                "mae": 20.9, "rmse": 24.47, "desvio_rmse": 3.8,
                "r2": -0.04, "mape": 6.6,
            },
            "fuera": {}, "excluidas": 0,
            "n": n, "version": version, "origen_datos": origen,
            "archivo_dataset": "dataset_prueba.csv",
            "sha256_dataset": "a" * 64,
            "criterio": {
                "elegido": elegido,
                "motivo": f"{elegido} gana con el menor RMSE",
                "sigma": 1.24,
            },
        }

    def _tubo_fuera(self, carpeta, version, algoritmo="REGRESION_LINEAL"):
        tubo, _, _ = entrenamiento.entrenar_completo(
            datos_sinteticos(), algoritmo
        )
        ruta = Path(carpeta) / f"entrenado_{version}.joblib"
        joblib.dump(tubo, ruta)
        return ruta


class Bloque2bTests(Bloque2Base):
    """Pruebas 369-371: registrar_modelo da de alta 1 entrenamiento y 3
    modelos con sus protecciones (30 campañas, demostración con bandera,
    versión única, permisos), y la activación garantiza un solo modelo
    activo con archivo, huella y predicción de prueba (decisiones
    220-222)."""

    # ------------------------------------------------------------------ #
    def test_369_registrar_modelo_crea_un_entrenamiento_y_tres_modelos(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "ml_models"
            ruta = self._tubo_fuera(tmp, "t369")
            resumen = registro.registrar(
                usuario=self.admin,
                resultados=self._metricas(version="t369"),
                version="t369",
                archivo=ruta,
                destino=destino,
            )

            entrenamiento_ml = resumen["entrenamiento"]
            self.assertEqual(entrenamiento_ml.n_registros, 48)
            self.assertEqual(entrenamiento_ml.n_entrenamiento, 48)
            self.assertEqual(entrenamiento_ml.n_prueba, 0)
            self.assertEqual(entrenamiento_ml.ejecutado_por, self.admin)
            self.assertEqual(
                entrenamiento_ml.observaciones,
                "REGRESION_LINEAL gana con el menor RMSE",
            )
            usadas = entrenamiento_ml.variables_usadas
            self.assertEqual(
                set(usadas),
                {"variables", "conjunto", "origen_datos",
                 "sha256_dataset", "semilla", "estrategia"},
                "variables_usadas guarda lo de la decisión 223",
            )
            self.assertEqual(usadas["conjunto"], "plan")
            self.assertEqual(usadas["semilla"], 42)
            self.assertEqual(usadas["origen_datos"], "real")
            self.assertIn("semilla_kg_ha", usadas["variables"])
            self.assertIn("cultivo", usadas["variables"])

            modelos = list(ModeloML.objects.order_by("algoritmo"))
            self.assertEqual(len(modelos), 3, "los tres algoritmos")
            self.assertFalse(
                any(m.activo for m in modelos),
                "sin --activar no queda nada activo",
            )
            elegido = ModeloML.objects.get(algoritmo="REGRESION_LINEAL")
            self.assertEqual(elegido.version, "t369")
            self.assertEqual(elegido.mae, Decimal("4.50"))
            self.assertEqual(elegido.rmse, Decimal("5.48"))
            self.assertEqual(elegido.r2, Decimal("0.9400"))
            self.assertEqual(
                elegido.archivo, "regresion_lineal_vt369.joblib"
            )
            otros = [m for m in modelos if m.algoritmo != "REGRESION_LINEAL"]
            self.assertTrue(all(m.archivo is None for m in otros))

            rf = ModeloML.objects.get(algoritmo="RANDOM_FOREST")
            hiper = rf.hiperparametros
            self.assertEqual(
                set(hiper), {"hiperparametros", "linea_base", "validacion"}
            )
            self.assertEqual(hiper["hiperparametros"]["n_estimators"], 300)
            self.assertEqual(hiper["linea_base"]["rmse"], 24.47)
            self.assertIn("desvio_rmse", hiper["validacion"])

            # El archivo vino de fuera: se copia y su huella entra al
            # manifiesto (decisión 220)
            final = destino / "regresion_lineal_vt369.joblib"
            self.assertTrue(final.exists())
            self.assertTrue(guardado.verificar(final, destino=destino))

            # Auditoría CREAR, sin variables de entrada (234)
            evento = Auditoria.objects.get(
                accion="CREAR", modulo="Machine Learning"
            )
            self.assertEqual(evento.usuario, self.admin)
            self.assertEqual(evento.detalle["version"], "t369")
            self.assertEqual(evento.detalle["algoritmo"], "REGRESION_LINEAL")
            self.assertEqual(evento.detalle["n_registros"], 48)
            self.assertNotIn("variables", evento.detalle)

    # ------------------------------------------------------------------ #
    def test_370_el_registro_rechaza_lo_que_el_diseno_no_permite(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "ml_models"
            ruta = self._tubo_fuera(tmp, "t370")

            # a) menos de 30 campañas → rechazado (221)
            with self.assertRaisesMessage(ErrorRegistro, "30"):
                registro.registrar(
                    usuario=self.admin,
                    resultados=self._metricas(version="t370", n=13),
                    version="t370",
                    archivo=ruta,
                    destino=destino,
                )
            self.assertFalse(ModeloML.objects.exists())

            # b) demostración sin la bandera → rechazado; con ella, aceptado
            with self.assertRaisesMessage(ErrorRegistro, "--desarrollo"):
                registro.registrar(
                    usuario=self.admin,
                    resultados=self._metricas(
                        version="t370", origen="demostración"
                    ),
                    version="t370",
                    archivo=ruta,
                    destino=destino,
                )
            resumen = registro.registrar(
                usuario=self.admin,
                resultados=self._metricas(
                    version="t370", origen="demostración"
                ),
                version="t370",
                archivo=ruta,
                destino=destino,
                desarrollo=True,
            )
            self.assertEqual(resumen["origen"], "demostración")
            self.assertEqual(ModeloML.objects.filter(version="t370").count(), 3)

            # c) versión repetida → rechazado (221)
            with self.assertRaisesMessage(ErrorRegistro, "ya está registrada"):
                registro.registrar(
                    usuario=self.admin,
                    resultados=self._metricas(version="t370"),
                    version="t370",
                    archivo=ruta,
                    destino=destino,
                )

            # d) sin el permiso ml.entrenar → rechazado (Coordinador)
            with self.assertRaisesMessage(ErrorRegistro, "ml.entrenar"):
                registro.registrar(
                    usuario=self.coordinador,
                    resultados=self._metricas(version="t370d"),
                    version="t370d",
                    archivo=ruta,
                    destino=destino,
                )

            # e) usuario inactivo → rechazado
            self.admin.is_active = False
            self.admin.save()
            with self.assertRaisesMessage(ErrorRegistro, "activo"):
                registro.registrar(
                    usuario=self.admin,
                    resultados=self._metricas(version="t370e"),
                    version="t370e",
                    archivo=ruta,
                    destino=destino,
                )
            self.admin.is_active = True
            self.admin.save()

            # f) criterio sin elegido (nada gana a la línea base) → nada
            metricas = self._metricas(version="t370f", elegido=None)
            with self.assertRaisesMessage(ErrorRegistro, "criterio"):
                registro.registrar(
                    usuario=self.admin,
                    resultados=metricas,
                    version="t370f",
                    archivo=ruta,
                    destino=destino,
                )

            # g) archivo inexistente → rechazado
            with self.assertRaisesMessage(ErrorRegistro, "No existe"):
                registro.registrar(
                    usuario=self.admin,
                    resultados=self._metricas(version="t370g"),
                    version="t370g",
                    archivo=Path(tmp) / "no_existe.joblib",
                    destino=destino,
                )

            # h) --dry-run del comando: valida y NO escribe (220)
            ruta_metricas = Path(tmp) / "metricas_t370h.json"
            ruta_metricas.write_text(
                json.dumps(self._metricas(version="t370h")),
                encoding="utf-8",
            )
            antes = ModeloML.objects.count()
            salida = io.StringIO()
            call_command(
                "registrar_modelo",
                "--usuario", "admin_ml",
                "--metricas", str(ruta_metricas),
                "--archivo", str(ruta),
                "--version-modelo", "t370h",
                "--dry-run",
                stdout=salida,
            )
            self.assertEqual(ModeloML.objects.count(), antes)
            self.assertIn("Dry-run", salida.getvalue())
            self.assertIn("Sin cambios", salida.getvalue())

    # ------------------------------------------------------------------ #
    def test_371_la_activacion_garantiza_un_solo_modelo_activo(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "ml_models"
            ruta_a = self._tubo_fuera(tmp, "t371a")
            resumen_a = registro.registrar(
                usuario=self.admin,
                resultados=self._metricas(version="t371a"),
                version="t371a",
                archivo=ruta_a,
                destino=destino,
            )
            elegido_a = resumen_a["activado"] or next(
                m for m in resumen_a["modelos"]
                if m.algoritmo == resumen_a["elegido"]
            )

            # a) sin permiso ml.activar_modelo → rechazado (Coordinador)
            with self.assertRaisesMessage(ErrorRegistro, "ml.activar_modelo"):
                registro.activar_modelo(elegido_a, self.coordinador,
                                        destino=destino)

            # b) modelo sin archivo (los no elegidos) → rechazado
            sin_archivo = ModeloML.objects.get(
                version="t371a", algoritmo="RANDOM_FOREST"
            )
            with self.assertRaisesMessage(ErrorRegistro, "no tiene archivo"):
                registro.activar_modelo(sin_archivo, self.admin,
                                        destino=destino)

            # c) activación correcta: queda activo y deja evento ACTIVAR
            registro.activar_modelo(elegido_a, self.admin, destino=destino)
            self.assertTrue(
                ModeloML.objects.get(pk=elegido_a.pk).activo
            )
            self.assertEqual(
                ModeloML.objects.filter(activo=True).count(), 1
            )
            self.assertTrue(
                Auditoria.objects.filter(
                    accion="ACTIVAR", modulo="Machine Learning"
                ).exists()
            )

            # d) un segundo modelo activo DESACTIVA al anterior (222)
            ruta_b = self._tubo_fuera(tmp, "t371b")
            resumen_b = registro.registrar(
                usuario=self.admin,
                resultados=self._metricas(version="t371b"),
                version="t371b",
                archivo=ruta_b,
                destino=destino,
            )
            elegido_b = next(
                m for m in resumen_b["modelos"]
                if m.algoritmo == resumen_b["elegido"]
            )
            registro.activar_modelo(elegido_b, self.admin, destino=destino)
            self.assertTrue(ModeloML.objects.get(pk=elegido_b.pk).activo)
            self.assertFalse(ModeloML.objects.get(pk=elegido_a.pk).activo)
            self.assertEqual(ModeloML.objects.filter(activo=True).count(), 1)
            self.assertTrue(
                Auditoria.objects.filter(
                    accion="DESACTIVAR", modulo="Machine Learning"
                ).exists()
            )

            # e) archivo alterado → la huella no coincide y NO se activa
            final_b = destino / elegido_b.archivo
            original = final_b.read_bytes()
            final_b.write_bytes(original + b"\x00")
            with self.assertRaisesMessage(ErrorRegistro, "huella"):
                registro.activar_modelo(elegido_b, self.admin,
                                        destino=destino)
            self.assertTrue(
                ModeloML.objects.get(pk=elegido_b.pk).activo,
                "el intento fallido no cambia el modelo activo",
            )
            final_b.write_bytes(original)

            # f) un archivo que carga pero no es el pipeline → la
            #    predicción de prueba falla y NO se activa
            import pickle

            final_b.write_bytes(pickle.dumps({"no": "es un tubo"}))
            guardado.registrar_archivo(
                final_b, destino=destino,
                algoritmo=elegido_b.algoritmo, version=elegido_b.version,
            )
            with self.assertRaisesMessage(ErrorRegistro, "pipeline"):
                registro.activar_modelo(elegido_b, self.admin,
                                        destino=destino)
            self.assertEqual(ModeloML.objects.filter(activo=True).count(), 1)


# ---------------------------------------------------------------------- #
# Fase F2c: servicio de predicción (372-380)
# ---------------------------------------------------------------------- #
class Bloque2cTests(Bloque2Base):
    """Pruebas 372-380: el servicio usa las variables de la vista (225),
    carga el modelo activo con su huella y lo recarga si cambia (226),
    solo predice en estados elegibles y guarda lo enviado (227, 238),
    los valores planificados tienen prioridad y guardan su origen (228),
    los avisos declaran faltantes, categorías nuevas y fuera de rango con
    la confiabilidad (229), el resultado es kg/ha + producción estimada
    sin intervalo y un negativo va a cero con marca (230), la respuesta
    lleva la marca de demostración con el texto y el MAE (231) y el
    comparativo con lo real se completa al cosechar y se limpia al
    deshacer (236, 237)."""

    def setUp(self):
        super().setUp()
        self._carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self._carpeta.cleanup)
        self.destino = Path(self._carpeta.name) / "ml_models"
        self.addCleanup(servicio.limpiar_cache)
        servicio.limpiar_cache()
        self.blanca, _ = Variedad.objects.get_or_create(
            cultivo=Cultivo.objects.get(nombre="Quinua"), nombre="Blanca"
        )
        self._n = 0

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _activo(self, version, datos=None, origen="demostración"):
        """Registra y activa un modelo con un tubo entrenado aquí."""
        tubo, _, _ = entrenamiento.entrenar_completo(
            datos if datos is not None else datos_sinteticos(),
            "REGRESION_LINEAL",
        )
        ruta = Path(self._carpeta.name) / f"entrenado_{version}.joblib"
        joblib.dump(tubo, ruta)
        resumen = registro.registrar(
            usuario=self.admin,
            resultados=self._metricas(version=version, origen=origen),
            version=version,
            archivo=ruta,
            destino=self.destino,
            desarrollo=True,
            activar=True,
        )
        servicio.limpiar_cache()
        return resumen

    def _camp(self, **extra):
        """Campaña EN_PRODUCCION con cultivo/variedad vistos en el tubo."""
        self._n += 1
        productor = self._productor(
            dni=f"960001{self._n:02d}", nombre=f"P{self._n}"
        )
        parcela = self._parcela(productor)
        datos = {"cultivo": self.blanca.cultivo, "variedad": self.blanca}
        datos.update(extra)
        return self._campania(parcela, **datos)

    def _usos(self, campania, **totales):
        recursos = {
            "semilla": ("Semilla (total histórico)", "Kilogramo"),
            "fertilizante": ("Fertilizante (total histórico)", "Kilogramo"),
            "jornales": ("Mano de obra (total histórico)", "Jornal"),
            "agua": ("Agua (total histórico)", "Metro cúbico"),
        }
        for clave, valor in totales.items():
            if valor is None:
                continue
            nombre, unidad = recursos[clave]
            UsoRecurso.objects.create(
                campania=campania,
                recurso=Recurso.objects.get(nombre=nombre),
                fecha=campania.fecha_inicio + timedelta(days=5),
                cantidad=Decimal(str(valor)),
                unidad=Unidad.objects.get(nombre=unidad),
                cantidad_base=Decimal("0"),
                registrado_por=self.admin,
            )

    # ------------------------------------------------------------------ #
    def test_372_las_variables_del_servicio_coinciden_con_la_fila_de_la_vista(self):
        campania = self._camp()
        self._usos(campania, semilla="67.5", fertilizante="180",
                   jornales="45", agua="300")
        self._producir(campania, "1.50", "300")
        self._cerrar(campania)

        fila, origenes = servicio.fila_de_campania(campania)
        self.assertEqual(set(fila), set(catalogo.columnas_conjunto("plan")))

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vw_dataset_entrenamiento WHERE campania_id = %s",
                [campania.pk],
            )
            nombres = [columna.name for columna in cursor.description]
            vista = dict(zip(nombres, cursor.fetchone()))
        for columna in catalogo.columnas_conjunto("plan"):
            self.assertEqual(fila[columna], vista[columna], columna)

        # El origen de cada valor queda declarado (228)
        self.assertEqual(origenes["semilla_kg_ha"], "registrado")
        self.assertEqual(origenes["cultivo"], "campaña")
        self.assertEqual(origenes["altitud_msnm"], "parcela")

    # ------------------------------------------------------------------ #
    def test_373_el_modelo_se_carga_con_su_huella_y_se_recarga_si_cambia(self):
        campania = self._camp()
        self._usos(campania, semilla="67.5", fertilizante="180",
                   jornales="45", agua="300")
        self._activo("373a")
        primera = servicio.predecir(campania, self.admin, destino=self.destino)
        self.assertEqual(primera["modelo"]["version"], "373a")

        # Caché: el mismo tubo mientras la huella no cambie (226)
        _, tubo1 = servicio.cargar_modelo(destino=self.destino)
        _, tubo2 = servicio.cargar_modelo(destino=self.destino)
        self.assertIs(tubo1, tubo2)

        # Otro activo (entrenado con la mitad del rendimiento) → se
        # recarga y el resultado cambia
        mitad = datos_sinteticos()
        mitad["rendimiento_kg_ha"] = mitad["rendimiento_kg_ha"] / 2
        self._activo("373b", datos=mitad)
        segunda = servicio.predecir(campania, self.admin, destino=self.destino)
        self.assertEqual(segunda["modelo"]["version"], "373b")
        self.assertNotEqual(
            segunda["rendimiento_predicho"], primera["rendimiento_predicho"]
        )

        # Archivo alterado → la huella no coincide y NO predice (226)
        ruta = self.destino / "regresion_lineal_v373b.joblib"
        original = ruta.read_bytes()
        ruta.write_bytes(original + b"\x00")
        with self.assertRaises(ErrorModelo):
            servicio.predecir(campania, self.admin, destino=self.destino)
        ruta.write_bytes(original)
        tercera = servicio.predecir(campania, self.admin, destino=self.destino)
        self.assertEqual(tercera["modelo"]["version"], "373b")

    # ------------------------------------------------------------------ #
    def test_374_solo_se_predice_en_estados_validos_y_con_modelo_activo(self):
        self._activo("374")
        activo = ModeloML.objects.get(activo=True)
        campania = self._camp()

        # Sin modelo activo → ErrorSinModelo (la API responde 409)
        ModeloML.objects.filter(activo=True).update(activo=False)
        with self.assertRaises(ErrorSinModelo):
            servicio.predecir(campania, self.admin, destino=self.destino)
        activo.activo = True
        activo.save(update_fields=["activo"])

        # Estados que rechazan (227)
        cosechada = self._camp()
        self._producir(cosechada, "1.50", "300")
        cerrada = self._camp()
        self._producir(cerrada, "1.50", "300")
        self._cerrar(cerrada)
        cancelada = self._camp()
        self._sql(
            "UPDATE campanias SET estado = 'CANCELADA' WHERE id = %s",
            [cancelada.pk],
        )
        cancelada.refresh_from_db()
        for campania_mala in (cosechada, cerrada, cancelada):
            with self.assertRaisesMessage(
                servicio.ErrorEstado, campania_mala.estado
            ):
                servicio.predecir(campania_mala, self.admin,
                                  destino=self.destino)

        # PLANIFICADA sí es elegible (227)
        planificada = self._camp(estado=Campania.ESTADO_PLANIFICADA)
        respuesta_plan = servicio.predecir(
            planificada, self.admin, destino=self.destino
        )
        self.assertIsNotNone(respuesta_plan["prediccion"].pk)

        # Guardar y consultar: campos propios, sin intervalo y varias
        # por campaña (230, 232)
        respuesta = servicio.predecir(campania, self.admin,
                                      destino=self.destino)
        prediccion = respuesta["prediccion"]
        self.assertEqual(prediccion.campania, campania)
        self.assertEqual(prediccion.modelo, activo)
        self.assertEqual(prediccion.creado_por, self.admin)
        self.assertEqual(
            prediccion.rendimiento_predicho, respuesta["rendimiento_predicho"]
        )
        self.assertEqual(
            prediccion.produccion_estimada_kg,
            (prediccion.rendimiento_predicho * Decimal("1.50")).quantize(
                Decimal("0.01")
            ),
        )
        self.assertIsNone(prediccion.intervalo_inferior)
        self.assertIsNone(prediccion.intervalo_superior)
        self.assertIsNone(prediccion.dias_ciclo)  # sin siembra (238)
        self.assertEqual(campania.predicciones.count(), 1)
        servicio.predecir(campania, self.admin, destino=self.destino)
        self.assertEqual(campania.predicciones.count(), 2)

        # Auditoría CREAR sin variables de entrada (234)
        evento = Auditoria.objects.filter(
            accion="CREAR", modulo="Machine Learning"
        ).order_by("-id").first()
        self.assertEqual(evento.detalle["tabla"], "predicciones")
        self.assertEqual(evento.detalle["campania"], campania.pk)
        self.assertNotIn("variables", evento.detalle)

        # Con fecha de siembra, dias_ciclo cuenta desde la siembra (238)
        con_siembra = self._camp(
            fecha_siembra=self.hoy - timedelta(days=30)
        )
        respuesta_siembra = servicio.predecir(
            con_siembra, self.admin, destino=self.destino
        )
        self.assertEqual(respuesta_siembra["dias_ciclo"], 30)

    # ------------------------------------------------------------------ #
    def test_375_los_valores_planificados_tienen_prioridad_y_guardan_su_origen(self):
        self._activo("375")
        campania = self._camp()
        self._usos(campania, semilla="67.5", fertilizante="180",
                   jornales="45", agua="300")

        respuesta = servicio.predecir(
            campania, self.admin, destino=self.destino,
            planificados={"semilla": 50, "agua": 100},
        )
        guardadas = respuesta["prediccion"].variables_entrada
        self.assertEqual(guardadas["planificados"], {"semilla": 50.0, "agua": 100.0})
        self.assertEqual(guardadas["origenes"]["semilla_kg_ha"], "planificado")
        self.assertEqual(guardadas["origenes"]["agua_m3_ha"], "planificado")
        self.assertEqual(guardadas["origenes"]["fertilizante_kg_ha"], "registrado")
        self.assertEqual(guardadas["origenes"]["jornales_ha"], "registrado")
        # La copia exacta de lo enviado al modelo lleva el planificado
        self.assertEqual(guardadas["valores"]["semilla_kg_ha"], 50.0)
        self.assertEqual(guardadas["valores"]["fertilizante_kg_ha"], 120.0)

        # Sin registrados, el planificado también deja constancia
        otra = self._camp()
        sin_registrados = servicio.predecir(
            otra, self.admin, destino=self.destino,
            planificados={"fertilizante": 120},
        )
        origenes = sin_registrados["prediccion"].variables_entrada["origenes"]
        self.assertEqual(origenes["fertilizante_kg_ha"], "planificado")
        self.assertEqual(origenes["semilla_kg_ha"], "imputada")

        # Validaciones de lo planificado (228)
        with self.assertRaisesMessage(ErrorVariables, "negativo"):
            servicio.predecir(campania, self.admin, destino=self.destino,
                              planificados={"semilla": -1})
        with self.assertRaisesMessage(ErrorVariables, "desconocida"):
            servicio.predecir(campania, self.admin, destino=self.destino,
                              planificados={"siembra": 5})
        with self.assertRaisesMessage(ErrorVariables, "número"):
            servicio.predecir(campania, self.admin, destino=self.destino,
                              planificados={"semilla": "x"})

    # ------------------------------------------------------------------ #
    def test_376_los_avisos_declaran_faltantes_categorias_y_fuera_de_rango(self):
        self._activo("376")
        # Cultivo y variedad que el tubo nunca vio («Quinua S21»)
        campania = self._camp(cultivo=self.cultivo, variedad=self.variedad)
        respuesta = servicio.predecir(
            campania, self.admin, destino=self.destino,
            planificados={"semilla": 5000},
        )
        guardadas = respuesta["prediccion"].variables_entrada
        avisos = "\n".join(guardadas["avisos"])
        self.assertIn("mediana", avisos)  # fertilizante/jornales/agua
        self.assertIn("no se vio en el entrenamiento", avisos)
        self.assertIn("Quinua S21", avisos)
        self.assertIn("fuera del rango", avisos)  # 5000 fuera de 30-60
        self.assertEqual(guardadas["origenes"]["semilla_kg_ha"], "planificado")
        self.assertEqual(guardadas["origenes"]["fertilizante_kg_ha"], "imputada")
        # Los avisos también viajan en la respuesta
        self.assertEqual(len(respuesta["avisos"]), len(guardadas["avisos"]))

    # ------------------------------------------------------------------ #
    def test_377_el_resultado_es_rendimiento_mas_produccion_sin_intervalo_y_negativo_en_cero(self):
        self._activo("377")
        campania = self._camp()  # superficie 1.50
        self._usos(campania, semilla="67.5", fertilizante="180",
                   jornales="45", agua="300")
        respuesta = servicio.predecir(campania, self.admin,
                                      destino=self.destino)
        rendimiento = respuesta["rendimiento_predicho"]
        self.assertIsInstance(rendimiento, Decimal)
        self.assertFalse(respuesta["negativo_ajustado"])
        esperada = (rendimiento * Decimal("1.50")).quantize(Decimal("0.01"))
        self.assertEqual(respuesta["produccion_estimada_kg"], esperada)
        self.assertIsNone(respuesta["intervalo_inferior"])
        self.assertIsNone(respuesta["intervalo_superior"])
        guardada = respuesta["prediccion"]
        self.assertIsNone(guardada.intervalo_inferior)
        self.assertIsNone(guardada.intervalo_superior)
        self.assertEqual(guardada.produccion_estimada_kg, esperada)

        # Un modelo que predice negativo va a 0 con la marca (230)
        datos = datos_sinteticos()
        datos["rendimiento_kg_ha"] = -datos["rendimiento_kg_ha"]
        self._activo("377n", datos=datos)
        negativa = servicio.predecir(campania, self.admin,
                                     destino=self.destino)
        self.assertTrue(negativa["negativo_ajustado"])
        self.assertEqual(negativa["rendimiento_predicho"], Decimal("0.00"))
        self.assertEqual(negativa["produccion_estimada_kg"], Decimal("0.00"))
        self.assertEqual(
            negativa["prediccion"].rendimiento_predicho, Decimal("0.00")
        )

    # ------------------------------------------------------------------ #
    def test_378_al_cosechar_se_compara_predicho_vs_real_y_al_deshacer_se_limpia(self):
        self._activo("378")
        campania = self._camp()
        respuesta = servicio.predecir(campania, self.admin,
                                      destino=self.destino)
        prediccion = respuesta["prediccion"]
        # Con el ejemplo de la decisión 236: 1580 predicho vs 1620 real
        prediccion.rendimiento_predicho = Decimal("1580.00")
        prediccion.save(update_fields=["rendimiento_predicho"])

        # Registrar la producción completa el comparativo (fn; 236)
        self._producir(campania, "1.50", "2430")  # → 1620 kg/ha
        prediccion.refresh_from_db()
        self.assertEqual(prediccion.rendimiento_real, Decimal("1620.00"))
        self.assertEqual(prediccion.error_abs, Decimal("40.00"))
        self.assertEqual(prediccion.error_pct, Decimal("2.47"))

        # 237: borrada por SQL directo, el comparativo NO se limpia
        self._sql(
            "DELETE FROM producciones WHERE campania_id = %s",
            [campania.pk],
        )
        prediccion.refresh_from_db()
        self.assertEqual(prediccion.error_abs, Decimal("40.00"))
        self.assertEqual(servicio.limpiar_comparacion(campania), 1)
        prediccion.refresh_from_db()
        self.assertIsNone(prediccion.rendimiento_real)
        self.assertIsNone(prediccion.error_abs)
        self.assertIsNone(prediccion.error_pct)

        # Vía API: deshacer-cosecha limpia en la MISMA transacción (236)
        self._sql(
            "UPDATE campanias SET estado = 'EN_PRODUCCION' WHERE id = %s",
            [campania.pk],
        )
        self._producir(campania, "1.50", "2430")
        prediccion.refresh_from_db()
        self.assertEqual(prediccion.error_abs, Decimal("40.00"))
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM producciones WHERE campania_id = %s",
                [campania.pk],
            )
            produccion_id = cursor.fetchone()[0]
        self._entrar_admin()
        respuesta_deshacer = self._api(
            "post",
            f"/api/producciones/{produccion_id}/deshacer-cosecha/",
            {"motivo": "Prueba 378"},
        )
        self.assertEqual(respuesta_deshacer.status_code, 200)
        prediccion.refresh_from_db()
        self.assertIsNone(prediccion.rendimiento_real)
        self.assertIsNone(prediccion.error_abs)
        self.assertIsNone(prediccion.error_pct)

    # ------------------------------------------------------------------ #
    def test_379_la_confiabilidad_es_baja_con_dos_variables_de_manejo_ausentes(self):
        self._activo("379")

        # 4 ausentes → BAJA (229)
        sin_nada = self._camp()
        r1 = servicio.predecir(sin_nada, self.admin, destino=self.destino)
        self.assertEqual(r1["confiabilidad"], "BAJA")
        self.assertEqual(
            r1["prediccion"].variables_entrada["confiabilidad"], "BAJA"
        )

        # Exactamente 2 de 4 ausentes → BAJA
        dos = self._camp()
        r2 = servicio.predecir(
            dos, self.admin, destino=self.destino,
            planificados={"semilla": 45, "fertilizante": 120},
        )
        self.assertEqual(r2["confiabilidad"], "BAJA")

        # 1 ausente → todavía ALTA
        una = self._camp()
        r3 = servicio.predecir(
            una, self.admin, destino=self.destino,
            planificados={"semilla": 45, "fertilizante": 120,
                          "mano_de_obra": 30},
        )
        self.assertEqual(r3["confiabilidad"], "ALTA")

        # Completas → ALTA
        completa = self._camp()
        self._usos(completa, semilla="67.5", fertilizante="180",
                   jornales="45", agua="300")
        r4 = servicio.predecir(completa, self.admin, destino=self.destino)
        self.assertEqual(r4["confiabilidad"], "ALTA")

    # ------------------------------------------------------------------ #
    def test_380_la_respuesta_lleva_la_marca_de_demostracion_el_texto_y_el_mae(self):
        texto = "Es una estimación basada en datos históricos, no una medición."
        self._activo("380d", origen="demostración")
        campania = self._camp()
        respuesta = servicio.predecir(campania, self.admin,
                                      destino=self.destino)
        self.assertTrue(respuesta["datos_demostracion"])
        self.assertEqual(respuesta["texto_estimacion"], texto)
        self.assertEqual(respuesta["modelo"]["mae"], "4.50")

        # Un modelo de datos reales no lleva la marca, pero sí el
        # texto y el MAE junto al resultado (231)
        self._activo("380r", origen="real")
        respuesta_real = servicio.predecir(campania, self.admin,
                                           destino=self.destino)
        self.assertFalse(respuesta_real["datos_demostracion"])
        self.assertEqual(respuesta_real["texto_estimacion"], texto)
        self.assertEqual(respuesta_real["modelo"]["mae"], "4.50")


# ---------------------------------------------------------------------- #
# F2d: API de Machine Learning (381-387)
# ---------------------------------------------------------------------- #
class Bloque2dTests(Bloque2Base):
    """Pruebas 381-387: la API de la decisión 235 — la colección exige
    permiso, ignora campos protegidos y no admite escrituras (381), la
    ficha trae avisos, marca de demostración y MAE sin datos personales
    (382), el Técnico solo ve sus asignados y sin creado_por (383), el
    Coordinador consulta sin predecir ni ver modelos (384), predecir
    tiene límite de 30 por hora y usuario (385), modelo-activo y
    campañas predecibles siguen el contrato (386) y activar por la API
    usa los mismos controles que el comando (387, decisión 222)."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.addCleanup(servicio.limpiar_cache)
        servicio.limpiar_cache()
        # La API siempre usa el destino real (ml_models/): se registra
        # aquí el modelo versionado en el repo (S22 F1, datos demo, 231)
        registro.registrar(
            usuario=self.admin,
            resultados=guardado.leer_resultados("1"),
            version="1",
            desarrollo=True,
            activar=True,
        )
        self.blanca, _ = Variedad.objects.get_or_create(
            cultivo=Cultivo.objects.get(nombre="Quinua"), nombre="Blanca"
        )
        self._n = 0

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _camp(self, **extra):
        """Campaña EN_PRODUCCION (o la que se pida) con cultivo/variedad
        comunes; la fila sin usos es válida: el servicio imputa."""
        self._n += 1
        productor = self._productor(
            dni=f"960002{self._n:02d}", nombre=f"A{self._n}"
        )
        parcela = self._parcela(productor)
        datos = {"cultivo": self.blanca.cultivo, "variedad": self.blanca}
        datos.update(extra)
        return self._campania(parcela, **datos)

    def _predecir(self, campania, **planificados):
        return self._api(
            "post", "/api/ml/predicciones/",
            {"campania": campania.pk, **planificados},
        )

    def _tecnico(self):
        return Usuario.objects.create_user(
            username="tec_ml",
            password="TecMl2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )

    # ------------------------------------------------------------------ #
    def test_381_la_coleccion_exige_permiso_ignora_lo_protegido_y_rechaza_escrituras(self):
        campania = self._camp()
        # El endpoint nace cerrado (401 sin sesión)
        self.assertEqual(
            self.client.get("/api/ml/predicciones/").status_code, 401
        )
        self._entrar_admin()
        # Campos protegidos que el cliente intenta inyectar (232)
        respuesta = self._predecir(
            campania,
            semilla=45,
            rendimiento_predicho="999.00",
            modelo=999,
            error_abs="1.00",
            creado_por=self.coordinador.pk,
        )
        self.assertEqual(respuesta.status_code, 201)
        datos = self._json(respuesta)
        prediccion = Prediccion.objects.get(pk=datos["id"])
        self.assertEqual(
            prediccion.modelo,
            ModeloML.objects.get(activo=True),
            "el modelo lo elige el servidor, no el cliente",
        )
        self.assertEqual(prediccion.creado_por, self.admin)
        self.assertEqual(datos["creado_por"], "admin_ml")
        self.assertIsNone(prediccion.error_abs)
        self.assertNotEqual(datos["rendimiento_predicho"], 999)
        # La lista trae la predicción con su campaña y su modelo
        lista = self._json(self.client.get("/api/ml/predicciones/"))
        self.assertEqual(lista["count"], 1)
        self.assertEqual(lista["results"][0]["id"], prediccion.pk)
        self.assertEqual(lista["results"][0]["campania"]["id"], campania.pk)
        self.assertEqual(
            lista["results"][0]["modelo"]["algoritmo"], "REGRESION_LINEAL"
        )
        # Filtro de comparación del historial (HU-177): por defecto las
        # pendientes, y el valor inválido responde 400 en español
        self.assertEqual(
            self._json(
                self.client.get("/api/ml/predicciones/?comparacion=pendiente")
            )["count"],
            1,
        )
        self.assertEqual(
            self._json(
                self.client.get("/api/ml/predicciones/?comparacion=comparada")
            )["count"],
            0,
        )
        self.assertEqual(
            self._json(
                self.client.get("/api/ml/predicciones/?comparacion=todas")
            )["count"],
            1,
        )
        mala = self._json(
            self.client.get("/api/ml/predicciones/?comparacion=rara")
        )
        self.assertEqual(mala["comparacion"], "Use pendiente, comparada o todas.")
        # Sin PUT/PATCH/DELETE: 405 en el detalle (232)
        url = f"/api/ml/predicciones/{prediccion.pk}/"
        self.assertEqual(self._api("put", url, {}).status_code, 405)
        self.assertEqual(self._api("patch", url, {}).status_code, 405)
        self.assertEqual(self._api("delete", url).status_code, 405)

    # ------------------------------------------------------------------ #
    def test_382_la_ficha_trae_variables_avisos_demostracion_y_mae_sin_dni(self):
        campania = self._camp()
        self._entrar_admin()
        creada = self._json(self._predecir(campania, semilla=45))
        url = f"/api/ml/predicciones/{creada['id']}/"
        ficha = self._json(self.client.get(url))
        self.assertIn("variables_entrada", ficha)
        self.assertEqual(
            ficha["confiabilidad"],
            ficha["variables_entrada"]["confiabilidad"],
        )
        self.assertEqual(ficha["avisos"], ficha["variables_entrada"]["avisos"])
        self.assertIn("origenes", ficha["variables_entrada"])
        self.assertEqual(
            ficha["variables_entrada"]["origenes"]["semilla_kg_ha"],
            "planificado",
        )
        # La marca de demostración con el texto fijo y el MAE (231)
        self.assertTrue(ficha["datos_demostracion"])
        self.assertEqual(
            ficha["texto_estimacion"],
            "Es una estimación basada en datos históricos, no una medición.",
        )
        self.assertIsInstance(ficha["modelo"]["mae"], str)
        self.assertEqual(ficha["modelo"]["version"], "1")
        self.assertTrue(ficha["modelo"]["activo"])
        self.assertEqual(ficha["creado_por"], "admin_ml")
        # Sin datos personales del productor (233)
        crudo = self.client.get(url).content.decode("utf-8").lower()
        self.assertNotIn('"dni"', crudo)
        self.assertNotIn("telefono", crudo)
        # Un id que no existe responde el 404 genérico (decisión 11, S4)
        perdido = self.client.get("/api/ml/predicciones/999999/")
        self.assertEqual(perdido.status_code, 404)
        self.assertEqual(self._json(perdido)["detail"], "No encontrado.")

    # ------------------------------------------------------------------ #
    def test_383_el_tecnico_solo_ve_sus_asignados_y_no_recibe_quien_predijo(self):
        tecnico = self._tecnico()
        p1 = self._productor(dni="96000231", nombre="Tres")
        p2 = self._productor(dni="96000232", nombre="Cuatro")
        AsignacionTecnico.objects.create(tecnico=tecnico, productor=p1)
        propia = self._campania(
            self._parcela(p1),
            cultivo=self.blanca.cultivo,
            variedad=self.blanca,
        )
        ajena = self._campania(
            self._parcela(p2),
            cultivo=self.blanca.cultivo,
            variedad=self.blanca,
        )
        self._entrar_admin()
        self.assertEqual(self._predecir(propia).status_code, 201)
        self.assertEqual(self._predecir(ajena).status_code, 201)

        self._entrar("tec_ml", "TecMl2026!")
        lista = self._json(self.client.get("/api/ml/predicciones/"))
        self.assertEqual(lista["count"], 1)
        fila = lista["results"][0]
        self.assertEqual(fila["campania"]["id"], propia.pk)
        self.assertNotIn("creado_por", fila)
        ficha = self._json(
            self.client.get(f"/api/ml/predicciones/{fila['id']}/")
        )
        self.assertNotIn("creado_por", ficha)

        # La ajena responde 404, el mismo que si no existiera (227)
        ajena_id = Prediccion.objects.get(campania=ajena).pk
        perdida = self.client.get(f"/api/ml/predicciones/{ajena_id}/")
        self.assertEqual(perdida.status_code, 404)
        self.assertEqual(self._json(perdida)["detail"], "No encontrado.")
        # Predecir una campaña ajena también es 404 (227)
        self.assertEqual(self._predecir(ajena).status_code, 404)
        # Y la propia sí: el Técnico tiene ml.predecir
        self.assertEqual(self._predecir(propia).status_code, 201)

    # ------------------------------------------------------------------ #
    def test_384_el_coordinador_consulta_sin_predecir_ni_ver_modelos(self):
        campania = self._camp()
        self._entrar_admin()
        self.assertEqual(self._predecir(campania).status_code, 201)

        self._entrar("coord_ml", "CoordMl2026!")
        self.assertEqual(
            self.client.get("/api/ml/predicciones/").status_code, 200
        )
        self.assertEqual(self._predecir(campania).status_code, 403)
        self.assertEqual(self.client.get("/api/ml/modelos/").status_code, 403)
        self.assertEqual(
            self.client.get("/api/ml/modelo-activo/").status_code, 403
        )
        self.assertEqual(
            self.client.get("/api/ml/campanas-predecibles/").status_code, 403
        )

        # El Administrador sí ve los tres modelos con sus métricas (223)
        self._entrar_admin()
        modelos = self._json(self.client.get("/api/ml/modelos/"))
        self.assertEqual(modelos["count"], 3)
        elegido = next(m for m in modelos["results"] if m["activo"])
        self.assertEqual(elegido["algoritmo"], "REGRESION_LINEAL")
        self.assertEqual(elegido["version"], "1")
        self.assertEqual(
            elegido["entrenamiento"]["origen_datos"], "demostración"
        )
        self.assertTrue(elegido["datos_demostracion"])

    # ------------------------------------------------------------------ #
    def test_385_predecir_tiene_limite_de_30_por_hora_y_por_usuario(self):
        campania = self._camp()
        tecnico = self._tecnico()
        p = self._productor(dni="96000251", nombre="Cinco")
        AsignacionTecnico.objects.create(tecnico=tecnico, productor=p)
        propia = self._campania(
            self._parcela(p),
            cultivo=self.blanca.cultivo,
            variedad=self.blanca,
        )
        self._entrar_admin()
        # DRF fija las tasas al importar (THROTTLE_RATES de la clase):
        # se parcha el diccionario y se restaura solo al salir
        with patch.dict(
            ScopedRateThrottle.THROTTLE_RATES, {"ml_prediccion": "3/hour"}
        ):
            for _ in range(3):
                self.assertEqual(self._predecir(campania).status_code, 201)
            bloqueo = self._predecir(campania)
            self.assertEqual(bloqueo.status_code, 429)
            datos = self._json(bloqueo)
            self.assertIn("Demasiadas solicitudes", datos["detail"])
            self.assertGreaterEqual(datos["retry_after"], 1)
            self.assertEqual(bloqueo["Retry-After"], str(datos["retry_after"]))
            # Cada usuario tiene su propia ventana (232)
            self._entrar("tec_ml", "TecMl2026!")
            self.assertEqual(self._predecir(propia).status_code, 201)
            # Solo el POST está limitado: el listado sigue respondiendo
            self._entrar_admin()
            self.assertEqual(
                self.client.get("/api/ml/predicciones/").status_code, 200
            )

    # ------------------------------------------------------------------ #
    def test_386_modelo_activo_y_campanas_predecibles_sigue_el_contrato(self):
        self._entrar_admin()
        activo = self._json(self.client.get("/api/ml/modelo-activo/"))
        self.assertEqual(activo["algoritmo"], "REGRESION_LINEAL")
        self.assertEqual(activo["version"], "1")
        self.assertTrue(activo["activo"])
        self.assertTrue(activo["datos_demostracion"])

        # Solo campañas elegibles para predecir (227)
        planificada = self._camp(estado=Campania.ESTADO_PLANIFICADA)
        en_produccion = self._camp()
        cosechada = self._camp()
        self._producir(cosechada, "1.50", "300")
        lista = self._json(self.client.get("/api/ml/campanas-predecibles/"))
        self.assertEqual(lista["count"], 2)
        estados = {c["id"]: c["estado"] for c in lista["results"]}
        self.assertEqual(
            estados,
            {
                planificada.pk: Campania.ESTADO_PLANIFICADA,
                en_produccion.pk: Campania.ESTADO_EN_PRODUCCION,
            },
        )
        # Sin modelo activo el recurso responde 404 (no un banner vacío)
        ModeloML.objects.filter(activo=True).update(activo=False)
        perdido = self.client.get("/api/ml/modelo-activo/")
        self.assertEqual(perdido.status_code, 404)
        self.assertIn("modelo activo", self._json(perdido)["detail"])

    # ------------------------------------------------------------------ #
    def test_387_activar_por_la_api_con_los_mismos_controles(self):
        modelo = ModeloML.objects.get(
            version="1", algoritmo="REGRESION_LINEAL"
        )
        rf = ModeloML.objects.get(version="1", algoritmo="RANDOM_FOREST")
        self._entrar_admin()
        # La acción es solo POST: GET responde 405
        self.assertEqual(
            self._api("get", f"/api/ml/modelos/{modelo.pk}/activar/").status_code,
            405,
        )
        # Sin ml.activar_modelo: 403
        self._entrar("coord_ml", "CoordMl2026!")
        self.assertEqual(
            self._api(
                "post", f"/api/ml/modelos/{modelo.pk}/activar/", {}
            ).status_code,
            403,
        )
        # El Administrador lo desactiva y vuelve a activarlo (222)
        self._entrar_admin()
        modelo.activo = False
        modelo.save(update_fields=["activo"])
        activada = self._api(
            "post", f"/api/ml/modelos/{modelo.pk}/activar/", {}
        )
        self.assertEqual(activada.status_code, 200)
        self.assertTrue(self._json(activada)["activo"])
        modelo.refresh_from_db()
        self.assertTrue(modelo.activo)
        self.assertEqual(ModeloML.objects.filter(activo=True).count(), 1)
        self.assertTrue(
            Auditoria.objects.filter(
                accion="ACTIVAR", modulo="Machine Learning"
            ).exists()
        )
        # Un modelo sin archivo no se puede activar: 400 con detalle (222)
        sin_archivo = self._api(
            "post", f"/api/ml/modelos/{rf.pk}/activar/", {}
        )
        self.assertEqual(sin_archivo.status_code, 400)
        self.assertIn("no tiene archivo", self._json(sin_archivo)["detail"])


# ---------------------------------------------------------------------- #
# Fase F2a: app ml, 3 tablas del diseño y fn de producción completa (388)
# ---------------------------------------------------------------------- #
class EsquemaMLTests(TestCase):
    """Prueba 388 (decisiones 216-218): las migraciones dejan 32 tablas
    de dominio y 25 triggers, con las tres tablas de ML de
    01_tablas.sql:385-431, sus restricciones, los índices del diseño y
    fn_produccion_post completa."""

    def test_388_las_tres_tablas_ml_con_32_tablas_y_25_triggers(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema = 'public'"
                " AND table_type = 'BASE TABLE'"
            )
            todas = {fila[0] for fila in cursor.fetchall()}
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"
            )
            triggers = cursor.fetchone()[0]

        dominio = {
            t for t in todas
            if not t.startswith(("auth_", "django_", "token_"))
        }
        self.assertEqual(
            len(dominio),
            32,
            "las migraciones deben crear 32 tablas de dominio "
            "(29 + entrenamientos_ml, modelos_ml y predicciones)",
        )
        self.assertEqual(triggers, 25, "los triggers siguen en 25")
        self.assertLessEqual(
            {"entrenamientos_ml", "modelos_ml", "predicciones"}, todas
        )
        # El resto de apps no debe crear tablas con ese nombre
        self.assertEqual(
            [t for t in todas if t.startswith("ml")], [],
            "el prefijo de app no aparece en las tablas (db_table fijo)",
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'modelos_ml'::regclass"
            )
            modelos = {fila[0] for fila in cursor.fetchall()}
            cursor.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'predicciones'::regclass"
            )
            predicciones = {fila[0] for fila in cursor.fetchall()}
            cursor.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'entrenamientos_ml'::regclass"
            )
            entrenamientos = {fila[0] for fila in cursor.fetchall()}
            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename IN ('modelos_ml', 'predicciones')"
            )
            indices = {fila[0] for fila in cursor.fetchall()}
            cursor.execute(
                "SELECT i.indisunique, i.indpred IS NOT NULL"
                " FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid"
                " WHERE c.relname = 'uq_modelo_activo'"
            )
            activo = cursor.fetchone()
            cursor.execute(
                "SELECT prosrc FROM pg_proc WHERE proname = 'fn_produccion_post'"
            )
            fn_post = cursor.fetchone()[0]

        # Restricciones de modelos_ml (01_tablas.sql:396-411)
        self.assertLessEqual(
            {
                "ck_modelo_algoritmo",
                "ck_modelo_mae",
                "ck_modelo_rmse",
                "uq_modelo_entrenamiento",
                "uq_modelo_version",
            },
            modelos,
        )
        # Índices de modelos_ml: el único parcial de modelo activo
        # (01_tablas.sql:497-500) y los de predicciones (:523-524)
        self.assertIn("uq_modelo_activo", indices)
        self.assertLessEqual(
            {"ix_predicciones_campania", "ix_predicciones_modelo"}, indices
        )
        # Restricciones de predicciones (01_tablas.sql:413-431)
        self.assertLessEqual(
            {"ck_prediccion_dias", "ck_prediccion_intervalo"},
            predicciones,
        )
        # Restricciones de entrenamientos_ml (01_tablas.sql:385-394)
        self.assertLessEqual(
            {
                "ck_entrenamiento_registros",
                "ck_entrenamiento_entrenamiento",
                "ck_entrenamiento_prueba",
            },
            entrenamientos,
        )
        # uq_modelo_activo: único y PARCIAL (solo las filas activas)
        self.assertIsNotNone(activo, "falta el índice uq_modelo_activo")
        self.assertTrue(activo[0], "uq_modelo_activo debe ser único")
        self.assertTrue(activo[1], "uq_modelo_activo debe ser parcial")

        # fn_produccion_post completa: comparación predicho vs. real
        self.assertIn("predicciones", fn_post)
        self.assertIn("error_abs", fn_post)
        self.assertIn("error_pct", fn_post)
