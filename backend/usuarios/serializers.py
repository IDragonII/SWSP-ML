"""Serializadores de la sesión, la gestión de usuarios y los roles.

Semana 2: datos de la sesión (DatosUsuarioSerializer) y alta de prueba
(CrearUsuarioSerializer). Semana 12: la gestión completa sustituye al
endpoint de prueba — UsuarioListaSerializer (tabla), UsuarioDetalleSerializer
(ficha), UsuarioEscrituraSerializer (alta y edición) y
RestablecerClaveSerializer; más RolSerializer reutilizado por el
desplegable de roles.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from . import ratelimit
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
        fields = (
            'id',
            'username',
            'nombre_completo',
            'rol',
            'permisos',
            # Semana 13 (HU-112): la interfaz redirige a /cambiar-clave
            'debe_cambiar_clave',
        )

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_permisos(self, obj):
        if obj.rol_id is None:
            return []
        return sorted(obj.rol.permisos.values_list('codigo', flat=True))


class UsuarioListaSerializer(serializers.ModelSerializer):
    """Fila de la tabla de usuarios (Semana 12): identidad, contacto, rol,
    estado de la cuenta y si está bloqueada por intentos fallidos (el
    bloqueo vive en caché, no en la fila)."""

    nombre_completo = serializers.SerializerMethodField()
    rol = RolSerializer(read_only=True)
    bloqueado = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            'id',
            'username',
            'nombre_completo',
            'email',
            'telefono',
            'rol',
            'is_active',
            'bloqueado',
        )

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_bloqueado(self, obj):
        return ratelimit.segundos_de_bloqueo(obj.username) is not None


class UsuarioDetalleSerializer(serializers.ModelSerializer):
    """Ficha (Semana 12): identidad, contacto, rol, estado, bloqueo con
    segundos restantes, trazabilidad de la cuenta y los códigos de permiso
    del rol (la misma lista que /me, para enseñar qué puede hacer)."""

    nombre_completo = serializers.SerializerMethodField()
    rol = RolSerializer(read_only=True)
    bloqueado = serializers.SerializerMethodField()
    bloqueado_segundos = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            'id',
            'username',
            'nombre_completo',
            'first_name',
            'last_name',
            'email',
            'telefono',
            'rol',
            'is_active',
            'bloqueado',
            'bloqueado_segundos',
            'date_joined',
            'last_login',
            'permisos',
        )
    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_bloqueado(self, obj):
        return ratelimit.segundos_de_bloqueo(obj.username) is not None

    def get_bloqueado_segundos(self, obj):
        return ratelimit.segundos_de_bloqueo(obj.username)

    def get_permisos(self, obj):
        if obj.rol_id is None:
            return []
        return sorted(obj.rol.permisos.values_list('codigo', flat=True))


class UsuarioEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición de usuarios (Semana 12, sustituye al endpoint de
    prueba de la Semana 2).

    - password: solo en alta; en edición se rechaza (existe la acción
      restablecer-clave, que además cierra las sesiones abiertas).
    - username: obligatorio y único en alta; inmutable al editar.
    - rol: obligatorio y activo (el rol se cambia con el formulario, no
      con acciones de estado).
    - nombres y apellidos: obligatorios (la tabla y el menú usan el
      nombre completo; vacíos no ayudan a nadie).
    """

    password = serializers.CharField(
        write_only=True,
        required=False,
        error_messages={'required': 'La contraseña es obligatoria.'},
    )
    username = serializers.CharField(
        max_length=150,
        validators=[],
        error_messages={'required': 'El nombre de usuario es obligatorio.'},
    )
    rol = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(),
        error_messages={
            'required': 'El rol es obligatorio.',
            'does_not_exist': 'El rol indicado no existe.',
        },
    )

    class Meta:
        model = Usuario
        fields = (
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'email',
            'telefono',
            'rol',
        )

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate_username(self, value):
        valor = (value or '').strip()
        if not valor:
            raise serializers.ValidationError('El nombre de usuario es obligatorio.')
        if self.instance is not None and valor != self.instance.username:
            raise serializers.ValidationError(
                'El nombre de usuario no se puede modificar.'
            )
        return valor

    def validate_rol(self, value):
        if not value.activo:
            raise serializers.ValidationError('El rol indicado está inactivo.')
        return value

    def validate(self, attrs):
        for campo, etiqueta in (('first_name', 'nombres'), ('last_name', 'apellidos')):
            if campo in attrs and not (attrs[campo] or '').strip():
                raise serializers.ValidationError(
                    {campo: f'Los {etiqueta} son obligatorios.'}
                )
        if self.instance is None:
            valor = (attrs.get('username') or '').strip()
            existente = Usuario.objects.filter(username=valor).first()
            if existente is not None:
                raise serializers.ValidationError(
                    {
                        'username': (
                            f'Ya existe un usuario con el nombre de usuario '
                            f'«{valor}» (id {existente.pk}).'
                        ),
                        'usuario_existente': str(existente.pk),
                    }
                )
            if not attrs.get('password'):
                raise serializers.ValidationError(
                    {'password': 'La contraseña es obligatoria.'}
                )
            faltantes = {
                campo: f'Los {etiqueta} son obligatorios.'
                for campo, etiqueta in (
                    ('first_name', 'nombres'),
                    ('last_name', 'apellidos'),
                )
                if campo not in attrs
            }
            if faltantes:
                raise serializers.ValidationError(faltantes)
        else:
            if 'password' in attrs:
                raise serializers.ValidationError(
                    {
                        'password': (
                            'Para cambiar la contraseña use la acción '
                            'restablecer-clave.'
                        )
                    }
                )
            request = self.context.get('request')
            if request is not None and self.instance.pk == request.user.pk:
                rol_nuevo = attrs.get('rol')
                if rol_nuevo is not None and rol_nuevo.pk != self.instance.rol_id:
                    raise serializers.ValidationError(
                        {'rol': 'No puedes cambiar tu propio rol.'}
                    )
        return attrs

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)


class RestablecerClaveSerializer(serializers.Serializer):
    """Nueva contraseña de un usuario (Semana 12): write_only y con los
    validadores de Django (mensaje en español)."""

    password = serializers.CharField(
        write_only=True,
        error_messages={'required': 'La contraseña es obligatoria.'},
    )

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class CambiarClaveSerializer(serializers.Serializer):
    """Cambio de la propia contraseña (Semana 13, HU-112): exige la
    contraseña actual y una nueva con los validadores de Django."""

    password_actual = serializers.CharField(
        write_only=True,
        error_messages={'required': 'La contraseña actual es obligatoria.'},
    )
    password_nueva = serializers.CharField(
        write_only=True,
        error_messages={'required': 'La contraseña nueva es obligatoria.'},
    )

    def validate_password_nueva(self, value):
        # Con el usuario de la petición los validadores revisan también la
        # similitud con el nombre de usuario (UserAttributeSimilarityValidator)
        usuario = None
        peticion = self.context.get('request')
        if peticion is not None:
            usuario = peticion.user
        try:
            validate_password(value, user=usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value
