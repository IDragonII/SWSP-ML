"""API del panel de indicadores (Semana 16, HU-133..HU-140).

App de solo lectura SIN modelos ni migraciones propias: cuatro lecturas
bajo el permiso dashboard.ver (sembrado en la Semana 2) y SIN escritura
—POST/PUT/DELETE responden 405— con los mismos 401/403 que el resto de
la API y el portón de cambio obligatorio de contraseña.

- /dashboard/resumen/       tarjetas: productores, superficie sembrada,
                            campañas por estado, aptas para entrenar,
                            revisiones pendientes y alertas.
- /dashboard/campanias-estado/  campañas agrupadas por estado, con
                            ?periodo= opcional.
- /dashboard/produccion/    producción agrupada por cultivo o distrito
                            con rendimiento PONDERADO y los mismos
                            filtros que el listado de producciones.
- /dashboard/filtros/       períodos, cultivos y ubicación disponibles,
                            dentro del alcance del usuario.

Cada agregado aplica el alcance del Técnico con filtrar_asignados
(Semana 4), igual que los listados. Los números sin datos son null —nunca
cero falso—; los decimales salen como texto con las unidades en las
etiquetas (convención global de la API). La fecha de respuesta
(generado_en) es la hora de Lima.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from alertas.models import Alerta
from campanias.models import Campania
from catalogos.models import Cultivo
from productores.models import Comunidad, Distrito, Productor, Provincia
from productores.views import PermisosPorAccion, _id_numerico, filtrar_asignados
from produccion.models import Produccion

# Decimales de las cifras agregadas del panel (ha y kg)
_PRECISION = Decimal("0.01")

# Mínimo de campañas de una fila para considerar su promedio representativo
_MINIMO_CAMPANIAS_FILA = 3


def ahora_lima():
    """Hora actual en la zona del proyecto (America/Lima) con huso."""
    return timezone.localtime()


def _texto(valor):
    """Cifra decimal a texto con 2 decimales (None se queda en null)."""
    if valor is None:
        return None
    return str(Decimal(valor).quantize(_PRECISION, rounding=ROUND_HALF_UP))


def _cuentas_por_estado(campanias):
    """Conteo de campañas por cada uno de los 5 estados, con ceros."""
    cuentas = {estado: 0 for estado, _ in Campania.ESTADOS}
    for fila in campanias.values("estado").annotate(total=Count("id")):
        cuentas[fila["estado"]] = fila["total"]
    return cuentas


def _id_existente(params, campo, modelo, mensaje):
    """Id numérico que además existe en la tabla (si viene en la URL)."""
    if not params.get(campo):
        return None
    ident = _id_numerico(params[campo], campo)
    if not modelo.objects.filter(pk=ident).exists():
        raise ValidationError({campo: mensaje})
    return ident


class PermisosDashboard(PermisosPorAccion):
    """dashboard.ver (sembrado en la Semana 2) para las cuatro lecturas;
    no hay acciones de escritura que mapear."""

    permiso_requerido = "dashboard.ver"
    PERMISOS = {
        "resumen": "dashboard.ver",
        "campanias_estado": "dashboard.ver",
        "produccion": "dashboard.ver",
        "filtros": "dashboard.ver",
    }


class DashboardViewSet(PermisosDashboard, viewsets.GenericViewSet):
    """Panel de indicadores de solo lectura (HU-133..HU-140).

    Sin queryset ni serializer: cada acción arma su respuesta con
    agregados de las tablas de negocio, alcance del usuario y ceros
    explícitos donde la interfaz necesita serie completa.
    """

    @action(detail=False, methods=("get",), url_path="resumen")
    def resumen(self, request):
        """Tarjetas del panel (HU-133 y HU-134).

        productores: activos, inactivos y con al menos una campaña en
        un estado activo. superficie_sembrada_ha: suma de las campañas
        activas (planificadas, en producción y cosechadas) del alcance.
        aptas_entrenar: campañas CERRADA cuya producción mantiene
        incluir_en_entrenamiento —las mismas condiciones del WHERE de
        vw_dataset_entrenamiento (DB_sql/02_reglas_y_vista.sql:463-464).
        revisiones_pendientes: producciones con la marca de revisión.
        alertas: total y pendientes del alcance (la insignia).
        """
        usuario = request.user
        productores = filtrar_asignados(Productor.objects.all(), usuario)
        campanias = filtrar_asignados(
            Campania.objects.all(), usuario, "parcela__productor_id"
        )
        producciones = filtrar_asignados(
            Produccion.objects.all(), usuario, "campania__parcela__productor_id"
        )
        alertas = filtrar_asignados(
            Alerta.objects.all(), usuario, "productor_id"
        )
        superficie = campanias.filter(
            estado__in=Campania.ESTADOS_ACTIVOS
        ).aggregate(total=Sum("superficie_sembrada_ha"))["total"]
        return Response(
            {
                "generado_en": ahora_lima().isoformat(timespec="seconds"),
                "productores": {
                    "activos": productores.filter(
                        estado=Productor.ESTADO_ACTIVO
                    ).count(),
                    "inactivos": productores.filter(
                        estado=Productor.ESTADO_INACTIVO
                    ).count(),
                    "con_campania_activa": productores.filter(
                        parcelas__campanias__estado__in=Campania.ESTADOS_ACTIVOS
                    )
                    .distinct()
                    .count(),
                },
                "superficie_sembrada_ha": _texto(superficie),
                "campanias_por_estado": _cuentas_por_estado(campanias),
                "aptas_entrenar": campanias.filter(
                    estado=Campania.ESTADO_CERRADA,
                    produccion__incluir_en_entrenamiento=True,
                ).count(),
                "revisiones_pendientes": producciones.filter(
                    requiere_revision=True
                ).count(),
                "alertas": {
                    "total": alertas.count(),
                    "pendientes": alertas.filter(atendida=False).count(),
                },
            }
        )

    @action(detail=False, methods=("get",), url_path="campanias-estado")
    def campanias_estado(self, request):
        """Campañas agrupadas por estado (HU-135), con ?periodo= opcional.

        Siempre devuelve los 5 estados (0 cuando no hay) para poder
        pintar la serie completa; con un período inexistente la serie
        sale a cero —mismo criterio que los listados—.
        """
        periodo = request.query_params.get("periodo") or None
        campanias = filtrar_asignados(
            Campania.objects.all(), request.user, "parcela__productor_id"
        )
        if periodo:
            campanias = campanias.filter(periodo=periodo)
        return Response(
            {"periodo": periodo, "estados": _cuentas_por_estado(campanias)}
        )

    @action(detail=False, methods=("get",), url_path="produccion")
    def produccion(self, request):
        """Producción agrupada (HU-136), con los filtros del listado.

        ?agrupar=cultivo|distrito (por defecto cultivo; otro valor → 400)
        y los filtros periodo/cultivo/provincia/distrito/comunidad, con
        la misma lectura numérica que el listado de producciones (un id
        no numérico → 400).

        Excluye las producciones con requiere_revision (dato aún no
        validado) y agrupa por campaña (1:1 con producción). Por fila:
        rendimiento_kg_ha PONDERADO (kg ÷ superficie cosechada, el que
        manda en el cierre) junto a rendimiento_promedio_kg_ha (media
        simple, solo comparación), provisional si queda alguna campaña
        sin cerrar y pocos_datos con menos de 3 campañas. Los totales
        sin filas quedan en null —no en cero—.
        """
        params = request.query_params
        agrupar = params.get("agrupar", "cultivo")
        if agrupar not in ("cultivo", "distrito"):
            raise ValidationError({"agrupar": "Use cultivo o distrito."})
        base = filtrar_asignados(
            Produccion.objects.exclude(requiere_revision=True),
            request.user,
            "campania__parcela__productor_id",
        )
        if params.get("periodo"):
            base = base.filter(campania__periodo=params["periodo"])
        if params.get("cultivo"):
            base = base.filter(
                campania__cultivo_id=_id_numerico(params["cultivo"], "cultivo")
            )
        if params.get("provincia"):
            base = base.filter(
                campania__parcela__comunidad__distrito__provincia_id=_id_numerico(
                    params["provincia"], "provincia"
                )
            )
        if params.get("distrito"):
            base = base.filter(
                campania__parcela__comunidad__distrito_id=_id_numerico(
                    params["distrito"], "distrito"
                )
            )
        if params.get("comunidad"):
            base = base.filter(
                campania__parcela__comunidad_id=_id_numerico(
                    params["comunidad"], "comunidad"
                )
            )
        if agrupar == "cultivo":
            grupos = base.values(
                clave=F("campania__cultivo_id"),
                etiqueta=F("campania__cultivo__nombre"),
            )
        else:
            grupos = base.values(
                clave=F("campania__parcela__comunidad__distrito_id"),
                etiqueta=F("campania__parcela__comunidad__distrito__nombre"),
            )
        filas = []
        for fila in (
            grupos.annotate(
                campanias=Count("id"),
                superficie_ha=Sum("superficie_cosechada_ha"),
                produccion_kg=Sum("produccion_kg"),
                rendimiento_promedio=Avg("rendimiento_kg_ha"),
                sin_cerrar=Count(
                    "id", filter=Q(campania__estado=Campania.ESTADO_COSECHADA)
                ),
            )
            .order_by("-produccion_kg", "clave")
        ):
            superficie = fila["superficie_ha"]
            kilos = fila["produccion_kg"]
            filas.append(
                {
                    "clave": fila["clave"],
                    "etiqueta": fila["etiqueta"],
                    "campanias": fila["campanias"],
                    "superficie_ha": _texto(superficie),
                    "produccion_kg": _texto(kilos),
                    "rendimiento_kg_ha": _texto(
                        None if not superficie else kilos / superficie
                    ),
                    "rendimiento_promedio_kg_ha": _texto(
                        fila["rendimiento_promedio"]
                    ),
                    "provisional": fila["sin_cerrar"] > 0,
                    "pocos_datos": fila["campanias"] < _MINIMO_CAMPANIAS_FILA,
                }
            )
        totales = base.aggregate(
            campanias=Count("id"),
            superficie_ha=Sum("superficie_cosechada_ha"),
            produccion_kg=Sum("produccion_kg"),
        )
        superficie_total = totales["superficie_ha"]
        return Response(
            {
                "agrupar": agrupar,
                "filtros": {
                    "periodo": params.get("periodo") or None,
                    "cultivo": (
                        _id_numerico(params["cultivo"], "cultivo")
                        if params.get("cultivo")
                        else None
                    ),
                    "provincia": (
                        _id_numerico(params["provincia"], "provincia")
                        if params.get("provincia")
                        else None
                    ),
                    "distrito": (
                        _id_numerico(params["distrito"], "distrito")
                        if params.get("distrito")
                        else None
                    ),
                    "comunidad": (
                        _id_numerico(params["comunidad"], "comunidad")
                        if params.get("comunidad")
                        else None
                    ),
                },
                "totales": {
                    "campanias": totales["campanias"],
                    "superficie_ha": _texto(superficie_total),
                    "produccion_kg": _texto(totales["produccion_kg"]),
                    "rendimiento_kg_ha": _texto(
                        None
                        if not superficie_total
                        else totales["produccion_kg"] / superficie_total
                    ),
                },
                "filas": filas,
            }
        )

    @action(detail=False, methods=("get",), url_path="filtros")
    def filtros(self, request):
        """Opciones de los filtros del panel (HU-137), del alcance.

        Períodos y cultivos: los que tengan campañas del alcance. La
        ubicación: catálogo activo para los roles sin límite y las
        comunidades/distritos/provincias de SUS productores para el
        Técnico. ?provincia= y ?distrito= estrechan los niveles
        inferiores; un id no numérico o inexistente → 400.
        """
        params = request.query_params
        provincia_id = _id_existente(
            params, "provincia", Provincia, "La provincia indicada no existe."
        )
        distrito_id = _id_existente(
            params, "distrito", Distrito, "El distrito indicado no existe."
        )
        usuario = request.user
        campanias = filtrar_asignados(
            Campania.objects.all(), usuario, "parcela__productor_id"
        )
        productores = filtrar_asignados(Productor.objects.all(), usuario)
        rol = getattr(usuario, "rol", None)
        if rol is not None and rol.limita_a_asignados:
            comunidades = Comunidad.objects.filter(productores__in=productores)
        else:
            comunidades = Comunidad.objects.filter(activo=True)
        if provincia_id is not None:
            comunidades = comunidades.filter(distrito__provincia_id=provincia_id)
        if distrito_id is not None:
            comunidades = comunidades.filter(distrito_id=distrito_id)
        comunidades = comunidades.distinct().order_by("nombre")
        distritos = Distrito.objects.filter(
            pk__in=comunidades.values("distrito_id")
        ).order_by("nombre")
        if provincia_id is not None:
            distritos = distritos.filter(provincia_id=provincia_id)
        provincias = Provincia.objects.filter(
            pk__in=distritos.values("provincia_id")
        ).order_by("nombre")
        return Response(
            {
                "periodos": sorted(
                    set(campanias.values_list("periodo", flat=True))
                ),
                "cultivos": [
                    {"id": cultivo.id, "nombre": cultivo.nombre}
                    for cultivo in Cultivo.objects.filter(
                        pk__in=campanias.values("cultivo_id")
                    ).order_by("nombre")
                ],
                "provincias": [
                    {"id": provincia.id, "nombre": provincia.nombre}
                    for provincia in provincias
                ],
                "distritos": [
                    {
                        "id": distrito.id,
                        "nombre": distrito.nombre,
                        "provincia": distrito.provincia_id,
                    }
                    for distrito in distritos
                ],
                "comunidades": [
                    {
                        "id": comunidad.id,
                        "nombre": comunidad.nombre,
                        "distrito": comunidad.distrito_id,
                    }
                    for comunidad in comunidades
                ],
            }
        )
