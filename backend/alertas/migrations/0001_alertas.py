"""Tabla alertas (Semana 15): estructura, CHECKs e índices únicos.

Extiende 01_tablas.sql:30 (H. SISTEMA) con los cambios de diseño de la
Semana 15 (HU-124..HU-132): incidencia_id (opcional, exigida solo en
INCIDENCIA_SEVERA), nota_atencion (solo si atendida), índice único por
incidencia (una sola alerta por incidencia) e índice único parcial por
campaña+tipo pendiente para SIN_ACTIVIDAD/RENDIMIENTO_BAJO. Sin
triggers (la lógica vive en alertas/servicio.py).
"""
import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('campanias', '0003_fn_validar_campania_completa'),
        ('productores', '0004_funciones_y_triggers'),
        ('seguimiento', '0010_fn_trg_seguimiento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Alerta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('INCIDENCIA_SEVERA', 'Incidencia severa'), ('SIN_ACTIVIDAD', 'Sin actividad'), ('RENDIMIENTO_BAJO', 'Rendimiento bajo')], max_length=25, verbose_name='tipo')),
                ('mensaje', models.CharField(max_length=250, verbose_name='mensaje')),
                ('creada_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, verbose_name='creada el')),
                ('atendida', models.BooleanField(default=False, verbose_name='atendida')),
                ('atendida_en', models.DateTimeField(blank=True, null=True, verbose_name='atendida el')),
                ('nota_atencion', models.CharField(blank=True, max_length=250, null=True, verbose_name='nota de atención')),
                ('atendida_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alertas_atendidas', to=settings.AUTH_USER_MODEL, verbose_name='atendida por')),
                ('campania', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alertas', to='campanias.campania', verbose_name='campaña')),
                ('incidencia', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alertas', to='seguimiento.incidencia', verbose_name='incidencia')),
                ('productor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alertas', to='productores.productor', verbose_name='productor')),
            ],
            options={
                'verbose_name': 'alerta',
                'verbose_name_plural': 'alertas',
                'db_table': 'alertas',
                'ordering': ('atendida', '-creada_en', '-id'),
                'indexes': [models.Index(condition=models.Q(('atendida', False)), fields=['productor'], name='ix_alertas_pendientes'), models.Index(fields=['campania'], name='ix_alertas_campania')],
                'constraints': [models.UniqueConstraint(fields=('incidencia',), name='uq_alerta_incidencia'), models.UniqueConstraint(condition=models.Q(('atendida', False), ('tipo__in', ('SIN_ACTIVIDAD', 'RENDIMIENTO_BAJO'))), fields=('campania', 'tipo'), name='uq_alerta_pendiente_campania_tipo'), models.CheckConstraint(condition=models.Q(('tipo__in', ('INCIDENCIA_SEVERA', 'SIN_ACTIVIDAD', 'RENDIMIENTO_BAJO'))), name='ck_alerta_tipo'), models.CheckConstraint(condition=models.Q(('atendida', True), ('atendida_en__isnull', True), _connector='OR'), name='ck_alerta_atendida'), models.CheckConstraint(condition=models.Q(('nota_atencion__isnull', True), ('atendida', True), _connector='OR'), name='ck_alerta_nota'), models.CheckConstraint(condition=models.Q(models.Q(('incidencia__isnull', False), ('tipo', 'INCIDENCIA_SEVERA')), models.Q(('incidencia__isnull', True), ('tipo', 'INCIDENCIA_SEVERA'), _negated=True), _connector='OR'), name='ck_alerta_incidencia')],
            },
        ),
    ]
