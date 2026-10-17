"""Campo debe_cambiar_clave en usuarios (Semana 13, HU-112/RF-73).

TRUE = primer ingreso (o restablecimiento admin): el usuario debe
cambiar su contraseña; la puerta en DEFAULT_PERMISSION_CLASSES responde
403 «Debes cambiar tu contraseña…» hasta que lo haga. Restablecer la
contraseña desde la administración lo pone a TRUE; el cambio propio lo
pone a FALSE.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0003_trigger_rol_sistema"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="debe_cambiar_clave",
            field=models.BooleanField(db_default=False, default=False, verbose_name="debe cambiar contraseña"),
        ),
    ]
