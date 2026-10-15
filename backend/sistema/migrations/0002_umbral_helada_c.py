"""Quinto parámetro del sistema: umbral_helada_c (Semana 10, pregunta K).

Valor inicial 0 °C (CONFIRMAR): por debajo o igual a esa temperatura
mínima, la API marca el día como helada. Se carga con una migración de
datos porque los parámetros son claves fijas (no hay POST/DELETE por la
API). Cambiar el umbral **no recalcula** los registros ya guardados,
igual que los demás umbrales.

Solo se crea/borra esta fila: las 4 claves de sistema.0001 no se tocan.
Es la quinta fila de 03_insert.sql (ahí anotada también).
"""
from django.db import migrations

CLAVE = "umbral_helada_c"
VALOR = "0"
DESCRIPCION = (
    "Temperatura mínima (°C) a partir de la cual un día se marca como "
    "helada"
)


def sembrar_umbral(apps, schema_editor):
    ParametroSistema = apps.get_model("sistema", "ParametroSistema")
    ParametroSistema.objects.get_or_create(
        clave=CLAVE,
        defaults={"valor": VALOR, "descripcion": DESCRIPCION},
    )


def borrar_umbral(apps, schema_editor):
    ParametroSistema = apps.get_model("sistema", "ParametroSistema")
    ParametroSistema.objects.filter(clave=CLAVE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("sistema", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(sembrar_umbral, borrar_umbral),
    ]
