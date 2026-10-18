"""Filas, resumen y advertencias de cada reporte (Semana 17).

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

Orden fijado por el servidor: período descendente y luego apellidos.
"""
from decimal import Decimal

from django.db.models import Count, F, Prefetch, Q
from rest_framework.exceptions import ValidationError

from campanias.models import Campania
from catalogos.models import Cultivo
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

from . import catalogo


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
        if clave == "cultivo":
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
# Punto de entrada común
# --------------------------------------------------------------------- #
def preparar(reporte, usuario, params):
    """Filas + resumen + advertencias + filtros del reporte elegido."""
    if reporte["tipo"] == "productores":
        filas, resumen, advertencias, filtros = _productores(usuario, params)
    else:
        filas, resumen, advertencias, filtros = _productivo(usuario, params)
    return {
        "filas": filas,
        "resumen": resumen,
        "advertencias": advertencias,
        "filtros": filtros,
        "filtros_texto": descripcion_filtros(filtros),
    }
