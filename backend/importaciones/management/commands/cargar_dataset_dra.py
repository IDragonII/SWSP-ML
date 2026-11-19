"""cargar_dataset_dra: lleva un CSV de dataset DRA al sistema (S24).

La fuente DRA Puno (Excel «Ejecución y perspectivas de la información
agrícola») es agregada: una fila es distrito × cultivo × campaña, en el
MISMO formato de 28 columnas que escribe exportar_dataset (ml.columnas).
Ese formato no lo entiende importar_historico, así que este comando lo
traduce a las tres formas que espera importaciones.servicio (productores,
parcelas y campañas con producción) y reutiliza importar_productores /
importar_parcelas / importar_campanias: mismas validaciones de la API,
transacción por fila, idempotencia por clave natural y cierre de campaña
por triggers (EN_PRODUCCION → COSECHADA → CERRADA).

Decisiones de traducción (documentadas porque la fuente no trae el dato):

- productor = distrito del archivo de referencia (DNI sintético 90000001+
  en orden alfabético); comunidad = «Comunidad {distrito}» creada bajo la
  provincia y el distrito de la fuente (nombres únicos en el sistema);
- parcela = fila del dataset (clave DRA-{campania_id}); altitud 3800 msnm
  constante porque el esquema no admite vacío y la fuente no tiene
  altitudes (columna sin varianza = sin poder predictivo); sin suelo,
  pendiente ni riego;
- campaña: periodo del dataset, variedad «Local» creada por cultivo,
  fecha de siembra = día 15 del mes principal (si la fuente no lo trae:
  cosecha - 183 días) y fecha de cosecha = día 15 de su mes principal;
  fecha_inicio = siembra y fecha_fin_prevista = cosecha;
- superficie sembrada = max(sembrada, cosechada): fn_validar_produccion
  rechaza cosechada > sembrada y el Excel DRA trae filas incoherentes;
- las filas con producción > 100.000 t se descartan con aviso:
  produccion_kg es numeric(10,2) y el trigger no puede guardarlas.

Ojo con el umbral: fn_validar_produccion marca requiere_revision fuera
de [rendimiento_min_plausible, rendimiento_max_plausible] y esas campañas
quedan COSECHADA, fuera del dataset. Con el umbral por defecto (5000
kg/ha) la mayoría de los forrajes DRA no entran: sube el parámetro
antes de cargar (rendimiento_max_plausible).

Uso:
    manage.py cargar_dataset_dra --archivo salida.csv \
        --referencia salida_referencia.csv --usuario admin [--dry-run]
"""
import csv
import os
import re
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from alertas.servicio import evaluar_todo
from auditoria.registrar import registrar_evento
from catalogos.models import Cultivo, Variedad
from productores.models import Comunidad, Distrito, Provincia
from usuarios.models import RolPermiso

from importaciones import servicio
from importaciones.models import Importacion
from ml.columnas import COLUMNAS_EXPORTADAS

PERMISO = "importacion.ejecutar"
VARIEDAD_DEFAULT = "Local"
ALTITUD_FIJA_MSNM = 3800
DNI_PRIMERO = 90000001
MAX_PRODUCCION_KG = Decimal("99999999.99")  # produccion_kg numeric(10,2)
LARGO_CULTIVO = 60  # catalogos.Cultivo.nombre
DIAS_FALLBACK_SIEMBRA = 183
FECHA_INCORPORACION = "01/01/2020"
OBSERVACIONES = "Carga DRA Puno (EXCEL_DRA_DISTRITAL)"

# Columnas que el CSV de referencia debe traer (una fila por campania_id)
COLUMNAS_REFERENCIA = (
    "campania_id",
    "provincia",
    "distrito",
    "mes_siembra_principal",
    "mes_cosecha_principal",
    "superficie_sembrada_ha",
    "superficie_cosechada_ha",
    "produccion_t",
)

_PERIODO = re.compile(r"^(\d{4})-(\d{4})$")
DOS_DECIMALES = Decimal("0.01")


class Command(BaseCommand):
    help = (
        "Carga un CSV de dataset DRA (28 columnas) al sistema como "
        "productores, parcelas y campañas con producción, con las reglas "
        "de la API, informe de errores y re-ejecución idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            help="Ruta del CSV de dataset (las 28 columnas de ml.columnas).",
        )
        parser.add_argument(
            "--referencia",
            help=(
                "Ruta del CSV de referencia (campania_id, provincia, "
                "distrito, meses y superficies/producción)."
            ),
        )
        parser.add_argument(
            "--usuario",
            help=f"Usuario que ejecuta (su rol debe tener el permiso {PERMISO}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Traduce y valida todo, pero no deja ningún cambio.",
        )
        parser.add_argument(
            "--forzar",
            action="store_true",
            help=(
                "Marca como CON_ERRORES la importación EN_PROCESO que haya "
                "quedado interrumpida y continúa."
            ),
        )

    def handle(self, *args, **opciones):
        faltan = [n for n in ("archivo", "referencia", "usuario") if not opciones[n]]
        if faltan:
            raise CommandError(
                "Faltan argumentos obligatorios: "
                + ", ".join(f"--{n}" for n in faltan)
            )
        usuario = self._usuario(opciones["usuario"])
        dataset = self._leer_csv(
            opciones["archivo"], COLUMNAS_EXPORTADAS, "dataset", estricto=True
        )
        referencia = self._leer_csv(
            opciones["referencia"],
            COLUMNAS_REFERENCIA,
            "CSV de referencia",
            estricto=False,
        )
        indice = self._indice_referencia(referencia)

        seco = opciones["dry_run"]
        if not seco:
            self._liberar_previa(opciones["forzar"])

        try:
            if seco:
                with transaction.atomic():
                    resumen = self._cargar(dataset, indice, usuario, seco=True)
                    transaction.set_rollback(True)
            else:
                resumen = self._cargar(dataset, indice, usuario, seco=False)
        except servicio.ErrorArchivo as error:
            raise CommandError(str(error))
        except KeyboardInterrupt:
            raise CommandError("Carga interrumpida por el usuario.")
        except CommandError:
            raise
        except Exception as error:
            raise CommandError(f"La carga falló: {error}")

        self._resumen(resumen, seco)
        if resumen["informe"]:
            self.stdout.write(f"Informe de errores: {resumen['informe']}")

    # ------------------------------------------------------------------ #
    # Lectura de archivos
    # ------------------------------------------------------------------ #
    def _leer_csv(self, ruta, requeridas, etiqueta, estricto):
        ruta = Path(ruta)
        if not ruta.exists() or not ruta.is_file():
            raise CommandError(f"No se encuentra el {etiqueta}: {ruta}")
        try:
            with open(ruta, encoding="utf-8-sig", newline="") as archivo:
                lector = csv.DictReader(archivo)
                nombres = lector.fieldnames or []
                faltan = [c for c in requeridas if c not in nombres]
                if faltan:
                    raise CommandError(
                        f"El {etiqueta} no trae las columnas: {', '.join(faltan)}"
                    )
                if estricto:
                    sobran = [c for c in nombres if c not in COLUMNAS_EXPORTADAS]
                    if sobran:
                        raise CommandError(
                            "El dataset trae columnas desconocidas: "
                            + ", ".join(sobran)
                        )
                filas = list(lector)
        except UnicodeDecodeError:
            raise CommandError(f"El {etiqueta} no está en UTF-8: {ruta}")
        if not filas:
            raise CommandError(f"El {etiqueta} no trae filas de datos: {ruta}")
        return filas

    def _indice_referencia(self, filas):
        indice = {}
        for i, fila in enumerate(filas):
            clave = (fila.get("campania_id") or "").strip()
            if not clave:
                raise CommandError(
                    f"CSV de referencia: la fila {i + 2} no trae campania_id."
                )
            if clave in indice:
                raise CommandError(
                    f"CSV de referencia: campania_id duplicado «{clave}»."
                )
            indice[clave] = fila
        return indice

    # ------------------------------------------------------------------ #
    # Traducción dataset -> filas del importador
    # ------------------------------------------------------------------ #
    def _construir(self, dataset, indice):
        registros = []
        descartadas = []
        avisos = {
            "overflow": [],
            "sin_sembrada": 0,
            "sembrada_normalizada": 0,
            "sin_mes_siembra": 0,
            "siembra_ajustada": 0,
            "cosecha_ajustada": 0,
        }

        for i, ds in enumerate(dataset):
            numero = i + 2
            clave = (ds.get("campania_id") or "").strip()
            ref = indice.get(clave)
            if ref is None:
                descartadas.append(
                    (numero, f"campania_id «{clave}» sin fila en la referencia")
                )
                continue

            cultivo = (ds.get("cultivo") or "").strip()
            if not cultivo:
                descartadas.append((numero, "sin cultivo"))
                continue
            if len(cultivo) > LARGO_CULTIVO:
                descartadas.append(
                    (
                        numero,
                        f"cultivo de {len(cultivo)} caracteres "
                        f"(máximo {LARGO_CULTIVO})",
                    )
                )
                continue

            periodo = (ds.get("periodo") or "").strip()
            rango = _rango_periodo(periodo)
            if rango is None:
                descartadas.append(
                    (numero, f"periodo inválido «{periodo}» (AAAA-AAAA)")
                )
                continue
            minima, maxima = rango

            provincia = (ref.get("provincia") or "").strip()
            distrito = (ref.get("distrito") or "").strip()
            if not provincia or not distrito:
                descartadas.append((numero, "sin provincia o distrito en la referencia"))
                continue

            cosechada = _decimal(ref.get("superficie_cosechada_ha"))
            if cosechada is None or cosechada <= 0:
                descartadas.append(
                    (numero, "superficie_cosechada_ha vacía o no positiva")
                )
                continue
            # los serializers admiten 2 decimales: se redondea antes de
            # comparar para no perder filas por decimales de más
            cosechada = cosechada.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            sembrada = _decimal(ds.get("superficie_sembrada_ha"))
            if sembrada is None or sembrada <= 0:
                sembrada = cosechada
            else:
                sembrada = sembrada.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            if _decimal(ref.get("superficie_sembrada_ha")) is None:
                avisos["sin_sembrada"] += 1
            if cosechada > sembrada:
                # fn_validar_produccion rechaza cosechada > sembrada
                sembrada = cosechada
                avisos["sembrada_normalizada"] += 1

            produccion_t = _decimal(ref.get("produccion_t"))
            if produccion_t is None or produccion_t <= 0:
                descartadas.append((numero, "produccion_t vacía o no positiva"))
                continue
            produccion_kg = (produccion_t * 1000).quantize(Decimal("0.01"))
            if produccion_kg > MAX_PRODUCCION_KG:
                # produccion_kg numeric(10,2): el trigger no la guarda
                avisos["overflow"].append((numero, clave, produccion_t))
                continue

            cosecha = _fecha_mes(ref.get("mes_cosecha_principal"))
            if cosecha is None:
                descartadas.append((numero, "sin mes_cosecha_principal"))
                continue
            if not minima <= cosecha <= maxima:
                cosecha = min(max(cosecha, minima), maxima)
                avisos["cosecha_ajustada"] += 1

            siembra = _fecha_mes(ref.get("mes_siembra_principal"))
            if siembra is None:
                siembra = max(
                    cosecha - timedelta(days=DIAS_FALLBACK_SIEMBRA), minima
                )
                avisos["sin_mes_siembra"] += 1
            else:
                ajustada = min(max(siembra, minima), cosecha)
                if ajustada != siembra:
                    siembra = ajustada
                    avisos["siembra_ajustada"] += 1

            registros.append(
                {
                    "numero": numero,
                    "clave": clave,
                    "provincia": provincia,
                    "distrito": distrito,
                    "cultivo": cultivo,
                    "periodo": periodo,
                    "sembrada": sembrada,
                    "cosechada": cosechada,
                    "siembra": siembra,
                    "cosecha": cosecha,
                    "produccion_kg": produccion_kg,
                }
            )

        if not registros:
            raise CommandError(
                "Ninguna fila del dataset es apta para cargar "
                f"(descartadas: {len(descartadas)})."
            )

        distritos = sorted({(r["provincia"], r["distrito"]) for r in registros})
        dni_de = {
            par: str(DNI_PRIMERO + i) for i, par in enumerate(distritos)
        }
        comunidad_de = {par: f"Comunidad {par[1]}" for par in distritos}
        nombres = list(comunidad_de.values())
        if len(set(n.lower() for n in nombres)) != len(nombres):
            raise CommandError(
                "Hay distritos repetidos entre provincias: los nombres de "
                "comunidad generados no serían únicos."
            )

        filas_productores = [
            (
                i + 2,
                {
                    "nombres": distrito,
                    "apellidos": provincia,
                    "dni": dni_de[(provincia, distrito)],
                    "telefono": "",
                    "comunidad": comunidad_de[(provincia, distrito)],
                    "referencia_ubicacion": f"Distrito {distrito}",
                    "fecha_incorporacion": FECHA_INCORPORACION,
                },
            )
            for i, (provincia, distrito) in enumerate(distritos)
        ]

        filas_parcelas = []
        filas_campanias = []
        for reg in registros:
            par = (reg["provincia"], reg["distrito"])
            dni = dni_de[par]
            # clave estable de parcela = campania_id del dataset
            referencia = f"DRA-{reg['clave']}"
            filas_parcelas.append(
                (
                    reg["numero"],
                    {
                        "dni_productor": dni,
                        "comunidad": comunidad_de[par],
                        "referencia_ubicacion": referencia,
                        "superficie_ha": _texto(reg["sembrada"]),
                        "altitud_msnm": str(ALTITUD_FIJA_MSNM),
                        "latitud": "",
                        "longitud": "",
                        "tipo_suelo": "",
                        "pendiente": "",
                        "disponibilidad_agua": "",
                        "sistema_riego": "",
                    },
                )
            )
            filas_campanias.append(
                (
                    reg["numero"],
                    {
                        "dni_productor": dni,
                        "referencia_parcela": referencia,
                        "cultivo": reg["cultivo"],
                        "variedad": VARIEDAD_DEFAULT,
                        "periodo": reg["periodo"],
                        "fecha_inicio": _fecha_texto(reg["siembra"]),
                        "fecha_fin_prevista": _fecha_texto(reg["cosecha"]),
                        "fecha_siembra": _fecha_texto(reg["siembra"]),
                        "superficie_sembrada_ha": _texto(reg["sembrada"]),
                        "fecha_cosecha": _fecha_texto(reg["cosecha"]),
                        "superficie_cosechada_ha": _texto(reg["cosechada"]),
                        "produccion_kg": _texto(reg["produccion_kg"]),
                        "semilla_kg": "",
                        "fertilizante_kg": "",
                        "jornales": "",
                        "agua_m3": "",
                        "observaciones": OBSERVACIONES,
                    },
                )
            )

        return {
            "filas_productores": filas_productores,
            "filas_parcelas": filas_parcelas,
            "filas_campanias": filas_campanias,
            "ubicaciones": {
                par: comunidad_de[par] for par in distritos
            },
            "cultivos": sorted({r["cultivo"] for r in registros}),
            "descartadas": descartadas,
            "avisos": avisos,
        }

    # ------------------------------------------------------------------ #
    # Catálogos (esta carga sí los crea: la fuente es la única verdad)
    # ------------------------------------------------------------------ #
    def _asegurar_catalogos(self, ubicaciones, cultivos):
        creados = {
            "provincias": 0,
            "distritos": 0,
            "comunidades": 0,
            "cultivos": 0,
            "variedades": 0,
        }
        for (provincia, distrito), nombre in sorted(ubicaciones.items()):
            prov, nueva = Provincia.objects.get_or_create(nombre=provincia)
            creados["provincias"] += int(nueva)
            dis, nueva = Distrito.objects.get_or_create(
                provincia=prov, nombre=distrito
            )
            creados["distritos"] += int(nueva)
            existente = Comunidad.objects.filter(nombre__iexact=nombre).first()
            if existente is None:
                Comunidad.objects.create(distrito=dis, nombre=nombre)
                creados["comunidades"] += 1
            elif existente.distrito_id != dis.pk:
                raise CommandError(
                    f"La comunidad «{nombre}» ya existe en otro distrito: "
                    "los nombres deben ser únicos en todo el sistema."
                )
        for nombre in cultivos:
            cultivo = Cultivo.objects.filter(nombre__iexact=nombre).first()
            if cultivo is None:
                cultivo = Cultivo.objects.create(nombre=nombre)
                creados["cultivos"] += 1
            elif not cultivo.activo:
                raise CommandError(
                    f"El cultivo «{nombre}» existe pero está inactivo."
                )
            variedad, nueva = Variedad.objects.get_or_create(
                cultivo=cultivo, nombre=VARIEDAD_DEFAULT
            )
            creados["variedades"] += int(nueva)
            if not variedad.activo:
                raise CommandError(
                    f"La variedad {VARIEDAD_DEFAULT} de «{nombre}» está inactiva."
                )
        return creados

    # ------------------------------------------------------------------ #
    # Ejecución (registro, auditoría, informe y alertas)
    # ------------------------------------------------------------------ #
    def _cargar(self, dataset, indice, usuario, seco):
        construido = self._construir(dataset, indice)
        resumen = {
            "filas_dataset": len(dataset),
            "descartadas": construido["descartadas"],
            "avisos": construido["avisos"],
            "catalogos": self._asegurar_catalogos(
                construido["ubicaciones"], construido["cultivos"]
            ),
            "tipos": {},
            "alertas": None,
            "informe": None,
        }

        errores = []
        pares = (
            ("productores", construido["filas_productores"]),
            ("parcelas", construido["filas_parcelas"]),
            ("campanias", construido["filas_campanias"]),
        )
        for tipo, filas in pares:
            resultado = self._procesar_tipo(tipo, filas, usuario, seco)
            resumen["tipos"][tipo] = resultado
            errores.extend((tipo, error) for error in resultado.errores)

        if errores and not seco:
            resumen["informe"] = self._escribir_informe(errores)

        if not seco:
            try:
                resumen["alertas"] = evaluar_todo()
            except Exception as error:
                self.stdout.write(
                    self.style.WARNING(
                        f"No se pudieron evaluar las alertas al terminar: {error}"
                    )
                )
        return resumen

    def _procesar_tipo(self, tipo, filas, usuario, seco):
        registro = None
        if not seco:
            registro = Importacion.objects.create(
                archivo="dataset_dra",
                tipo=tipo.upper(),
                usuario=usuario,
                filas_totales=len(filas),
            )
        try:
            resultado = self._importar(tipo, filas, usuario)
        except Exception as error:
            if registro is not None:
                registro.estado = "CON_ERRORES"
                registro.detalle_errores = [
                    {
                        "fila": 0,
                        "columna": "",
                        "mensaje": str(error)[:200],
                    }
                ]
                registro.save()
            raise
        if registro is not None:
            registro.filas_ok = resultado.creadas + resultado.omitidas
            registro.filas_error = len(resultado.errores)
            registro.estado = (
                "CON_ERRORES" if resultado.errores else "COMPLETADA"
            )
            registro.detalle_errores = resultado.errores or None
            registro.save()
            registrar_evento(
                usuario=usuario,
                accion="CREAR",
                modulo="importaciones",
                tabla="importaciones",
                registro_id=registro.pk,
                detalle={
                    "tipo": tipo,
                    "archivo": "dataset_dra",
                    "filas_totales": resultado.totales,
                    "filas_ok": resultado.creadas + resultado.omitidas,
                    "filas_error": len(resultado.errores),
                },
            )
        return resultado

    def _importar(self, tipo, filas, usuario):
        if tipo == "productores":
            return servicio.importar_productores(filas, usuario)
        if tipo == "parcelas":
            return servicio.importar_parcelas(filas, usuario)
        return servicio.importar_campanias(filas, usuario)

    # ------------------------------------------------------------------ #
    # Utilidades de comando
    # ------------------------------------------------------------------ #
    def _usuario(self, username):
        User = get_user_model()
        try:
            usuario = User.objects.select_related("rol").get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No existe el usuario «{username}».")
        if not usuario.is_active:
            raise CommandError(f"El usuario «{username}» está inactivo.")
        permisos = set(
            RolPermiso.objects.filter(rol_id=usuario.rol_id).values_list(
                "permiso__codigo", flat=True
            )
        )
        if PERMISO not in permisos:
            raise CommandError(
                f"El usuario «{username}» no tiene el permiso {PERMISO}."
            )
        return usuario

    def _liberar_previa(self, forzar):
        previa = (
            Importacion.objects.filter(estado="EN_PROCESO").order_by("-id").first()
        )
        if previa is None:
            return
        if not forzar:
            raise CommandError(
                f"Ya hay una importación EN_PROCESO (id {previa.pk}, "
                f"{previa.fecha:%Y-%m-%d %H:%M}, archivo {previa.archivo}). "
                "Si quedó interrumpida, repite con --forzar."
            )
        previa.estado = "CON_ERRORES"
        previa.detalle_errores = [
            {"fila": 0, "columna": "", "mensaje": "Marcada CON_ERRORES por --forzar."}
        ]
        previa.save()
        self.stdout.write(
            f"Importación EN_PROCESO {previa.pk} marcada CON_ERRORES (--forzar)."
        )

    def _resumen(self, resumen, seco):
        sufijo = " (dry-run: sin cambios)" if seco else ""
        self.stdout.write(f"Filas del dataset: {resumen['filas_dataset']}{sufijo}")

        descartadas = resumen["descartadas"]
        self.stdout.write(f"Descartadas en la traducción: {len(descartadas)}")
        for numero, motivo in descartadas[:10]:
            self.stdout.write(f"  fila {numero}: {motivo}")
        if len(descartadas) > 10:
            self.stdout.write(f"  … y {len(descartadas) - 10} más")

        avisos = resumen["avisos"]
        overflow = avisos["overflow"]
        if overflow:
            self.stdout.write(
                f"  producción > 100.000 t (numeric(10,2)): {len(overflow)}"
            )
            for numero, clave, toneladas in overflow[:10]:
                self.stdout.write(
                    f"  fila {numero} (campania_id {clave}): {toneladas} t"
                )
        self.stdout.write(
            "Avisos: "
            f"sembrada normalizada (cosechada > sembrada) "
            f"{avisos['sembrada_normalizada']} · "
            f"sin superficie de siembra en la fuente {avisos['sin_sembrada']} · "
            f"sin mes de siembra (fallback cosecha - 183 d) "
            f"{avisos['sin_mes_siembra']} · "
            f"siembra ajustada al período {avisos['siembra_ajustada']} · "
            f"cosecha ajustada al período {avisos['cosecha_ajustada']}"
        )

        catalogos = resumen["catalogos"]
        self.stdout.write(
            "Catálogos: "
            + " · ".join(
                f"{clave} {valor}" for clave, valor in catalogos.items() if valor
            )
            + (" (todos ya existían)" if not any(catalogos.values()) else "")
        )

        for tipo, resultado in resumen["tipos"].items():
            self.stdout.write(
                f"{tipo}: creadas {resultado.creadas} · "
                f"ya existían {resultado.omitidas} · "
                f"con error {len(resultado.errores)}"
            )
            for error in resultado.errores[:10]:
                columna = f" [{error['columna']}]" if error["columna"] else ""
                self.stdout.write(
                    f"  fila {error['fila']}{columna}: {error['mensaje']}"
                )
            if len(resultado.errores) > 10:
                self.stdout.write(
                    f"  … y {len(resultado.errores) - 10} errores más"
                )

        if resumen["alertas"] is not None:
            self.stdout.write(
                f"Alertas: creadas {resumen['alertas']['creadas']} · "
                f"cerradas {resumen['alertas']['cerradas']}"
            )

    def _escribir_informe(self, errores):
        carpeta = os.getenv("IMPORTACION_DIR", "").strip()
        if not carpeta:
            self.stdout.write(
                self.style.WARNING(
                    "IMPORTACION_DIR no está definido: el informe de errores "
                    "no se escribe (siguen en la consola y en el registro)."
                )
            )
            return None
        destino = Path(carpeta).expanduser()
        destino.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = destino / f"informe_carga_dataset_dra_{marca}.csv"
        with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(("tipo", "fila", "columna", "mensaje"))
            for tipo, error in errores:
                escritor.writerow(
                    (tipo, error["fila"], error["columna"], error["mensaje"])
                )
        return ruta


# ---------------------------------------------------------------------- #
# Auxiliares puros
# ---------------------------------------------------------------------- #
def _decimal(valor):
    texto = (valor or "").strip().replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto:
        texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def _rango_periodo(periodo):
    """(1 de enero del primer año, 31 de diciembre del segundo) o None."""
    coincidencia = _PERIODO.match(periodo or "")
    if coincidencia is None:
        return None
    anio_1, anio_2 = int(coincidencia.group(1)), int(coincidencia.group(2))
    if anio_2 != anio_1 + 1:
        return None
    return date(anio_1, 1, 1), date(anio_2, 12, 31)


def _fecha_mes(valor):
    """«AAAA-MM» con día 15; vacío o inválido → None."""
    texto = (valor or "").strip()
    if len(texto) != 7 or texto[4] != "-":
        return None
    try:
        return date(int(texto[:4]), int(texto[5:7]), 15)
    except ValueError:
        return None


def _fecha_texto(valor):
    return f"{valor.day:02d}/{valor.month:02d}/{valor.year}"


def _texto(valor):
    return format(valor, "f")
