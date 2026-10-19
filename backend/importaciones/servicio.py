"""Servicio de importación de datos históricos (Semana 20, RF-49/50).

Tres tipos de archivo, un tipo por ejecución, con las MISMAS reglas que
la API: cada fila se valida con los serializers de productores, parcelas,
campañas y producción, y si algo falla la fila entera se descarta sin
dejar nada a medias (transacción por fila). Re-ejecutar un archivo no
duplica: las claves naturales (DNI; productor+referencia; parcela+período)
se omiten sin actualizar lo ya existente.

El importador nunca crea catálogos (comunidades, cultivos, variedades ni
recursos): si falta uno, la fila lleva el error con una sugerencia
difflib. Los cuatro recursos genéricos «(total histórico)» y las unidades
base los trae la migración catalogos.0003 y la 0002.

Nada de esto escribe en el registro de importaciones ni en la auditoría:
lo decide el comando importar_historico, que también escribe el informe
de errores (sin datos personales: el DNI va enmascarado).
"""
import csv
import difflib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import openpyxl
from django.db import DatabaseError, transaction

from campanias.models import Campania
from campanias.serializers import CampaniaEscrituraSerializer
from catalogos.models import Cultivo, Recurso, Unidad, Variedad
from productores.models import Comunidad, Parcela, Productor
from productores.serializers import (
    ParcelaEscrituraSerializer,
    ProductorEscrituraSerializer,
)
from produccion.serializers import ProduccionEscrituraSerializer
from seguimiento.models import UsoRecurso

from .plantillas import COLUMNA_MARCA, COLUMNAS, VALOR_EJEMPLO

LIMITE_BYTES = 5 * 1024 * 1024
LIMITE_FILAS = 5000

# Totales de recursos del archivo de campañas: columna -> nombre exacto
# del recurso genérico (lo crea catalogos.0003; la categoría y la unidad
# base las elige el importador, no el archivo)
RECURSOS_GENERICOS = {
    "semilla_kg": "Semilla (total histórico)",
    "fertilizante_kg": "Fertilizante (total histórico)",
    "jornales": "Mano de obra (total histórico)",
    "agua_m3": "Agua (total histórico)",
}

# Unidades base necesarias (kg, jornal, m3): migración catalogos.0002
TIPOS_UNIDAD_BASE = ("MASA", "LABOR", "VOLUMEN")


class ErrorArchivo(Exception):
    """Fallo que impide empezar: el archivo no se puede leer o está vacío."""


class ErroresFila(Exception):
    """La fila tiene uno o varios errores; no se guarda nada de la fila."""

    def __init__(self, errores):
        self.errores = list(errores)
        super().__init__(" · ".join(mensaje for _, mensaje in self.errores))


def error_uno(columna, mensaje):
    """Error único de fila, listo para lanzar: raise error_uno(...)."""
    return ErroresFila([(columna, mensaje)])


class Resultado:
    """Conteo de una ejecución: creadas, omitidas (ya existían) y errores."""

    def __init__(self, totales):
        self.totales = totales
        self.creadas = 0
        self.omitidas = 0
        self.errores = []


# ---------------------------------------------------------------------- #
# Lectura del archivo (CSV o XLSX), sin chardet y sin pandas
# ---------------------------------------------------------------------- #
def leer_archivo(tipo, ruta):
    """Devuelve [(número de fila, dict)] de datos, ya sin la fila EJEMPLO.

    Falla con ErrorArchivo si el archivo no existe, pesa más de 5 MB, no
    tiene las columnas del tipo, no trae datos o pasa de 5000 filas.
    """
    ruta = Path(ruta)
    if not ruta.exists() or not ruta.is_file():
        raise ErrorArchivo(f"No se encuentra el archivo: {ruta}")
    tamano = ruta.stat().st_size
    if tamano > LIMITE_BYTES:
        raise ErrorArchivo(
            f"El archivo pesa {tamano:,} bytes: el límite es {LIMITE_BYTES:,} (5 MB)."
        )
    if ruta.suffix.lower() == ".csv":
        filas = _leer_csv(tipo, ruta)
    elif ruta.suffix.lower() == ".xlsx":
        filas = _leer_xlsx(tipo, ruta)
    else:
        raise ErrorArchivo(
            f"Extensión no admitida ({ruta.suffix or 'sin extensión'}): usa .csv o .xlsx."
        )
    filas = [fila for fila in filas if not _es_ejemplo(fila[1])]
    if not filas:
        raise ErrorArchivo(
            "El archivo no trae filas de datos (solo encabezados o la fila EJEMPLO)."
        )
    if len(filas) > LIMITE_FILAS:
        raise ErrorArchivo(
            f"El archivo trae {len(filas)} filas de datos: el límite es {LIMITE_FILAS}."
        )
    return filas


def _leer_csv(tipo, ruta):
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as archivo:
            texto = archivo.read()
    except UnicodeDecodeError:
        raise ErrorArchivo(
            "El archivo no está en UTF-8: ábrelo y guárdalo como UTF-8."
        )
    lineas = texto.splitlines()
    if not lineas:
        raise ErrorArchivo("El archivo está vacío.")
    cabecera = lineas[0]
    delimitador = ";" if cabecera.count(";") > cabecera.count(",") else ","
    filas = list(csv.reader(io.StringIO(texto), delimiter=delimitador))
    nombres = [(celda or "").strip().lower() for celda in filas[0]]
    _exigir_columnas(tipo, nombres)
    return _convertir_filas(nombres, filas[1:])


def _leer_xlsx(tipo, ruta):
    try:
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception as error:
        raise ErrorArchivo(f"No se pudo leer el .xlsx: {error}")
    try:
        hoja = libro.active
        filas = [list(fila) for fila in hoja.iter_rows(values_only=True)]
    finally:
        libro.close()
    if not filas:
        raise ErrorArchivo("El archivo está vacío.")
    nombres = [
        (str(celda).strip().lower() if celda is not None else "")
        for celda in filas[0]
    ]
    _exigir_columnas(tipo, nombres)
    return _convertir_filas(nombres, filas[1:])


def _exigir_columnas(tipo, nombres):
    faltan = [columna for columna in COLUMNAS[tipo] if columna not in nombres]
    if faltan:
        encontradas = ", ".join(nombre for nombre in nombres if nombre) or "ninguna"
        raise ErrorArchivo(
            f"Faltan columnas requeridas: {', '.join(faltan)} "
            f"(columnas encontradas: {encontradas})."
        )


def _convertir_filas(nombres, filas):
    """Filas a dicts de texto; las filas totalmente vacías no cuentan."""
    resultado = []
    for indice, valores in enumerate(filas, start=2):
        fila = {nombre: "" for nombre in nombres if nombre}
        for nombre, valor in zip(nombres, valores):
            if not nombre:
                continue
            if valor is None:
                fila[nombre] = ""
            elif isinstance(valor, (datetime, date)):
                fila[nombre] = valor.strftime("%d/%m/%Y")
            else:
                fila[nombre] = str(valor).strip()
        if any(fila.values()):
            resultado.append((indice, fila))
    return resultado


def _es_ejemplo(fila):
    return (fila.get(COLUMNA_MARCA) or "").strip().upper() == VALOR_EJEMPLO


# ---------------------------------------------------------------------- #
# Normalización de celdas
# ---------------------------------------------------------------------- #
def parsear_fecha(valor, columna):
    """dd/mm/aaaa o aaaa-mm-dd; cualquier otra forma se rechaza."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = (valor or "").strip()
    if not texto:
        raise error_uno(columna, "La fecha es obligatoria.")
    if len(texto) == 10 and texto[2] == "/" and texto[5] == "/":
        try:
            return datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            raise error_uno(columna, f"Fecha inválida «{texto}».")
    if len(texto) == 10 and texto[4] == "-" and texto[7] == "-":
        try:
            return date.fromisoformat(texto)
        except ValueError:
            raise error_uno(columna, f"Fecha inválida «{texto}».")
    raise error_uno(
        columna,
        f"Fecha no reconocida «{texto}»: usa dd/mm/aaaa o aaaa-mm-dd.",
    )


def _fecha_opcional(valor, columna):
    if (valor or "").strip() == "":
        return None
    return parsear_fecha(valor, columna)


def normalizar_dni(valor, columna="dni"):
    """7 dígitos (Excel borra el cero) u 8; otra cosa se rechaza."""
    texto = (valor or "").strip()
    if re.fullmatch(r"\d{7}", texto):
        texto = "0" + texto
    if not re.fullmatch(r"\d{8}", texto):
        raise error_uno(columna, "El DNI debe tener 7 u 8 dígitos numéricos.")
    return texto


def enmascarar_dni(dni):
    """DNI para mensajes e informes: solo los dos últimos dígitos."""
    return "******" + str(dni)[-2:]


def normalizar_numero(valor, columna):
    """Texto numérico para los serializers: admite coma decimal («1,5»)."""
    texto = (valor or "").strip().replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto:
        texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        Decimal(texto)
    except InvalidOperation:
        raise error_uno(columna, f"Valor numérico no reconocido «{valor}».")
    return texto


def _total_recurso(valor, columna):
    """Total de un recurso genérico: vacío/0 = no hay uso, negativo = error."""
    texto = normalizar_numero(valor, columna)
    if texto is None:
        return None
    numero = Decimal(texto)
    if numero < 0:
        raise error_uno(columna, "El total no puede ser negativo.")
    if numero == 0:
        return None
    return numero.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _entero(valor, columna):
    texto = (valor or "").strip().replace(".", "").replace(",", "").replace(" ", "")
    if not texto.isdigit():
        raise error_uno(columna, f"Número entero no reconocido «{valor}».")
    return int(texto)


def _opcion(valor):
    texto = (valor or "").strip().upper()
    return texto or None


# ---------------------------------------------------------------------- #
# Resolución de catálogos (nunca se crean; error con sugerencia)
# ---------------------------------------------------------------------- #
def _sugerencia(valor, disponibles):
    cercanos = difflib.get_close_matches(valor, disponibles, n=3, cutoff=0.6)
    if cercanos:
        return f" ¿Quizá quiso decir: {', '.join(cercanos)}?"
    if disponibles:
        return f" Disponibles: {', '.join(disponibles[:5])}"
    return ""


def _nombres_disponibles(consulta):
    return list(consulta.order_by("nombre").values_list("nombre", flat=True).distinct())


def _resolver_comunidad(valor):
    texto = (valor or "").strip()
    if not texto:
        raise error_uno("comunidad", "La comunidad es obligatoria.")
    encontradas = list(Comunidad.objects.filter(nombre__iexact=texto))
    if not encontradas:
        disponibles = _nombres_disponibles(Comunidad.objects.filter(activo=True))
        raise error_uno(
            "comunidad",
            f"No existe la comunidad «{texto}»." + _sugerencia(texto, disponibles),
        )
    if len(encontradas) > 1:
        raise error_uno(
            "comunidad",
            f"La comunidad «{texto}» está registrada en {len(encontradas)} "
            "distritos: no se cuál usar.",
        )
    return encontradas[0]


def _resolver_cultivo(valor):
    texto = (valor or "").strip()
    if not texto:
        raise error_uno("cultivo", "El cultivo es obligatorio.")
    cultivo = Cultivo.objects.filter(nombre__iexact=texto, activo=True).first()
    if cultivo is None:
        if Cultivo.objects.filter(nombre__iexact=texto).exists():
            raise error_uno("cultivo", f"El cultivo «{texto}» está inactivo.")
        disponibles = _nombres_disponibles(Cultivo.objects.filter(activo=True))
        raise error_uno(
            "cultivo",
            f"No existe el cultivo «{texto}»." + _sugerencia(texto, disponibles),
        )
    return cultivo


def _resolver_variedad(valor, cultivo):
    texto = (valor or "").strip()
    if not texto:
        raise error_uno("variedad", "La variedad es obligatoria.")
    consulta = Variedad.objects.filter(cultivo=cultivo, nombre__iexact=texto)
    variedad = consulta.filter(activo=True).first()
    if variedad is None:
        if consulta.exists():
            raise error_uno("variedad", f"La variedad «{texto}» está inactiva.")
        disponibles = _nombres_disponibles(
            Variedad.objects.filter(cultivo=cultivo, activo=True)
        )
        raise error_uno(
            "variedad",
            f"No existe la variedad «{texto}» del cultivo {cultivo.nombre}."
            + _sugerencia(texto, disponibles),
        )
    return variedad


def _resolver_productor(dni, columna):
    productor = Productor.objects.filter(dni=dni).first()
    if productor is None:
        raise error_uno(
            columna,
            f"No existe productor con DNI {enmascarar_dni(dni)}.",
        )
    return productor


def _resolver_parcela(productor, valor):
    texto = (valor or "").strip()
    if not texto:
        raise error_uno(
            "referencia_parcela",
            "La referencia de la parcela es obligatoria.",
        )
    encontradas = list(
        Parcela.objects.filter(
            productor=productor, referencia_ubicacion__iexact=texto
        )
    )
    if not encontradas:
        raise error_uno(
            "referencia_parcela",
            f"El productor {enmascarar_dni(productor.dni)} no tiene parcelas "
            f"con la referencia «{texto}».",
        )
    if len(encontradas) > 1:
        raise error_uno(
            "referencia_parcela",
            f"La referencia «{texto}» es ambigua: hay {len(encontradas)} "
            "parcelas del productor con esa referencia.",
        )
    return encontradas[0]


def _errores_de(serializer):
    """Errores de un serializer DRF como lista de (columna, mensaje)."""
    errores = []
    for campo, mensajes in serializer.errors.items():
        if campo == "campania_existente":
            continue
        columna = "" if campo == "non_field_errors" else str(campo)
        for mensaje in mensajes:
            if isinstance(mensaje, dict):
                for subcampo, submensajes in mensaje.items():
                    for texto in submensajes:
                        errores.append((str(subcampo), str(texto)))
            else:
                errores.append((columna, str(mensaje)))
    return errores


def _errores_de_serializer(serializer):
    if serializer.is_valid():
        return None
    return ErroresFila(_errores_de(serializer))


def _mensaje_bd(error):
    texto = str(error).strip()
    primera = texto.splitlines()[0] if texto else "Error de base de datos."
    return primera.replace("DETAIL: ", "").strip()


def _anotar_error(resultado, numero, excepcion):
    for columna, mensaje in excepcion.errores:
        resultado.errores.append(
            {"fila": numero, "columna": columna, "mensaje": str(mensaje)}
        )


def _procesar_filas(filas, usuario, accion, recursos=None, unidades=None):
    """Una transacción por fila: el fallo de una no toca a las demás."""
    resultado = Resultado(len(filas))
    for numero, fila in filas:
        try:
            with transaction.atomic():
                creada = accion(fila, usuario, recursos, unidades)
        except ErroresFila as excepcion:
            _anotar_error(resultado, numero, excepcion)
        except DatabaseError as excepcion:
            _anotar_error(
                resultado, numero, ErroresFila([("", _mensaje_bd(excepcion))])
            )
        else:
            if creada:
                resultado.creadas += 1
            else:
                resultado.omitidas += 1
    return resultado


# ---------------------------------------------------------------------- #
# Importación por tipo
# ---------------------------------------------------------------------- #
def importar_productores(filas, usuario):
    """Filas de productores: crea los que falten; los existentes se omiten."""
    return _procesar_filas(filas, usuario, _crear_productor)


def importar_parcelas(filas, usuario):
    """Filas de parcelas: clave productor+referencia; se crea si falta."""
    return _procesar_filas(filas, usuario, _crear_parcela)


def importar_campanias(filas, usuario):
    """Filas de campañas con su producción y los 4 totales de recursos."""
    recursos = _recursos_genericos()
    unidades = _unidades_base()
    return _procesar_filas(filas, usuario, _crear_campania, recursos, unidades)


def _recursos_genericos():
    recursos = {}
    faltan = []
    for clave, nombre in RECURSOS_GENERICOS.items():
        recurso = Recurso.objects.filter(nombre=nombre).first()
        if recurso is None:
            faltan.append(nombre)
        else:
            recursos[clave] = recurso
    if faltan:
        raise ErrorArchivo(
            "Faltan los recursos genéricos de la importación: "
            f"{', '.join(faltan)} (ejecuta las migraciones: catalogos.0003)."
        )
    return recursos


def _unidades_base():
    unidades = {}
    for tipo in TIPOS_UNIDAD_BASE:
        unidad = Unidad.objects.filter(tipo=tipo, es_base=True).first()
        if unidad is None:
            raise ErrorArchivo(
                f"No existe la unidad base de tipo {tipo}: ejecuta las migraciones."
            )
        unidades[tipo] = unidad
    return unidades


def _crear_productor(fila, usuario, _recursos, _unidades):
    dni = normalizar_dni(fila.get("dni"))
    if Productor.objects.filter(dni=dni).exists():
        return False
    nombres = (fila.get("nombres") or "").strip()
    if not nombres:
        raise error_uno("nombres", "El nombre es obligatorio.")
    apellidos = (fila.get("apellidos") or "").strip()
    if not apellidos:
        raise error_uno("apellidos", "El apellido es obligatorio.")
    datos = {
        "nombres": nombres,
        "apellidos": apellidos,
        "dni": dni,
        "telefono": (fila.get("telefono") or "").strip(),
        "comunidad": _resolver_comunidad(fila.get("comunidad")).pk,
        "referencia_ubicacion": (fila.get("referencia_ubicacion") or "").strip(),
    }
    fecha = _fecha_opcional(
        fila.get("fecha_incorporacion"), "fecha_incorporacion"
    )
    if fecha is not None:
        datos["fecha_incorporacion"] = fecha.isoformat()
    serializer = ProductorEscrituraSerializer(data=datos)
    fallo = _errores_de_serializer(serializer)
    if fallo is not None:
        raise fallo
    serializer.save(creado_por=usuario)
    return True


def _crear_parcela(fila, usuario, _recursos, _unidades):
    dni = normalizar_dni(fila.get("dni_productor"), "dni_productor")
    productor = _resolver_productor(dni, "dni_productor")
    referencia = (fila.get("referencia_ubicacion") or "").strip()
    if not referencia:
        raise error_uno(
            "referencia_ubicacion",
            "La referencia de ubicación es obligatoria: es la clave para "
            "no duplicar parcelas.",
        )
    consulta = Parcela.objects.filter(
        productor=productor, referencia_ubicacion__iexact=referencia
    )
    if consulta.exists():
        return False
    superficie = normalizar_numero(fila.get("superficie_ha"), "superficie_ha")
    if superficie is None:
        raise error_uno("superficie_ha", "La superficie es obligatoria.")
    altitud = (fila.get("altitud_msnm") or "").strip()
    if not altitud:
        raise error_uno("altitud_msnm", "La altitud es obligatoria.")
    datos = {
        "productor": productor.pk,
        "comunidad": _resolver_comunidad(fila.get("comunidad")).pk,
        "referencia_ubicacion": referencia,
        "superficie_ha": superficie,
        "altitud_msnm": _entero(altitud, "altitud_msnm"),
        "latitud": normalizar_numero(fila.get("latitud"), "latitud"),
        "longitud": normalizar_numero(fila.get("longitud"), "longitud"),
        "tipo_suelo": _opcion(fila.get("tipo_suelo")),
        "pendiente": _opcion(fila.get("pendiente")),
        "disponibilidad_agua": _opcion(fila.get("disponibilidad_agua")),
        "sistema_riego": _opcion(fila.get("sistema_riego")),
    }
    serializer = ParcelaEscrituraSerializer(data=datos)
    fallo = _errores_de_serializer(serializer)
    if fallo is not None:
        raise fallo
    serializer.save(creado_por=usuario)
    return True


def _crear_campania(fila, usuario, recursos, unidades):
    dni = normalizar_dni(fila.get("dni_productor"), "dni_productor")
    productor = _resolver_productor(dni, "dni_productor")
    parcela = _resolver_parcela(productor, fila.get("referencia_parcela"))
    cultivo = _resolver_cultivo(fila.get("cultivo"))
    variedad = _resolver_variedad(fila.get("variedad"), cultivo)
    periodo = (fila.get("periodo") or "").strip()
    if not periodo:
        raise error_uno("periodo", "El período es obligatorio.")
    existente = (
        Campania.objects.filter(parcela=parcela, periodo=periodo)
        .exclude(estado=Campania.ESTADO_CANCELADA)
        .first()
    )
    if existente is not None:
        return False

    fecha_inicio = parsear_fecha(fila.get("fecha_inicio"), "fecha_inicio")
    fecha_fin = parsear_fecha(
        fila.get("fecha_fin_prevista"), "fecha_fin_prevista"
    )
    fecha_siembra = parsear_fecha(fila.get("fecha_siembra"), "fecha_siembra")
    fecha_cosecha = parsear_fecha(fila.get("fecha_cosecha"), "fecha_cosecha")
    # Espejo de fn_validar_fecha_campania: la siembra (una actividad
    # SIEMBRA en el flujo normal) tendría que caer dentro del período
    if not fecha_inicio <= fecha_siembra <= fecha_fin:
        raise error_uno(
            "fecha_siembra",
            f"La fecha de siembra debe caer dentro del período de la campaña "
            f"({fecha_inicio} a {fecha_fin}).",
        )
    if fecha_cosecha < fecha_siembra:
        raise error_uno(
            "fecha_cosecha",
            f"La fecha de cosecha no puede ser anterior a la fecha de "
            f"siembra ({fecha_siembra}).",
        )

    datos = {
        "periodo": periodo,
        "parcela": parcela.pk,
        "cultivo": cultivo.pk,
        "variedad": variedad.pk,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin_prevista": fecha_fin.isoformat(),
        "observaciones": (fila.get("observaciones") or "").strip(),
    }
    superficie = normalizar_numero(
        fila.get("superficie_sembrada_ha"), "superficie_sembrada_ha"
    )
    if superficie is not None:
        datos["superficie_sembrada_ha"] = superficie
    serializer = CampaniaEscrituraSerializer(data=datos)
    fallo = _errores_de_serializer(serializer)
    if fallo is not None:
        raise fallo
    datos_validados = serializer.validated_data

    produccion_kg = normalizar_numero(
        fila.get("produccion_kg"), "produccion_kg"
    )
    if produccion_kg is None:
        raise error_uno("produccion_kg", "La producción (kg) es obligatoria.")
    superficie_cosechada = normalizar_numero(
        fila.get("superficie_cosechada_ha"), "superficie_cosechada_ha"
    )
    if superficie_cosechada is None:
        superficie_cosechada = datos_validados["superficie_sembrada_ha"]
    totales = {
        clave: _total_recurso(fila.get(clave), clave) for clave in RECURSOS_GENERICOS
    }

    campania = Campania.objects.create(
        **datos_validados,
        fecha_siembra=fecha_siembra,
        estado=Campania.ESTADO_EN_PRODUCCION,
        origen=Campania.ORIGEN_IMPORTADA,
        creado_por=usuario,
    )

    for clave, nombre in RECURSOS_GENERICOS.items():
        cantidad = totales[clave]
        if not cantidad:
            continue
        recurso = recursos[clave]
        UsoRecurso.objects.create(
            campania=campania,
            recurso=recurso,
            fecha=fecha_siembra,
            cantidad=cantidad,
            unidad=unidades[recurso.tipo_unidad],
            cantidad_base=cantidad,
            registrado_por=usuario,
        )

    serializer_produccion = ProduccionEscrituraSerializer(
        data={
            "campania": campania.pk,
            "fecha_cosecha": fecha_cosecha.isoformat(),
            "superficie_cosechada_ha": superficie_cosechada,
            "cantidad_producida": produccion_kg,
            "unidad": unidades["MASA"].pk,
        }
    )
    fallo = _errores_de_serializer(serializer_produccion)
    if fallo is not None:
        raise fallo
    produccion = serializer_produccion.save(registrado_por=usuario)
    # fn_produccion_post pasó la campaña a COSECHADA y fn_validar_produccion
    # marcó la revisión con los umbrales del sistema
    produccion.refresh_from_db()
    campania.refresh_from_db()
    if not produccion.requiere_revision:
        campania.estado = Campania.ESTADO_CERRADA
        campania.save()
    return True
