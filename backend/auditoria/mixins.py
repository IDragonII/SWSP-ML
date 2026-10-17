"""Mezcla de auditoría para los ViewSets que escriben (Semana 13, RF-72).

perform_create/perform_update registran el evento en la misma
transacción que el negocio (sin ATOMIC_REQUESTS global). Los ViewSets
con perform_create propio (productores, campanias…) conservan su
método y añaden _registrar_auditoria('CREAR', obj) dentro de su bloque
atómico; los @action de estado/anular usan la acción que corresponda.
"""
from django.db import transaction

from .registrar import ip_de_request, registrar_evento


class AuditoriaMixin:
    auditoria_modulo = ""
    auditoria_tabla = None  # None = db_table del modelo del queryset

    def _registrar_auditoria(
        self, accion, obj=None, registro_id=None, detalle=None, tabla=None
    ):
        if registro_id is None and obj is not None:
            registro_id = obj.pk
        if tabla is None:
            tabla = self.auditoria_tabla
        if tabla is None:
            tabla = self.get_queryset().model._meta.db_table
        registrar_evento(
            usuario=self.request.user,
            accion=accion,
            modulo=self.auditoria_modulo,
            tabla=tabla,
            registro_id=registro_id,
            detalle=detalle,
            ip=ip_de_request(self.request),
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            obj = serializer.save()
            self._registrar_auditoria("CREAR", obj)

    def perform_update(self, serializer):
        with transaction.atomic():
            obj = serializer.save()
            self._registrar_auditoria("MODIFICAR", obj)
