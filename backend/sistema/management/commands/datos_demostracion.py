"""datos_demostracion: datos de demostración mínimos para el panel (Semana 16).

Crea un puñado de productores, parcelas, campañas, producciones y
actividades INVENTADOS y marcados como tales, para que el panel de
indicadores se pinte con datos reales de prueba. No sustituye a la lista
real de ubicaciones (`cargar_ubicacion`) ni a los catálogos
(`cargar_catalogos`), y no se usa en las pruebas de Django ni en la
colección de la API (decisión 40 de `decisiones_semana16.md`).

Idempotente: los DNI fijos de los productores demo marcan el conjunto;
si ya existen no se vuelve a crear nada. Todo se hace en una sola
transacción: si algo falla, no queda media siembra.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Unidad, Variedad
from productores.models import Comunidad, Parcela, Productor
from produccion.models import Produccion
from seguimiento.models import Actividad

# DNI fijos: son la marca de idempotencia del conjunto demo
DEMO_DNIS = ("99000001", "99000002", "99000003", "99000004", "99000005")
MARCA = "Datos de demostración inventados (Semana 16)"
PERIODO = "2026-2027"
FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-12-31"

PRODUCTORES = [
    ("Valeria", "Demo Norte", "99000001", "ACTIVO"),
    ("Mauricio", "Demo Sur", "99000002", "ACTIVO"),
    ("Rosa", "Demo Este", "99000003", "ACTIVO"),
    ("Julio", "Demo Oeste", "99000004", "ACTIVO"),
    ("Nilda", "Demo Baja", "99000005", "INACTIVO"),
]

# superficie_ha de cada parcela demo (la 1 al 5)
PARCELAS = [
    ("99000001", "1.20"),
    ("99000002", "0.80"),
    ("99000003", "2.00"),
    ("99000004", "1.50"),
    ("99000001", "1.00"),
]

ACTIVIDADES = [
    ("2026-03-05", 0),  # (fecha, índice de campaña)
    ("2026-04-02", 1),
    ("2026-06-18", 2),
    ("2026-05-12", 3),
]

# (campaña, fecha_cosecha, superficie_cosechada, cantidad en kg)
PRODUCCIONES = [
    (1, "2026-08-20", "0.80", "40"),  # 50 kg/ha → queda para revisión
    (2, "2026-09-10", "2.00", "6400"),  # 3 200 kg/ha
    (3, "2026-09-25", "1.50", "6150"),  # 4 100 kg/ha
]


class Command(BaseCommand):
    help = (
        "Siembra datos de demostración inventados y marcados para el panel "
        "de indicadores (idempotente; no sustituye a cargar_ubicacion ni a "
        "cargar_catalogos)."
    )

    def handle(self, *args, **opciones):
        if Productor.objects.filter(dni__in=DEMO_DNIS).exists():
            self.stdout.write(
                "Los datos de demostración ya existen; nada que crear."
            )
            return

        comunidades = list(
            Comunidad.objects.filter(activo=True).order_by("id")[:20]
        )
        if not comunidades:
            raise CommandError(
                "No hay comunidades activas: ejecuta "
                "`manage.py cargar_ubicacion` antes que este comando."
            )
        com_a = comunidades[0]
        com_b = next(
            (c for c in comunidades if c.distrito_id != com_a.distrito_id),
            com_a,
        )

        # Solo cultivos activos que además tengan variedad activa: la
        # campaña necesita la clave compuesta (variedad, cultivo)
        con_variedad = Variedad.objects.filter(activo=True).values("cultivo_id")
        cultivos = list(
            Cultivo.objects.filter(activo=True, pk__in=con_variedad).order_by(
                "id"
            )
        )
        if not cultivos:
            raise CommandError(
                "No hay cultivos activos con variedad: ejecuta "
                "`manage.py cargar_catalogos` antes que este comando."
            )
        cultivo_b = cultivos[1] if len(cultivos) > 1 else cultivos[0]
        variedades = []
        for cultivo in (cultivos[0], cultivo_b):
            variedad = (
                Variedad.objects.filter(cultivo=cultivo, activo=True)
                .order_by("id")
                .first()
            )
            if variedad is None:
                raise CommandError(
                    f"El cultivo {cultivo.nombre} no tiene variedades "
                    "activas: ejecuta `manage.py cargar_catalogos`."
                )
            variedades.append(variedad)

        unidad = (
            Unidad.objects.filter(tipo="MASA", es_base=True, activo=True)
            .order_by("id")
            .first()
        )
        if unidad is None:
            raise CommandError(
                "No hay unidad de masa base: ejecuta "
                "`manage.py cargar_catalogos` antes que este comando."
            )
        tipo_actividad = (
            TipoActividad.objects.filter(activo=True, codigo="PREPARACION")
            .first()
            or TipoActividad.objects.filter(activo=True)
            .exclude(codigo="SIEMBRA")
            .order_by("codigo")
            .first()
            or TipoActividad.objects.filter(activo=True)
            .order_by("codigo")
            .first()
        )
        if tipo_actividad is None:
            raise CommandError(
                "No hay tipos de actividad: ejecuta "
                "`manage.py cargar_catalogos` antes que este comando."
            )

        Usuario = get_user_model()
        admin = Usuario.objects.filter(is_superuser=True).first()

        with transaction.atomic():
            productores = {}
            for nombres, apellidos, dni, estado in PRODUCTORES:
                productor = Productor.objects.create(
                    nombres=nombres,
                    apellidos=apellidos,
                    dni=dni,
                    comunidad=com_a if estado == "ACTIVO" else com_b,
                    referencia_ubicacion=MARCA,
                    estado=estado,
                    creado_por=admin,
                )
                productores[dni] = productor

            parcelas = []
            for indice, (dni, superficie) in enumerate(PARCELAS):
                parcelas.append(
                    Parcela.objects.create(
                        productor=productores[dni],
                        comunidad=com_a if indice != 3 else com_b,
                        referencia_ubicacion=MARCA,
                        superficie_ha=Decimal(superficie),
                        altitud_msnm=3000,
                        tipo_suelo="FRANCO",
                        pendiente="SUAVE",
                        disponibilidad_agua="MEDIA",
                        sistema_riego="GRAVEDAD",
                        creado_por=admin,
                    )
                )

            # 5 campañas: una por estado (la cancelada sobre la parcela 5)
            estados = [
                Campania.ESTADO_PLANIFICADA,
                Campania.ESTADO_EN_PRODUCCION,
                Campania.ESTADO_EN_PRODUCCION,
                Campania.ESTADO_EN_PRODUCCION,
                Campania.ESTADO_PLANIFICADA,
            ]
            campanias = []
            for indice, estado in enumerate(estados):
                cultivo = cultivos[0] if indice % 2 == 0 else cultivo_b
                campanias.append(
                    Campania.objects.create(
                        periodo=PERIODO,
                        parcela=parcelas[indice],
                        cultivo=cultivo,
                        variedad=variedades[0] if indice % 2 == 0 else variedades[1],
                        fecha_inicio=FECHA_INICIO,
                        fecha_fin_prevista=FECHA_FIN,
                        superficie_sembrada_ha=parcelas[indice].superficie_ha,
                        estado=estado,
                        observaciones=MARCA,
                        creado_por=admin,
                    )
                )

            for fecha, indice_campania in ACTIVIDADES:
                Actividad.objects.create(
                    campania=campanias[indice_campania],
                    tipo_actividad=tipo_actividad,
                    fecha=fecha,
                    observaciones=MARCA,
                    registrado_por=admin,
                )

            # Producciones: la primera es atípica (queda en revisión) y
            # devuelve su campaña a EN_PRODUCCION; las otras dos dejan
            # una campaña COSECHADA (provisional) y otra CERRADA (apta).
            for indice_campania, fecha, superficie, cantidad in PRODUCCIONES:
                campania = campanias[indice_campania]
                Produccion.objects.create(
                    campania=campania,
                    fecha_cosecha=fecha,
                    superficie_cosechada_ha=Decimal(superficie),
                    cantidad_producida=Decimal(cantidad),
                    unidad=unidad,
                    produccion_kg=Decimal("0"),
                    rendimiento_kg_ha=Decimal("0"),
                    observaciones=MARCA,
                    registrado_por=admin,
                )
                campania.refresh_from_db()
                if indice_campania == 1:
                    # fn_produccion_post la pasó a COSECHADA; se revierte
                    # para que el panel tenga una campaña en producción
                    campania.estado = Campania.ESTADO_EN_PRODUCCION
                    campania.save(update_fields=["estado", "actualizado_en"])
                elif indice_campania == 3:
                    campania.estado = Campania.ESTADO_CERRADA
                    campania.save(update_fields=["estado", "actualizado_en"])

            campanias[4].estado = Campania.ESTADO_CANCELADA
            campanias[4].save(update_fields=["estado", "actualizado_en"])

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de demostración creados: "
                f"{len(PRODUCTORES)} productores, {len(PARCELAS)} parcelas, "
                "5 campañas (una por estado), 3 producciones "
                "(1 para revisión) y 4 actividades. Todos los registros "
                f"llevan la marca «{MARCA}»."
            )
        )
