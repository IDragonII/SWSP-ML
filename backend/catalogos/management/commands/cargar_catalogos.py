"""cargar_catalogos: carga los catálogos de ejemplo de la Semana 5.

Idempotente: se puede ejecutar muchas veces sin duplicar nada; informa de
las filas creadas y de las que ya existían y nunca pisa filas editadas
(get_or_create). Asegura los 26 registros de referencia que también siembra
la migración 0002 y añade los datos de ejemplo del diseño (decisión de la
Semana 5: los valores CONFIRMAR entran SOLO por este comando, nunca por
migración): el quintal, los agentes y las etapas fenológicas de Quinua y
Cañihua, todos marcados hasta confirmar con el proyecto.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from catalogos.models import (
    Agente,
    Cultivo,
    EtapaFenologica,
    TipoActividad,
    TipoIncidencia,
    Unidad,
)

# 26 filas de referencia (DB_sql/03_insert.sql) — mismas que la migración 0002
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

# Datos de ejemplo del diseño — HASTA CONFIRMAR con el proyecto
QUINTAL = ("Quintal", "qq", "MASA", Decimal("46"), False)

AGENTES = [
    ("Kcona kcona (polilla de la quinua)", "PLAGA"),
    ("Ticona (gusano cortador)", "PLAGA"),
    ("Pulgón", "PLAGA"),
    ("Mildiu", "ENFERMEDAD"),
    ("Mancha foliar", "ENFERMEDAD"),
]

ETAPAS = [
    "Siembra",
    "Emergencia",
    "Desarrollo vegetativo",
    "Floración",
    "Maduración",
    "Cosecha",
]
ETAPAS_CULTIVOS = ["Quinua", "Cañihua"]  # Tarwi, sin etapas de ejemplo


class Command(BaseCommand):
    help = (
        "Carga los catálogos de ejemplo de forma idempotente: asegura los "
        "26 registros de referencia de la migración 0002 y añade los datos "
        "de ejemplo del diseño (quintal, agentes y etapas fenológicas), "
        "creando solo lo que falta y sin pisar lo ya existente."
    )

    def handle(self, *args, **opciones):
        creadas = existentes = 0

        def _anotar(creada):
            nonlocal creadas, existentes
            if creada:
                creadas += 1
            else:
                existentes += 1

        self.stdout.write("Cargando catálogos de ejemplo del diseño…")

        for nombre in CULTIVOS:
            _, creada = Cultivo.objects.get_or_create(nombre=nombre)
            _anotar(creada)

        for codigo, nombre in TIPOS_ACTIVIDAD:
            _, creada = TipoActividad.objects.get_or_create(
                codigo=codigo, defaults={"nombre": nombre}
            )
            _anotar(creada)

        for nombre, categoria in TIPOS_INCIDENCIA:
            _, creada = TipoIncidencia.objects.get_or_create(
                nombre=nombre, defaults={"categoria": categoria}
            )
            _anotar(creada)

        for nombre, simbolo, tipo, factor, es_base in [*UNIDADES, QUINTAL]:
            _, creada = Unidad.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "simbolo": simbolo,
                    "tipo": tipo,
                    "factor_a_base": factor,
                    "es_base": es_base,
                },
            )
            _anotar(creada)

        for nombre, tipo in AGENTES:
            _, creada = Agente.objects.get_or_create(
                nombre=nombre, defaults={"tipo": tipo}
            )
            _anotar(creada)

        for nombre_cultivo in ETAPAS_CULTIVOS:
            cultivo, _ = Cultivo.objects.get_or_create(
                nombre=nombre_cultivo
            )
            for orden, nombre in enumerate(ETAPAS, start=1):
                _, creada = EtapaFenologica.objects.get_or_create(
                    cultivo=cultivo,
                    nombre=nombre,
                    defaults={"orden": orden},
                )
                _anotar(creada)

        self.stdout.write(
            f"Filas creadas: {creadas} · ya existían: {existentes}"
        )
        self.stdout.write(
            "Totales: cultivos {c} · tipos de actividad {ta} · "
            "tipos de incidencia {ti} · unidades {u} · agentes {a} · "
            "etapas fenológicas {e}".format(
                c=Cultivo.objects.count(),
                ta=TipoActividad.objects.count(),
                ti=TipoIncidencia.objects.count(),
                u=Unidad.objects.count(),
                a=Agente.objects.count(),
                e=EtapaFenologica.objects.count(),
            )
        )
        self.stdout.write(
            "AVISO: quintal, agentes y etapas fenológicas son datos de "
            "ejemplo, hasta confirmar con el proyecto."
        )
