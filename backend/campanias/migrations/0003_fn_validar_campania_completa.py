"""fn_validar_campania completa (Sprint 4) — reemplaza la versión parcial.

- fn_validar_campania (02_reglas_y_vista.sql:100-134, texto literal):
  además de lo de la versión parcial (superficie ≤ parcela y estado
  inicial PLANIFICADA/EN_PRODUCCION), habilita las transiciones
  PLANIFICADA → {EN_PRODUCCION, CANCELADA},
  EN_PRODUCCION → {COSECHADA, CANCELADA} y
  COSECHADA → {CERRADA, EN_PRODUCCION}, y exige producción registrada
  para pasar a CERRADA.
- trg_campanias_validar se recrea apuntando a la función nueva (el nombre
  del trigger no cambia).
- La reversión restaura la VERSIÓN PARCIAL de campanias.0002 (nunca se
  edita una migración aplicada): se dropea el trigger, se reemplaza la
  función por el texto de 0002 y se recrea el trigger.
- trg_campanias_actualizado no se toca.
"""
from django.db import migrations

# Texto completo del diseño (02_reglas_y_vista.sql:100-134).
FN_VALIDAR_CAMPANIA_COMPLETA = """
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
        IF NOT (
            (OLD.estado = 'PLANIFICADA'   AND NEW.estado IN ('EN_PRODUCCION','CANCELADA')) OR
            (OLD.estado = 'EN_PRODUCCION' AND NEW.estado IN ('COSECHADA','CANCELADA'))     OR
            (OLD.estado = 'COSECHADA'     AND NEW.estado IN ('CERRADA','EN_PRODUCCION'))
        ) THEN
            RAISE EXCEPTION 'Transición de estado no permitida: % -> %.', OLD.estado, NEW.estado;
        END IF;

        IF NEW.estado = 'CERRADA'
           AND NOT EXISTS (SELECT 1 FROM producciones WHERE campania_id = NEW.id) THEN
            RAISE EXCEPTION 'No se puede cerrar la campaña: no tiene producción registrada.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

# Versión parcial de campanias.0002 (se restaura al revertir).
FN_VALIDAR_CAMPANIA_PARCIAL = """
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
            (OLD.estado = 'EN_PRODUCCION' AND NEW.estado IN ('CANCELADA'))
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

DROP_TRG_VALIDAR = "DROP TRIGGER IF EXISTS trg_campanias_validar ON campanias;"
DROP_FN_VALIDAR = "DROP FUNCTION IF EXISTS fn_validar_campania();"


class Migration(migrations.Migration):
    dependencies = [
        ("campanias", "0002_funciones_y_triggers"),
        # la función completa consulta la tabla producciones al cerrar
        ("produccion", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(
            [
                DROP_TRG_VALIDAR,
                DROP_FN_VALIDAR,
                FN_VALIDAR_CAMPANIA_COMPLETA,
                TRG_VALIDAR,
            ],
            [
                DROP_TRG_VALIDAR,
                DROP_FN_VALIDAR,
                FN_VALIDAR_CAMPANIA_PARCIAL,
                TRG_VALIDAR,
            ],
        ),
    ]
