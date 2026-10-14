"""fn_uso_recurso y los 3 triggers de uso_recursos (Semana 9).

- fn_uso_recurso (02_reglas_y_vista.sql:213-241, texto literal): la unidad
  debe ser del mismo tipo que el recurso y la actividad (si se indica) de
  la misma campaña; calcula cantidad_base = cantidad × factor, redondeada
  a 3 decimales.
- trg_uso_recursos_base: BEFORE INSERT OR UPDATE.
- trg_uso_recursos_fecha: reutiliza fn_validar_fecha_campania
  (seguimiento.0002): la campaña no puede estar CERRADA/CANCELADA y la
  fecha debe caer entre el inicio y el fin previsto.
- trg_uso_recursos_actualizado: BEFORE UPDATE fija actualizado_en con
  fn_set_actualizado_en (productores.0002).

La reversión dropea los 3 triggers y fn_uso_recurso; NO se dropean
fn_set_actualizado_en ni fn_validar_fecha_campania, porque las usan
otras tablas (productores, parcelas, actividades, incidencias…).
"""
from django.db import migrations

FN_USO_RECURSO = """
CREATE FUNCTION fn_uso_recurso() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_factor      numeric;
    v_tipo_unidad text;
    v_tipo_recurso text;
BEGIN
    SELECT factor_a_base, tipo INTO v_factor, v_tipo_unidad
      FROM unidades WHERE id = NEW.unidad_id;
    SELECT tipo_unidad INTO v_tipo_recurso
      FROM recursos WHERE id = NEW.recurso_id;

    IF v_tipo_unidad <> v_tipo_recurso THEN
        RAISE EXCEPTION 'La unidad elegida (tipo %) no es compatible con el recurso (tipo %).',
                        v_tipo_unidad, v_tipo_recurso;
    END IF;

    IF NEW.actividad_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM actividades WHERE id = NEW.actividad_id AND campania_id = NEW.campania_id
    ) THEN
        RAISE EXCEPTION 'La actividad indicada no pertenece a esta campaña.';
    END IF;

    NEW.cantidad_base := round(NEW.cantidad * v_factor, 3);
    RETURN NEW;
END;
$$;
""".strip()

TRG_BASE = """
CREATE TRIGGER trg_uso_recursos_base BEFORE INSERT OR UPDATE ON uso_recursos
    FOR EACH ROW EXECUTE FUNCTION fn_uso_recurso();
""".strip()

TRG_FECHA = """
CREATE TRIGGER trg_uso_recursos_fecha BEFORE INSERT OR UPDATE OF fecha, campania_id ON uso_recursos
    FOR EACH ROW EXECUTE FUNCTION fn_validar_fecha_campania('fecha');
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_uso_recursos_actualizado BEFORE UPDATE ON uso_recursos
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

# Reversión: triggers antes que su función; fn_validar_fecha_campania
# (seguimiento.0002) y fn_set_actualizado_en (productores.0002) aquí no
# se tocan: las usan otras tablas.
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_uso_recursos_actualizado ON uso_recursos;"
)
DROP_TRG_FECHA = "DROP TRIGGER IF EXISTS trg_uso_recursos_fecha ON uso_recursos;"
DROP_TRG_BASE = "DROP TRIGGER IF EXISTS trg_uso_recursos_base ON uso_recursos;"
DROP_FN = "DROP FUNCTION IF EXISTS fn_uso_recurso();"


class Migration(migrations.Migration):
    dependencies = [
        ("seguimiento", "0003_uso_recursos"),
        # fn_set_actualizado_en (productores.0002) y la tabla de
        # actividades de seguimiento.0002; fn_validar_fecha_campania
        # viene de seguimiento.0002 y esta migración depende de ella.
        ("productores", "0004_funciones_y_triggers"),
    ]
    operations = [
        migrations.RunSQL(
            [
                FN_USO_RECURSO,
                TRG_BASE,
                TRG_FECHA,
                TRG_ACTUALIZADO,
            ],
            [
                DROP_TRG_ACTUALIZADO,
                DROP_TRG_FECHA,
                DROP_TRG_BASE,
                DROP_FN,
            ],
        ),
    ]
