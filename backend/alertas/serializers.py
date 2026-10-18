"""Serializadores de la API de alertas (Semana 15, HU-124..HU-132).

La lista y el detalle muestran la alerta con su productor y campaña
(código y nombre: el personal con alertas.ver está autorizado a verlo);
el MENSAJE de la alerta no contiene datos personales (RF-63/RF-64
pendientes de documentar en el .tex). El detalle añade la nota de
atención y quién atendió — este último solo para roles sin
limita_a_asignados (el Técnico no ve quién atendió). La escritura es la
atención manual: nota opcional de hasta 250 caracteres.
"""
from rest_framework import serializers

from .models import Alerta


class AlertaListaSerializer(serializers.ModelSerializer):
    """Listado: alerta con productor y campaña; sin nota ni atendiente."""

    productor_codigo = serializers.CharField(source="productor.codigo")
    productor_nombre = serializers.SerializerMethodField()
    campania_periodo = serializers.CharField(source="campania.periodo")

    class Meta:
        model = Alerta
        fields = (
            "id",
            "tipo",
            "mensaje",
            "creada_en",
            "atendida",
            "atendida_en",
            "productor",
            "productor_codigo",
            "productor_nombre",
            "campania",
            "campania_periodo",
            "incidencia",
        )

    def get_productor_nombre(self, obj):
        return f"{obj.productor.apellidos} {obj.productor.nombres}".strip()


class AlertaDetalleSerializer(AlertaListaSerializer):
    """Detalle: además nota y atendiente (este solo si el rol no está
    limitado a sus asignados)."""

    nota_atencion = serializers.CharField(allow_null=True)
    atendida_por_nombre = serializers.SerializerMethodField()

    class Meta(AlertaListaSerializer.Meta):
        fields = AlertaListaSerializer.Meta.fields + (
            "nota_atencion",
            "atendida_por",
            "atendida_por_nombre",
        )

    def get_atendida_por_nombre(self, obj):
        rol = getattr(self.context.get("request"), "user", None)
        rol = getattr(rol, "rol", None)
        if rol is not None and rol.limita_a_asignados:
            return None
        if obj.atendida_por is None:
            return None
        return obj.atendida_por.get_full_name() or obj.atendida_por.username


class AtenderEscrituraSerializer(serializers.Serializer):
    """Atención manual: nota opcional de hasta 250 caracteres."""

    nota = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=250,
        error_messages={
            "max_length": "La nota no puede superar los 250 caracteres."
        },
    )
