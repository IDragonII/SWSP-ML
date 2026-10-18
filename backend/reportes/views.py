"""API de reportes descargables (Semana 17, HU-141..HU-149).

Tres lecturas y una escritura bajo doble permiso:

- GET  /reportes/                     catálogo: solo los reportes que el
                                       usuario puede usar (reportes.ver
                                       + el ver del módulo de cada uno)
- GET  /reportes/{tipo}/vista-previa/ total de filas, primeras 20 y
                                       resumen (no registra eventos)
- POST /reportes/{tipo}/exportar/     genera el archivo en memoria y
                                       deja el evento EXPORTAR ANTES de
                                       entregarlo (si la auditoría falla
                                       → 503 sin archivo)

Filtros: los mismos del panel con la misma validación (400 si no son
válidos), combinables, en la query string; el formato (xlsx|pdf) va en
el cuerpo. Alcance del Técnico aplicado igual que en todo el sistema;
columnas y orden fijados por el servidor. Límites de filas (400 con el
número y la sugerencia, nunca se trunca), límite de 20 exportaciones
por hora y usuario (429 con retry_after; la vista previa no cuenta) y
cabeceras anti-caché con el nombre reporte_<tipo>_<fecha de Lima>.

Privacidad por diseño: los reportes no llevan DNI, teléfono ni
registrado_por (pregunta V, pendiente del responsable).
"""
import logging

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from auditoria.registrar import ip_de_request, registrar_evento
from dashboard.consultas import ahora_lima
from productores.views import PermisosPorAccion
from usuarios.permisos import permisos_de_peticion
from usuarios.ratelimit import exportaciones_restantes, registrar_exportacion

from . import catalogo, formato
from .consultas import preparar
from .excel import generar_excel
from .pdf import generar_pdf

logger = logging.getLogger(__name__)


class PermisosReportes(PermisosPorAccion):
    """Primera capa: reportes.ver (catálogo y vista previa) y
    reportes.exportar (exportar); la segunda capa —el ver del módulo de
    donde salen los datos— se exige en get_object."""

    permiso_requerido = "reportes.ver"
    PERMISOS = {
        "list": "reportes.ver",
        "vista_previa": "reportes.ver",
        "exportar": "reportes.exportar",
    }


class ReportesViewSet(PermisosReportes, viewsets.GenericViewSet):
    """Catálogo, vista previa y exportación de los reportes."""

    auditoria_modulo = "reportes"

    def list(self, request):
        """Catálogo (HU-149): solo reportes que este usuario puede usar."""
        permisos = permisos_de_peticion(request)
        return Response(
            {
                "reportes": [
                    {
                        "tipo": reporte["tipo"],
                        "nombre": reporte["nombre"],
                        "descripcion": reporte["descripcion"],
                        "filtros": list(reporte["filtros"]),
                        "formatos": list(catalogo.FORMATOS),
                        "limites": {
                            "xlsx": catalogo.limite_de("xlsx"),
                            "pdf": catalogo.limite_de("pdf"),
                        },
                        "aviso_privacidad": catalogo.AVISO_PRIVACIDAD,
                        # Semana 18: el de auditoría es «sensible» y su
                        # aviso acompaña a la confirmación de descarga
                        "sensible": bool(reporte.get("sensible")),
                        "aviso": reporte.get("aviso"),
                    }
                    for reporte in catalogo.disponibles(permisos)
                ]
            }
        )

    def get_object(self):
        """El reporte del path: 404 si no existe y 403 si el usuario no
        tiene el ver del módulo de donde salen sus datos (segunda capa)."""
        reporte = catalogo.obtener(self.kwargs["pk"])
        if reporte is None:
            raise NotFound("El tipo de reporte indicado no existe.")
        if reporte["permiso"] not in permisos_de_peticion(self.request):
            raise PermissionDenied("No tienes permiso para realizar esta acción.")
        return reporte

    @action(detail=True, methods=("get",), url_path="vista-previa")
    def vista_previa(self, request, pk=None):
        """Vista previa (HU-145): total de filas, primeras 20 y resumen.

        De solo lectura y sin eventos: contar filas no es exportar.
        """
        reporte = self.get_object()
        datos = preparar(reporte, request.user, request.query_params)
        return Response(
            {
                "tipo": reporte["tipo"],
                "nombre": reporte["nombre"],
                "total_filas": len(datos["filas"]),
                "limites": {
                    "xlsx": catalogo.limite_de("xlsx"),
                    "pdf": catalogo.limite_de("pdf"),
                },
                "columnas": [
                    {"clave": columna["clave"], "etiqueta": columna["etiqueta"]}
                    for columna in datos["columnas"]
                ],
                "filas": [
                    formato.vista_preview(datos["columnas"], fila)
                    for fila in datos["filas"][:20]
                ],
                "resumen": formato.resumen_preview(
                    reporte["tipo"], datos["resumen"]
                ),
                "advertencias": datos["advertencias"],
                "filtros": datos["filtros"],
                "filtros_texto": datos["filtros_texto"],
                "aviso_privacidad": catalogo.AVISO_PRIVACIDAD,
            }
        )

    @action(detail=True, methods=("post",), url_path="exportar")
    def exportar(self, request, pk=None):
        """Exportar (HU-143 y HU-144): reportes.exportar + el ver del
        módulo; formato en el cuerpo y filtros en la query.

        Orden: validaciones (formato, filtros, límite de filas), límite
        de frecuencia, generación en memoria, auditoría EXPORTAR y solo
        entonces la entrega del archivo con las cabeceras anti-caché.
        """
        reporte = self.get_object()
        formato_solicitado = (request.data or {}).get("formato")
        if formato_solicitado not in catalogo.FORMATOS:
            raise ValidationError({"formato": "Use xlsx o pdf."})
        datos = preparar(reporte, request.user, request.query_params)
        total = len(datos["filas"])
        limite = catalogo.limite_de(formato_solicitado)
        if total > limite:
            sugerencia = (
                "Descarga en Excel (admite más filas) o afina los filtros."
                if formato_solicitado == "pdf"
                else "Afina los filtros para reducir el número de filas."
            )
            return Response(
                {
                    "detail": (
                        f"El reporte tiene {total} filas y el máximo para "
                        f"{formato_solicitado.upper()} es {limite}. "
                        f"{sugerencia}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        restante = exportaciones_restantes(request.user.username)
        if restante is not None:
            respuesta = Response(
                {
                    "detail": (
                        "Has alcanzado el límite de exportaciones por hora. "
                        f"Intenta de nuevo en {restante} segundos."
                    ),
                    "retry_after": restante,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            respuesta["Retry-After"] = str(restante)
            return respuesta

        generado_en = ahora_lima()
        if formato_solicitado == "xlsx":
            contenido = generar_excel(
                reporte, datos, request.user.username, generado_en
            )
        else:
            contenido = generar_pdf(
                reporte, datos, request.user.username, generado_en
            )

        # Sin rastro no hay descarga: si la auditoría falla, no se entrega
        try:
            registrar_evento(
                usuario=request.user,
                accion="EXPORTAR",
                modulo=self.auditoria_modulo,
                detalle={
                    "tipo": reporte["tipo"],
                    "formato": formato_solicitado,
                    "filtros": datos["filtros"],
                    "filas": total,
                },
                ip=ip_de_request(request),
            )
        except Exception:
            logger.exception("No se pudo registrar la auditoría de la exportación")
            return Response(
                {
                    "detail": (
                        "No se pudo registrar la auditoría de la exportación; "
                        "no se entregó el archivo. Vuelve a intentarlo."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        registrar_exportacion(request.user.username)

        extension = "xlsx" if formato_solicitado == "xlsx" else "pdf"
        nombre = f"reporte_{reporte['tipo']}_{generado_en:%Y%m%d-%H%M}.{extension}"
        respuesta = HttpResponse(
            contenido, content_type=catalogo.CONTENT_TYPES[formato_solicitado]
        )
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        respuesta["Cache-Control"] = "no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta
