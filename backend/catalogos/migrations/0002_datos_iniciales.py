from decimal import Decimal

from django.db import migrations

# 26 filas de referencia de DB_sql/03_insert.sql (semana 5). Todo lo que el
# proyecto confirme más tarde (quintal, etapas, agentes, variedades,
# recursos) entra por el comando cargar_catalogos, nunca por migración.

CULTIVOS = ["Quinua", "Cañihua", "Tarwi"]

TIPOS_ACTIVIDAD = [
    ("PREPARACION", "Preparación del terreno"),
    ("SIEMBRA", "Siembra"),
    ("FERTILIZACION", "Fertilización"),
    ("FITOSANITARIO", "Control fitosanitario"),
    ("RIEGO", "Riego"),
    ("DESHIERBO", "Deshierbo"),
    ("COSECHA", "Cosecha"),
]

TIPOS_INCIDENCIA = [
    ("Helada", "CLIMATICA"),
    ("Sequía", "CLIMATICA"),
    ("Granizada", "CLIMATICA"),
    ("Exceso de lluvia", "CLIMATICA"),
    ("Plaga", "BIOLOGICA"),
    ("Enfermedad", "BIOLOGICA"),
    ("Daño por animales", "BIOLOGICA"),
    ("Otros", "OTRA"),
]

# 8 unidades: el quintal (CONFIRMAR 46 kg) lo carga el comando, no la migración
UNIDADES = [
    ("Kilogramo", "kg", "MASA", Decimal("1"), True),
    ("Gramo", "g", "MASA", Decimal("0.001"), False),
    ("Tonelada", "t", "MASA", Decimal("1000"), False),
    ("Hectárea", "ha", "SUPERFICIE", Decimal("1"), True),
    ("Metro cúbico", "m3", "VOLUMEN", Decimal("1"), True),
    ("Litro", "L", "VOLUMEN", Decimal("0.001"), False),
    ("Jornal", "jornal", "LABOR", Decimal("1"), True),
    ("Hora", "h", "TIEMPO", Decimal("1"), True),
]


def cargar(apps, schema_editor):
    """Sembrado idempotente: get_or_create y no pisa filas ya editadas."""
    Cultivo = apps.get_model("catalogos", "Cultivo")
    TipoActividad = apps.get_model("catalogos", "TipoActividad")
    TipoIncidencia = apps.get_model("catalogos", "TipoIncidencia")
    Unidad = apps.get_model("catalogos", "Unidad")

    for nombre in CULTIVOS:
        Cultivo.objects.get_or_create(nombre=nombre)

    for codigo, nombre in TIPOS_ACTIVIDAD:
        TipoActividad.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre}
        )

    for nombre, categoria in TIPOS_INCIDENCIA:
        TipoIncidencia.objects.get_or_create(
            nombre=nombre, defaults={"categoria": categoria}
        )

    for nombre, simbolo, tipo, factor, es_base in UNIDADES:
        Unidad.objects.get_or_create(
            nombre=nombre,
            defaults={
                "simbolo": simbolo,
                "tipo": tipo,
                "factor_a_base": factor,
                "es_base": es_base,
            },
        )


def _sin_referencias(objeto):
    """True si ninguna fila de otra tabla apunta a esta (se conserva)."""
    for relacion in type(objeto)._meta.related_objects:
        if relacion.one_to_many or relacion.one_to_one:
            nombre = relacion.get_accessor_name()
            if nombre and getattr(objeto, nombre).exists():
                return False
    return True


def revertir(apps, schema_editor):
    """Quita las 26 filas por su identidad original. Lo que ya esté
    referenciado (variedades, etapas o tablas de sprints posteriores) se
    conserva para no romper restricciones."""
    Cultivo = apps.get_model("catalogos", "Cultivo")
    TipoActividad = apps.get_model("catalogos", "TipoActividad")
    TipoIncidencia = apps.get_model("catalogos", "TipoIncidencia")
    Unidad = apps.get_model("catalogos", "Unidad")

    for incidencia in TipoIncidencia.objects.filter(
        nombre__in=[n for n, _ in TIPOS_INCIDENCIA]
    ):
        if _sin_referencias(incidencia):
            incidencia.delete()

    for unidad in Unidad.objects.filter(
        nombre__in=[n for n, *_ in UNIDADES]
    ):
        if _sin_referencias(unidad):
            unidad.delete()

    for actividad in TipoActividad.objects.filter(
        codigo__in=[c for c, _ in TIPOS_ACTIVIDAD]
    ):
        if _sin_referencias(actividad):
            actividad.delete()

    for cultivo in Cultivo.objects.filter(nombre__in=CULTIVOS):
        if _sin_referencias(cultivo):
            cultivo.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogos", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(cargar, revertir),
    ]
