"""Filas, resumen y advertencias de cada reporte (Semanas 17 y 18).

Una sola fuente de cálculo: el reporte productivo reutiliza los
mismos filtros, el mismo resumen agrupado con rendimiento PONDERADO y
las mismas marcas (provisional, pocos datos, exclusiones por revisión)
que el panel —dashboard.consultas—, de modo que con los mismos filtros
las cifras coinciden. El reporte de productores calcula lo suyo aquí
mismo con las reglas documentadas:

- una fila por productor y campaña (sin canceladas; un productor sin
  campañas aparece con la campaña vacía; con filtros de campaña no
  aparece si no tiene campañas que cumplan);
- la ubicación es la del productor (su comunidad, distrito y
  provincia), a diferencia del panel, que usa la de la parcela;
- superficie de parcelas = parcelas ACTIVAS del productor, contado una
  sola vez por productor en el resumen (evita duplicarlo con varias
  campañas);
- estado del productor: por defecto «solo activos».

La Semana 18 agrega dos reportes más con sus propias reglas:

- actividades (RF-68): una fila por actividad, ubicación de la PARCELA,
  campañas canceladas incluidas (el estado va en la fila), por defecto
  solo activas, orden fecha descendente y luego productor, y la columna
  «responsable» omitida para roles con limita_a_asignados;
- auditoría (HU-156): un evento por fila con los mismos filtros de su
  pantalla más un rango OBLIGATORIO de hasta 366 días, evento sin
  usuario como «(sin usuario)» y el detalle reducido a un resumen sin
  valores libres (resumen_evento).

Orden fijado por el servidor: período descendente y luego apellidos
(productores y productivo); fecha descendente (actividades y auditoría).
"""
from datetime import date
from decimal import Decimal

from django.db.models import Count, F, Max, Min, Prefetch, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from auditoria.filtros import aplicar_filtros
from auditoria.models import Auditoria
from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad
from dashboard import consultas as comun
from productores.models import (
    Comunidad,
    Distrito,
    Parcela,
    Productor,
    Provincia,
)
from productores.views import filtrar_asignados
from produccion.models import Produccion
from seguimiento.models import Actividad
from usuarios.models import Usuario

from . import catalogo

# Máximo de días del rango del reporte de auditoría (HU-156): el rango
# es obligatorio para que la bitácora jamás se exporte «entera» sin
# afinar; la pantalla, en cambio, sigue sin exigirlo
DIAS_MAX_RANGO_AUDITORIA = 366


def _plural(n, singular, plural):
    return singular if n == 1 else plural


def _nombre_de(modelo, ident):
    """Nombre de un catálogo para el texto de filtros (o el id si ya no
    existe)."""
    objeto = modelo.objects.filter(pk=ident).first()
    return objeto.nombre if objeto is not None else str(ident)


def descripcion_filtros(filtros):
    """Texto de los filtros aplicados, para los archivos y el encabezado."""
    if not filtros:
        return "ninguno"
    partes = []
    for clave, valor in filtros.items():
        etiqueta = catalogo.ETIQUETAS_FILTROS.get(clave, clave)
        if isinstance(valor, date):
            valor = valor.strftime("%d/%m/%Y")
        elif clave == "cultivo":
            valor = _nombre_de(Cultivo, valor)
        elif clave == "provincia":
            valor = _nombre_de(Provincia, valor)
        elif clave == "distrito":
            valor = _nombre_de(Distrito, valor)
        elif clave == "comunidad":
            valor = _nombre_de(Comunidad, valor)
        elif clave == "estado":
            valor = dict(Campania.ESTADOS).get(valor, valor)
        elif clave == "estado_productor":
            valor = catalogo.ESTADOS_PRODUCTOR_FILTRO.get(valor, valor)
        elif clave == "tipo_actividad":
            valor = _nombre_de(TipoActividad, valor)
        elif clave == "estado_actividad":
            valor = catalogo.ESTADOS_ACTIVIDAD_FILTRO.get(valor, valor)
        elif clave == "usuario":
            objeto = Usuario.objects.filter(pk=valor).first()
            valor = objeto.username if objeto is not None else str(valor)
        elif clave == "accion":
            valor = dict(Auditoria.ACCIONES).get(valor, valor)
        partes.append(f"{etiqueta}: {valor}")
    return " · ".join(partes)


def _filtros_no_nulos(eco, **extra):
    filtros = {**eco, **extra}
    return {clave: valor for clave, valor in filtros.items() if valor is not None}


# --------------------------------------------------------------------- #
# Reporte de productores (HU-141)
# --------------------------------------------------------------------- #
def _productores(usuario, params):
    estado_campania = comun.estado_de_campania(params)
    eco = comun.filtros_eco(params)
    estado_productor = params.get("estado_productor") or Productor.ESTADO_ACTIVO
    if estado_productor not in ("ACTIVO", "INACTIVO", "TODOS"):
        raise ValidationError(
            {"estado_productor": "Use ACTIVO, INACTIVO o TODOS."}
        )
    filtros_campania = bool(
        eco["periodo"] or eco["cultivo"] or estado_campania
    )

    base = filtrar_asignados(
        Productor.objects.select_related(
            "comunidad__distrito__provincia"
        ).prefetch_related(
            Prefetch(
                "parcelas",
                queryset=Parcela.objects.prefetch_related(
                    Prefetch(
                        "campanias",
                        queryset=Campania.objects.exclude(
                            estado=Campania.ESTADO_CANCELADA
                        ).select_related("cultivo", "variedad"),
                    )
                ),
            )
        ),
        usuario,
    )
    if estado_productor != "TODOS":
        base = base.filter(estado=estado_productor)
    if eco["provincia"]:
        base = base.filter(comunidad__distrito__provincia_id=eco["provincia"])
    if eco["distrito"]:
        base = base.filter(comunidad__distrito_id=eco["distrito"])
    if eco["comunidad"]:
        base = base.filter(comunidad_id=eco["comunidad"])

    filas_crudas = []  # (periodo, apellidos, nombres, fila)
    superficie_parcelas = Decimal("0.00")
    superficie_sembrada = Decimal("0.00")
    productores_vistos = set()
    for productor in base:
        parcelas = list(productor.parcelas.all())
        activas = [pa for pa in parcelas if pa.estado == Parcela.ESTADO_ACTIVA]
        campanias = []
        for parcela in parcelas:
            for campania in parcela.campanias.all():
                if eco["periodo"] and campania.periodo != eco["periodo"]:
                    continue
                if eco["cultivo"] and campania.cultivo_id != eco["cultivo"]:
                    continue
                if estado_campania and campania.estado != estado_campania:
                    continue
                campanias.append(campania)
        if not campanias and filtros_campania:
            continue
        productores_vistos.add(productor.pk)
        superficie_p = sum(
            (parcela.superficie_ha for parcela in activas), Decimal("0.00")
        )
        superficie_parcelas += superficie_p
        comunes = {
            "codigo": productor.codigo,
            "productor": f"{productor.nombres} {productor.apellidos}",
            "estado": productor.estado,
            "provincia": productor.comunidad.distrito.provincia.nombre,
            "distrito": productor.comunidad.distrito.nombre,
            "comunidad": productor.comunidad.nombre,
            "parcelas_activas": len(activas),
            "superficie_parcelas_ha": superficie_p,
        }
        if not campanias:
            filas_crudas.append(
                (
                    None,
                    productor.apellidos,
                    productor.nombres,
                    {
                        **comunes,
                        "campania": None,
                        "cultivo": None,
                        "variedad": None,
                        "estado_campania": None,
                        "superficie_sembrada_ha": None,
                    },
                )
            )
            continue
        for campania in campanias:
            superficie_sembrada += campania.superficie_sembrada_ha
            filas_crudas.append(
                (
                    campania.periodo,
                    productor.apellidos,
                    productor.nombres,
                    {
                        **comunes,
                        "campania": campania.periodo,
                        "cultivo": campania.cultivo.nombre,
                        "variedad": campania.variedad.nombre,
                        "estado_campania": campania.estado,
                        "superficie_sembrada_ha": campania.superficie_sembrada_ha,
                    },
                )
            )

    filas = _ordenar(filas_crudas)
    resumen = {
        "productores": len(productores_vistos),
        "filas": len(filas),
        "superficie_parcelas_ha": superficie_parcelas,
        "superficie_sembrada_ha": superficie_sembrada,
    }
    filtros = _filtros_no_nulos(
        eco, estado=estado_campania, estado_productor=params.get("estado_productor")
    )
    return filas, resumen, [], filtros


# --------------------------------------------------------------------- #
# Reporte productivo (HU-142)
# --------------------------------------------------------------------- #
def _productivo(usuario, params):
    estado_campania = comun.estado_de_campania(params)
    eco = comun.filtros_eco(params)
    base = filtrar_asignados(
        Produccion.objects.all(), usuario, "campania__parcela__productor_id"
    )
    base = comun.aplicar_filtros_produccion(base, params)

    # Resumen: exactamente el mismo conjunto que el panel (excluye las
    # revisiones pendientes) y, si se pide un estado, con ese estado
    incluye = base.exclude(requiere_revision=True)
    if estado_campania:
        incluye = incluye.filter(campania__estado=estado_campania)
    por_cultivo = comun.resumen_agrupado(incluye, "cultivo")
    totales = comun.totales_de(incluye)

    pendientes = base.filter(requiere_revision=True)
    if estado_campania:
        pendientes = pendientes.filter(campania__estado=estado_campania)
    excluidas = {
        fila["clave"]: fila["total"]
        for fila in pendientes.values(clave=F("campania__cultivo_id")).annotate(
            total=Count("id")
        )
    }
    provisionales = {
        fila["clave"]: fila["total"]
        for fila in incluye.filter(
            campania__estado=Campania.ESTADO_COSECHADA
        ).values(clave=F("campania__cultivo_id")).annotate(total=Count("id"))
    }
    for fila in por_cultivo:
        kilos = fila["produccion_kg"]
        fila["toneladas"] = None if kilos is None else kilos / Decimal("1000")
        fila["excluidas_revision"] = excluidas.get(fila["clave"], 0)
        fila["provisionales"] = provisionales.get(fila["clave"], 0)

    # Detalle: campañas cosechadas y cerradas; una producción pendiente
    # se muestra marcada aunque su campaña no esté en esos estados
    if estado_campania:
        detalle = base.filter(campania__estado=estado_campania)
    else:
        detalle = base.filter(
            Q(campania__estado__in=("COSECHADA", "CERRADA"))
            | Q(requiere_revision=True)
        )
    detalle = detalle.select_related(
        "campania__parcela__productor",
        "campania__parcela__comunidad__distrito",
        "campania__cultivo",
        "campania__variedad",
    )
    filas_crudas = []
    for produccion in detalle:
        campania = produccion.campania
        productor = campania.parcela.productor
        filas_crudas.append(
            (
                campania.periodo,
                productor.apellidos,
                productor.nombres,
                {
                    "periodo": campania.periodo,
                    "cultivo": campania.cultivo.nombre,
                    "variedad": campania.variedad.nombre,
                    "codigo_productor": productor.codigo,
                    "productor": f"{productor.nombres} {productor.apellidos}",
                    "parcela": campania.parcela.codigo,
                    "distrito": campania.parcela.comunidad.distrito.nombre,
                    "fecha_cosecha": produccion.fecha_cosecha,
                    "superficie_cosechada_ha": produccion.superficie_cosechada_ha,
                    "produccion_kg": produccion.produccion_kg,
                    "rendimiento_kg_ha": produccion.rendimiento_kg_ha,
                    "estado_campania": campania.estado,
                    "requiere_revision": produccion.requiere_revision,
                },
            )
        )
    filas = _ordenar(filas_crudas)

    provisionales_total = sum(provisionales.values())
    excluidas_total = sum(excluidas.values())
    resumen = {
        "por_cultivo": por_cultivo,
        "totales": totales,
        "campanias_provisionales": provisionales_total,
        "excluidas_revision": excluidas_total,
    }
    advertencias = []
    if excluidas_total:
        advertencias.append(
            f"{excluidas_total} "
            f"{_plural(excluidas_total, 'producción espera', 'producciones esperan')} "
            f"revisión y "
            f"{_plural(excluidas_total, 'no cuenta', 'no cuentan')} "
            "en el rendimiento"
        )
    if provisionales_total:
        advertencias.append(
            f"{provisionales_total} "
            f"{_plural(provisionales_total, 'campaña sin cerrar aparece', 'campañas sin cerrar aparecen')} "
            f"como {_plural(provisionales_total, 'provisional', 'provisionales')}"
        )
    sin_datos = [fila["etiqueta"] for fila in por_cultivo if fila["pocos_datos"]]
    if sin_datos:
        advertencias.append(
            "Cultivos con menos de 3 campañas en el resumen: "
            + ", ".join(sin_datos)
            + ". Su rendimiento puede no ser representativo"
        )
    filtros = _filtros_no_nulos(eco, estado=estado_campania)
    return filas, resumen, advertencias, filtros


def _ordenar(filas_crudas):
    """Orden fijado por el servidor: apellidos primero y, sobre eso,
    período descendente (sort estable)."""
    filas_crudas.sort(key=lambda fila: (fila[1] or "", fila[2] or ""))
    filas_crudas.sort(key=lambda fila: fila[0] or "", reverse=True)
    return [fila[3] for fila in filas_crudas]


def fila_totales(resumen):
    """Fila «Totales» del resumen productivo (hoja «Resumen» y PDF)."""
    totales = resumen["totales"]
    kilos = totales["produccion_kg"]
    return {
        "etiqueta": "Totales",
        "campanias": totales["campanias"],
        "superficie_ha": totales["superficie_ha"],
        "produccion_kg": kilos,
        "toneladas": None if kilos is None else kilos / Decimal("1000"),
        "rendimiento_kg_ha": totales["rendimiento_kg_ha"],
        "provisionales": resumen["campanias_provisionales"],
        "excluidas_revision": resumen["excluidas_revision"],
        "pocos_datos": None,
    }


# --------------------------------------------------------------------- #
# Reporte de actividades (Semana 18, RF-68)
# --------------------------------------------------------------------- #
def _fecha_param(params, campo):
    """Fecha AAAA-MM-DD de la query (None si no viene; 400 si no es
    válida, con el mismo mensaje del resto del sistema)."""
    valor = params.get(campo)
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValidationError(
            {campo: "La fecha no es válida: usa el formato AAAA-MM-DD."}
        )


def _actividades(usuario, params):
    """Una fila por actividad (las anuladas solo si se piden), con la
    ubicación de la PARCELA —a diferencia del reporte de productores,
    que usa la del productor— y la campaña cancelada incluida: el
    estado de la campaña va en la fila, no filtra. Por defecto, solo
    actividades activas (HU-150..HU-154)."""
    estado_campania = comun.estado_de_campania(params)
    eco = comun.filtros_eco(params)
    estado_actividad = params.get("estado_actividad") or "ACTIVAS"
    if estado_actividad not in ("ACTIVAS", "ANULADAS", "TODAS"):
        raise ValidationError(
            {"estado_actividad": "Use ACTIVAS, ANULADAS o TODAS."}
        )
    tipo_actividad = comun.id_existente(
        params,
        "tipo_actividad",
        TipoActividad,
        "El tipo de actividad indicado no existe.",
    )
    desde = _fecha_param(params, "fecha_actividad_desde")
    hasta = _fecha_param(params, "fecha_actividad_hasta")
    if desde and hasta and desde > hasta:
        raise ValidationError(
            {
                "fecha_actividad_desde": (
                    "La fecha inicial no puede ser posterior a la final."
                )
            }
        )

    base = Actividad.objects.all()
    if eco["periodo"]:
        base = base.filter(campania__periodo=eco["periodo"])
    if eco["cultivo"]:
        base = base.filter(campania__cultivo_id=eco["cultivo"])
    if eco["provincia"]:
        base = base.filter(
            campania__parcela__comunidad__distrito__provincia_id=eco["provincia"]
        )
    if eco["distrito"]:
        base = base.filter(
            campania__parcela__comunidad__distrito_id=eco["distrito"]
        )
    if eco["comunidad"]:
        base = base.filter(campania__parcela__comunidad_id=eco["comunidad"])
    if estado_campania:
        base = base.filter(campania__estado=estado_campania)
    if tipo_actividad:
        base = base.filter(tipo_actividad_id=tipo_actividad)
    if estado_actividad == "ACTIVAS":
        base = base.filter(anulada=False)
    elif estado_actividad == "ANULADAS":
        base = base.filter(anulada=True)
    if desde:
        base = base.filter(fecha__gte=desde)
    if hasta:
        base = base.filter(fecha__lte=hasta)
    # Alcance Técnico: sus campañas son las de sus productores asignados
    base = filtrar_asignados(base, usuario, "campania__parcela__productor_id")

    agregado = base.aggregate(
        total=Count("id"),
        campanias=Count("campania", distinct=True),
        productores=Count("campania__parcela__productor", distinct=True),
        con_horas=Count("horas"),
        horas=Sum("horas"),
        fecha_min=Min("fecha"),
        fecha_max=Max("fecha"),
    )
    por_tipo = [
        {"etiqueta": fila["tipo_actividad__nombre"], "cantidad": fila["total"]}
        for fila in base.values("tipo_actividad__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo_actividad__nombre")
    ]

    unidades = dict(Actividad.UNIDADES_DENSIDAD)
    filas = []
    for actividad in base.select_related(
        "campania__parcela__productor",
        "campania__parcela__comunidad__distrito",
        "campania__cultivo",
        "tipo_actividad",
        "registrado_por",
    ):
        campania = actividad.campania
        parcela = campania.parcela
        productor = parcela.productor
        densidad = None
        if actividad.densidad_siembra is not None:
            unidad = unidades.get(actividad.densidad_unidad, "")
            densidad = f"{comun.texto(actividad.densidad_siembra)} {unidad}".strip()
        responsable = None
        if actividad.registrado_por is not None:
            responsable = (
                actividad.registrado_por.get_full_name()
                or actividad.registrado_por.username
            )
        filas.append(
            {
                "fecha": actividad.fecha,
                "productor": (
                    f"{productor.codigo} · {productor.nombres} {productor.apellidos}"
                ),
                "parcela": parcela.codigo,
                "distrito": parcela.comunidad.distrito.nombre,
                "campania": campania.periodo,
                "cultivo": campania.cultivo.nombre,
                "estado_campania": campania.estado,
                "tipo_actividad": actividad.tipo_actividad.nombre,
                "metodo": actividad.metodo or None,
                "densidad": densidad,
                "horas": actividad.horas,
                "estado_actividad": "Anulada" if actividad.anulada else "Activa",
                "responsable": responsable,
            }
        )
    # Orden fijado por el servidor: fecha descendente y, sobre eso,
    # productor ascendente (sort estable)
    filas.sort(key=lambda fila: fila["productor"] or "")
    filas.sort(key=lambda fila: fila["fecha"], reverse=True)

    resumen = {
        "total": agregado["total"],
        "por_tipo": por_tipo,
        "horas_totales": agregado["horas"],
        "actividades_con_horas": agregado["con_horas"],
        "campanias_distintas": agregado["campanias"],
        "productores_distintos": agregado["productores"],
        "fecha_min": agregado["fecha_min"],
        "fecha_max": agregado["fecha_max"],
    }
    filtros = _filtros_no_nulos(
        eco,
        estado=estado_campania,
        tipo_actividad=params.get("tipo_actividad"),
        fecha_actividad_desde=desde,
        fecha_actividad_hasta=hasta,
        estado_actividad=params.get("estado_actividad"),
    )
    return filas, resumen, [], filtros


# --------------------------------------------------------------------- #
# Reporte de auditoría (Semana 18, HU-155/HU-156)
# --------------------------------------------------------------------- #
# Claves del detalle cuyo VALOR se puede mostrar en el reporte: son
# identificadores, contadores y estados, nunca textos libres. El resto
# de claves aparece solo con su nombre; «resumen» es el centinela del
# barrido de alertas y no se muestra
_DETALLE_SEGURO = frozenset(
    {
        "tipo",
        "formato",
        "filas",
        "creadas",
        "cerradas",
        "estado",
        "operacion",
        "clave",
        "username",
        "agregados",
        "quitados",
        "creados",
        "actualizados",
        "omitidos_manual",
        "omitidos_api",
        "sin_datos",
        "descartados",
    }
)
_DETALLE_OMITIDO = frozenset({"resumen"})


def _texto_detalle(valor):
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, dict):
        # Un detalle anidado se reduce a sus claves (nunca sus valores)
        return ", ".join(sorted(valor)) or "—"
    if isinstance(valor, list):
        return ", ".join(str(elemento) for elemento in valor) or "—"
    return str(valor)


def resumen_evento(detalle):
    """Detalle de un evento reducido a un resumen SIN valores libres.

    La bitácora nunca guarda estados antes/después; solo claves
    puntuales. Estas se muestran con su valor (tipo/formato/filas de
    EXPORTAR, contadores de alertas, estado de campaña, agregados y
    quitados de permisos como NOMBRES de códigos…); cualquier otra
    clave —motivo, nota— aparece únicamente con su nombre. Detalle
    vacío o nulo → None (la celda se pinta «—»).
    """
    if not detalle or not isinstance(detalle, dict):
        return None
    partes = [
        f"{clave}: {_texto_detalle(detalle[clave])}"
        for clave in sorted(detalle)
        if clave in _DETALLE_SEGURO and detalle[clave] is not None
    ]
    nombres = [
        clave
        for clave in sorted(detalle)
        if clave not in _DETALLE_SEGURO
        and clave not in _DETALLE_OMITIDO
        and detalle[clave] is not None
    ]
    if nombres:
        partes.append("Campos: " + ", ".join(nombres))
    return " · ".join(partes) if partes else None


def _rango_auditoria(params):
    """Rango obligatorio del reporte de auditoría (HU-156): los dos
    días, formato AAAA-MM-DD, inicial ≤ final, no futuras y máximo 366
    días — la bitácora jamás se exporta «entera» sin afinar."""
    faltantes = [
        campo
        for campo in ("fecha_desde", "fecha_hasta")
        if not params.get(campo)
    ]
    if faltantes:
        raise ValidationError(
            {campo: "El rango de fechas es obligatorio." for campo in faltantes}
        )
    desde = _fecha_param(params, "fecha_desde")
    hasta = _fecha_param(params, "fecha_hasta")
    if desde > hasta:
        raise ValidationError(
            {"fecha_desde": "La fecha inicial no puede ser posterior a la final."}
        )
    if hasta > timezone.localdate():
        raise ValidationError(
            {"fecha_hasta": "La fecha final no puede ser futura."}
        )
    if (hasta - desde).days + 1 > DIAS_MAX_RANGO_AUDITORIA:
        raise ValidationError(
            {
                "fecha_hasta": (
                    f"El rango admite como máximo {DIAS_MAX_RANGO_AUDITORIA} días."
                )
            }
        )
    return desde, hasta


def _auditoria(usuario, params):
    """Un evento por fila, con los MISMOS filtros que la pantalla
    (auditoria.filtros) más el rango obligatorio. Orden fecha
    descendente; evento sin usuario → «(sin usuario)»."""
    desde, hasta = _rango_auditoria(params)
    base = aplicar_filtros(
        Auditoria.objects.select_related("usuario"), params
    ).order_by("-fecha", "-id")

    accion_etiquetas = dict(Auditoria.ACCIONES)
    filas = [
        {
            # Hora de Lima en todas las capas (la tabla guarda UTC)
            "fecha": timezone.localtime(evento.fecha),
            "usuario": (
                evento.usuario.username
                if evento.usuario_id is not None
                else "(sin usuario)"
            ),
            "accion": accion_etiquetas.get(evento.accion, evento.accion),
            "modulo": evento.modulo,
            "tabla": evento.tabla,
            "registro_id": evento.registro_id,
            "ip": evento.ip,
            "detalle": resumen_evento(evento.detalle),
        }
        for evento in base
    ]

    agregado = base.aggregate(
        total=Count("id"),
        sin_usuario=Count("id", filter=Q(usuario__isnull=True)),
        fecha_min=Min("fecha"),
        fecha_max=Max("fecha"),
    )
    fecha_min = agregado["fecha_min"]
    fecha_max = agregado["fecha_max"]
    por_accion = [
        {
            "etiqueta": accion_etiquetas.get(fila["accion"], fila["accion"]),
            "cantidad": fila["total"],
        }
        for fila in base.values("accion")
        .annotate(total=Count("id"))
        .order_by("accion")
    ]
    por_modulo = [
        {"etiqueta": fila["modulo"], "cantidad": fila["total"]}
        for fila in base.values("modulo")
        .annotate(total=Count("id"))
        .order_by("modulo")
    ]
    resumen = {
        "total": agregado["total"],
        "por_accion": por_accion,
        "por_modulo": por_modulo,
        "sin_usuario": agregado["sin_usuario"],
        "fecha_min": (
            timezone.localtime(fecha_min) if fecha_min is not None else None
        ),
        "fecha_max": (
            timezone.localtime(fecha_max) if fecha_max is not None else None
        ),
    }
    filtros = _filtros_no_nulos(
        {},
        fecha_desde=desde,
        fecha_hasta=hasta,
        usuario=params.get("usuario"),
        accion=params.get("accion"),
        modulo=params.get("modulo"),
        tabla=params.get("tabla"),
        registro=params.get("registro"),
        ip=params.get("ip"),
    )
    return filas, resumen, [], filtros


# --------------------------------------------------------------------- #
# Punto de entrada común
# --------------------------------------------------------------------- #
def preparar(reporte, usuario, params):
    """Filas + resumen + advertencias + filtros + columnas efectivas del
    reporte elegido (las columnas se recalculan aquí: «responsable» se
    omite para los roles con limita_a_asignados)."""
    preparadores = {
        "productores": _productores,
        "productivo": _productivo,
        "actividades": _actividades,
        "auditoria": _auditoria,
    }
    filas, resumen, advertencias, filtros = preparadores[reporte["tipo"]](
        usuario, params
    )
    return {
        "filas": filas,
        "resumen": resumen,
        "advertencias": advertencias,
        "filtros": filtros,
        "filtros_texto": descripcion_filtros(filtros),
        "columnas": catalogo.columnas_de(reporte, usuario),
    }
