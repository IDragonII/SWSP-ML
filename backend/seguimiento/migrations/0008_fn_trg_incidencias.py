"""fn_validar_incidencia y los 3 triggers de incidencias (Semana 11).

- fn_validar_incidencia (02_reglas_y_vista.sql:189-208, texto literal):
  la superficie afectada no puede superar la sembrada de la campaña y el
  agente solo se indique en tipos biológicos (categoria = 'BIOLOGICA').
- trg_incidencias_superficie: BEFORE INSERT OR UPDATE.
- trg_incidencias_fecha: reutiliza fn_validar_fecha_campania
  (seguimiento.0002): la campaña no puede estar CERRADA/CANCELADA y la
  fecha debe caer entre el inicio y el fin previsto.
- trg_incidencias_actualizado: BEFORE UPDATE fija actualizado_en con
  fn_set_actualizado_en (productores.0002).

Con estas 3 piezas los triggers implementados llegan a 22 (los 2 que
faltan del diseño, los de las etapas de la línea de tiempo, llegan en la
Semana 12). La reversión dropea los 3 triggers y fn_validar_incidencia;
NO se dropean fn_set_actualizado_en ni fn_validar_fecha_campania, porque
las usan otras tablas (productores, parcelas, actividades,
uso_recursos, clima…).
"""
from django.db import migrations

FN_VALIDAR_INCIDENCIA = """
CREATE FUNCTION fn_validar_incidencia() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_sembrada numeric;
BEGIN
    IF NEW.superficie_afectada_ha IS NOT NULL THEN
        SELECT superficie_sembrada_ha INTO v_sembrada FROM campanias WHERE id = NEW.campania_id;
        IF NEW.superficie_afectada_ha > v_sembrada THEN
            RAISE EXCEPTION 'La superficie afectada (% ha) supera la sembrada (% ha).',
                            NEW.superficie_afectada_ha, v_sembrada;
        END IF;
    END IF;
    IF NEW.agente_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM tipos_incidencia WHERE id = NEW.tipo_incidencia_id AND categoria = 'BIOLOGICA'
    ) THEN
        RAISE EXCEPTION 'Solo las incidencias de tipo biológico (plaga, enfermedad) pueden indicar un agente.';
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_SUPERFICIE = """
CREATE TRIGGER trg_incidencias_superficie BEFORE INSERT OR UPDATE ON incidencias
    FOR EACH ROW EXECUTE FUNCTION fn_validar_incidencia();
""".strip()

TRG_FECHA = """
CREATE TRIGGER trg_incidencias_fecha BEFORE INSERT OR UPDATE OF fecha, campania_id ON incidencias
    FOR EACH ROW EXECUTE FUNCTION fn_validar_fecha_campania('fecha');
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_incidencias_actualizado BEFORE UPDATE ON incidencias
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

# Reversión: triggers antes que su función; fn_validar_fecha_campania
# (seguimiento.0002) y fn_set_actualizado_en (productores.0002) aquí no
# se tocan: las usan otras tablas.
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_incidencias_actualizado ON incidencias;"
)
DROP_TRG_FECHA = "DROP TRIGGER IF EXISTS trg_incidencias_fecha ON incidencias;"
DROP_TRG_SUPERFICIE = (
    "DROP TRIGGER IF EXISTS trg_incidencias_superficie ON incidencias;"
)
DROP_FN = "DROP FUNCTION IF EXISTS fn_validar_incidencia();"


class Migration(migrations.Migration):
    dependencies = [
        ("seguimiento", "0007_incidencias"),
        # fn_set_actualizado_en (productores.0002) y la tabla de
        # incidencias de seguimiento.0007; fn_validar_fecha_campania
        # viene de seguimiento.0002 y esta migración depende de ella.
        ("productores", "0004_funciones_y_triggers"),
    ]
    operations = [
        migrations.RunSQL(
            [
                FN_VALIDAR_INCIDENCIA,
                TRG_SUPERFICIE,
                TRG_FECHA,
                TRG_ACTUALIZADO,
            ],
            [
                DROP_TRG_ACTUALIZADO,
                DROP_TRG_FECHA,
                DROP_TRG_SUPERFICIE,
                DROP_FN,
            ],
        ),
    ]
