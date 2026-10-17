"""Tabla auditoria (Semana 13): estructura, CHECK de 15 acciones e índices.

Copia de 01_tablas.sql:192-203 con el CHECK ampliado de 5 a 15 acciones
(los estados que producen los endpoints que escriben, RF-71) y el índice
nuevo tabla+registro (ix_auditoria_tabla_registro) que alimenta el
«Ver historial» de las fichas. El trigger de inmutabilidad
(fn_auditoria_inmutable, el 25 del diseño) lo crea la migración 0002.
"""
import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0002_datos_iniciales"),
    ]

    operations = [
        migrations.CreateModel(
            name="Auditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accion", models.CharField(choices=[("CREAR", "Crear"), ("MODIFICAR", "Modificar"), ("ELIMINAR", "Eliminar"), ("ACTIVAR", "Activar"), ("DESACTIVAR", "Desactivar"), ("ANULAR", "Anular"), ("REACTIVAR", "Reactivar"), ("ASIGNAR", "Asignar"), ("DESASIGNAR", "Desasignar"), ("LOGIN", "Iniciar sesión"), ("LOGOUT", "Cerrar sesión"), ("BLOQUEAR", "Bloquear acceso"), ("DESBLOQUEAR", "Desbloquear acceso"), ("RESTABLECER_CLAVE", "Restablecer contraseña"), ("CAMBIAR_CLAVE", "Cambiar contraseña")], max_length=20, verbose_name="acción")),
                ("modulo", models.CharField(max_length=40, verbose_name="módulo")),
                ("tabla", models.CharField(blank=True, max_length=60, null=True, verbose_name="tabla")),
                ("registro_id", models.BigIntegerField(blank=True, null=True, verbose_name="id del registro")),
                ("detalle", models.JSONField(blank=True, null=True, verbose_name="detalle")),
                ("ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("fecha", models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, verbose_name="fecha")),
                ("usuario", models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="eventos_auditoria", to=settings.AUTH_USER_MODEL, verbose_name="usuario")),
            ],
            options={
                "verbose_name": "evento de auditoría",
                "verbose_name_plural": "auditoría",
                "db_table": "auditoria",
                "ordering": ("-fecha", "-id"),
                "indexes": [models.Index(fields=["fecha"], name="ix_auditoria_fecha"), models.Index(fields=["usuario"], name="ix_auditoria_usuario"), models.Index(fields=["modulo"], name="ix_auditoria_modulo"), models.Index(fields=["tabla", "registro_id"], name="ix_auditoria_tabla_registro")],
                "constraints": [models.CheckConstraint(condition=models.Q(("accion__in", ("CREAR", "MODIFICAR", "ELIMINAR", "ACTIVAR", "DESACTIVAR", "ANULAR", "REACTIVAR", "ASIGNAR", "DESASIGNAR", "LOGIN", "LOGOUT", "BLOQUEAR", "DESBLOQUEAR", "RESTABLECER_CLAVE", "CAMBIAR_CLAVE"))), name="ck_auditoria_accion")],
            },
        ),
    ]
