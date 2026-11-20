"""Campo debe_cambiar_credenciales en usuarios (S24, primer ingreso).

TRUE = el usuario todavía no ha elegido su propio usuario y contraseña:
toda cuenta (alta nueva o existente) debe cambiarlos en el primer
ingreso; la puerta en DEFAULT_PERMISSION_CLASSES responde 403 «Debes
cambiar tus credenciales…» hasta que lo haga. El backfill marca TODAS
las cuentas existentes al aplicarse (decisión S24: todos).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0004_debe_cambiar_clave"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="debe_cambiar_credenciales",
            field=models.BooleanField(
                db_default=False,
                default=False,
                verbose_name="debe cambiar credenciales",
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE usuarios SET debe_cambiar_credenciales = TRUE;",
            reverse_sql="UPDATE usuarios SET debe_cambiar_credenciales = FALSE;",
        ),
    ]
