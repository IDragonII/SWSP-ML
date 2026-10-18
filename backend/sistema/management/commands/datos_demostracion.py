"""datos_demostracion: datos de demostración para panel y reportes.

Crea productores, parcelas, campañas, producciones, actividades y
eventos de bitácora INVENTADOS y marcados como tales, para que el panel
de indicadores (HU-133..HU-140), los reportes descargables (HU-141..
HU-149) y los reportes nuevos de actividades y de auditoría (Semana 18)
se pinten con datos de prueba. No sustituye a la lista real de
ubicaciones (`cargar_ubicacion`) ni a los catálogos
(`cargar_catalogos`), y no se usa en las pruebas de Django ni en la
colección de la API (decisión 40 de `decisiones_semana16.md`).

Dos bloques idempotentes por separado (decisión 55 de
`decisiones_semana17.md`), más un tercero en la Semana 18 (ver
`decisiones_semana18.md`):

- **V1 — Semana 16**: 5 productores, 5 parcelas, 5 campañas (una por
  estado), 3 producciones (1 para revisión) y 4 actividades.
- **V2 — Semana 17**: 5 productores con **ñ, tildes y el canario
  «=1+1»** (un nombre que empieza por «=»: en Excel debe guardarse como
  texto, nunca como fórmula), 10 parcelas, **20 campañas** repartidas en
  dos períodos (10 CERRADA de 2025-2026 con producción, 5
  EN_PRODUCCION y 5 PLANIFICADA de 2026-2027), 10 producciones (1
  atípica para revisión) y 4 actividades. Con V2 el resumen por cultivo
  queda con un cultivo con 9+ producciones y otro con menos de 3 (marca
  POCOS DATOS) y hay campañas COSECHADA/PROVISIONAL del bloque V1.
- **V3 — Semana 18**: 6 actividades para los reportes nuevos —fechas
  recientes, dos tipos (PREPARACIÓN y SIEMBRA), horas, método, densidad,
  una anulada con motivo, una sin horas y una campaña creada, con su
  actividad registrada y cancelada DESPUÉS (los triggers rechazan altas
  sobre campañas canceladas)— y 8 eventos de bitácora inventados (LOGIN
  con y sin usuario, CREAR, MODIFICAR, ANULAR, CAMBIAR_CLAVE y dos
  EXPORTAR, con IPs y detalles variados) para que el reporte de
  auditoría (HU-155/HU-156) y su pantalla se pinten con un rango de
  fechas. Idempotente por sus propios marcadores (la marca V3 en las
  actividades y el módulo «sesiones_demo» en la bitácora).

El reparto respeta los índices únicos de la base: **una sola campaña
activa (PLANIFICADA/EN_PRODUCCION/COSECHADA) por parcela**
(`uq_campania_activa_por_parcela`) y **una campaña no cancelada por
parcela y período** (`uq_campania_parcela_periodo`) — por eso cada
parcela V2 tiene su campaña de 2025 terminada en CERRADA **antes** de
crear la activa de 2026-2027.

Idempotente por DNI: cada bloque se crea solo si le falta algún
productor; si los diez existen nada se hace. Todo se hace en una sola
transacción: si algo falla, no queda media siembra.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from auditoria.models import Auditoria
from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Unidad, Variedad
from productores.models import Comunidad, Parcela, Productor
from produccion.models import Produccion
from seguimiento.models import Actividad

# DNI fijos: son la marca de idempotencia de cada bloque demo
DEMO_DNIS_V1 = (
    "99000001",
    "99000002",
    "99000003",
    "99000004",
    "99000005",
)
DEMO_DNIS_V2 = (
    "99000011",
    "99000012",
    "99000013",
    "99000014",
    "99000015",
)
DEMO_DNIS = DEMO_DNIS_V1 + DEMO_DNIS_V2

MARCA = "Datos de demostración inventados (Semana 16)"
MARCA_V2 = "Datos de demostración inventados (Semana 17)"
MARCA_V3 = "Datos de demostración inventados (Semana 18)"
# Módulo de los dos LOGIN de la demo: es la marca de idempotencia del
# bloque V3 de bitácora (los otros eventos usan módulos realistas)
MODULO_V3 = "sesiones_demo"
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

# --------------------------------------------------------------------- #
# V2 (Semana 17): ñ/tildes, canario «=1+1», 20 campañas en 2 períodos
# --------------------------------------------------------------------- #
PRODUCTORES_V2 = [
    ("José Ñahui", "Muñoz", "99000011", "ACTIVO"),
    ("Maëlys", "Ñuñwaylla", "99000012", "ACTIVO"),
    ("Teófilo", "Quispe", "99000013", "ACTIVO"),
    ("=1+1", "Ñandú", "99000014", "ACTIVO"),  # texto inelástico en Excel
    ("Rosa", "Farfán", "99000015", "INACTIVO"),
]

# (dni, superficie_ha); dos parcelas por productor, ubicación alterna
PARCELAS_V2 = [
    ("99000011", "1.50"),
    ("99000011", "1.20"),
    ("99000012", "2.50"),
    ("99000012", "2.00"),
    ("99000013", "0.75"),
    ("99000013", "1.80"),
    ("99000014", "3.00"),
    ("99000014", "2.20"),
    ("99000015", "1.10"),
    ("99000015", "0.90"),
]

# (índice de parcela, período, índice de cultivo, producción o None,
#  estado final) — **las 10 filas de 2025-2026 van primero**: cada una
#  se crea EN_PRODUCCION, recibe su producción (el trigger la pasa a
#  COSECHADA) y se cierra a CERRADA en el acto, antes de crear la
#  campaña activa de 2026-2027 de la misma parcela (índices únicos).
#  La producción es (fecha_cosecha, superficie, kilos); la de
#  0.70 ha con 35 kg da 50 kg/ha y queda para revisión.
CAMPANIAS_V2 = [
    (0, "2025-2026", 0, ("2025-07-18", "1.45", "1160"), Campania.ESTADO_CERRADA),
    (1, "2025-2026", 0, ("2025-07-30", "1.15", "920"), Campania.ESTADO_CERRADA),
    (2, "2025-2026", 0, ("2025-08-12", "2.40", "2640"), Campania.ESTADO_CERRADA),
    (3, "2025-2026", 0, ("2025-08-25", "1.90", "1330"), Campania.ESTADO_CERRADA),
    (4, "2025-2026", 0, ("2025-09-08", "0.70", "35"), Campania.ESTADO_CERRADA),
    (5, "2025-2026", 0, ("2025-09-19", "1.70", "1530"), Campania.ESTADO_CERRADA),
    (6, "2025-2026", 0, ("2025-09-30", "2.85", "3420"), Campania.ESTADO_CERRADA),
    (7, "2025-2026", 0, ("2025-10-11", "2.10", "1890"), Campania.ESTADO_CERRADA),
    (8, "2025-2026", 0, ("2025-10-24", "1.05", "735"), Campania.ESTADO_CERRADA),
    (9, "2025-2026", 1, ("2025-11-05", "0.85", "680"), Campania.ESTADO_CERRADA),
    (0, "2026-2027", 0, None, Campania.ESTADO_EN_PRODUCCION),
    (1, "2026-2027", 1, None, Campania.ESTADO_PLANIFICADA),
    (2, "2026-2027", 0, None, Campania.ESTADO_EN_PRODUCCION),
    (3, "2026-2027", 1, None, Campania.ESTADO_PLANIFICADA),
    (4, "2026-2027", 0, None, Campania.ESTADO_EN_PRODUCCION),
    (5, "2026-2027", 1, None, Campania.ESTADO_PLANIFICADA),
    (6, "2026-2027", 0, None, Campania.ESTADO_EN_PRODUCCION),
    (7, "2026-2027", 1, None, Campania.ESTADO_PLANIFICADA),
    (8, "2026-2027", 0, None, Campania.ESTADO_EN_PRODUCCION),
    (9, "2026-2027", 1, None, Campania.ESTADO_PLANIFICADA),
]

# (fecha, índice de campaña en CAMPANIAS_V2): sobre las de 2026-2027
ACTIVIDADES_V2 = [
    ("2026-03-10", 10),
    ("2026-04-15", 11),
    ("2026-05-20", 12),
    ("2026-06-25", 13),
]

# --------------------------------------------------------------------- #
# V3 (Semana 18): actividades para el reporte RF-68 y bitácora inventada
# para el reporte HU-155/HU-156
# --------------------------------------------------------------------- #
# (fecha, código de tipo, horas, método, densidad (cantidad, unidad),
#  anulada, motivo de anulación, registrado por admin)
# - sin responsable → el administrador no registró esa actividad
# - sin horas → no cuenta en «actividades con horas»
# - la anulada solo aparece con estado_actividad=ANULADAS o TODAS
# La sexta (la de la campaña cancelada) se crea aparte, en el bloque.
ACTIVIDADES_V3 = [
    ("2026-08-15", "PREPARACION", "2.0", "", None, False, None, False),
    ("2026-09-20", "PREPARACION", "4.5", "Arado por disco", None, False, None, True),
    (
        "2026-09-28",
        "SIEMBRA",
        "6.0",
        "Siembra mecanizada",
        ("80", "KG_HA"),
        False,
        None,
        True,
    ),
    (
        "2026-10-05",
        "SIEMBRA",
        None,
        "",
        ("60", "KG_HA"),
        False,
        None,
        True,
    ),
    (
        "2026-10-12",
        "PREPARACION",
        "3.5",
        "Rastreo",
        None,
        True,
        "Lluvia persistente (demo)",
        True,
    ),
]

# (acción, módulo, tabla, registro_id, ip, detalle, horas atrás, con usuario)
# El detalle mezcla claves seguras (tipo, formato, filas, estado, motivo
# NO lo es…) para que el reporte muestre su «blanco seguro»: valores de
# identificadores y contadores, y el resto solo con su nombre en «Campos:»
EVENTOS_V3 = [
    ("LOGIN", MODULO_V3, None, None, "190.42.55.10", None, 6, True),
    ("LOGIN", MODULO_V3, None, None, "190.42.55.99", None, 9, False),
    (
        "CREAR",
        "productores",
        "productores",
        99000011,
        "190.42.55.10",
        {"estado": "ACTIVO", "nota": "Alta de la demo, revisar DNI"},
        74,
        True,
    ),
    (
        "MODIFICAR",
        "productores",
        "productores",
        99000014,
        "190.42.55.10",
        {"estado": "ACTIVO"},
        122,
        True,
    ),
    (
        "ANULAR",
        "seguimiento",
        "actividades",
        4,
        "190.42.55.10",
        {"operacion": "anular", "motivo": "Lluvia persistente (demo)"},
        170,
        True,
    ),
    (
        "EXPORTAR",
        "reportes",
        "productores",
        None,
        "190.42.55.10",
        {
            "tipo": "productores",
            "formato": "pdf",
            "filtros": {"periodo": "2026-2027"},
            "filas": 24,
        },
        220,
        True,
    ),
    (
        "EXPORTAR",
        "reportes",
        None,
        None,
        "127.0.0.1",
        {"tipo": "productivo", "formato": "xlsx", "filtros": {}, "filas": 12},
        480,
        True,
    ),
    (
        "CAMBIAR_CLAVE",
        "usuarios",
        "usuarios",
        1,
        "127.0.0.1",
        {"username": "coordinador"},
        620,
        True,
    ),
]


class Command(BaseCommand):
    help = (
        "Siembra datos de demostración inventados y marcados para el panel "
        "y los reportes (idempotente por bloques; no sustituye a "
        "cargar_ubicacion ni a cargar_catalogos)."
    )

    def handle(self, *args, **opciones):
        faltan = [
            dni
            for dni in DEMO_DNIS
            if not Productor.objects.filter(dni=dni).exists()
        ]
        # Cada bloque se mide por su propia marca: el V3 no crea
        # productores, así que su ausencia no lo excluye del recorrido
        falta_v1 = any(dni in faltan for dni in DEMO_DNIS_V1)
        falta_v2 = any(dni in faltan for dni in DEMO_DNIS_V2)
        falta_v3_act = not Actividad.objects.filter(
            observaciones=MARCA_V3
        ).exists()
        falta_v3_aud = not Auditoria.objects.filter(modulo=MODULO_V3).exists()
        if not (falta_v1 or falta_v2 or falta_v3_act or falta_v3_aud):
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
        if len(cultivos) < 2:
            self.stdout.write(
                self.style.WARNING(
                    "Solo hay un cultivo con variedad activa: el resumen "
                    "por cultivo saldrá con una sola fila (sin POCOS "
                    "DATOS). Crea una variedad para otro cultivo para ver "
                    "el caso completo."
                )
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

        n_prod = 0
        n_par = 0
        n_cam = 0
        n_produ = 0
        n_act = 0
        n_aud = 0
        marcas = []

        with transaction.atomic():
            # --------------------------------------------------------- #
            # V1 — Semana 16 (bloque original, sin cambios)
            # --------------------------------------------------------- #
            if falta_v1:
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
                n_prod += len(PRODUCTORES)

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
                n_par += len(PARCELAS)

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
                n_cam += len(campanias)

                for fecha, indice_campania in ACTIVIDADES:
                    Actividad.objects.create(
                        campania=campanias[indice_campania],
                        tipo_actividad=tipo_actividad,
                        fecha=fecha,
                        observaciones=MARCA,
                        registrado_por=admin,
                    )
                    n_act += 1

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
                    n_produ += 1
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
                marcas.append(MARCA)

            # --------------------------------------------------------- #
            # V2 — Semana 17 (ampliación para los reportes)
            # --------------------------------------------------------- #
            if falta_v2:
                productores_v2 = {}
                for nombres, apellidos, dni, estado in PRODUCTORES_V2:
                    productores_v2[dni] = Productor.objects.create(
                        nombres=nombres,
                        apellidos=apellidos,
                        dni=dni,
                        comunidad=com_a if estado == "ACTIVO" else com_b,
                        referencia_ubicacion=MARCA_V2,
                        estado=estado,
                        creado_por=admin,
                    )
                n_prod += len(PRODUCTORES_V2)

                parcelas_v2 = []
                for indice, (dni, superficie) in enumerate(PARCELAS_V2):
                    parcelas_v2.append(
                        Parcela.objects.create(
                            productor=productores_v2[dni],
                            comunidad=com_a if indice % 2 == 0 else com_b,
                            referencia_ubicacion=MARCA_V2,
                            superficie_ha=Decimal(superficie),
                            altitud_msnm=3100,
                            tipo_suelo="FRANCO",
                            pendiente="SUAVE",
                            disponibilidad_agua="MEDIA",
                            sistema_riego="GRAVEDAD",
                            creado_por=admin,
                        )
                    )
                n_par += len(PARCELAS_V2)

                campanias_v2 = []
                for parcela_i, periodo, cultivo_i, produccion, final in CAMPANIAS_V2:
                    parcela = parcelas_v2[parcela_i]
                    cultivo = (
                        cultivos[cultivo_i] if cultivo_i < len(cultivos) else cultivos[0]
                    )
                    variedad = (
                        variedades[cultivo_i] if cultivo_i < len(variedades) else variedades[0]
                    )
                    # Con producción se crean EN_PRODUCCION (el trigger
                    # las pasa a COSECHADA) y se cierran en el acto tras
                    # producir; sin producción, directo al estado final
                    # (solo PLANIFICADA/EN_PRODUCCION, que es lo único
                    # compatible con los índices de campaña activa).
                    creacion = (
                        Campania.ESTADO_EN_PRODUCCION
                        if produccion is not None
                        else final
                    )
                    anio = periodo[:4]
                    campania = Campania.objects.create(
                        periodo=periodo,
                        parcela=parcela,
                        cultivo=cultivo,
                        variedad=variedad,
                        fecha_inicio=f"{anio}-01-01",
                        fecha_fin_prevista=f"{anio}-12-31",
                        superficie_sembrada_ha=parcela.superficie_ha,
                        estado=creacion,
                        observaciones=MARCA_V2,
                        creado_por=admin,
                    )
                    campanias_v2.append(campania)
                    n_cam += 1
                    if produccion is not None:
                        fecha, superficie, cantidad = produccion
                        Produccion.objects.create(
                            campania=campania,
                            fecha_cosecha=fecha,
                            superficie_cosechada_ha=Decimal(superficie),
                            cantidad_producida=Decimal(cantidad),
                            unidad=unidad,
                            produccion_kg=Decimal("0"),
                            rendimiento_kg_ha=Decimal("0"),
                            observaciones=MARCA_V2,
                            registrado_por=admin,
                        )
                        n_produ += 1
                        # Cierre inmediato (antes de crear la campaña
                        # activa de 2026-2027 de esta misma parcela)
                        campania.refresh_from_db()
                        campania.estado = final
                        campania.save(update_fields=["estado", "actualizado_en"])

                for fecha, indice_campania in ACTIVIDADES_V2:
                    Actividad.objects.create(
                        campania=campanias_v2[indice_campania],
                        tipo_actividad=tipo_actividad,
                        fecha=fecha,
                        observaciones=MARCA_V2,
                        registrado_por=admin,
                    )
                    n_act += 1
                marcas.append(MARCA_V2)

            # --------------------------------------------------------- #
            # V3 — Semana 18 (actividades RF-68 y bitácora HU-155/HU-156)
            # --------------------------------------------------------- #
            if falta_v3_act:
                tipos_v3 = {
                    t.codigo: t
                    for t in TipoActividad.objects.filter(activo=True)
                }
                tipo_prep = tipos_v3.get("PREPARACION") or tipo_actividad
                # Campañas activas del período para las cinco primeras
                # actividades (índice por módulo: evita desbordes si la
                # base demo tiene menos campañas de las esperadas)
                activas_v3 = list(
                    Campania.objects.filter(
                        periodo=PERIODO,
                        estado__in=(
                            Campania.ESTADO_PLANIFICADA,
                            Campania.ESTADO_EN_PRODUCCION,
                        ),
                    ).order_by("id")
                )
                if not activas_v3:
                    raise CommandError(
                        "No hay campañas activas para el bloque V3: ejecuta "
                        "antes los bloques V1/V2 de los datos de demostración."
                    )
                for indice, (
                    fecha,
                    codigo,
                    horas,
                    metodo,
                    densidad,
                    anulada,
                    motivo,
                    con_responsable,
                ) in enumerate(ACTIVIDADES_V3):
                    datos_v3 = {
                        "campania": activas_v3[indice % len(activas_v3)],
                        "tipo_actividad": tipos_v3.get(codigo) or tipo_prep,
                        "fecha": fecha,
                        "metodo": metodo,
                        "anulada": anulada,
                        "observaciones": MARCA_V3,
                        "registrado_por": admin if con_responsable else None,
                    }
                    if horas is not None:
                        datos_v3["horas"] = horas
                    if densidad is not None:
                        datos_v3["densidad_siembra"] = densidad[0]
                        datos_v3["densidad_unidad"] = densidad[1]
                    if motivo is not None:
                        datos_v3["motivo_anulacion"] = motivo
                    Actividad.objects.create(**datos_v3)
                    n_act += 1

                # La sexta: campaña creada, actividad registrada y la
                # campaña cancelada DESPUÉS — los triggers rechazan altas
                # sobre campañas canceladas. Se busca una parcela sin
                # campaña activa y sin campaña no cancelada del período
                # (los dos índices únicos de campañas)
                con_activa = set(
                    Campania.objects.filter(
                        estado__in=(
                            Campania.ESTADO_PLANIFICADA,
                            Campania.ESTADO_EN_PRODUCCION,
                            Campania.ESTADO_COSECHADA,
                        )
                    ).values_list("parcela_id", flat=True)
                )
                ocupadas_periodo = set(
                    Campania.objects.filter(periodo=PERIODO)
                    .exclude(estado=Campania.ESTADO_CANCELADA)
                    .values_list("parcela_id", flat=True)
                )
                parcela_libre = (
                    Parcela.objects.exclude(
                        pk__in=con_activa | ocupadas_periodo
                    )
                    .order_by("id")
                    .first()
                )
                if parcela_libre is not None:
                    campania_v3 = Campania.objects.create(
                        periodo=PERIODO,
                        parcela=parcela_libre,
                        cultivo=cultivos[0],
                        variedad=variedades[0],
                        fecha_inicio="2026-02-01",
                        fecha_fin_prevista="2026-11-30",
                        superficie_sembrada_ha=parcela_libre.superficie_ha,
                        estado=Campania.ESTADO_PLANIFICADA,
                        observaciones=MARCA_V3,
                        creado_por=admin,
                    )
                    Actividad.objects.create(
                        campania=campania_v3,
                        tipo_actividad=tipo_prep,
                        fecha="2026-08-25",
                        horas="1.5",
                        observaciones=MARCA_V3,
                        registrado_por=admin,
                    )
                    n_act += 1
                    campania_v3.estado = Campania.ESTADO_CANCELADA
                    campania_v3.save(
                        update_fields=["estado", "actualizado_en"]
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "No hay parcela libre para la campaña cancelada "
                            "del bloque V3: faltará esa fila en el reporte "
                            "de actividades."
                        )
                    )

            if falta_v3_aud:
                for (
                    accion,
                    modulo,
                    tabla,
                    registro_id,
                    ip,
                    detalle,
                    horas_atras,
                    con_usuario,
                ) in EVENTOS_V3:
                    Auditoria.objects.create(
                        usuario=admin if con_usuario else None,
                        accion=accion,
                        modulo=modulo,
                        tabla=tabla,
                        registro_id=registro_id,
                        ip=ip,
                        detalle=detalle,
                        fecha=timezone.now() - timedelta(hours=horas_atras),
                    )
                    n_aud += 1

            if falta_v3_act or falta_v3_aud:
                marcas.append(MARCA_V3)

        marcas_texto = " y ".join(f"«{m}»" for m in marcas)
        self.stdout.write(
            self.style.SUCCESS(
                "Datos de demostración creados: "
                f"{n_prod} productores, {n_par} parcelas, {n_cam} campañas, "
                f"{n_produ} producciones, {n_act} actividades y "
                f"{n_aud} eventos de bitácora. "
                f"Todos los registros llevan la marca {marcas_texto}."
            )
        )
