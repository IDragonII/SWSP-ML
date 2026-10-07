"""Endpoints de autenticación: login, refresh, logout y datos del usuario.

Contratos (docs/api_autenticacion.md):
- POST /api/auth/login/    → cookies + {usuario}; 401 genérico si falla; 429 si
                            la IP está limitada o la cuenta está bloqueada
- POST /api/auth/refresh/  → rota y refija cookies; 401 si inválido/vencido/cerrado
- POST /api/auth/logout/   → black-list del refresh y borra cookies; 401 sin sesión
- GET  /api/auth/me/       → {usuario}; 401 sin token o con token inválido
"""
import math
import logging

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from . import ratelimit
from .autenticacion import COOKIE_REFRESH, fijar_cookies_auth, limpiar_cookies_auth
from .permisos import TienePermiso
from .serializers import CrearUsuarioSerializer, DatosUsuarioSerializer

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
                return _respuesta_bloqueado(restante)
            return _credenciales_invalidas()

        ratelimit.limpiar_acceso(username)
        logger.info('login_correcto username=%s ip=%s', username, ip)
        refresh = RefreshToken.for_user(user)
        response = Response({'usuario': DatosUsuarioSerializer(user).data})
        fijar_cookies_auth(response, access=refresh.access_token, refresh=refresh)
        return response


class RenovarSesionView(APIView):
    """Renueva el access (y el refresh, si hay rotación). El token puede venir
    en la cookie httpOnly o en el cuerpo, para clientes nativos."""
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        bruto = request.data.get('refresh') or request.COOKIES.get(COOKIE_REFRESH)
        if not bruto:
            raise SesionInvalida()
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
        response = Response({'detail': 'Sesión cerrada.'})
        limpiar_cookies_auth(response)
        return response


class DatosSesionView(APIView):
    """Datos actuales del usuario: la única fuente de verdad del menú."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'usuario': DatosUsuarioSerializer(request.user).data})


class CrearUsuarioView(APIView):
    """Endpoint de prueba protegido con usuarios.crear.

    Demostración de la Semana 2: 401 sin token, 403 sin permiso, 200 con él.
    Todos los módulos futuros reutilizan TienePermiso de la misma forma.
    """
    permiso_requerido = 'usuarios.crear'
    permission_classes = (TienePermiso,)

    def post(self, request):
        serializador = CrearUsuarioSerializer(data=request.data)
        serializador.is_valid(raise_exception=True)
        usuario = serializador.save()
        return Response({
            'detail': 'Usuario creado.',
            'usuario': DatosUsuarioSerializer(usuario).data,
        })
