"""Serializador de lectura de la auditoría (Semana 13, RF-72)."""
from rest_framework import serializers

from .models import Auditoria


class AuditoriaSerializer(serializers.ModelSerializer):
    """Solo lectura: usuario en forma corta {id, username} (null si la
    cuenta se borró o el evento es de un login anónimo)."""

    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Auditoria
        fields = (
            "id",
            "fecha",
            "usuario",
            "accion",
            "modulo",
            "tabla",
            "registro_id",
            "detalle",
            "ip",
        )
        read_only_fields = fields

    def get_usuario(self, obj):
        if obj.usuario_id is None:
            return None
        return {"id": obj.usuario.pk, "username": obj.usuario.username}
