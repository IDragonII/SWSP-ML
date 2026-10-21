"""entrenar_modelos: entrena los tres algoritmos y guarda el elegido.

    manage.py entrenar_modelos [--archivo R] [--version-modelo 1]
                               [--informe R] [--dry-run]

Parte del dataset exportado con `exportar_dataset` (por defecto, el CSV
más reciente de ML_EXPORT_DIR): lo carga por la puerta `ml.carga`,
aplica la limpieza, evalúa los tres candidatos y la línea base con la
MISMA validación agrupada (semilla 42), aplica el criterio escrito
(`docs/criterio_seleccion.md`, decisión 210) y guarda:

- `ml_models/<algoritmo>_v<version>.joblib` (el elegido, entrenado con
  TODOS los datos limpios) + su huella en `manifiesto.json`;
- `ml_models/resultados_v<version>.json` (métricas de los tres, para
  `registrar_modelo`);
- `docs/informe_resultados_ml.md` (informe de resultados).

No toca la base de datos: el alta en tablas la hace `registrar_modelo`
(con su permiso y su auditoría). Con --dry-run no escribe nada.
"""
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ml import criterio, entrenamiento, guardado, limpieza
from ml.carga import cargar
from ml.exportacion import ZONA_LIMA


class Command(BaseCommand):
    help = (
        "Entrena los tres algoritmos con el criterio escrito y guarda "
        "el modelo elegido en ml_models/ con su manifiesto de huellas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            help="CSV del dataset (por defecto: el más reciente de "
            "ML_EXPORT_DIR).",
        )
        parser.add_argument(
            "--version-modelo",
            default="1",
            help="Versión del modelo que se va a guardar (default: 1). "
            "«--version» lo reserva Django.",
        )
        parser.add_argument(
            "--informe",
            help="Ruta del informe markdown (default: "
            "docs/informe_resultados_ml.md).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Entrena e informa sin escribir ningún archivo.",
        )

    def handle(self, *args, **opciones):
        ruta = self._dataset(opciones["archivo"])
        origen = self._origen(ruta)
        datos = cargar(ruta)
        limpio, resumen = limpieza.limpiar(datos)
        if len(limpio) < 5:
            raise CommandError(
                f"Quedan {len(limpio)} filas tras la limpieza: no hay "
                "datos suficientes para validar por grupos."
            )

        plan = entrenamiento.estrategia_de(len(limpio))
        resultado = entrenamiento.evaluar(limpio, estrategia=plan)
        resolucion = entrenamiento.aplicar_criterio(resultado)

        self._tabla(resultado, resolucion)

        if opciones["dry_run"]:
            self.stdout.write(
                "Dry-run: no se escriben modelos, resultados ni informe."
            )
            return

        fecha = datetime.now(ZONA_LIMA).isoformat(timespec="seconds")
        salida = entrenamiento.a_json(resultado)
        salida.update(
            {
                "version": opciones["version_modelo"],
                "fecha_lima": fecha,
                "archivo_dataset": ruta.name,
                "sha256_dataset": guardado.huella_de(ruta),
                "origen_datos": origen,
                "excluidas": resumen.get("filas_excluidas"),
                "criterio": resolucion,
                "criterio_archivo": "docs/criterio_seleccion.md",
            }
        )
        ruta_resultados = guardado.guardar_resultados(
            salida, opciones["version_modelo"]
        )

        if resolucion["elegido"]:
            tubo, _, _ = entrenamiento.entrenar_completo(
                limpio, resolucion["elegido"]
            )
            ruta_modelo = guardado.guardar(
                tubo, resolucion["elegido"], opciones["version_modelo"]
            )
            guardado.registrar_archivo(
                ruta_modelo,
                algoritmo=resolucion["elegido"],
                version=opciones["version_modelo"],
                sha256_dataset=salida["sha256_dataset"],
                fecha_lima=fecha,
                n_registros=salida["n"],
                origen_datos=origen,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Modelo guardado: {ruta_modelo.name} "
                    f"(huella {guardado.huella_de(ruta_modelo)[:12]}…)"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Ningún modelo supera a la línea base: no se guarda "
                    "archivo de modelo (solo resultados e informe)."
                )
            )

        ruta_informe = self._informe(opciones["informe"])
        ruta_informe.write_text(
            entrenamiento.informe_markdown(
                resultado,
                resolucion,
                origen=origen,
                version=opciones["version_modelo"],
                archivo=ruta.name,
            ),
            encoding="utf-8",
        )
        self.stdout.write(f"Resultados: {ruta_resultados}")
        self.stdout.write(f"Informe: {ruta_informe}")
        self.stdout.write(
            f"Tramo de datos: {entrenamiento.nombre_tramo(resultado['n'])}"
            f" ({resultado['n']} filas limpias, "
            f"{resumen.get('filas_excluidas', 0)} excluidas)"
        )

    # ------------------------------------------------------------------ #
    def _tabla(self, resultado, resolucion):
        self.stdout.write("")
        self.stdout.write(
            f"Estrategia: {resultado['estrategia']['nombre']} "
            f"({resultado['estrategia']['pliegues']} pliegues ×- "
            f"{resultado['estrategia']['repeticiones']}, semilla "
            f"{resultado['estrategia']['semilla']})"
        )
        self.stdout.write(
            f"{'Algoritmo':<22}{'MAE':>10}{'RMSE':>10}{'Desvío':>10}"
            f"{'R²':>10}"
        )
        for nombre in entrenamiento.NOMBRES:
            m = resultado["candidatos"][nombre]
            self.stdout.write(
                f"{nombre:<22}{m['mae']:>10.2f}{m['rmse']:>10.2f}"
                f"{m['desvio_rmse']:>10.2f}{m['r2']:>10.3f}"
            )
        base = resultado["linea_base"]
        self.stdout.write(
            f"{'Línea base':<22}{base['mae']:>10.2f}{base['rmse']:>10.2f}"
            f"{base['desvio_rmse']:>10.2f}{base['r2']:>10.3f}"
        )
        self.stdout.write("")
        self.stdout.write(f"Criterio: {resolucion['motivo']}")
        self.stdout.write(
            f"Modelo elegido: {resolucion['elegido'] or 'ninguno'}"
        )
        self.stdout.write("")

    def _dataset(self, archivo):
        if archivo:
            ruta = Path(archivo)
            if not ruta.exists():
                raise CommandError(f"No existe el archivo {archivo}.")
            return ruta
        cruda = os.getenv("ML_EXPORT_DIR", "").strip()
        if not cruda:
            raise CommandError(
                "ML_EXPORT_DIR no está definido en el .env: exporta el "
                "dataset o indica --archivo."
            )
        carpeta = Path(cruda).expanduser()
        if not carpeta.exists():
            raise CommandError(
                f"La carpeta {carpeta} no existe: ejecuta primero "
                "exportar_dataset."
            )
        candidatos = sorted(
            carpeta.glob("dataset_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidatos:
            raise CommandError(
                f"No hay dataset_*.csv en {carpeta}: ejecuta primero "
                "exportar_dataset."
            )
        return candidatos[0]

    def _origen(self, ruta):
        nombre = ruta.name.lower()
        if "demostracion" in nombre:
            return "demostración"
        if "dataset_real" in nombre:
            return "real"
        return "desconocido"

    def _informe(self, informe):
        if informe:
            return Path(informe)
        return (
            settings.BASE_DIR.parent / "docs" / "informe_resultados_ml.md"
        )
