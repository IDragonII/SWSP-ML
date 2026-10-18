"""Endpoints de la app de usuarios: autenticación y gestión de cuentas.

Contratos (docs/api_autenticacion.md; Semana 12 amplía con la gestión):
- POST /api/auth/login/    → cookies + {usuario}; 401 genérico si falla; 429 si
                            la IP está limitada o la cuenta está bloqueada
- POST /api/auth/refresh/  → rota y refija cookies; 401 si inválido/vencido/cerrado
- POST /api/auth/logout/   → black-list del refresh y borra cookies; 401 sin sesión
- GET  /api/auth/me/       → {usuario}; 401 sin token o con token inválido

Gestión (Semana 12; el antiguo endpoint de prueba POST /api/usuarios/ es
ahora el CRUD completo, sin DELETE — las cuentas se desactivan):
- GET    /api/usuarios/               → lista (?busqueda=); usuarios.ver
- POST   /api/usuarios/               → alta (201 + ficha); usuarios.crear
- GET    /api/usuarios/{id}/          → ficha; usuarios.ver
- PATCH  /api/usuarios/{id}/          → edición; usuarios.editar
- POST   /api/usuarios/{id}/desactivar/      → usuarios.desactivar
- POST   /api/usuarios/{id}/reactivar/       → usuarios.desactivar
- POST   /api/usuarios/{id}/restablecer-clave/ → usuarios.editar
- POST   /api/usuarios/{id}/desbloquear/     → usuarios.editar
- GET    /api/roles/                  → roles activos (desplegable); usuarios.ver

Roles y permisos (Semana 14, HU-114..HU-118; SIN DELETE — los roles no se
borran y el trigger del Sprint 1 protege a los del sistema):
- GET    /api/roles-admin/            → listado paginado con conteos
                                         (?busqueda=&estado=&tipo=); roles.gestionar
- POST   /api/roles-admin/            → alta (nombre, limita_a_asignados,
                                         permisos o basado_en); roles.gestionar
- GET    /api/roles-admin/{id}/       → ficha + permisos; roles.gestionar
- PATCH  /api/roles-admin/{id}/       → nombre/descripción/limita; roles.gestionar
- POST   /api/roles-admin/{id}/desactivar/  → roles.gestionar
- POST   /api/roles-admin/{id}/reactivar/   → roles.gestionar
- PUT    /api/roles-admin/{id}/permisos/    → reemplaza el conjunto completo
                                         (agregados/quitados/afectados); roles.gestionar
- GET    /api/permisos-catalogo/      → catálogo agrupado por módulo; roles.gestionar
"""
import math
import logging

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from auditoria.mixins import AuditoriaMixin
from auditoria.registrar import ip_de_request, registrar_evento
from productores.views import BusquedaPorNombre, PermisosPorAccion

from . import ratelimit
from .autenticacion import (
    COOKIE_REFRESH,
    esperar_tras_marca,
    fijar_cookies_auth,
    limpiar_cookies_auth,
    marcar_sesion_cambiada,
    sesion_cambiada_despues,
)
from .models import Permiso, Rol, Usuario
from .permisos import DebeCambiarClave, TienePermiso
from .serializers import (
    CambiarClaveSerializer,
    DatosUsuarioSerializer,
    RestablecerClaveSerializer,
    RolDetalleSerializer,
    RolEdicionSerializer,
    RolEscrituraSerializer,
    RolListaSerializer,
    RolPermisosSerializer,
    RolSerializer,
    UsuarioDetalleSerializer,
    UsuarioEscrituraSerializer,
    UsuarioListaSerializer,
)

logger = logging.getLogger('sigpa.seguridad')

DETALLE_CREDENCIALES = 'Credenciales incorrectas.'
DETALLE_SESION = 'Sesión inválida o expirada.'


class SesionInvalida(APIException):
    """401 único para refresh/logout inválidos, vencidos o ya cerrados."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = DETALLE_SESION
    default_code = 'session_invalid'


def _credenciales_invalidas():
    # Mismo cuerpo para usuario inexistente, clave incorrecta o usuario
    # desactivado: nunca se revela si la cuenta existe.
    return Response({'detail': DETALLE_CREDENCIALES}, status=status.HTTP_401_UNAUTHORIZED)


def _respuesta_bloqueado(segundos_restantes):
    """429 del bloqueo de cuenta: indica cuánto esperar sin pistas de la cuenta."""
    minutos = max(1, math.ceil(segundos_restantes / 60))
    respuesta = Response(
        {
            'detail': f'Demasiados intentos fallidos. Inténtalo de nuevo en {minutos} minuto(s).',
            'retry_after': segundos_restantes,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    respuesta['Retry-After'] = str(segundos_restantes)
    return respuesta


def _ip_de(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'desconocida')


class LoginView(APIView):
    """Iniciar sesión. Autenticación desactivada: una cookie vieja no debe
    impedir volver a entrar.

    Rate limit: límite por IP (throttle con scope 'login') + bloqueo de la
    cuenta tras LOGIN_INTENTOS fallos (usuarios/ratelimit.py).
    """
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'login'

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        ip = _ip_de(request)

        restante = ratelimit.segundos_de_bloqueo(username)
        if restante is not None:
            logger.warning('login_bloqueado username=%s ip=%s restante_s=%s', username, ip, restante)
            return _respuesta_bloqueado(restante)

        user = authenticate(request=request, username=username, password=password)
        if user is None:
            bloqueado, restante = ratelimit.registrar_fallo(username)
            logger.warning('login_fallido username=%s ip=%s', username, ip)
            if bloqueado:
                logger.warning('login_bloqueado username=%s ip=%s restante_s=%s',
                               username, ip, restante)
                registrar_evento(
                    usuario=Usuario.objects.filter(username=username).first(),
                    accion='BLOQUEAR',
                    modulo='usuarios',
                    tabla='usuarios',
                    detalle={'username': username},
                    ip=ip_de_request(request),
                )
                return _respuesta_bloqueado(restante)
            return _credenciales_invalidas()

        ratelimit.limpiar_acceso(username)
        logger.info('login_correcto username=%s ip=%s', username, ip)
        registrar_evento(
            usuario=user,
            accion='LOGIN',
            modulo='usuarios',
            tabla='usuarios',
            registro_id=user.pk,
            ip=ip_de_request(request),
        )
        # Si la cuenta acababa de pasar por una marca de sesión (cambio o
        # restablecimiento de clave), los tokens nuevos esperan al segundo
        # siguiente para no quedar invalidados por la propia marca (HU-113).
        esperar_tras_marca(user.pk)
        refresh = RefreshToken.for_user(user)
        response = Response({'usuario': DatosUsuarioSerializer(user).data})
        fijar_cookies_auth(response, access=refresh.access_token, refresh=refresh)
        return response

class RenovarSesionView(APIView):
    """Renueva el access (y el refresh, si hay rotación). El token puede venir
    en la cookie httpOnly o en el cuerpo, para clientes nativos. Un refresh
    emitido antes de la última marca de sesión (Semana 12: restablecimiento
    de contraseña o desactivación) ya no rota: el usuario vuelve a entrar."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        bruto = request.data.get('refresh') or request.COOKIES.get(COOKIE_REFRESH)
        if not bruto:
            raise SesionInvalida()
        try:
            token = RefreshToken(bruto)
        except TokenError:
            raise SesionInvalida()
        if sesion_cambiada_despues(
            token.payload.get('user_id'), token.payload.get('iat')
        ):
            raise SesionInvalida('Sesión cerrada por cambio de credenciales.')
        try:
            serializador = TokenRefreshSerializer(data={'refresh': bruto})
            serializador.is_valid(raise_exception=True)
        except TokenError:
            raise SesionInvalida()
        datos = serializador.validated_data
        response = Response({
            'access': datos['access'],
            **({'refresh': datos['refresh']} if 'refresh' in datos else {}),
        })
        fijar_cookies_auth(
            response,
            access=datos['access'],
            refresh=datos.get('refresh'),
        )
        return response


class CerrarSesionView(APIView):
    """Invalida el refresh (lista de tokens invalidados) y borra las cookies."""
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        bruto = request.data.get('refresh') or request.COOKIES.get(COOKIE_REFRESH)
        if not bruto:
            raise SesionInvalida('No hay sesión activa.')
        try:
            token = RefreshToken(bruto)
            token.check_blacklist()
            token.blacklist()
        except TokenError:
            raise SesionInvalida('No hay sesión activa.')
        registrar_evento(
            usuario=Usuario.objects.filter(
                pk=token.payload.get('user_id')
            ).first(),
            accion='LOGOUT',
            modulo='usuarios',
            tabla='usuarios',
            ip=ip_de_request(request),
        )
        response = Response({'detail': 'Sesión cerrada.'})
        limpiar_cookies_auth(response)
        return response


class CambiarClaveView(APIView):
    """Cambio de la propia contraseña (HU-112, Semana 13, RF-73).

    Exige la contraseña actual y una nueva con los validadores de Django.
    Al guardar: cierra todas las sesiones abiertas (marca de sesión),
    limpia la marca debe_cambiar_clave, borra el contador de intentos y
    emite cookies nuevas (las anteriores quedaron invalidadas), para que
    la interfaz siga dentro sin volver a entrar. Máximo 5 intentos por
    usuario y hora (429 con los minutos a esperar).
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        usuario = request.user
        permitido, restante = ratelimit.registrar_cambio_clave(usuario.username)
        if not permitido:
            minutos = max(1, math.ceil(restante / 60))
            respuesta = Response(
                {
                    'detail': (
                        f'Demasiados intentos de cambio de contraseña. '
                        f'Inténtalo de nuevo en {minutos} minuto(s).'
                    ),
                    'retry_after': restante,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            respuesta['Retry-After'] = str(restante)
            return respuesta
        serializador = CambiarClaveSerializer(
            data=request.data, context={'request': request}
        )
        serializador.is_valid(raise_exception=True)
        if not usuario.check_password(
            serializador.validated_data['password_actual']
        ):
            raise ValidationError(
                {'password_actual': 'La contraseña actual no es correcta.'}
            )
        with transaction.atomic():
            usuario.set_password(serializador.validated_data['password_nueva'])
            usuario.debe_cambiar_clave = False
            usuario.save(update_fields=('password', 'debe_cambiar_clave'))
            marcar_sesion_cambiada(usuario.pk)
            registrar_evento(
                usuario=usuario,
                accion='CAMBIAR_CLAVE',
                modulo='usuarios',
                tabla='usuarios',
                registro_id=usuario.pk,
                ip=ip_de_request(request),
            )
        ratelimit.limpiar_cambio_clave(usuario.username)
        logger.info('clave_cambiada id=%s', usuario.pk)
        # La marca de sesión acaba de invalidar los tokens antiguos; los
        # nuevos esperan al segundo siguiente para no caer en esa misma
        # invalidación por iat con precisión de segundo (HU-113).
        esperar_tras_marca(usuario.pk)
        refresh = RefreshToken.for_user(usuario)
        response = Response(
            {
                'detail': 'Contraseña actualizada.',
                'usuario': DatosUsuarioSerializer(usuario).data,
            }
        )
        fijar_cookies_auth(
            response, access=refresh.access_token, refresh=refresh
        )
        return response


class DatosSesionView(APIView):
    """Datos actuales del usuario: la única fuente de verdad del menú."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'usuario': DatosUsuarioSerializer(request.user).data})


class PermisosUsuario(PermisosPorAccion):
    """Permisos de la gestión de usuarios (Semana 12): el catálogo de la
    Semana 2 (usuarios.ver/crear/editar/desactivar). Desactivar y
    reactivar comparten el de estado; restablecer la contraseña y
    desbloquear son mantenimiento (usuarios.editar)."""

    permiso_requerido = 'usuarios.ver'
    PERMISOS = {
        'list': 'usuarios.ver',
        'retrieve': 'usuarios.ver',
        'create': 'usuarios.crear',
        'update': 'usuarios.editar',
        'partial_update': 'usuarios.editar',
        'desactivar': 'usuarios.desactivar',
        'reactivar': 'usuarios.desactivar',
        'restablecer_clave': 'usuarios.editar',
        'desbloquear': 'usuarios.editar',
    }


class UsuarioViewSet(
    AuditoriaMixin,
    PermisosUsuario,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Gestión de usuarios (Semana 12): SIN DELETE (405) — las cuentas se
    desactivan, nunca se borran (la traza es de auditoría y el rol
    protege las filas). El bloqueo por intentos fallidos vive en caché
    (usuarios/ratelimit.py): la acción desbloquear solo lo limpia y la
    ficha enseña los segundos restantes. Restablecer la contraseña cierra
    las sesiones abiertas del usuario (marca de sesión en autenticación).
    """

    auditoria_modulo = 'usuarios'
    queryset = Usuario.objects.select_related('rol').order_by(
        'last_name', 'first_name', 'username'
    )
    serializer_class = UsuarioDetalleSerializer
    escritura_serializer = UsuarioEscrituraSerializer
    filter_backends = (BusquedaPorNombre,)
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return self.escritura_serializer
        if self.action == 'list':
            return UsuarioListaSerializer
        return self.serializer_class

    @staticmethod
    def _gestiona_roles(rol):
        """El rol concede el permiso de gestionar roles (HU-103: nunca
        perder al último). Los superusuarios también pasan por aquí: se
        rigen por su rol (docs/decisiones_seguridad.md §7)."""
        if rol is None:
            return False
        return rol.permisos.filter(codigo='roles.gestionar').exists()

    def _exigir_gestor_restante(self, usuario, se_perdiera):
        if not se_perdiera:
            return
        queda_otro = (
            Usuario.objects.filter(
                is_active=True, rol__permisos__codigo='roles.gestionar'
            )
            .exclude(pk=usuario.pk)
            .exists()
        )
        if not queda_otro:
            raise ValidationError(
                {
                    'estado': (
                        'Debe quedar al menos un usuario activo con permiso '
                        'para gestionar roles.'
                    )
                }
            )

    def _lectura(self, obj):
        return UsuarioDetalleSerializer(obj, context=self.get_serializer_context())

    def create(self, request, *args, **kwargs):
        serializador = self.get_serializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        with transaction.atomic():
            serializador.save()
            self._registrar_auditoria('CREAR', serializador.instance)
        return Response(self._lectura(serializador.instance).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        usuario = self.get_object()
        serializador = self.get_serializer(usuario, data=request.data, partial=partial)
        serializador.is_valid(raise_exception=True)
        rol_final = serializador.validated_data.get('rol', usuario.rol)
        se_pierde = (
            usuario.is_active
            and self._gestiona_roles(usuario.rol)
            and not self._gestiona_roles(rol_final)
        )
        self._exigir_gestor_restante(usuario, se_pierde)
        with transaction.atomic():
            serializador.save()
            self._registrar_auditoria('MODIFICAR', serializador.instance)
        return Response(self._lectura(serializador.instance).data)

    @action(detail=True, methods=('post',), url_path='desactivar')
    def desactivar(self, request, pk=None):
        """Desactiva la cuenta (HU-101): no puede ser la propia y debe
        seguir quedando alguien activo con roles.gestionar. Las sesiones
        abiertas quedan invalidadas con la marca de sesión (y simplejwt
        ya rechaza tokens de cuentas inactivas)."""
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            raise ValidationError({'estado': 'No puedes desactivar tu propia cuenta.'})
        if not usuario.is_active:
            raise ValidationError({'estado': 'El usuario ya está desactivado.'})
        self._exigir_gestor_restante(
            usuario, usuario.is_active and self._gestiona_roles(usuario.rol)
        )
        with transaction.atomic():
            usuario.is_active = False
            usuario.save(update_fields=('is_active',))
            marcar_sesion_cambiada(usuario.pk)
            self._registrar_auditoria('DESACTIVAR', usuario)
        logger.info(
            'usuario_desactivado id=%s por=%s', usuario.pk, request.user.pk
        )
        return Response(self._lectura(usuario).data)

    @action(detail=True, methods=('post',), url_path='reactivar')
    def reactivar(self, request, pk=None):
        """Reactiva una cuenta desactivada (HU-101). No se marca sesión:
        los tokens anteriores a la desactivación quedaron invalidados con
        ella y la reactivación no debe revivirlos."""
        usuario = self.get_object()
        if usuario.is_active:
            raise ValidationError({'estado': 'El usuario ya está activo.'})
        with transaction.atomic():
            usuario.is_active = True
            usuario.save(update_fields=('is_active',))
            self._registrar_auditoria('ACTIVAR', usuario)
        logger.info('usuario_reactivado id=%s por=%s', usuario.pk, request.user.pk)
        return Response(self._lectura(usuario).data)

    @action(detail=True, methods=('post',), url_path='restablecer-clave')
    def restablecer_clave(self, request, pk=None):
        """Pone una contraseña nueva a un usuario (HU-104): cierra sus
        sesiones abiertas (marca de sesión) y limpia el bloqueo por
        intentos fallidos. No es la cuenta propia: el cambio propio de
        contraseña llega en una función aparte (Sprint 7)."""
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            raise ValidationError(
                {
                    'password': (
                        'No puedes restablecer tu propia contraseña desde '
                        'aquí; el cambio propio llega en una función aparte.'
                    )
                }
            )
        serializador = RestablecerClaveSerializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        with transaction.atomic():
            usuario.set_password(serializador.validated_data['password'])
            # Semana 13 (HU-112): el restablecimiento admin exige que el
            # usuario cambie su contraseña en el primer ingreso.
            usuario.debe_cambiar_clave = True
            usuario.save(update_fields=('password', 'debe_cambiar_clave'))
            marcar_sesion_cambiada(usuario.pk)
            ratelimit.limpiar_acceso(usuario.username, motivo='manual')
            self._registrar_auditoria('RESTABLECER_CLAVE', usuario)
        logger.info('clave_restablecida id=%s por=%s', usuario.pk, request.user.pk)
        return Response(
            {
                'detail': 'Contraseña restablecida.',
                'usuario': self._lectura(usuario).data,
            }
        )

    @action(detail=True, methods=('post',), url_path='desbloquear')
    def desbloquear(self, request, pk=None):
        """Limpia el bloqueo por intentos fallidos (HU-103, Semana 12: el
        panel de Django ya lo ofrecía). No toca la cuenta ni su estado:
        solo la caché. La respuesta aclara si había un bloqueo activo."""
        usuario = self.get_object()
        habia_bloqueo = ratelimit.limpiar_acceso(usuario.username, motivo='manual')
        if habia_bloqueo:
            self._registrar_auditoria('DESBLOQUEAR', usuario)
        logger.info(
            'usuario_desbloqueado id=%s habia_bloqueo=%s por=%s',
            usuario.pk, habia_bloqueo, request.user.pk,
        )
        return Response(
            {
                'detail': (
                    'Acceso desbloqueado.'
                    if habia_bloqueo
                    else 'El usuario no estaba bloqueado.'
                ),
                'usuario': self._lectura(usuario).data,
            }
        )


class RolViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Roles activos para el desplegable del formulario de usuarios
    (Semana 12): solo listado, sin paginación (lista corta) y exige
    usuarios.ver — quien no ve usuarios no necesita la lista de roles.
    La gestión completa vive en RolAdminViewSet (Semana 14)."""

    permission_classes = (DebeCambiarClave, TienePermiso)
    permiso_requerido = 'usuarios.ver'
    queryset = Rol.objects.filter(activo=True)
    serializer_class = RolSerializer
    pagination_class = None


class PermisosRolesAdmin(PermisosPorAccion):
    """Gestión de roles y permisos (Semana 14, HU-120): roles.gestionar
    en todas las acciones — es control total sobre los permisos."""

    permiso_requerido = 'roles.gestionar'
    PERMISOS = {
        accion: 'roles.gestionar'
        for accion in (
            'list',
            'retrieve',
            'create',
            'update',
            'partial_update',
            'desactivar',
            'reactivar',
            'permisos',
        )
    }


class RolAdminViewSet(
    AuditoriaMixin,
    PermisosRolesAdmin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Administración de roles (Semana 14, HU-114..HU-118): SIN DELETE
    (405) — los roles no se borran y el trigger del Sprint 1 protege a
    los del sistema. El Administrador conserva siempre los 55 permisos
    del catálogo; Técnico y Coordinador admiten editar permisos y
    descripción pero no su nombre ni su condición de limitar a
    asignados. Última escritura gana: dos administradores editando a la
    vez guardan el último conjunto y la auditoría refleja cada diff."""

    auditoria_modulo = 'roles'
    auditoria_tabla = 'roles'
    queryset = Rol.objects.all().order_by('nombre')
    filter_backends = (BusquedaPorNombre,)
    search_fields = ('nombre',)

    def get_queryset(self):
        queryset = (
            Rol.objects.all()
            .order_by('nombre')
            .annotate(
                usuarios_activos=Count(
                    'usuarios',
                    filter=Q(usuarios__is_active=True),
                    distinct=True,
                ),
                total_permisos=Count('permisos', distinct=True),
            )
        )
        estado = (self.request.query_params.get('estado') or '').strip().lower()
        if estado == 'activo':
            queryset = queryset.filter(activo=True)
        elif estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        elif estado:
            raise ValidationError({'estado': 'Usa «activo» o «inactivo».'})
        tipo = (self.request.query_params.get('tipo') or '').strip().lower()
        if tipo == 'sistema':
            queryset = queryset.filter(es_sistema=True)
        elif tipo == 'personalizado':
            queryset = queryset.filter(es_sistema=False)
        elif tipo:
            raise ValidationError({'tipo': 'Usa «sistema» o «personalizado».'})
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return RolListaSerializer
        if self.action == 'create':
            return RolEscrituraSerializer
        if self.action in ('update', 'partial_update'):
            return RolEdicionSerializer
        return RolDetalleSerializer

    def create(self, request, *args, **kwargs):
        serializador = RolEscrituraSerializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        codigos = serializador.validated_data.get('_codigos', [])
        with transaction.atomic():
            rol = serializador.save()
            self._registrar_auditoria(
                'CREAR', rol, detalle={'permisos': sorted(codigos)}
            )
        return Response(
            RolDetalleSerializer(rol, context=self.get_serializer_context()).data,
            status=201,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        rol = self.get_object()
        serializador = self.get_serializer(
            rol, data=request.data, partial=partial
        )
        serializador.is_valid(raise_exception=True)
        with transaction.atomic():
            serializador.save()
            self._registrar_auditoria('MODIFICAR', rol)
        return Response(
            RolDetalleSerializer(rol, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=('post',), url_path='desactivar')
    def desactivar(self, request, pk=None):
        """Desactiva un rol sin usuarios activos (HU-118): los roles del
        sistema no se desactivan y el historial se conserva (sin borrar)."""
        rol = self.get_object()
        if rol.es_sistema:
            raise ValidationError(
                {'estado': 'Los roles del sistema no se pueden desactivar.'}
            )
        if not rol.activo:
            raise ValidationError({'estado': 'El rol ya está desactivado.'})
        con_cuentas = rol.usuarios.filter(is_active=True).count()
        if con_cuentas:
            plural = 's' if con_cuentas != 1 else ''
            raise ValidationError(
                {
                    'estado': (
                        f'No se puede desactivar el rol: tiene {con_cuentas} '
                        f'usuario{plural} activo{plural}.'
                    )
                }
            )
        with transaction.atomic():
            rol.activo = False
            rol.save(update_fields=('activo',))
            self._registrar_auditoria('DESACTIVAR', rol)
        logger.info('rol_desactivado id=%s por=%s', rol.pk, request.user.pk)
        return Response(RolDetalleSerializer(rol).data)

    @action(detail=True, methods=('post',), url_path='reactivar')
    def reactivar(self, request, pk=None):
        """Reactiva un rol desactivado (HU-118)."""
        rol = self.get_object()
        if rol.activo:
            raise ValidationError({'estado': 'El rol ya está activo.'})
        with transaction.atomic():
            rol.activo = True
            rol.save(update_fields=('activo',))
            self._registrar_auditoria('ACTIVAR', rol)
        logger.info('rol_reactivado id=%s por=%s', rol.pk, request.user.pk)
        return Response(RolDetalleSerializer(rol).data)

    @action(detail=True, methods=('put',), url_path='permisos')
    def permisos(self, request, pk=None):
        """Reemplaza el conjunto completo de permisos del rol (HU-115) en
        una sola transacción: o se guarda todo o nada. Responde los
        códigos agregados y quitados y cuántos usuarios activos se ven
        afectados; si el conjunto es igual, no hace nada ni registra
        evento. El Administrador nunca admite cambios (siempre los 55) y
        nadie se puede quitar roles.gestionar de su propio rol."""
        rol = self.get_object()
        if rol.nombre == 'Administrador':
            raise ValidationError(
                {
                    'permisos': (
                        'Los permisos del rol Administrador no se pueden '
                        'cambiar: siempre tiene todos los permisos del '
                        'catálogo.'
                    )
                }
            )
        serializador = RolPermisosSerializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        nuevos = serializador.validated_data['permisos']
        actuales = sorted(rol.permisos.values_list('codigo', flat=True))
        afectados = rol.usuarios.filter(is_active=True).count()
        if sorted(nuevos) == actuales:
            return Response(
                {
                    'detail': 'Sin cambios: el rol ya tenía esos permisos.',
                    'permisos': actuales,
                    'agregados': [],
                    'quitados': [],
                    'usuarios_afectados': afectados,
                }
            )
        if (
            request.user.rol_id == rol.pk
            and 'roles.gestionar' in actuales
            and 'roles.gestionar' not in nuevos
        ):
            raise ValidationError(
                {
                    'permisos': (
                        'No puedes quitarte el permiso de gestionar roles '
                        'de tu propio rol.'
                    )
                }
            )
        if 'roles.gestionar' in actuales and 'roles.gestionar' not in nuevos:
            queda_gestor = (
                Usuario.objects.filter(
                    is_active=True, rol__permisos__codigo='roles.gestionar'
                )
                .exclude(rol_id=rol.pk)
                .exists()
            )
            if not queda_gestor:
                raise ValidationError(
                    {
                        'permisos': (
                            'Debe quedar al menos un usuario activo con '
                            'permiso para gestionar roles.'
                        )
                    }
                )
        agregados = sorted(set(nuevos) - set(actuales))
        quitados = sorted(set(actuales) - set(nuevos))
        with transaction.atomic():
            rol.permisos.set(Permiso.objects.filter(codigo__in=nuevos))
            self._registrar_auditoria(
                'MODIFICAR',
                rol,
                detalle={'agregados': agregados, 'quitados': quitados},
            )
        logger.info(
            'rol_permisos_cambiados id=%s agregados=%s quitados=%s por=%s',
            rol.pk, len(agregados), len(quitados), request.user.pk,
        )
        return Response(
            {
                'detail': 'Permisos actualizados.',
                'permisos': sorted(nuevos),
                'agregados': agregados,
                'quitados': quitados,
                'usuarios_afectados': afectados,
            }
        )


class CatalogoPermisosView(APIView):
    """Catálogo de permisos (Semana 14): solo lectura, agrupado por
    módulo y con su descripción — lo define el desarrollador, no el
    Administrador. Dibuja la matriz de la pantalla de roles."""

    permission_classes = (DebeCambiarClave, TienePermiso)
    permiso_requerido = 'roles.gestionar'

    def get(self, request):
        grupos = {}
        for permiso in Permiso.objects.order_by('modulo', 'codigo'):
            grupos.setdefault(permiso.modulo, []).append(
                {
                    'codigo': permiso.codigo,
                    'accion': permiso.accion,
                    'descripcion': permiso.descripcion,
                }
            )
        return Response(
            {
                'modulos': [
                    {'modulo': modulo, 'permisos': permisos}
                    for modulo, permisos in grupos.items()
                ]
            }
        )
