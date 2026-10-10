"""fn_validar_campania (versión parcial del Sprint 3) y sus 2 triggers.

- fn_validar_campania: superficie sembrada ≤ superficie de la parcela,
  estado inicial PLANIFICADA/EN_PRODUCCION y solo las transiciones
  planificada → en producción/cancelada y en producción → cancelada.
  RECHAZA cosechada y cerrada: el Sprint 4 publica la versión completa con
  una migración NUEVA que reemplaza esta función (nunca se edita esta).
  Diseño completo en 02_reglas_y_vista.sql:100-134.
- trg_campanias_validar: BEFORE INSERT OR UPDATE ejecuta la función.
- trg_campanias_actualizado: BEFORE UPDATE fija actualizado_en con
  fn_set_actualizado_en (migración 0002 de productores: al revertir esta
  migración NO se dropea esa función, la usan otras tablas).

La reversión dropea los 2 triggers y fn_validar_campania en ese orden.
"""
from django.db import migrations

FN_VALIDAR_CAMPANIA = """
CREATE FUNCTION fn_validar_campania() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_sup_parcela numeric;
BEGIN
    SELECT superficie_ha INTO v_sup_parcela FROM parcelas WHERE id = NEW.parcela_id;
    IF NEW.superficie_sembrada_ha > v_sup_parcela THEN
        RAISE EXCEPTION 'La superficie sembrada (% ha) supera la superficie de la parcela (% ha).',
                        NEW.superficie_sembrada_ha, v_sup_parcela;
    END IF;

    IF TG_OP = 'INSERT' THEN
        -- Una campaña nace planificada o en producción (esta última, para cargas históricas)
        IF NEW.estado NOT IN ('PLANIFICADA','EN_PRODUCCION') THEN
            RAISE EXCEPTION 'Una campaña nueva debe crearse como PLANIFICADA o EN_PRODUCCION.';
        END IF;
    ELSIF NEW.estado <> OLD.estado THEN
        -- Versión Sprint 3: cosechada y cerrada todavía no existen (Sprint 4)
        IF NOT (
            (OLD.estado = 'PLANIFICADA'   AND NEW.estado IN ('EN_PRODUCCION','CANCELADA')) OR
            (OLD.estado = 'EN_PRODUCCION' AND NEW.estado = 'CANCELADA')
        ) THEN
            RAISE EXCEPTION 'Transición de estado no permitida: % -> %.', OLD.estado, NEW.estado;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_VALIDAR = """
CREATE TRIGGER trg_campanias_validar BEFORE INSERT OR UPDATE ON campanias
    FOR EACH ROW EXECUTE FUNCTION fn_validar_campania();
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_campanias_actualizado BEFORE UPDATE ON campanias
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

# Reversión: triggers antes que su función; fn_set_actualizado_en
# pertenece a productores.0002 y aquí no se toca.
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_campanias_actualizado ON campanias;"
)
DROP_TRG_VALIDAR = "DROP TRIGGER IF EXISTS trg_campanias_validar ON campanias;"
DROP_FN_VALIDAR = "DROP FUNCTION IF EXISTS fn_validar_campania();"


class Migration(migrations.Migration):
    dependencies = [
        ("campanias", "0001_initial"),
        ("productores", "0004_funciones_y_triggers"),
    ]
    operations = [
        migrations.RunSQL(
            [FN_VALIDAR_CAMPANIA, TRG_VALIDAR, TRG_ACTUALIZADO],
            [DROP_TRG_ACTUALIZADO, DROP_TRG_VALIDAR, DROP_FN_VALIDAR],
        ),
    ]
