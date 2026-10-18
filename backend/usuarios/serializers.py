"""Serializadores de la sesión, la gestión de usuarios y los roles.

Semana 2: datos de la sesión (DatosUsuarioSerializer) y alta de prueba
(CrearUsuarioSerializer). Semana 12: la gestión completa sustituye al
endpoint de prueba — UsuarioListaSerializer (tabla), UsuarioDetalleSerializer
(ficha), UsuarioEscrituraSerializer (alta y edición) y
RestablecerClaveSerializer; más RolSerializer reutilizado por el
desplegable de roles.

Semana 14 (HU-114..HU-116): los serializers de gestión de roles —
RolListaSerializer (tabla), RolDetalleSerializer (ficha con permisos),
RolEscrituraSerializer (alta con «basado en»), RolEdicionSerializer
(nombre/descripción/limita_a_asignados) y RolPermisosSerializer
(reemplazo del conjunto completo).
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from . import ratelimit
from .dependencias import validar_dependencias
from .models import Permiso, Rol, RolPermiso, Usuario


class RolSerializer(serializers.ModelSerializer):
    """Desplegable de roles (Semana 12): lista corta para Usuarios."""

    class Meta:
        model = Rol
        fields = ('id', 'nombre')


class RolListaSerializer(serializers.ModelSerializer):
    """Fila del listado de gestión (Semana 14): nombre, descripción, tipo,
    alcance, número de usuarios y de permisos, y estado. Los conteos
    vienen anotados en el listado; en el detalle se calculan."""

    usuarios_activos = serializers.SerializerMethodField()
    total_permisos = serializers.SerializerMethodField()

    class Meta:
        model = Rol
        fields = (
            'id',
            'nombre',
            'descripcion',
            'es_sistema',
            'limita_a_asignados',
            'activo',
            'usuarios_activos',
            'total_permisos',
        )

    def get_usuarios_activos(self, obj):
        anotado = getattr(obj, 'usuarios_activos', None)
        if anotado is not None:
            return anotado
        return obj.usuarios.filter(is_active=True).count()

    def get_total_permisos(self, obj):
        anotado = getattr(obj, 'total_permisos', None)
        if anotado is not None:
            return anotado
        return obj.permisos.count()


class RolDetalleSerializer(RolListaSerializer):
    """Ficha: los datos del listado más los códigos de permiso asignados."""

    permisos = serializers.SerializerMethodField()

    class Meta(RolListaSerializer.Meta):
        fields = RolListaSerializer.Meta.fields + ('permisos',)

    def get_permisos(self, obj):
        return sorted(obj.permisos.values_list('codigo', flat=True))


class RolEscrituraSerializer(serializers.ModelSerializer):
    """Alta de un rol (Semana 14): nombre normalizado y único sin
    distinguir mayúsculas, descripción opcional, limita_a_asignados
    obligatorio y explícito (sin valor por defecto), y los permisos como
    lista de códigos o «basado en» otro rol (no ambos). El cliente no
    puede enviar es_sistema: la pantalla nunca crea roles del sistema."""

    nombre = serializers.CharField(
        max_length=50,
        error_messages={'required': 'El nombre del rol es obligatorio.'},
    )
    descripcion = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=''
    )
    limita_a_asignados = serializers.BooleanField(
        error_messages={
            'required': (
                'Indica si el rol limita a los productores asignados.'
            )
        }
    )
    permisos = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    basado_en = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(), required=False
    )

    class Meta:
        model = Rol
        fields = (
            'nombre',
            'descripcion',
            'limita_a_asignados',
            'permisos',
            'basado_en',
        )

    def validate_nombre(self, value):
        nombre = ' '.join((value or '').split())
        if len(nombre) < 3:
            raise serializers.ValidationError(
                'El nombre del rol debe tener al menos 3 caracteres.'
            )
        existente = Rol.objects.filter(nombre__iexact=nombre).first()
        if existente is not None:
            raise serializers.ValidationError(
                f'Ya existe un rol con el nombre «{nombre}» '
                f'(id {existente.pk}).'
            )
        return nombre

    def validate(self, attrs):
        if 'permisos' in attrs and 'basado_en' in attrs:
            raise serializers.ValidationError(
                {
                    'permisos': (
                        'Elige permisos directos o «basado en» otro rol, '
                        'no ambos.'
                    )
                }
            )
        codigos = self._codigos_validos(attrs)
        validar_dependencias(codigos)
        attrs['_codigos'] = codigos
        return attrs

    @staticmethod
    def _codigos_validos(attrs):
        """Resuelve la lista final de códigos y rechaza los desconocidos."""
        if attrs.get('basado_en') is not None:
            codigos = list(
                attrs['basado_en'].permisos.values_list('codigo', flat=True)
            )
        else:
            codigos = []
            for item in attrs.get('permisos') or []:
                codigo = (item or '').strip()
                if codigo and codigo not in codigos:
                    codigos.append(codigo)
        conocidos = set(Permiso.objects.values_list('codigo', flat=True))
        desconocidos = [c for c in codigos if c not in conocidos]
        if desconocidos:
            raise serializers.ValidationError(
                {
                    'permisos': [
                        f'El permiso «{codigo}» no existe.'
                        for codigo in desconocidos
                    ]
                }
            )
        return codigos

    def create(self, validated_data):
        codigos = validated_data.pop('_codigos', [])
        validated_data.pop('permisos', None)
        validated_data.pop('basado_en', None)
        rol = Rol.objects.create(es_sistema=False, activo=True, **validated_data)
        permisos = {
            p.codigo: p for p in Permiso.objects.filter(codigo__in=codigos)
        }
        RolPermiso.objects.bulk_create(
            RolPermiso(rol=rol, permiso=permisos[codigo]) for codigo in codigos
        )
        return rol


class RolEdicionSerializer(serializers.ModelSerializer):
    """Edición de datos de un rol (Semana 14): nombre, descripción y
    limita_a_asignados. En los roles del sistema el nombre no cambia y
    el alcance tampoco; en un rol personalizado con usuarios el alcance
    tampoco (cambiaría de golpe lo que ven)."""

    nombre = serializers.CharField(max_length=50, required=False)
    descripcion = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    limita_a_asignados = serializers.BooleanField(required=False)

    class Meta:
        model = Rol
        fields = ('nombre', 'descripcion', 'limita_a_asignados')

    def validate_nombre(self, value):
        nombre = ' '.join((value or '').split())
        if len(nombre) < 3:
            raise serializers.ValidationError(
                'El nombre del rol debe tener al menos 3 caracteres.'
            )
        if self.instance.es_sistema:
            raise serializers.ValidationError(
                'El nombre de un rol del sistema no se modifica.'
            )
        existente = (
            Rol.objects.filter(nombre__iexact=nombre)
            .exclude(pk=self.instance.pk)
            .first()
        )
        if existente is not None:
            raise serializers.ValidationError(
                f'Ya existe un rol con el nombre «{nombre}» '
                f'(id {existente.pk}).'
            )
        return nombre

    def validate_limita_a_asignados(self, value):
        if self.instance.es_sistema:
            raise serializers.ValidationError(
                'No se puede cambiar «limita a asignados» de un rol del '
                'sistema.'
            )
        if self.instance.usuarios.exists():
            raise serializers.ValidationError(
                'No se puede cambiar «limita a asignados» de un rol que '
                'tiene usuarios.'
            )
        return value


class RolPermisosSerializer(serializers.Serializer):
    """Reemplazo del conjunto completo de permisos de un rol (Semana 14):
    lista de códigos, sin duplicados, existentes y con sus dependencias
    cumplidas. La lista vacía es válida: retira todos los permisos."""

    permisos = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        error_messages={
            'required': 'La lista de permisos es obligatoria.'
        },
    )

    def validate_permisos(self, value):
        codigos = []
        for item in value:
            codigo = (item or '').strip()
            if codigo and codigo not in codigos:
                codigos.append(codigo)
        conocidos = set(Permiso.objects.values_list('codigo', flat=True))
        desconocidos = [c for c in codigos if c not in conocidos]
        if desconocidos:
            raise serializers.ValidationError(
                [
                    f'El permiso «{codigo}» no existe.'
                    for codigo in desconocidos
                ]
            )
        validar_dependencias(codigos)
        return codigos


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
