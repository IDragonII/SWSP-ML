"""Tabla parametros_sistema, su trigger y las 4 claves fijas.

- Triggers: trg_parametros_sistema_actualizado (reutiliza
  fn_set_actualizado_en de productores.0002; al revertir esta migración NO
  se dropea esa función).
- Datos: las 4 claves de 03_insert.sql:137-141, todas CONFIRMAR. Se cargan
  aquí porque fn_validar_produccion depende de rendimiento_min_plausible y
  rendimiento_max_plausible, y las alertas del Sprint 8 usarán las otras
  dos. Idempotentes (get_or_create por clave).
"""
import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_parametros_sistema_actualizado BEFORE UPDATE ON parametros_sistema
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_parametros_sistema_actualizado ON parametros_sistema;"
)

# 03_insert.sql:137-141 (CONFIRMAR todos los valores)
PARAMETROS = [
    (
        "dias_sin_actividad",
        "30",
        "Días sin actividades para generar la alerta SIN_ACTIVIDAD",
    ),
    (
        "umbral_rendimiento_bajo",
        "800",
        "Rendimiento predicho (kg/ha) bajo el cual se genera la alerta "
        "RENDIMIENTO_BAJO",
    ),
    (
        "rendimiento_min_plausible",
        "100",
        "Rendimiento mínimo (kg/ha) antes de marcar la producción para revisión",
    ),
    (
        "rendimiento_max_plausible",
        "5000",
        "Rendimiento máximo (kg/ha) antes de marcar la producción para revisión",
    ),
]


def sembrar_parametros(apps, schema_editor):
    ParametroSistema = apps.get_model("sistema", "ParametroSistema")
    for clave, valor, descripcion in PARAMETROS:
        ParametroSistema.objects.get_or_create(
            clave=clave,
            defaults={"valor": valor, "descripcion": descripcion},
        )


def borrar_parametros(apps, schema_editor):
    ParametroSistema = apps.get_model("sistema", "ParametroSistema")
    ParametroSistema.objects.filter(clave__in=[p[0] for p in PARAMETROS]).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # fn_set_actualizado_en (el trigger de esta tabla vive aquí)
        ("productores", "0004_funciones_y_triggers"),
    ]

    operations = [
        migrations.CreateModel(
            name='ParametroSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=60, unique=True, verbose_name='clave')),
                ('valor', models.CharField(max_length=100, verbose_name='valor')),
                ('descripcion', models.CharField(blank=True, max_length=200, null=True, verbose_name='descripción')),
                ('actualizado_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, verbose_name='actualizado en')),
            ],
            options={
                'verbose_name': 'parámetro del sistema',
                'verbose_name_plural': 'parámetros del sistema',
                'db_table': 'parametros_sistema',
                'ordering': ('clave',),
            },
        ),
        migrations.RunSQL([TRG_ACTUALIZADO], [DROP_TRG_ACTUALIZADO]),
        migrations.RunPython(sembrar_parametros, borrar_parametros),
    ]
