from django.db import migrations

# Semana 20: los cuatro recursos genéricos contra los que la importación
# histórica registra los TOTALES por campaña del archivo de campañas
# (decisión: una sola colección de recursos «(total histórico)» por
# categoría, sin inventar nombres de insumos que el archivo no trae).
# El importador los busca por nombre exacto; si falta, la migración los
# crea (get_or_create, idempotente).

GENERICOS = [
    ("Semilla (total histórico)", "SEMILLA", "MASA"),
    ("Fertilizante (total histórico)", "FERTILIZANTE", "MASA"),
    ("Mano de obra (total histórico)", "MANO_OBRA", "LABOR"),
    ("Agua (total histórico)", "AGUA", "VOLUMEN"),
]


def cargar(apps, schema_editor):
    Recurso = apps.get_model("catalogos", "Recurso")
    for nombre, categoria, tipo_unidad in GENERICOS:
        Recurso.objects.get_or_create(
            nombre=nombre,
            defaults={"categoria": categoria, "tipo_unidad": tipo_unidad},
        )


def revertir(apps, schema_editor):
    """Borra solo los cuatro genéricos; si ya tienen usos referenciados
    (importaciones reales), los conserva para no romper FK."""
    Recurso = apps.get_model("catalogos", "Recurso")
    for nombre, _, _ in GENERICOS:
        recurso = Recurso.objects.filter(nombre=nombre).first()
        if recurso is not None:
            tiene_usos = recurso.usos_recursos.exists()
            if not tiene_usos:
                recurso.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogos", "0002_datos_iniciales"),
    ]

    operations = [
        migrations.RunPython(cargar, revertir),
    ]
