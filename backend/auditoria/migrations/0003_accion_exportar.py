"""CHECK de auditoría con la acción EXPORTAR (Semana 17, HU-146).

Amplía las 15 acciones de 0001_auditoria a 16 (EXPORTAR, la que deja
cada descarga de reportes) y actualiza el CHECK ck_auditoria_accion,
que también está en 01_tablas.sql:199-202. La reversión se protege con
una comprobación previa: si quedan eventos con acción EXPORTAR, el
CHECK de 15 acciones no podría volver a crearse y, en vez de un error
críptico de la base de datos, la migración se detiene con un
IrreversibleError claro y un mensaje en español sin tocar el esquema.
"""
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError

_ACCIONES_16 = [
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
    ("EXPORTAR", "Exportar"),
]


def _antes_de_revertir(apps, schema_editor):
    """Sin eventos EXPORTAR no hay peligro al volver al CHECK de 15."""
    Auditoria = apps.get_model("auditoria", "Auditoria")
    cantidad = Auditoria.objects.filter(accion="EXPORTAR").count()
    if cantidad:
        raise IrreversibleError(
            f"No se puede revertir la migración: hay {cantidad} evento(s) "
            "de auditoría con acción EXPORTAR y el CHECK anterior solo admite "
            "15 acciones. Conserva la migración aplicada o elimina esos "
            "eventos antes de revertir."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_fn_trg_auditoria"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditoria",
            name="accion",
            field=models.CharField(choices=_ACCIONES_16, max_length=20, verbose_name="acción"),
        ),
        migrations.RemoveConstraint(
            model_name="auditoria",
            name="ck_auditoria_accion",
        ),
        migrations.AddConstraint(
            model_name="auditoria",
            constraint=models.CheckConstraint(
                condition=models.Q(("accion__in", tuple(a[0] for a in _ACCIONES_16))),
                name="ck_auditoria_accion",
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, _antes_de_revertir),
    ]
