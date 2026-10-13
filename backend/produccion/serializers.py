"""Serializadores de la API de producciones (Semana 8).

La lista muestra fecha de cosecha, campaña (período, cultivo, parcela y
productor), kg, superficie, rendimiento y la marca de revisión; la ficha
añade cantidad escrita, unidad, pérdida, calidad, motivo de revisión,
inclusión en entrenamiento, observaciones, registrado por y trazabilidad.
registrado_por lo pone el servidor y se OCULTA a los roles con
limita_a_asignados (decisión de la Semana 7). El de escritura no acepta
kg, rendimiento, marca, inclusión ni registrado por (los calcula la base),
no cambia la campaña al editar y valida ANTES que la base: campaña con
siembra en EN_PRODUCCION/COSECHADA, unidad de masa activa, fecha de
cosecha no anterior a la siembra ni al inicio (la futura queda pendiente
de la decisión H), superficie y cantidad, y una sola producción por
campaña.
"""
from rest_framework import serializers

from campanias.models import Campania
from catalogos.models import Unidad
from productores.models import AsignacionTecnico

from .models import Produccion


def _mini_campania(obj):
    """Campaña anidada con su estado ACTUALIZADO (tras guardar, la vista
    hace refresh_from_db: fn_produccion_post pudo pasarla a COSECHADA)."""
    campania = obj.campania
    return {
        "id": campania.id,
        "periodo": campania.periodo,
        "estado": campania.estado,
        "fecha_siembra": campania.fecha_siembra,
        "superficie_sembrada_ha": campania.superficie_sembrada_ha,
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


def _mini_unidad(obj):
    return {
        "id": obj.unidad_id,
        "nombre": obj.unidad.nombre,
        "simbolo": obj.unidad.simbolo,
    }


class ProduccionListaSerializer(serializers.ModelSerializer):
    """Fila del listado (HU-56): fecha, campaña con productor y parcela,
    kg, superficie, rendimiento y marca de revisión."""

    campania = serializers.SerializerMethodField()

    class Meta:
        model = Produccion
        fields = (
            "id",
            "fecha_cosecha",
            "campania",
            "produccion_kg",
            "superficie_cosechada_ha",
            "rendimiento_kg_ha",
            "requiere_revision",
        )

    def get_campania(self, obj):
        return _mini_campania(obj)


class ProduccionDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa (HU-57/HU-59). registrado_por se omite de la
    respuesta para los roles con limita_a_asignados."""

    campania = serializers.SerializerMethodField()
    unidad = serializers.SerializerMethodField()
    registrado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Produccion
        fields = (
            "id",
            "fecha_cosecha",
            "campania",
            "superficie_cosechada_ha",
            "cantidad_producida",
            "unidad",
            "produccion_kg",
            "perdida_kg",
            "calidad",
            "rendimiento_kg_ha",
            "requiere_revision",
            "motivo_revision",
            "incluir_en_entrenamiento",
            "observaciones",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "produccion_kg",
            "rendimiento_kg_ha",
            "requiere_revision",
            "motivo_revision",
            "incluir_en_entrenamiento",
            "registrado_por",
            "creado_en",
            "actualizado_en",
        )

    def get_campania(self, obj):
        return _mini_campania(obj)

    def get_unidad(self, obj):
        return _mini_unidad(obj)

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            datos.pop("registrado_por", None)
        return datos


class ProduccionEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición. produccion_kg, rendimiento_kg_ha, requiere_revision,
    incluir_en_entrenamiento y registrado_por no están en fields: los
    calcula la base y el cliente no puede forzarlos."""

    campania = serializers.PrimaryKeyRelatedField(
        queryset=Campania.objects.select_related(
            "parcela", "parcela__productor", "cultivo"
        ),
        error_messages={
            "required": "La campaña es obligatoria.",
            "does_not_exist": "La campaña indicada no existe.",
        },
    )
    fecha_cosecha = serializers.DateField(
        error_messages={
            "required": "La fecha de cosecha es obligatoria.",
            "invalid": "La fecha de cosecha no es válida: usa el formato AAAA-MM-DD.",
        }
    )
    superficie_cosechada_ha = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        error_messages={
            "required": "La superficie cosechada es obligatoria.",
            "invalid": "La superficie cosechada debe ser un número.",
            "max_digits": (
                "La superficie admite como máximo 6 dígitos enteros y 2 decimales."
            ),
            "max_decimal_places": "La superficie admite como máximo 2 decimales.",
        },
    )
    cantidad_producida = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        error_messages={
            "required": "La cantidad producida es obligatoria.",
            "invalid": "La cantidad producida debe ser un número.",
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
    perdida_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        error_messages={
            "invalid": "La pérdida debe ser un número.",
            "max_digits": "La pérdida admite como máximo 8 dígitos enteros y 2 decimales.",
            "max_decimal_places": "La pérdida admite como máximo 2 decimales.",
        },
    )
    calidad = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    observaciones = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )

    class Meta:
        model = Produccion
        fields = (
            "campania",
            "fecha_cosecha",
            "superficie_cosechada_ha",
            "cantidad_producida",
            "unidad",
            "perdida_kg",
            "calidad",
            "observaciones",
        )

    # ------------------------------------------------------------------ #
    # validaciones por campo
    # ------------------------------------------------------------------ #
    def validate_campania(self, valor):
        if valor.estado not in (
            Campania.ESTADO_EN_PRODUCCION,
            Campania.ESTADO_COSECHADA,
        ):
            raise serializers.ValidationError(
                f"La campaña está {valor.estado} y no admite nuevos registros."
            )
        if valor.fecha_siembra is None:
            raise serializers.ValidationError(
                "La campaña no tiene siembra registrada: registra la actividad "
                "de siembra antes de la producción."
            )
        # El técnico solo puede registrar en campañas de SUS productores
        # asignados: si no le corresponde, el mismo mensaje que si no existiera
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

    def validate_unidad(self, valor):
        if not valor.activo or valor.tipo != "MASA":
            raise serializers.ValidationError(
                "La unidad debe ser de masa (kg, quintal o tonelada) y estar activa."
            )
        return valor

    def validate_fecha_cosecha(self, valor):
        # Sin rechazo de fecha futura: la decisión H sigue pendiente del
        # responsable (a diferencia de las actividades, Semana 7)
        return valor

    def validate_superficie_cosechada_ha(self, valor):
        if valor <= 0:
            raise serializers.ValidationError(
                "La superficie cosechada debe ser mayor que 0."
            )
        return valor

    def validate_cantidad_producida(self, valor):
        if valor < 0:
            raise serializers.ValidationError(
                "La cantidad producida no puede ser negativa."
            )
        return valor

    def validate_perdida_kg(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("La pérdida no puede ser negativa.")
        return valor

    def validate_calidad(self, valor):
        if valor == "":
            return None
        if valor is not None and valor not in ("PRIMERA", "SEGUNDA", "TERCERA"):
            raise serializers.ValidationError(
                "La calidad debe ser PRIMERA, SEGUNDA o TERCERA."
            )
        return valor

    # ------------------------------------------------------------------ #
    # validaciones cruzadas (campaña única, fechas y superficie)
    # ------------------------------------------------------------------ #
    def validate(self, attrs):
        instancia = self.instance

        # La campaña no cambia al editar: deshacer y registrar otra
        if instancia is not None:
            campania_nueva = attrs.get("campania")
            if campania_nueva is not None and campania_nueva != instancia.campania:
                raise serializers.ValidationError(
                    {
                        "campania": (
                            "La campaña de una producción no se puede cambiar: "
                            "usa «deshacer cosecha» y registra otra producción."
                        )
                    }
                )
            if instancia.campania.estado == Campania.ESTADO_CERRADA:
                raise serializers.ValidationError(
                    "La campaña cerrada no admite cambios en la producción."
                )

        campania = attrs.get(
            "campania", getattr(instancia, "campania", None) if instancia else None
        )
        fecha = attrs.get(
            "fecha_cosecha",
            getattr(instancia, "fecha_cosecha", None) if instancia else None,
        )
        superficie = attrs.get(
            "superficie_cosechada_ha",
            getattr(instancia, "superficie_cosechada_ha", None) if instancia else None,
        )

        # Una sola producción por campaña (el UNIQUE es la red de seguridad)
        if instancia is None and campania is not None:
            existente = Produccion.objects.filter(campania=campania).first()
            if existente is not None:
                raise serializers.ValidationError(
                    {
                        "campania": (
                            f"Ya existe una producción para esta campaña "
                            f"(id {existente.pk})."
                        )
                    }
                )

        # La fecha de cosecha no puede ser anterior a la siembra ni al inicio
        if fecha is not None and campania is not None:
            if campania.fecha_siembra is not None and fecha < campania.fecha_siembra:
                raise serializers.ValidationError(
                    {
                        "fecha_cosecha": (
                            f"La fecha de cosecha no puede ser anterior a la "
                            f"fecha de siembra ({campania.fecha_siembra})."
                        )
                    }
                )
            if fecha < campania.fecha_inicio:
                raise serializers.ValidationError(
                    {
                        "fecha_cosecha": (
                            f"La fecha de cosecha no puede ser anterior al "
                            f"inicio de la campaña ({campania.fecha_inicio})."
                        )
                    }
                )

        # La superficie cosechada no puede superar la sembrada
        if superficie is not None and campania is not None:
            if superficie > campania.superficie_sembrada_ha:
                raise serializers.ValidationError(
                    {
                        "superficie_cosechada_ha": (
                            f"La superficie cosechada no puede superar la "
                            f"sembrada ({campania.superficie_sembrada_ha} ha)."
                        )
                    }
                )

        return attrs
