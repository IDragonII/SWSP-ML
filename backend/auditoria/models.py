from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

ACCIONES = [
    ("CREAR", "Crear"),
    ("MODIFICAR", "Modificar"),
    ("ELIMINAR", "Eliminar"),
    ("ACTIVAR", "Activar"),
    ("DESACTIVAR", "Desactivar"),
    ("ANULAR", "Anular"),
    ("REACTIVAR", "Reactivar"),
    ("ASIGNAR", "Asignar"),
    ("DESASIGNAR", "Desasignar"),
    ("LOGIN", "Iniciar sesión"),
    ("LOGOUT", "Cerrar sesión"),
    ("BLOQUEAR", "Bloquear acceso"),
    ("DESBLOQUEAR", "Desbloquear acceso"),
    ("RESTABLECER_CLAVE", "Restablecer contraseña"),
    ("CAMBIAR_CLAVE", "Cambiar contraseña"),
]


class Auditoria(models.Model):
    """Registro inmutable de acciones del sistema (Semana 13, RF-71/RF-72).

    Solo se inserta (la API lo hace en el mismo evento de negocio); un
    trigger (fn_auditoria_inmutable) impide UPDATE y DELETE. Quien no
    tiene `auditoria.ver` no ve la tabla ni su existencia.
    """

    ACCIONES = ACCIONES

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_auditoria",
        db_index=False,
        verbose_name="usuario",
    )
    accion = models.CharField("acción", max_length=20, choices=ACCIONES)
    modulo = models.CharField("módulo", max_length=40)
    tabla = models.CharField("tabla", max_length=60, null=True, blank=True)
    registro_id = models.BigIntegerField("id del registro", null=True, blank=True)
    detalle = models.JSONField("detalle", null=True, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    fecha = models.DateTimeField(
        "fecha", default=timezone.now, db_default=Now()
    )

    class Meta:
        db_table = "auditoria"
        verbose_name = "evento de auditoría"
        verbose_name_plural = "auditoría"
        ordering = ("-fecha", "-id")
        indexes = [
            models.Index(fields=["fecha"], name="ix_auditoria_fecha"),
            models.Index(fields=["usuario"], name="ix_auditoria_usuario"),
            models.Index(fields=["modulo"], name="ix_auditoria_modulo"),
            models.Index(fields=["tabla", "registro_id"], name="ix_auditoria_tabla_registro"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    ("accion__in", tuple(a[0] for a in ACCIONES))
                ),
                name="ck_auditoria_accion",
            ),
        ]

    def __str__(self):
        return f"{self.accion} · {self.modulo} · {self.fecha:%Y-%m-%d %H:%M}"
