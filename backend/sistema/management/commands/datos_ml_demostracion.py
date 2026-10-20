"""datos_ml_demostracion: genera el CSV de DEMOSTRACIÓN para el
entrenamiento del Sprint 13 (decisión 247).

    manage.py datos_ml_demostracion [--filas 48]

Escribe `dataset_demostracion_ml_<marca>.csv` + su ficha técnica en
ML_EXPORT_DIR (la misma carpeta y reglas de exportar_dataset). Los datos
son INVENTADOS por diseño:48 campañas con un patrón lineal conocido
(rendimiento en función de semilla, fertilizante y jornales, con ruido)
para que el criterio escrito pueda elegir un modelo y el flujo completo
(modelo activo → predicción → comparación en cosecha) sea demostrable
en la entrega. Con las 13 filas reales de la BD de desarrollo ningún
modelo gana a la línea base (informe: docs/informe_resultados_ml.md).

La generación es determinista (semilla 42): el contenido y la huella
SHA-256 se repiten en cada ejecución; solo cambia la marca de tiempo del
nombre. No toca la base de datos ni deja eventos de auditoría.
"""
import json
import os
import random
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ml import exportacion
from ml.columnas import COLUMNAS_EXPORTADAS

SEMILLA = 42
FILAS_DEFECTO = 48

CULTIVOS = (("Quinua", "Quinua Amarilla"), ("Cañihua", "Variedad S5 SEMANA5"))
PERIODOS = ("2024-2025", "2025-2026", "2026-2027")
SUELOS = ("FRANCO", "ARCILLOSO")
RIEGOS = ("GOTEO", "GRAVEDAD")


class Command(BaseCommand):
    help = (
        "Genera el dataset de demostración con patrón aprendible en "
        "ML_EXPORT_DIR (fuera del repositorio), marcado como demostración."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--filas",
            type=int,
            default=FILAS_DEFECTO,
            help=f"Filas a generar (default: {FILAS_DEFECTO}; mínimo 30 "
            "para que el registro acepte el modelo).",
        )

    def handle(self, *args, **opciones):
        filas = opciones["filas"]
        if filas < 30:
            raise CommandError(
                f"Se generaron {filas} filas: se necesitan al menos 30 "
                "para que registrar_modelo acepte el modelo."
            )
        carpeta = self._carpeta()

        registro = self._filas(filas)
        contenido = exportacion.bytes_csv(COLUMNAS_EXPORTADAS, registro)
        huella = exportacion.huella_sha256(contenido)

        marca = exportacion.marca_tiempo(
            datetime.now(exportacion.ZONA_LIMA)
        )
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta_csv = carpeta / f"dataset_demostracion_ml_{marca}.csv"
        ruta_csv.write_bytes(contenido)

        ficha = exportacion.ficha_tecnica(
            filas=len(registro),
            columnas=list(COLUMNAS_EXPORTADAS),
            huella=huella,
            origen_datos="demostracion",
        )
        ruta_ficha = carpeta / f"ficha_dataset_demostracion_ml_{marca}.json"
        ruta_ficha.write_text(
            json.dumps(ficha, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Dataset de demostración generado: {ruta_csv} "
                f"({len(registro)} filas, {len(COLUMNAS_EXPORTADAS)} "
                "columnas, patrón lineal inventado, semilla "
                f"{SEMILLA})"
            )
        )
        self.stdout.write(f"Ficha técnica: {ruta_ficha}")
        self.stdout.write(f"SHA-256: {huella}")
        self.stdout.write("Origen de los datos: demostración (inventado)")

    # ------------------------------------------------------------------ #
    def _filas(self, total):
        """Filas con el patrón inventado: rendimiento = 300 + 2,2·(semilla-40)
        + 1,1·(fertilizante-100) + 0,5·(jornales-18) + ruido ±10."""
        azar = random.Random(SEMILLA)
        filas = []
        for i in range(total):
            cultivo, variedad = CULTIVOS[i % len(CULTIVOS)]
            periodo = PERIODOS[i % len(PERIODOS)]
            semilla = 35 + 5 * (i % 4) + azar.uniform(-1.5, 1.5)
            fertilizante = 90 + 12 * (i % 5) + azar.uniform(-4, 4)
            jornales = 16 + 1.5 * (i % 6) + azar.uniform(-1, 1)
            agua = 18 + 4 * (i % 7) + azar.uniform(-2, 2)
            incidencias = i % 3
            dias_ciclo = 105 + 4 * (i % 6) + azar.uniform(-3, 3)
            rendimiento = (
                300
                + 2.2 * (semilla - 40)
                + 1.1 * (fertilizante - 100)
                + 0.5 * (jornales - 18)
                + azar.uniform(-10, 10)
            )
            dias_clima = 95 + (i % 20)
            fila = {
                "campania_id": 80001 + i,
                "parcela_id": 70001 + i,
                "productor_id": 60001 + i,
                "periodo": periodo,
                "anio_campania": int(periodo[:4]),
                "cultivo": cultivo,
                "variedad": variedad,
                "superficie_sembrada_ha": round(0.8 + 0.35 * (i % 7), 2),
                "altitud_msnm": 3700 + 45 * (i % 10),
                "tipo_suelo": SUELOS[i % len(SUELOS)],
                "pendiente": "SUAVE",
                "sistema_riego": RIEGOS[i % len(RIEGOS)],
                "origen": "SISTEMA",
                "precipitacion_acum_mm": round(
                    150 + 12 * (i % 10) + azar.uniform(-20, 20), 1
                ),
                "temp_prom_c": round(
                    9 + 0.5 * (i % 6) + azar.uniform(-1, 1), 1
                ),
                "humedad_prom_pct": round(
                    55 + 1.5 * (i % 8) + azar.uniform(-3, 3), 1
                ),
                "n_heladas": (3 * i) % 13,
                "dias_con_clima": dias_clima,
                "dias_ventana_clima": dias_clima,
                "semilla_kg_ha": round(semilla, 2),
                "fertilizante_kg_ha": round(fertilizante, 2),
                "jornales_ha": round(jornales, 2),
                "agua_m3_ha": round(agua, 2),
                "n_incidencias": incidencias,
                "severidad_max": incidencias,
                "n_aplicaciones": 2 + (i % 3),
                "dias_ciclo": round(dias_ciclo),
                "rendimiento_kg_ha": round(rendimiento, 2),
            }
            filas.append(tuple(fila[clave] for clave in COLUMNAS_EXPORTADAS))
        return filas

    def _carpeta(self):
        cruda = os.getenv("ML_EXPORT_DIR", "").strip()
        if not cruda:
            raise CommandError(
                "ML_EXPORT_DIR no está definido en el .env: define la "
                "carpeta de exportación (fuera del repositorio)."
            )
        try:
            return exportacion.validar_ruta(
                cruda, settings.BASE_DIR.parent
            )
        except exportacion.ErrorRuta as error:
            raise CommandError(str(error)) from error
