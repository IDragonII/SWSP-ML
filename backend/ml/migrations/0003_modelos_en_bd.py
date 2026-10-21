# Semana 23, decisiones 254 y 256: las tres columnas de modelo-en-BD en
# modelos_ml (contenido, huella y versiones_librerias) con el CHECK de
# 20 MiB vía SQL crudo. La reversión está ANOTADA: si existe algún modelo
# con contenido y sin archivo (su único artefacto vive en la BD), la
# reversión se niega y toca restaurar el respaldo previo.

from django.db import migrations, models


def _fallar_si_hay_modelos_solo_en_bd(apps, schema_editor):
    """Guarda de reversión (decisión 256)."""
    ModeloML = apps.get_model("ml", "ModeloML")
    if ModeloML.objects.filter(
        contenido__isnull=False, archivo__isnull=True
    ).exists():
        raise RuntimeError(
            "No se puede revertir ml/0003: hay modelos guardados solo en "
            "la base de datos (contenido sin archivo) que quedarían sin "
            "artefacto. Restaure el respaldo previo a la migración."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('ml', '0002_tareas_entrenamiento'),
    ]

    operations = [
        migrations.AddField(
            model_name='modeloml',
            name='contenido',
            field=models.BinaryField(blank=True, null=True, verbose_name='contenido'),
        ),
        migrations.AddField(
            model_name='modeloml',
            name='huella',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='huella'),
        ),
        migrations.AddField(
            model_name='modeloml',
            name='versiones_librerias',
            field=models.JSONField(blank=True, null=True, verbose_name='versiones de librerías'),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE modelos_ml ADD CONSTRAINT ck_modelo_tamano "
                "CHECK (contenido IS NULL OR octet_length(contenido) <= 20971520)"
            ),
            reverse_sql="ALTER TABLE modelos_ml DROP CONSTRAINT ck_modelo_tamano",
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            _fallar_si_hay_modelos_solo_en_bd,
        ),
    ]
