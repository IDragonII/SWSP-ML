"""Tabla incidencias (Semana 11): estructura, restricciones e índices.

Copia de 01_tablas.sql:309-322 más los campos de anulación lógica
anulada/motivo_anulacion de la decisión de la Semana 11 (mismo patrón
que uso_recursos: una incidencia tiene consecuencias, así que se anula
con motivo y no se borra). Índices del diseño: campaña+fecha
(ix_incidencias_campania) y agente (ix_incidencias_agente). Los triggers
y fn_validar_incidencia los crea la migración 0008; al revertir esta
migración no se tocan las funciones compartidas (fn_set_actualizado_en,
fn_validar_fecha_campania).
"""
import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campanias", "0003_fn_validar_campania_completa"),
        ("catalogos", "0002_datos_iniciales"),
        ("seguimiento", "0006_trg_clima_actualizado"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Incidencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField(verbose_name="fecha")),
                ("severidad", models.CharField(choices=[("BAJA", "Baja"), ("MEDIA", "Media"), ("ALTA", "Alta")], max_length=10, verbose_name="severidad")),
                ("descripcion", models.TextField(verbose_name="descripción")),
                ("superficie_afectada_ha", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name="superficie afectada (ha)")),
                ("producto_aplicado", models.CharField(blank=True, max_length=100, null=True, verbose_name="producto aplicado")),
                ("anulada", models.BooleanField(db_default=False, default=False, verbose_name="anulada")),
                ("motivo_anulacion", models.TextField(blank=True, null=True, verbose_name="motivo de anulación")),
                ("creado_en", models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, verbose_name="creado en")),
                ("actualizado_en", models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, verbose_name="actualizado en")),
                ("agente", models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="incidencias", to="catalogos.agente", verbose_name="agente")),
                ("campania", models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name="incidencias", to="campanias.campania", verbose_name="campaña")),
                ("registrado_por", models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="incidencias_registradas", to=settings.AUTH_USER_MODEL, verbose_name="registrado por")),
                ("tipo_incidencia", models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.PROTECT, related_name="incidencias", to="catalogos.tipoincidencia", verbose_name="tipo de incidencia")),
            ],
            options={
                "verbose_name": "incidencia",
                "verbose_name_plural": "incidencias",
                "db_table": "incidencias",
                "ordering": ("-fecha", "id"),
                "indexes": [models.Index(fields=["campania", "fecha"], name="ix_incidencias_campania"), models.Index(fields=["agente"], name="ix_incidencias_agente")],
                "constraints": [models.CheckConstraint(condition=models.Q(("severidad__in", ("BAJA", "MEDIA", "ALTA"))), name="ck_incidencia_severidad"), models.CheckConstraint(condition=models.Q(("superficie_afectada_ha__isnull", True), ("superficie_afectada_ha__gte", 0), _connector="OR"), name="ck_incidencia_superficie"), models.CheckConstraint(condition=models.Q(("anulada", False), ("motivo_anulacion__isnull", False), _connector="OR"), name="ck_incidencia_anulacion")],
            },
        ),
    ]
