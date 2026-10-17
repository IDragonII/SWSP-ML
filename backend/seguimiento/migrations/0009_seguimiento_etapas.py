"""Tabla seguimiento_etapas (Semana 12): estructura e índices.

Copia literal de 01_tablas.sql:258-268: campaña CASCADE, etapa
RESTRICT, fechas y registrado_por, con la restricción de unicidad
(campaña, etapa) y el CHECK de fechas del diseño. Sin fechas de
creación/cambio: el diseño no las tiene (la auditoría del Sprint 7
cubre el «quién y cuándo»). Índice del diseño: campaña
(ix_seguimiento_campania); la unicidad también sirve de índice.

fn_validar_etapa y los 2 triggers (trg_seguimiento_fecha,
trg_seguimiento_etapa) los crea la migración 0010; con ellos los
triggers del diseño quedan completos (24 de 24). Al revertir esta
migración no se tocan funciones compartidas (fn_validar_fecha_campania
la usan actividades, uso_recursos e incidencias).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campanias", "0003_fn_validar_campania_completa"),
        ("catalogos", "0002_datos_iniciales"),
        ("seguimiento", "0008_fn_trg_incidencias"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SeguimientoEtapa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_inicio", models.DateField(verbose_name="fecha de inicio")),
                ("fecha_fin", models.DateField(blank=True, null=True, verbose_name="fecha de fin")),
                ("observaciones", models.TextField(blank=True, null=True, verbose_name="observaciones")),
                ("campania", models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name="etapas", to="campanias.campania", verbose_name="campaña")),
                ("etapa", models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.PROTECT, related_name="registros", to="catalogos.etapafenologica", verbose_name="etapa")),
                ("registrado_por", models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="etapas_registradas", to=settings.AUTH_USER_MODEL, verbose_name="registrado por")),
            ],
            options={
                "verbose_name": "etapa de seguimiento",
                "verbose_name_plural": "etapas de seguimiento",
                "db_table": "seguimiento_etapas",
                "ordering": ("-fecha_inicio", "id"),
                "indexes": [models.Index(fields=["campania"], name="ix_seguimiento_campania")],
                "constraints": [models.UniqueConstraint(fields=("campania", "etapa"), name="uq_seguimiento_etapa"), models.CheckConstraint(condition=models.Q(("fecha_fin__isnull", True), ("fecha_fin__gte", models.F("fecha_inicio")), _connector="OR"), name="ck_seguimiento_fechas")],
            },
        ),
    ]
