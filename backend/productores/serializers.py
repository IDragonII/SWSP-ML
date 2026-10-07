"""Serializadores de la API de ubicación y productores (Semana 3).

Los de lectura anidan el nivel superior (jerarquía completa para el
desplegable en cascada); los de escritura reciben el id del padre.

DNI y teléfono se enmascaran por rol (decisión 4 de
docs/decisiones_semana3.md; pendiente de confirmación del responsable):
Administrador y Técnico de campo los ven completos, el Coordinador
ve ****5678 y ****789.
"""
import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Comunidad, Distrito, Productor, Provincia

ROLES_CON_DATOS_COMPLETOS = ("Administrador", "Técnico de campo")
_MENSAJE_REQUERIDO = "Este campo es obligatorio."


def _rol_enmascara(context):
    """True si el usuario de la petición no ve datos personales completos."""
    request = (context or {}).get("request")
    user = getattr(request, "user", None)
    rol = getattr(user, "rol", None)
    nombre = getattr(rol, "nombre", None)
    return nombre is not None and nombre not in ROLES_CON_DATOS_COMPLETOS


def _mascara(valor, ultimos):
    if not valor:
        return valor
    return "****" + valor[-ultimos:]


class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = ("id", "nombre", "activo")


class DistritoSerializer(serializers.ModelSerializer):
    provincia = ProvinciaSerializer(read_only=True)

    class Meta:
        model = Distrito
        fields = ("id", "nombre", "activo", "provincia")


class DistritoEscrituraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distrito
        fields = ("nombre", "activo", "provincia")


class ComunidadSerializer(serializers.ModelSerializer):
    distrito = DistritoSerializer(read_only=True)

    class Meta:
        model = Comunidad
        fields = ("id", "nombre", "activo", "distrito")


class ComunidadEscrituraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comunidad
        fields = ("nombre", "activo", "distrito")


class ProductorListaSerializer(serializers.ModelSerializer):
    """Fila del listado: código, nombre completo, ubicación, estado y DNI
    enmascarado o completo según el rol."""

    nombre_completo = serializers.SerializerMethodField()
    dni = serializers.SerializerMethodField()
    comunidad = serializers.SerializerMethodField()
    distrito = serializers.SerializerMethodField()
    provincia = serializers.SerializerMethodField()

    class Meta:
        model = Productor
        fields = (
            "id",
            "codigo",
            "nombre_completo",
            "comunidad",
            "distrito",
            "provincia",
            "estado",
            "dni",
        )

    def get_nombre_completo(self, obj):
        return f"{obj.apellidos}, {obj.nombres}"

    def get_dni(self, obj):
        if _rol_enmascara(self.context):
            return _mascara(obj.dni, 4)
        return obj.dni

    def get_comunidad(self, obj):
        return {"id": obj.comunidad_id, "nombre": obj.comunidad.nombre}

    def get_distrito(self, obj):
        distrito = obj.comunidad.distrito
        return {"id": distrito.id, "nombre": distrito.nombre}

    def get_provincia(self, obj):
        provincia = obj.comunidad.distrito.provincia
        return {"id": provincia.id, "nombre": provincia.nombre}


class ProductorDetalleSerializer(serializers.ModelSerializer):
    """Ficha parcial (HU-22): todos los datos del productor y su ubicación
    completa. Parcelas y campañas se suman en la semana 4."""

    dni = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    creado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Productor
        fields = (
            "id",
            "codigo",
            "nombres",
            "apellidos",
            "dni",
            "telefono",
            "comunidad",
            "referencia_ubicacion",
            "fecha_incorporacion",
            "estado",
            "creado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("codigo", "creado_por", "creado_en", "actualizado_en")

    def get_dni(self, obj):
        if _rol_enmascara(self.context):
            return _mascara(obj.dni, 4)
        return obj.dni

    def get_telefono(self, obj):
        if _rol_enmascara(self.context):
            return _mascara(obj.telefono, 3)
        return obj.telefono


class ProductorEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición: sin código (lo genera la BD), sin creado_por (lo
    pone el servidor) y sin estado (se cambia con /estado/)."""

    dni = serializers.CharField(
        validators=[
            UniqueValidator(
                queryset=Productor.objects.all(),
                message="Ya existe un productor con ese DNI.",
            )
        ],
        error_messages={"required": _MENSAJE_REQUERIDO},
    )
    comunidad = serializers.PrimaryKeyRelatedField(
        queryset=Comunidad.objects.all(),
        error_messages={
            "required": "La comunidad es obligatoria.",
            "does_not_exist": "La comunidad indicada no existe.",
        },
    )
    nombres = serializers.CharField(error_messages={"required": _MENSAJE_REQUERIDO})
    apellidos = serializers.CharField(error_messages={"required": _MENSAJE_REQUERIDO})

    class Meta:
        model = Productor
        fields = (
            "nombres",
            "apellidos",
            "dni",
            "telefono",
            "comunidad",
            "referencia_ubicacion",
            "fecha_incorporacion",
        )

    def validate_dni(self, valor):
        if not re.fullmatch(r"\d{8}", valor or ""):
            raise serializers.ValidationError(
                "El DNI debe tener exactamente 8 dígitos numéricos."
            )
        return valor

    def validate_comunidad(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "La comunidad indicada no existe o está inactiva."
            )
        return valor

    def validate_telefono(self, valor):
        return valor or None
