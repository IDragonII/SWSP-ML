# Semana 23, decisión 253: la cuarta tabla de ml — tareas_entrenamiento

import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ml', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TareaEntrenamiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('PROCESANDO', 'En proceso'), ('COMPLETADA', 'Completada'), ('FALLIDA', 'Fallida'), ('CANCELADA', 'Cancelada')], default='PENDIENTE', max_length=15, verbose_name='estado')),
                ('progreso', models.JSONField(blank=True, null=True, verbose_name='progreso')),
                ('latido', models.DateTimeField(blank=True, null=True, verbose_name='latido')),
                ('observacion', models.CharField(blank=True, max_length=200, verbose_name='observación')),
                ('error', models.TextField(blank=True, null=True, verbose_name='error')),
                ('creado_en', models.DateTimeField(db_default=django.db.models.functions.datetime.Now(), default=django.utils.timezone.now, verbose_name='creado el')),
                ('resultado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tareas', to='ml.entrenamientoml', verbose_name='resultado')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tareas_entrenamiento', to=settings.AUTH_USER_MODEL, verbose_name='usuario')),
            ],
            options={
                'verbose_name': 'tarea de entrenamiento',
                'verbose_name_plural': 'tareas de entrenamiento',
                'db_table': 'tareas_entrenamiento',
                'ordering': ('-creado_en', 'id'),
                'constraints': [
                    models.CheckConstraint(
                        condition=models.Q(('estado__in', ['PENDIENTE', 'PROCESANDO', 'COMPLETADA', 'FALLIDA', 'CANCELADA'])),
                        name='ck_tarea_estado',
                    ),
                    models.UniqueConstraint(
                        models.Value(1),
                        condition=models.Q(('estado__in', ('PENDIENTE', 'PROCESANDO'))),
                        name='uq_tarea_activa',
                    ),
                    models.CheckConstraint(
                        condition=models.Q(('estado', 'COMPLETADA'), ('resultado__isnull', True), _connector='OR'),
                        name='ck_tarea_resultado',
                    ),
                ],
            },
        ),
    ]
