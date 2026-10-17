"""fn_validar_etapa y los 2 triggers de seguimiento_etapas (Semana 12).

- fn_validar_etapa (02_reglas_y_vista.sql:172-184, texto literal): la
  etapa seleccionada debe pertenecer al cultivo de la campaña.
- trg_seguimiento_etapa: BEFORE INSERT OR UPDATE OF etapa_id,
  campania_id (02_reglas_y_vista.sql:185-186).
- trg_seguimiento_fecha: reutiliza fn_validar_fecha_campania
  (seguimiento.0002): la campaña no puede estar CERRADA/CANCELADA y la
  fecha de inicio debe caer entre el inicio y el fin previsto
  (02_reglas_y_vista.sql:168-169).

No hay trigger de fecha de cambio ni de actualizado: la tabla no tiene
esas columnas en el diseño. Con estas 2 piezas los triggers
implementados llegan a 24 (el diseño completo). La reversión dropea los
2 triggers y fn_validar_etapa; NO se dropea fn_validar_fecha_campania,
porque la usan actividades, uso_recursos e incidencias.
"""
from django.db import migrations

FN_VALIDAR_ETAPA = """
CREATE FUNCTION fn_validar_etapa() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM campanias c
        JOIN etapas_fenologicas e ON e.cultivo_id = c.cultivo_id
        WHERE c.id = NEW.campania_id AND e.id = NEW.etapa_id
    ) THEN
        RAISE EXCEPTION 'La etapa seleccionada no corresponde al cultivo de la campaña.';
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_ETAPA = """
CREATE TRIGGER trg_seguimiento_etapa BEFORE INSERT OR UPDATE OF etapa_id, campania_id ON seguimiento_etapas
    FOR EACH ROW EXECUTE FUNCTION fn_validar_etapa();
""".strip()

TRG_FECHA = """
CREATE TRIGGER trg_seguimiento_fecha BEFORE INSERT OR UPDATE OF fecha_inicio, campania_id ON seguimiento_etapas
    FOR EACH ROW EXECUTE FUNCTION fn_validar_fecha_campania('fecha_inicio');
""".strip()

# Reversión: triggers antes que su función; fn_validar_fecha_campania
# (seguimiento.0002) aquí no se toca: la usan otras tablas.
DROP_TRG_FECHA = "DROP TRIGGER IF EXISTS trg_seguimiento_fecha ON seguimiento_etapas;"
DROP_TRG_ETAPA = "DROP TRIGGER IF EXISTS trg_seguimiento_etapa ON seguimiento_etapas;"
DROP_FN = "DROP FUNCTION IF EXISTS fn_validar_etapa();"


class Migration(migrations.Migration):
    dependencies = [
        ("seguimiento", "0009_seguimiento_etapas"),
        # La tabla de etapas (0009) y, por la cadena de dependencias,
        # fn_validar_fecha_campania (seguimiento.0002).
        ("seguimiento", "0002_funciones_y_triggers"),
    ]
    operations = [
        migrations.RunSQL(
            [
                FN_VALIDAR_ETAPA,
                TRG_ETAPA,
                TRG_FECHA,
            ],
            [
                DROP_TRG_FECHA,
                DROP_TRG_ETAPA,
                DROP_FN,
            ],
        ),
    ]
