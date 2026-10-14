"""Serializadores de la API de seguimiento (Semanas 7 y 9).

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
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from rest_framework import serializers

from catalogos.models import Recurso, TipoActividad, Unidad
from campanias.models import Campania
from productores.models import AsignacionTecnico

from .models import Actividad, UsoRecurso

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
