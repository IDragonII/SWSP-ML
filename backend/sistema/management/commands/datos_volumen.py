"""datos_volumen: siembra de datos de volumen para pruebas de rendimiento.

Crea un conjunto grande de datos de prueba para validar que las consultas y
operaciones del panel rinden dentro de los límites esperados (meta <2 s
en entorno local, confirmar en CI). Los datos son inventados y llevan una
marca de identificación para idempotencia.

Datos creados (por defecto, números de la planificación F4):
  • 500 productores, 1 000 parcelas, 1 200 campañas, 20 000 actividades,
    100 000 registros de clima.
Escalables con banderas: --productores, --parcelas, --campanias,
--actividades, --clima-dias.

Idempotente: si ya existen datos con la marca correspondiente, no vuelve a
crear nada. Requiere antes `cargar_ubicacion` y `cargar_catalogos`.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Unidad, Variedad
from productores.models import Comunidad, Parcela, Productor
from produccion.models import Produccion
from seguimiento.models import Actividad, Clima


class Command(BaseCommand):
    help = (
        "Siembra datos de volumen para pruebas de rendimiento (idempotente)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--productores",
            type=int,
            default=500,
            help="Cantidad de productores (default 500)",
        )
        parser.add_argument(
            "--parcelas",
            type=int,
            default=1000,
            help="Cantidad de parcelas (default 1000)",
        )
        parser.add_argument(
            "--campanias",
            type=int,
            default=1200,
            help="Cantidad de campañas (default 1 200)",
        )
        parser.add_argument(
            "--actividades",
            type=int,
            default=20000,
            help="Cantidad de actividades (default 20 000)",
        )
        parser.add_argument(
            "--clima-dias",
            type=int,
            default=100,
            help="Días de clima por parcela (default 100)",
        )

    def handle(self, *args, **opciones):
        n_prod = opciones["productores"]
        n_par = opciones["parcelas"]
        n_cam = opciones["campanias"]
        n_act = opciones["actividades"]
        dias_parcela = opciones["clima_dias"]

        marca = "Datos de volumen (Semana 19)"

        # ---- Idempotencia rápida
        if Campania.objects.filter(observaciones__contains=marca).exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "Datos de volumen ya existentes; nada que crear."
                )
            )
            return

        # ---- Verificaciones previas
        comunidades = list(Comunidad.objects.filter(activo=True).order_by("id")[:20])
        if not comunidades:
            raise CommandError(
                "No hay comunidades activas: ejecuta `manage.py cargar_ubicacion` "
                "antes que este comando."
            )

        con_variedad = Variedad.objects.filter(activo=True).values("cultivo_id")
        cultivos = list(
            Cultivo.objects.filter(activo=True, pk__in=con_variedad).order_by("id")
        )
        if not cultivos:
            raise CommandError(
                "No hay cultivos activos con variedad: ejecuta "
                "`manage.py cargar_catalogos` antes que este comando."
            )
        if len(cultivos) < 2:
            self.stdout.write(
                self.style.WARNING(
                    "Solo hay un cultivo con variedad activa: el resumen por "
                    "cultivo saldrá con una sola fila (sin POCOS DATOS). "
                    "Crea una variedad para otro cultivo para ver el caso completo."
                )
            )

        variedades = []
        for cultivo in (cultivos[0], cultivos[1] if len(cultivos) > 1 else cultivos[0]):
            variedad = Variedad.objects.filter(cultivo=cultivo, activo=True).order_by("id").first()
            if variedad is None:
                raise CommandError(
                    f"El cultivo {cultivo.nombre} no tiene variedades activas: "
                    "ejecuta `manage.py cargar_catalogos`."
                )
            variedades.append(variedad)

        unidad = (
            Unidad.objects.filter(tipo="MASA", es_base=True, activo=True)
            .order_by("id")
            .first()
        )
        if unidad is None:
            raise CommandError(
                "No hay unidad de masa base: ejecuta `manage.py cargar_catalogos` "
                "antes que este comando."
            )

        tipo_actividad = (
            TipoActividad.objects.filter(activo=True, codigo="PREPARACION")
            .first()
            or TipoActividad.objects.filter(activo=True)
            .exclude(codigo="SIEMBRA")
            .order_by("codigo")
            .first()
            or TipoActividad.objects.filter(activo=True).order_by("codigo").first()
        )
        if tipo_actividad is None:
            raise CommandError(
                "No hay tipos de actividad: ejecuta `manage.py cargar_catalogos` "
                "antes que este comando."
            )

        Usuario = get_user_model()
        admin = Usuario.objects.filter(is_superuser=True).first()
        if admin is None:
            raise CommandError("No hay usuario administrador: crea un superusuario antes.")

        with transaction.atomic():
            # ----- Productores
            n_prod_creados = 0
            for i in range(n_prod):
                dni = f"{10000001 + i:08d}"
                com = comunidades[0] if i % 2 == 0 else (comunidades[1] if len(comunidades) > 1 else comunidades[0])
                Productor.objects.create(
                    codigo="",
                    nombres=f"Prod{i+1}",
                    apellidos=f"Apellido{i+1}",
                    dni=dni,
                    comunidad=com,
                    telefono=f"+346000000{i}" if i % 10 == 0 else None,
                    referencia_ubicacion=marca,
                    estado="ACTIVO" if i % 2 == 0 else "INACTIVO",
                    creado_por=admin,
                )
                n_prod_creados += 1

            # ----- Parcelas
            n_par_creados = 0
            productores = list(Productor.objects.order_by("id")[:n_prod])
            for idx, prod in enumerate(productores):
                for _ in range(2):
                    if n_par_creados >= n_par:
                        break
                    Parcela.objects.create(
                        codigo="",
                        productor=prod,
                        comunidad=prod.comunidad,
                        referencia_ubicacion=marca,
                        superficie_ha=Decimal(str(round(1.00 + random.random() * 4.99, 2))),
                        altitud_msnm=3000 + idx,
                        latitud=Decimal(str(round(4.000000 + random.random() * 1.0, 6))),
                        longitud=Decimal(str(round(-3.000000 + random.random() * 1.0, 6))),
                        tipo_suelo=random.choice(["ARENOSO", "FRANCO", "ARCILLOSO", "OTRO"]),
                        pendiente=random.choice(["PLANA", "SUAVE", "MODERADA", "FUERTE"]),
                        disponibilidad_agua=random.choice(["ESCASA", "MEDIA", "ABUNDANTE"]),
                        sistema_riego=random.choice(["SECANO", "GRAVEDAD", "ASPERSION", "GOTEO"]),
                        creado_por=admin,
                    )
                    n_par_creados += 1

            # ----- Campañas
            # Estrategia (como datos_demostracion): crear 200 campañas 2025-2026,
            # producir y cerrar a CERRADA; luego crear n_cam_activas campañas
            # 2026-2027 en TODAS las parcelas (incluidas las 200 primeras).
            n_cam_activas = min(n_cam, n_par)
            n_historicas = min(max(n_cam - n_cam_activas, 0), 200, n_par)
            n_cam_creados = 0
            fecha_inicio_2025 = date(2025, 1, 1)
            fecha_fin_2025 = date(2025, 12, 31)
            fecha_inicio_2026 = date(2026, 1, 1)
            fecha_fin_2026 = date(2027, 12, 31)

            parcelas = list(Parcela.objects.order_by("id")[:n_par])

            # 1) Históricas 2025-2026 en las primeras n_historicas parcelas
            for i in range(n_historicas):
                parcela = parcelas[i]
                campania = Campania.objects.create(
                    periodo="2025-2026",
                    parcela=parcela,
                    cultivo=cultivos[i % len(cultivos)],
                    variedad=variedades[i % len(variedades)],
                    fecha_inicio=fecha_inicio_2025,
                    fecha_fin_prevista=fecha_fin_2025,
                    superficie_sembrada_ha=parcela.superficie_ha,
                    estado=Campania.ESTADO_EN_PRODUCCION,
                    observaciones=marca,
                    creado_por=admin,
                )
                # Produce y cierra (transición EN_PRODUCCION -> COSECHADA -> CERRADA)
                # fn_produccion_post pasa a COSECHADA; luego cerramos a CERRADA
                Produccion.objects.create(
                    campania=campania,
                    fecha_cosecha=date(2025, 9, 15),
                    superficie_cosechada_ha=parcela.superficie_ha,
                    cantidad_producida=Decimal(str(round(parcela.superficie_ha * 3000, 1))),
                    unidad=unidad,
                    observaciones=marca,
                    registrado_por=admin,
                )
                campania.refresh_from_db()
                if campania.estado == Campania.ESTADO_COSECHADA:
                    campania.estado = Campania.ESTADO_CERRADA
                    campania.save(update_fields=["estado", "actualizado_en"])
                n_cam_creados += 1

            # 2) Activas 2026-2027 en TODAS las parcelas
            for i in range(n_cam_activas):
                parcela = parcelas[i]
                Campania.objects.create(
                    periodo="2026-2027",
                    parcela=parcela,
                    cultivo=cultivos[i % len(cultivos)],
                    variedad=variedades[i % len(variedades)],
                    fecha_inicio=fecha_inicio_2026,
                    fecha_fin_prevista=fecha_fin_2026,
                    superficie_sembrada_ha=parcela.superficie_ha,
                    estado=Campania.ESTADO_EN_PRODUCCION,
                    observaciones=marca,
                    creado_por=admin,
                )
                n_cam_creados += 1

            # ----- Actividades
            campanias_activas = list(
                Campania.objects.filter(
                    observaciones__contains=marca, estado__in=Campania.ESTADOS_ACTIVOS
                ).order_by("id")
            )
            n_act_creadas = 0
            for i in range(n_act):
                campania = campanias_activas[i % len(campanias_activas)]
                # Fecha dentro del período de la campaña
                dias = (campania.fecha_fin_prevista - campania.fecha_inicio).days
                offset = i % max(1, dias)
                fecha = campania.fecha_inicio + timedelta(days=offset)
                Actividad.objects.create(
                    campania=campania,
                    tipo_actividad=tipo_actividad,
                    fecha=fecha,
                    metodo="",
                    observaciones=marca,
                    registrado_por=admin,
                )
                n_act_creadas += 1

            # ----- Clima
            n_clima_creados = 0
            for parcela in parcelas:
                for d in range(dias_parcela):
                    fecha = date(2025, 1, 1) + timedelta(days=d)
                    temp_min = round(random.uniform(-10, 30), 1)
                    temp_max = round(random.uniform(temp_min, 40), 1)
                    temp_prom = round((temp_min + temp_max) / 2, 1)
                    Clima.objects.create(
                        parcela=parcela,
                        fecha=fecha,
                        temp_min=Decimal(str(temp_min)),
                        temp_max=Decimal(str(temp_max)),
                        temp_prom=Decimal(str(temp_prom)),
                        precipitacion_mm=round(Decimal(str(random.uniform(0, 30))), 1),
                        humedad_pct=round(Decimal(str(random.uniform(20, 80))), 1),
                        viento_ms=round(Decimal(str(random.uniform(0, 15))), 1),
                        radiacion_mj=round(Decimal(str(random.uniform(0, 30))), 1),
                        helada=temp_min < 0,
                        fuente=Clima.FUENTE_MANUAL,
                    )
                    n_clima_creados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Datos de volumen creados: {n_prod_creados} productores, "
                f"{n_par_creados} parcelas, {n_cam_creados} campañas, "
                f"{n_act_creadas} actividades, {n_clima_creados} clima. "
                f"Todos con marca «{marca}»."
            )
        )