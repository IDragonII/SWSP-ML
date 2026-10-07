"""Serializadores de la sesión, los datos del usuario y el alta de usuarios."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Rol, Usuario


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id', 'nombre')


class DatosUsuarioSerializer(serializers.ModelSerializer):
    """Lo que devuelven login y /api/auth/me: identidad, rol y permisos.

    Los permisos van AQUÍ y no dentro del token, para que un cambio de rol
    se refleje en la siguiente consulta sin esperar a que venza el access.
    El superusuario se rige por su rol (docs/decisiones_seguridad.md §7).
    """
    nombre_completo = serializers.SerializerMethodField()
    rol = RolSerializer(read_only=True)
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ('id', 'username', 'nombre_completo', 'rol', 'permisos')

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_permisos(self, obj):
        if obj.rol_id is None:
            return []
        return sorted(obj.rol.permisos.values_list('codigo', flat=True))


class CrearUsuarioSerializer(serializers.ModelSerializer):
    """Alta de usuarios desde la API (endpoint de prueba protegido).

    El rol es obligatorio (la columna rol_id es NOT NULL en el diseño) y la
    contraseña pasa por los validadores de Django.
    """
    password = serializers.CharField(write_only=True)
    rol = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all())

    class Meta:
        model = Usuario
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'rol')

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)
