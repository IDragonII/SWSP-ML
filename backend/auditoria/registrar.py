"""Punto único de registro de auditoría (Semana 13, RF-71/RF-72).

registrar_evento se llama dentro de la transacción del evento de
negocio (AuditoriaMixin o los @action manuales): si el negocio falla,
el evento no se guarda — y viceversa. La IP es solo REMOTE_ADDR; la
cabecera X-Forwarded-For se ignora (no es fiable sin proxy de confianza).
"""
from .models import Auditoria


def ip_de_request(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None


def registrar_evento(
    *,
    usuario,
    accion,
    modulo,
    tabla=None,
    registro_id=None,
    detalle=None,
    ip=None,
):
    if not getattr(usuario, "is_authenticated", False):
        usuario = None
    Auditoria.objects.create(
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        detalle=detalle,
        ip=ip,
    )
