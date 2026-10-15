"""Serializadores de la API de seguimiento (Semanas 7, 9 y 10).

Semana 7 — actividades: la lista muestra fecha, tipo, campaña (período,
cultivo, parcela y productor), método, horas, costo y estado de anulación;
la ficha añade densidad, observaciones, motivo de anulación, registrado
por y fechas de trazabilidad. registrado_por lo pone el servidor y se
OCULTA a los roles con limita_a_asignados (decisión de la Semana 7). El de
escritura no acepta anulada ni registrado por, valida ANTES que la base
(campaña que admite registros, tipo activo, fecha dentro del período y no
futura — hora de Lima, pregunta H —, densidad solo en siembras y par
obligatorio, horas y costo no negativos) y bloquea campaña y tipo al
editar (anula y registra otra).

Semana 9 — usos de recursos: la lista muestra fecha, recurso (nombre,
categoría y tipo de unidad), cantidad con su unidad, cantidad base,
campaña, actividad, costo y estado; la ficha añade observaciones, motivo
de anulación y trazabilidad. cantidad_base, anulada, motivo_anulacion y
registrado_por no se aceptan del cliente: el primero lo calcula
fn_uso_recurso en la base (cantidad × factor de la unidad) y la vista
relee la fila antes de responder. El de escritura valida ANTES que la
base (campaña que admite registros, recurso y unidad activos, unidad del
mismo tipo que el recurso, cantidad > 0, costo ≥ 0, fecha dentro del
período y no futura, actividad de la misma campaña con la misma fecha) y
bloquea campaña al editar (anula y registra otro uso).

Semana 10 — registro de clima: una fila por parcela y día, SIN anulación
ni borrado (un error se corrige editando). Al menos una medida o la
helada marcada; mínima ≤ máxima y el promedio entre ambas; fechas entre
2000 y hoy (hora de Lima). El servidor calcula lo que el cliente no puede
forzar: temp_prom como punto medio cuando vienen mínima y máxima (marca
temp_prom_calculado en la ficha), helada derivada del umbral del sistema
umbral_helada_c cuando hay mínima (marca helada_calculada) y fuente
(MANUAL siempre en la API: editar un registro de la API lo convierte en
MANUAL y exige confirmar_reemplazo=true, decisión de la Semana 10).
registrado_por lo pone la vista y se OCULTA a los roles con
limita_a_asignados (igual que actividades y usos de recursos).
"""
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from rest_framework import serializers

from catalogos.models import Recurso, TipoActividad, Unidad
from campanias.models import Campania
from productores.models import AsignacionTecnico, Parcela
from sistema.models import ParametroSistema

from .models import Actividad, Clima, UsoRecurso

_UNIDADES_DENSIDAD = ("KG_HA", "PLANTAS_M2")


def _mini_tipo(obj):
    return {
        "id": obj.tipo_actividad_id,
        "codigo": obj.tipo_actividad.codigo,
        "nombre": obj.tipo_actividad.nombre,
    }


def _mini_campania(obj):
    """Campaña anidada con su estado y fecha de siembra ACTUALIZADOS (tras
    guardar, la vista hace refresh_from_db: los triggers pudieron cambiarlos)."""
    campania = obj.campania
    return {
        "id": campania.id,
        "periodo": campania.periodo,
        "estado": campania.estado,
        "fecha_siembra": campania.fecha_siembra,
        "cultivo": {"id": campania.cultivo_id, "nombre": campania.cultivo.nombre},
        "parcela": {
            "id": campania.parcela_id,
            "codigo": campania.parcela.codigo,
            "productor": {
                "id": campania.parcela.productor_id,
                "nombre_completo": (
                    f"{campania.parcela.productor.apellidos}, "
                    f"{campania.parcela.productor.nombres}"
                ),
            },
        },
    }


def _mini_actividad(obj):
    if obj.actividad_id is None:
        return None
    actividad = obj.actividad
    return {
        "id": actividad.id,
        "fecha": actividad.fecha.isoformat(),
        "tipo": {
            "id": actividad.tipo_actividad_id,
            "nombre": actividad.tipo_actividad.nombre,
        },
    }


def _mini_recurso(obj):
    return {
        "id": obj.recurso_id,
        "nombre": obj.recurso.nombre,
        "categoria": obj.recurso.categoria,
        "tipo_unidad": obj.recurso.tipo_unidad,
    }


def _mini_unidad(obj):
    return {
        "id": obj.unidad_id,
        "nombre": obj.unidad.nombre,
        "simbolo": obj.unidad.simbolo,
    }


class ActividadListaSerializer(serializers.ModelSerializer):
    """Fila del listado (HU-47): fecha, tipo, campaña con productor y
    parcela, método, horas, costo y estado de anulación."""

    tipo_actividad = serializers.SerializerMethodField()
    campania = serializers.SerializerMethodField()

    class Meta:
        model = Actividad
        fields = (
            "id",
            "fecha",
            "tipo_actividad",
            "campania",
            "metodo",
            "horas",
            "costo",
            "anulada",
        )

    def get_tipo_actividad(self, obj):
        return _mini_tipo(obj)

    def get_campania(self, obj):
        return _mini_campania(obj)


class ActividadDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa (HU-48). registrado_por se omite de la respuesta para
    los roles con limita_a_asignados (decisión de la Semana 7)."""

    tipo_actividad = serializers.SerializerMethodField()
    campania = serializers.SerializerMethodField()
    registrado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Actividad
        fields = (
            "id",
            "fecha",
            "tipo_actividad",
            "campania",
            "metodo",
            "densidad_siembra",
            "densidad_unidad",
            "horas",
            "costo",
            "observaciones",
            "anulada",
            "motivo_anulacion",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "anulada",
            "motivo_anulacion",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )

    def get_tipo_actividad(self, obj):
        return _mini_tipo(obj)

    def get_campania(self, obj):
        return _mini_campania(obj)

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            datos.pop("registrado_por", None)
        return datos


class ActividadEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición. anulada y registrado_por no están en fields: el
    cliente no puede forzarlos (se anulan con la acción anular/)."""

    campania = serializers.PrimaryKeyRelatedField(
        queryset=Campania.objects.select_related(
            "parcela", "parcela__productor", "cultivo"
        ),
        error_messages={
            "required": "La campaña es obligatoria.",
            "does_not_exist": "La campaña indicada no existe.",
        },
    )
    tipo_actividad = serializers.PrimaryKeyRelatedField(
        queryset=TipoActividad.objects.all(),
        error_messages={
            "required": "El tipo de actividad es obligatorio.",
            "does_not_exist": "El tipo de actividad indicado no existe.",
        },
    )
    fecha = serializers.DateField(
        error_messages={
            "required": "La fecha es obligatoria.",
            "invalid": "La fecha no es válida: usa el formato AAAA-MM-DD.",
        }
    )
    metodo = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    densidad_siembra = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La densidad de siembra debe ser un número.",
            "max_digits": (
                "La densidad admite como máximo 8 dígitos enteros y 2 decimales."
            ),
            "max_decimal_places": "La densidad admite como máximo 2 decimales.",
        },
    )
    densidad_unidad = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    horas = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "Las horas deben ser un número.",
            "max_digits": "Las horas admiten como máximo 3 dígitos enteros y 1 decimal.",
            "max_decimal_places": "Las horas admiten como máximo 1 decimal.",
        },
    )
    costo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "El costo debe ser un número.",
            "max_digits": "El costo admite como máximo 8 dígitos enteros y 2 decimales.",
            "max_decimal_places": "El costo admite como máximo 2 decimales.",
        },
    )
    observaciones = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )

    class Meta:
        model = Actividad
        fields = (
            "campania",
            "tipo_actividad",
            "fecha",
            "metodo",
            "densidad_siembra",
            "densidad_unidad",
            "horas",
            "costo",
            "observaciones",
        )

    # ------------------------------------------------------------------ #
    # validaciones por campo
    # ------------------------------------------------------------------ #
    def validate_campania(self, valor):
        if valor.estado not in Campania.ESTADOS_ACTIVOS:
            raise serializers.ValidationError(
                f"La campaña está {valor.estado} y no admite nuevos registros."
            )
        # El técnico solo puede registrar en campañas de SUS productores
        # asignados: si no le corresponde, el mismo mensaje que si no
        # existiera (igual que parcelas y productores en la Semana 6).
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            asignado = AsignacionTecnico.objects.filter(
                tecnico=request.user,
                productor=valor.parcela.productor,
                activo=True,
            ).exists()
            if not asignado:
                raise serializers.ValidationError("La campaña indicada no existe.")
        return valor

    def validate_tipo_actividad(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "El tipo de actividad indicado no existe o está inactivo."
            )
        return valor

    def validate_fecha(self, valor):
        # Pregunta H (pendiente del responsable): se rechazan fechas
        # futuras según la hora local de Lima (decisión de la Semana 7)
        hoy = datetime.now(ZoneInfo("America/Lima")).date()
        if valor > hoy:
            raise serializers.ValidationError("La fecha no puede ser futura.")
        return valor

    def validate_densidad_siembra(self, valor):
        if valor is not None and valor <= 0:
            raise serializers.ValidationError(
                "La densidad de siembra debe ser mayor que 0."
            )
        return valor

    def validate_densidad_unidad(self, valor):
        if valor == "":
            return None
        if valor is not None and valor not in _UNIDADES_DENSIDAD:
            raise serializers.ValidationError(
                "La unidad de densidad debe ser KG_HA o PLANTAS_M2."
            )
        return valor

    def validate_horas(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("Las horas no pueden ser negativas.")
        return valor

    def validate_costo(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return valor

    # ------------------------------------------------------------------ #
    # validaciones cruzadas (campos protegidos, densidad y período)
    # ------------------------------------------------------------------ #
    def validate(self, attrs):
        instancia = self.instance

        # Campaña y tipo no cambian al editar: anula y registra otra
        if instancia is not None:
            campania_nueva = attrs.get("campania")
            if campania_nueva is not None and campania_nueva != instancia.campania:
                raise serializers.ValidationError(
                    {
                        "campania": (
                            "La campaña de una actividad no se puede cambiar: "
                            "anula y registra otra actividad."
                        )
                    }
                )
            tipo_nuevo = attrs.get("tipo_actividad")
            if tipo_nuevo is not None and tipo_nuevo != instancia.tipo_actividad:
                raise serializers.ValidationError(
                    {
                        "tipo_actividad": (
                            "El tipo de actividad no se puede cambiar: anula y "
                            "registra otra actividad."
                        )
                    }
                )

        campania = attrs.get(
            "campania", getattr(instancia, "campania", None) if instancia else None
        )
        tipo = attrs.get(
            "tipo_actividad",
            getattr(instancia, "tipo_actividad", None) if instancia else None,
        )
        fecha = attrs.get(
            "fecha", getattr(instancia, "fecha", None) if instancia else None
        )
        densidad = attrs.get(
            "densidad_siembra",
            getattr(instancia, "densidad_siembra", None) if instancia else None,
        )
        unidad = attrs.get(
            "densidad_unidad",
            getattr(instancia, "densidad_unidad", None) if instancia else None,
        )

        # La densidad solo aplica a siembras y su valor y unidad van juntos
        if densidad is not None or unidad is not None:
            es_siembra = tipo is not None and tipo.codigo == "SIEMBRA"
            if not es_siembra:
                raise serializers.ValidationError(
                    {
                        "densidad_siembra": (
                            "La densidad de siembra solo aplica a actividades "
                            "de tipo SIEMBRA."
                        )
                    }
                )
            if (densidad is None) != (unidad is None):
                raise serializers.ValidationError(
                    {
                        "densidad_siembra": (
                            "La densidad de siembra y su unidad deben ir juntas "
                            "(o dejar ambas vacías)."
                        )
                    }
                )

        # La fecha debe caer dentro del período de la campaña (aunque el
        # trigger también lo verifica: aquí se responde 400 en español)
        if fecha is not None and campania is not None:
            if not campania.fecha_inicio <= fecha <= campania.fecha_fin_prevista:
                raise serializers.ValidationError(
                    {
                        "fecha": (
                            f"La fecha {fecha} está fuera del período de la "
                            f"campaña ({campania.fecha_inicio} a "
                            f"{campania.fecha_fin_prevista})."
                        )
                    }
                )

        return attrs


# ---------------------------------------------------------------------- #
# Usos de recursos (Semana 9)
# ---------------------------------------------------------------------- #
class UsoRecursoListaSerializer(serializers.ModelSerializer):
    """Fila del listado (HU-67): fecha, recurso con su categoría y tipo de
    unidad, cantidad con su unidad, cantidad base, campaña, actividad,
    costo y estado de anulación."""

    recurso = serializers.SerializerMethodField()
    unidad = serializers.SerializerMethodField()
    campania = serializers.SerializerMethodField()
    actividad = serializers.SerializerMethodField()

    class Meta:
        model = UsoRecurso
        fields = (
            "id",
            "fecha",
            "recurso",
            "cantidad",
            "unidad",
            "cantidad_base",
            "campania",
            "actividad",
            "costo",
            "anulada",
        )

    def get_recurso(self, obj):
        return _mini_recurso(obj)

    def get_unidad(self, obj):
        return _mini_unidad(obj)

    def get_campania(self, obj):
        return _mini_campania(obj)

    def get_actividad(self, obj):
        return _mini_actividad(obj)


class UsoRecursoDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa (HU-68). registrado_por se omite de la respuesta
    para los roles con limita_a_asignados (Semana 7)."""

    recurso = serializers.SerializerMethodField()
    unidad = serializers.SerializerMethodField()
    campania = serializers.SerializerMethodField()
    actividad = serializers.SerializerMethodField()
    registrado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = UsoRecurso
        fields = (
            "id",
            "fecha",
            "recurso",
            "cantidad",
            "unidad",
            "cantidad_base",
            "campania",
            "actividad",
            "costo",
            "observaciones",
            "anulada",
            "motivo_anulacion",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "cantidad_base",
            "anulada",
            "motivo_anulacion",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )

    def get_recurso(self, obj):
        return _mini_recurso(obj)

    def get_unidad(self, obj):
        return _mini_unidad(obj)

    def get_campania(self, obj):
        return _mini_campania(obj)

    def get_actividad(self, obj):
        return _mini_actividad(obj)

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            datos.pop("registrado_por", None)
        return datos


class UsoRecursoEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición (HU-69). cantidad_base, anulada, motivo_anulacion y
    registrado_por no están en fields: el cliente no puede forzarlos (la
    cantidad base la calcula fn_uso_recurso en cada INSERT/UPDATE)."""

    campania = serializers.PrimaryKeyRelatedField(
        queryset=Campania.objects.select_related(
            "parcela", "parcela__productor", "cultivo"
        ),
        error_messages={
            "required": "La campaña es obligatoria.",
            "does_not_exist": "La campaña indicada no existe.",
        },
    )
    actividad = serializers.PrimaryKeyRelatedField(
        queryset=Actividad.objects.select_related("campania", "tipo_actividad"),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "La actividad indicada no existe.",
        },
    )
    recurso = serializers.PrimaryKeyRelatedField(
        queryset=Recurso.objects.all(),
        error_messages={
            "required": "El recurso es obligatorio.",
            "does_not_exist": "El recurso indicado no existe.",
        },
    )
    fecha = serializers.DateField(
        error_messages={
            "required": "La fecha es obligatoria.",
            "invalid": "La fecha no es válida: usa el formato AAAA-MM-DD.",
        }
    )
    cantidad = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        error_messages={
            "required": "La cantidad es obligatoria.",
            "invalid": "La cantidad debe ser un número.",
            "max_digits": (
                "La cantidad admite como máximo 9 dígitos enteros y 3 decimales."
            ),
            "max_decimal_places": "La cantidad admite como máximo 3 decimales.",
        },
    )
    unidad = serializers.PrimaryKeyRelatedField(
        queryset=Unidad.objects.all(),
        error_messages={
            "required": "La unidad es obligatoria.",
            "does_not_exist": "La unidad indicada no existe.",
        },
    )
    costo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "El costo debe ser un número.",
            "max_digits": "El costo admite como máximo 8 dígitos enteros y 2 decimales.",
            "max_decimal_places": "El costo admite como máximo 2 decimales.",
        },
    )
    observaciones = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )

    class Meta:
        model = UsoRecurso
        fields = (
            "campania",
            "actividad",
            "recurso",
            "fecha",
            "cantidad",
            "unidad",
            "costo",
            "observaciones",
        )

    # ------------------------------------------------------------------ #
    # validaciones por campo
    # ------------------------------------------------------------------ #
    def validate_campania(self, valor):
        if valor.estado not in Campania.ESTADOS_ACTIVOS:
            raise serializers.ValidationError(
                f"La campaña está {valor.estado} y no admite nuevos registros."
            )
        # El técnico solo puede registrar en campañas de SUS productores
        # asignados (mismo filtro que las actividades, Semana 7)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            asignado = AsignacionTecnico.objects.filter(
                tecnico=request.user,
                productor=valor.parcela.productor,
                activo=True,
            ).exists()
            if not asignado:
                raise serializers.ValidationError("La campaña indicada no existe.")
        return valor

    def validate_actividad(self, valor):
        if valor is None:
            return None
        # El técnico solo puede vincular actividades de SUS productores
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            asignado = AsignacionTecnico.objects.filter(
                tecnico=request.user,
                productor=valor.campania.parcela.productor,
                activo=True,
            ).exists()
            if not asignado:
                raise serializers.ValidationError("La actividad indicada no existe.")
        return valor

    def validate_recurso(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "El recurso indicado no existe o está inactivo."
            )
        return valor

    def validate_unidad(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "La unidad indicada no existe o está inactiva."
            )
        return valor

    def validate_fecha(self, valor):
        # Mismo criterio que las actividades (pregunta H): se rechazan
        # fechas futuras según la hora local de Lima
        hoy = datetime.now(ZoneInfo("America/Lima")).date()
        if valor > hoy:
            raise serializers.ValidationError("La fecha no puede ser futura.")
        return valor

    def validate_cantidad(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que 0.")
        return valor

    def validate_costo(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return valor

    # ------------------------------------------------------------------ #
    # validaciones cruzadas (unidad del recurso, actividad y período)
    # ------------------------------------------------------------------ #
    def validate(self, attrs):
        instancia = self.instance

        # La campaña no cambia al editar: anula y registra otro uso
        if instancia is not None:
            campania_nueva = attrs.get("campania")
            if campania_nueva is not None and campania_nueva != instancia.campania:
                raise serializers.ValidationError(
                    {
                        "campania": (
                            "La campaña de un uso de recurso no se puede "
                            "cambiar: anula y registra otro uso."
                        )
                    }
                )
            # Editar y anular también están bloqueados si la campaña ya
            # cerró o se canceló (lo impide la base; aquí, 400 en español)
            if instancia.campania.estado not in Campania.ESTADOS_ACTIVOS:
                raise serializers.ValidationError(
                    f"La campaña está {instancia.campania.estado} y no admite "
                    "nuevos registros."
                )

        campania = attrs.get(
            "campania", getattr(instancia, "campania", None) if instancia else None
        )
        recurso = attrs.get(
            "recurso", getattr(instancia, "recurso", None) if instancia else None
        )
        unidad = attrs.get(
            "unidad", getattr(instancia, "unidad", None) if instancia else None
        )
        actividad = attrs.get(
            "actividad", getattr(instancia, "actividad", None) if instancia else None
        )
        fecha = attrs.get(
            "fecha", getattr(instancia, "fecha", None) if instancia else None
        )

        # La unidad debe ser del mismo tipo que el recurso (lo verifica
        # fn_uso_recurso; aquí se responde 400 en español nombrando las
        # unidades compatibles activas)
        if unidad is not None and recurso is not None:
            if unidad.tipo != recurso.tipo_unidad:
                compatibles = list(
                    Unidad.objects.filter(activo=True, tipo=recurso.tipo_unidad)
                    .order_by("nombre")
                    .values_list("simbolo", flat=True)
                )
                lista = ", ".join(compatibles[:-1])
                if lista:
                    lista += " o "
                lista += compatibles[-1] if compatibles else recurso.tipo_unidad
                raise serializers.ValidationError(
                    {
                        "unidad": (
                            f"Esta unidad no sirve para este recurso: "
                            f"use {lista}."
                        )
                    }
                )

        # La actividad debe pertenecer a la campaña y, si se indica, la
        # fecha del uso debe coincidir con la de la actividad
        if actividad is not None and campania is not None:
            if actividad.campania_id != campania.pk:
                raise serializers.ValidationError(
                    {"actividad": "La actividad indicada no pertenece a esta campaña."}
                )
            if fecha is not None and fecha != actividad.fecha:
                raise serializers.ValidationError(
                    {
                        "fecha": (
                            "La fecha debe coincidir con la de la actividad "
                            "indicada."
                        )
                    }
                )

        # La fecha debe caer dentro del período de la campaña (aunque el
        # trigger también lo verifica: aquí se responde 400 en español)
        if fecha is not None and campania is not None:
            if not campania.fecha_inicio <= fecha <= campania.fecha_fin_prevista:
                raise serializers.ValidationError(
                    {
                        "fecha": (
                            f"La fecha {fecha} está fuera del período de la "
                            f"campaña ({campania.fecha_inicio} a "
                            f"{campania.fecha_fin_prevista})."
                        )
                    }
                )

        return attrs


# ---------------------------------------------------------------------- #
# Registro de clima (Semana 10)
# ---------------------------------------------------------------------- #
def _mini_parcela_clima(obj):
    """Parcela anidada con su productor y comunidad (sin DNI)."""
    parcela = obj.parcela
    return {
        "id": parcela.id,
        "codigo": parcela.codigo,
        "comunidad": {"id": parcela.comunidad_id, "nombre": parcela.comunidad.nombre},
        "productor": {
            "id": parcela.productor_id,
            "nombre_completo": (
                f"{parcela.productor.apellidos}, {parcela.productor.nombres}"
            ),
        },
    }


def _umbral_helada():
    """Umbral de helada vigente (parametros_sistema.umbral_helada_c, con
    0 °C como respaldo si la fila aún no existe)."""
    parametro = ParametroSistema.objects.filter(clave="umbral_helada_c").first()
    if parametro is None:
        return Decimal("0")
    return Decimal(parametro.valor)


def _punto_medio(minima, maxima):
    """Punto medio de mínima y máxima con 1 decimal (igual que los campos
    del modelo; los empates se redondean hacia arriba, como ROUND de la
    base de datos)."""
    return ((minima + maxima) / Decimal("2")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def _validar_parcela_clima(valor, request):
    """Parcela activa y, para el Técnico, de SUS productores (mismo
    mensaje que si no existiera). Compartida por el alta manual (HU-78) y
    la consulta a la API meteorológica (HU-84)."""
    if valor.estado != Parcela.ESTADO_ACTIVA:
        raise serializers.ValidationError(
            "La parcela indicada no existe o está inactiva."
        )
    rol = getattr(getattr(request, "user", None), "rol", None)
    if rol is not None and rol.limita_a_asignados:
        asignado = AsignacionTecnico.objects.filter(
            tecnico=request.user, productor=valor.productor, activo=True
        ).exists()
        if not asignado:
            raise serializers.ValidationError("La parcela indicada no existe.")
    return valor


class ClimaListaSerializer(serializers.ModelSerializer):
    """Fila del listado (HU-76): fecha, parcela con productor y comunidad,
    temperaturas, precipitación, helada y fuente."""

    parcela = serializers.SerializerMethodField()

    class Meta:
        model = Clima
        fields = (
            "id",
            "fecha",
            "parcela",
            "temp_min",
            "temp_max",
            "temp_prom",
            "precipitacion_mm",
            "helada",
            "fuente",
        )

    def get_parcela(self, obj):
        return _mini_parcela_clima(obj)


class ClimaDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa (HU-77). Además de la trazabilidad, expone las dos
    marcas de lo calculado por el servidor: temp_prom_calculado (el valor
    guardado es el punto medio de mínima y máxima) y helada_calculada
    (hay mínima, así que la helada la derivó el servidor y el cliente no
    debería tocarla). registrado_por se omite para los roles con
    limita_a_asignados (Semana 7)."""

    parcela = serializers.SerializerMethodField()
    temp_prom_calculado = serializers.SerializerMethodField()
    helada_calculada = serializers.SerializerMethodField()
    registrado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Clima
        fields = (
            "id",
            "fecha",
            "parcela",
            "temp_min",
            "temp_max",
            "temp_prom",
            "temp_prom_calculado",
            "precipitacion_mm",
            "humedad_pct",
            "viento_ms",
            "radiacion_mj",
            "helada",
            "helada_calculada",
            "fuente",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "temp_prom_calculado",
            "helada_calculada",
            "fuente",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )

    def get_parcela(self, obj):
        return _mini_parcela_clima(obj)

    def get_temp_prom_calculado(self, obj):
        if obj.temp_min is None or obj.temp_max is None or obj.temp_prom is None:
            return False
        return obj.temp_prom == _punto_medio(obj.temp_min, obj.temp_max)

    def get_helada_calculada(self, obj):
        return obj.temp_min is not None

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            datos.pop("registrado_por", None)
        return datos


class ClimaEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición (HU-78). fuente, registrado_por, creado_en y
    actualizado_en no están en fields: la fuente la fija el servidor
    (siempre MANUAL en la API) y el resto lo rellena la base. Valida ANTES
    que la base: parcela activa y, para el Técnico, de SUS productores;
    fecha entre 2000 y hoy (hora de Lima); rangos de cada medida; al menos
    una medida o la helada marcada; mínima ≤ máxima y el promedio entre
    ambas; y una sola fila por parcela y día (uq_clima_parcela_fecha, con
    400 en español antes de que choque la restricción)."""

    parcela = serializers.PrimaryKeyRelatedField(
        queryset=Parcela.objects.select_related("productor", "comunidad"),
        error_messages={
            "required": "La parcela es obligatoria.",
            "does_not_exist": "La parcela indicada no existe.",
        },
    )
    fecha = serializers.DateField(
        error_messages={
            "required": "La fecha es obligatoria.",
            "invalid": "La fecha no es válida: usa el formato AAAA-MM-DD.",
        }
    )
    temp_min = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La temperatura mínima debe ser un número.",
            "max_digits": (
                "La temperatura mínima admite como máximo 2 dígitos enteros "
                "y 1 decimal."
            ),
            "max_decimal_places": (
                "La temperatura mínima admite como máximo 1 decimal."
            ),
        },
    )
    temp_max = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La temperatura máxima debe ser un número.",
            "max_digits": (
                "La temperatura máxima admite como máximo 2 dígitos enteros "
                "y 1 decimal."
            ),
            "max_decimal_places": (
                "La temperatura máxima admite como máximo 1 decimal."
            ),
        },
    )
    temp_prom = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La temperatura promedio debe ser un número.",
            "max_digits": (
                "La temperatura promedio admite como máximo 2 dígitos enteros "
                "y 1 decimal."
            ),
            "max_decimal_places": (
                "La temperatura promedio admite como máximo 1 decimal."
            ),
        },
    )
    precipitacion_mm = serializers.DecimalField(
        max_digits=6,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La precipitación debe ser un número.",
            "max_digits": (
                "La precipitación admite como máximo 4 dígitos enteros "
                "y 1 decimal."
            ),
            "max_decimal_places": "La precipitación admite como máximo 1 decimal.",
        },
    )
    humedad_pct = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La humedad debe ser un número.",
            "max_digits": (
                "La humedad admite como máximo 2 dígitos enteros y 1 decimal."
            ),
            "max_decimal_places": "La humedad admite como máximo 1 decimal.",
        },
    )
    viento_ms = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La velocidad del viento debe ser un número.",
            "max_digits": (
                "El viento admite como máximo 2 dígitos enteros y 1 decimal."
            ),
            "max_decimal_places": "El viento admite como máximo 1 decimal.",
        },
    )
    radiacion_mj = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "La radiación debe ser un número.",
            "max_digits": (
                "La radiación admite como máximo 3 dígitos enteros y 1 decimal."
            ),
            "max_decimal_places": "La radiación admite como máximo 1 decimal.",
        },
    )
    helada = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Clima
        fields = (
            "parcela",
            "fecha",
            "temp_min",
            "temp_max",
            "temp_prom",
            "precipitacion_mm",
            "humedad_pct",
            "viento_ms",
            "radiacion_mj",
            "helada",
        )
        # Sin el UniqueTogetherValidator automático: el duplicado se
        # responde con un mensaje propio que nombra el campo (igual que
        # las campañas) y la carrera con la base cae en el IntegrityError
        # que traduce la vista a 400
        validators = []

    # ------------------------------------------------------------------ #
    # validaciones por campo
    # ------------------------------------------------------------------ #
    def validate_parcela(self, valor):
        return _validar_parcela_clima(valor, self.context.get("request"))

    def validate_fecha(self, valor):
        # Rango del diseño: ni futura (hora de Lima, pregunta H) ni
        # anterior al 1 de enero de 2000 (nada de registros de antes)
        if valor < date(2000, 1, 1):
            raise serializers.ValidationError(
                "La fecha no puede ser anterior al 1 de enero de 2000."
            )
        hoy = datetime.now(ZoneInfo("America/Lima")).date()
        if valor > hoy:
            raise serializers.ValidationError("La fecha no puede ser futura.")
        return valor

    def validate_temp_min(self, valor):
        if valor is not None and not Decimal("-30") <= valor <= Decimal("45"):
            raise serializers.ValidationError(
                "La temperatura mínima debe estar entre -30 y 45 °C."
            )
        return valor

    def validate_temp_max(self, valor):
        if valor is not None and not Decimal("-30") <= valor <= Decimal("45"):
            raise serializers.ValidationError(
                "La temperatura máxima debe estar entre -30 y 45 °C."
            )
        return valor

    def validate_temp_prom(self, valor):
        if valor is not None and not Decimal("-30") <= valor <= Decimal("45"):
            raise serializers.ValidationError(
                "La temperatura promedio debe estar entre -30 y 45 °C."
            )
        return valor

    def validate_precipitacion_mm(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError(
                "La precipitación no puede ser negativa."
            )
        return valor

    def validate_humedad_pct(self, valor):
        if valor is not None and not Decimal("0") <= valor <= Decimal("100"):
            raise serializers.ValidationError(
                "La humedad debe estar entre 0 y 100 %."
            )
        return valor

    def validate_viento_ms(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("El viento no puede ser negativo.")
        return valor

    def validate_radiacion_mj(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError(
                "La radiación no puede ser negativa."
            )
        return valor

    # ------------------------------------------------------------------ #
    # validaciones cruzadas (medidas, unicidad y reemplazo de la API)
    # ------------------------------------------------------------------ #
    def validate(self, attrs):
        instancia = self.instance

        parcela = attrs.get(
            "parcela", getattr(instancia, "parcela", None) if instancia else None
        )
        fecha = attrs.get(
            "fecha", getattr(instancia, "fecha", None) if instancia else None
        )
        minima = attrs.get(
            "temp_min", getattr(instancia, "temp_min", None) if instancia else None
        )
        maxima = attrs.get(
            "temp_max", getattr(instancia, "temp_max", None) if instancia else None
        )
        # Si el cliente mueve las temperaturas sin enviar el promedio, lo
        # que se validará es el punto medio que calculará _completar (no
        # el promedio anterior, que quedaría desplazado)
        if attrs.get("temp_prom") is not None:
            promedio = attrs["temp_prom"]
        elif ("temp_min" in attrs or "temp_max" in attrs) and (
            minima is not None and maxima is not None
        ):
            promedio = _punto_medio(minima, maxima)
        else:
            promedio = (
                getattr(instancia, "temp_prom", None) if instancia else None
            )
        precipitacion = attrs.get(
            "precipitacion_mm",
            getattr(instancia, "precipitacion_mm", None) if instancia else None,
        )
        humedad = attrs.get(
            "humedad_pct",
            getattr(instancia, "humedad_pct", None) if instancia else None,
        )
        viento = attrs.get(
            "viento_ms", getattr(instancia, "viento_ms", None) if instancia else None
        )
        radiacion = attrs.get(
            "radiacion_mj",
            getattr(instancia, "radiacion_mj", None) if instancia else None,
        )
        helada_marcada = attrs.get(
            "helada", getattr(instancia, "helada", False) if instancia else False
        )

        # Al menos una medida o la helada marcada
        alguna_medida = any(
            valor is not None
            for valor in (
                minima,
                maxima,
                promedio,
                precipitacion,
                humedad,
                viento,
                radiacion,
            )
        )
        if not alguna_medida and not helada_marcada:
            raise serializers.ValidationError(
                {
                    "helada": (
                        "Indica al menos una medida meteorológica o marca "
                        "la helada."
                    )
                }
            )

        # mínima ≤ máxima y el promedio entre ambas
        if minima is not None and maxima is not None and minima > maxima:
            raise serializers.ValidationError(
                {
                    "temp_min": (
                        "La temperatura mínima no puede ser mayor que la "
                        "máxima."
                    )
                }
            )
        if promedio is not None and minima is not None and promedio < minima:
            raise serializers.ValidationError(
                {
                    "temp_prom": (
                        "La temperatura promedio debe estar entre la mínima "
                        "y la máxima."
                    )
                }
            )
        if promedio is not None and maxima is not None and promedio > maxima:
            raise serializers.ValidationError(
                {
                    "temp_prom": (
                        "La temperatura promedio debe estar entre la mínima "
                        "y la máxima."
                    )
                }
            )

        # Una fila por parcela y día, ANTES de guardar (el índice único es
        # la red de seguridad y la vista traduce su choque a 400 igual).
        # Este método es el que parchean las pruebas para forzar ese camino.
        if parcela is not None and fecha is not None:
            if self._existe_duplicado(parcela, fecha):
                raise serializers.ValidationError(
                    {
                        "fecha": (
                            f"Ya existe un registro de clima para esta "
                            f"parcela en la fecha {fecha}."
                        )
                    }
                )

        # Reemplazar un registro que vino de la API meteorológica exige la
        # confirmación explícita del técnico (decisión de la Semana 10):
        # al guardarlo, la fuente pasa a MANUAL. La propia consulta a la
        # API (contexto fuente_externa) la pisa sin confirmación: la fuente
        # de esos registros es el servicio y se refrescan como tales
        if (
            instancia is not None
            and instancia.fuente == Clima.FUENTE_API
            and not self.context.get("fuente_externa")
        ):
            crudo = self.initial_data.get("confirmar_reemplazo", False)
            confirmado = crudo is True or str(crudo).lower() in (
                "1",
                "true",
                "si",
                "sí",
                "yes",
            )
            if not confirmado:
                raise serializers.ValidationError(
                    {
                        "confirmar_reemplazo": (
                            "Este registro proviene de la API meteorológica: "
                            "envía confirmar_reemplazo=true para reemplazarlo "
                            "con valores manuales."
                        )
                    }
                )

        return attrs

    # ------------------------------------------------------------------ #
    # campos calculados por el servidor (nunca los pone el cliente)
    # ------------------------------------------------------------------ #
    def _existe_duplicado(self, parcela, fecha):
        """¿Ya hay un registro para esta parcela y día? (excluye el propio
        que se está editando). La prueba 143 parchea este método para
        forzar el choque con uq_clima_parcela_fecha en la base."""
        consulta = Clima.objects.filter(parcela=parcela, fecha=fecha)
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        return consulta.exists()

    def _completar(self, datos):
        """Completa lo que el cliente no puede forzar: temp_prom como punto
        medio si trae mínima y máxima y no lo indicó, y helada derivada del
        umbral del sistema cuando hay mínima (si no, manda la del técnico)."""
        if self.instance is None:
            minima = datos.get("temp_min")
            maxima = datos.get("temp_max")
            helada_enviada = datos.get("helada", False)
        else:
            minima = datos.get("temp_min", self.instance.temp_min)
            maxima = datos.get("temp_max", self.instance.temp_max)
            helada_enviada = datos.get("helada", self.instance.helada)
        if datos.get("temp_prom") is None and minima is not None and maxima is not None:
            datos["temp_prom"] = _punto_medio(minima, maxima)
        if minima is not None:
            datos["helada"] = minima <= _umbral_helada()
        else:
            datos["helada"] = helada_enviada

    def create(self, validated_data):
        self._completar(validated_data)
        # La consulta a la API meteorológica (HU-84) deja la fuente API
        validated_data["fuente"] = (
            Clima.FUENTE_API
            if self.context.get("fuente_externa")
            else Clima.FUENTE_MANUAL
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._completar(validated_data)
        # Un registro de la API editado a mano queda como MANUAL; si la
        # actualización viene de la propia consulta, conserva la fuente API
        if instance.fuente == Clima.FUENTE_API and not self.context.get(
            "fuente_externa"
        ):
            validated_data["fuente"] = Clima.FUENTE_MANUAL
        return super().update(instance, validated_data)


DIAS_MAX_CONSULTA_API = 92


class ClimaConsultaApiSerializer(serializers.Serializer):
    """Entrada de la consulta a la API meteorológica (HU-84, pregunta L):
    parcela con coordenadas y un rango de hasta 92 días, sin fechas
    futuras. Las medidas y el resto de reglas las aplica la vista con el
    mismo serializer del alta manual."""

    parcela = serializers.PrimaryKeyRelatedField(
        queryset=Parcela.objects.select_related("productor", "comunidad"),
        error_messages={
            "required": "La parcela es obligatoria.",
            "does_not_exist": "La parcela indicada no existe.",
        },
    )
    fecha_desde = serializers.DateField(
        error_messages={
            "required": "La fecha inicial es obligatoria.",
            "invalid": "La fecha inicial no es válida: usa el formato AAAA-MM-DD.",
        }
    )
    fecha_hasta = serializers.DateField(
        error_messages={
            "required": "La fecha final es obligatoria.",
            "invalid": "La fecha final no es válida: usa el formato AAAA-MM-DD.",
        }
    )

    def validate_parcela(self, valor):
        return _validar_parcela_clima(valor, self.context.get("request"))

    def validate(self, attrs):
        desde = attrs["fecha_desde"]
        hasta = attrs["fecha_hasta"]
        if desde > hasta:
            raise serializers.ValidationError(
                {"fecha_desde": "La fecha inicial no puede ser posterior a la final."}
            )
        # Lo mismo que un registro manual: la consulta solo puede guardar
        # fechas que la tabla admite
        if desde < date(2000, 1, 1):
            raise serializers.ValidationError(
                {"fecha_desde": "La fecha no puede ser anterior al 1 de enero de 2000."}
            )
        hoy = datetime.now(ZoneInfo("America/Lima")).date()
        if hasta > hoy:
            raise serializers.ValidationError(
                {"fecha_hasta": "La fecha final no puede ser futura."}
            )
        if (hasta - desde).days + 1 > DIAS_MAX_CONSULTA_API:
            raise serializers.ValidationError(
                {"fecha_hasta": "La consulta admite como máximo 92 días."}
            )
        parcela = attrs["parcela"]
        if parcela.latitud is None or parcela.longitud is None:
            raise serializers.ValidationError(
                {"parcela": "La parcela no tiene coordenadas registradas."}
            )
        return attrs
