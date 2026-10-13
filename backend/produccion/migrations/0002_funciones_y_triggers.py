"""fn_validar_produccion, fn_produccion_post (parcial) y 3 triggers.

- fn_validar_produccion (02_reglas_y_vista.sql:279-334, texto literal):
  campaña en EN_PRODUCCION/COSECHADA, superficie cosechada ≤ sembrada,
  fecha de cosecha no anterior a la siembra, unidad de masa; calcula
  produccion_kg (cantidad × factor) y rendimiento_kg_ha, y marca
  requiere_revision con los umbrales de sistema.parametros_sistema.
- trg_producciones_validar: BEFORE INSERT OR UPDATE.
- fn_produccion_post (02_reglas_y_vista.sql:339-355, VERSIÓN PARCIAL):
  pasa la campaña de EN_PRODUCCION a COSECHADA. Omitido el bloque de
  predicciones (tabla inexistente hasta los Sprints 13-14; la migración de
  esos sprints reemplazará la función por la completa del diseño).
- trg_producciones_post: AFTER INSERT OR UPDATE.
- trg_producciones_actualizado: BEFORE UPDATE fija actualizado_en con
  fn_set_actualizado_en (productores.0002: al revertir esta migración NO
  se dropea esa función).

La reversión dropea los 3 triggers y las 2 funciones en ese orden.
"""
from django.db import migrations

FN_VALIDAR_PRODUCION = """
CREATE FUNCTION fn_validar_produccion() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_estado   text;
    v_sembrada numeric;
    v_siembra  date;
    v_min      numeric;
    v_max      numeric;
    v_factor   numeric;
    v_tipo_u   text;
BEGIN
    SELECT estado, superficie_sembrada_ha, fecha_siembra
      INTO v_estado, v_sembrada, v_siembra
      FROM campanias WHERE id = NEW.campania_id;

    IF v_estado NOT IN ('EN_PRODUCCION','COSECHADA') THEN
        RAISE EXCEPTION 'No se puede registrar la cosecha: la campaña no está activa (estado %).', v_estado;
    END IF;
    IF NEW.superficie_cosechada_ha > v_sembrada THEN
        RAISE EXCEPTION 'La superficie cosechada (% ha) supera la sembrada (% ha).',
                        NEW.superficie_cosechada_ha, v_sembrada;
    END IF;
    IF v_siembra IS NOT NULL AND NEW.fecha_cosecha < v_siembra THEN
        RAISE EXCEPTION 'La fecha de cosecha (%) es anterior a la fecha de siembra (%).',
                        NEW.fecha_cosecha, v_siembra;
    END IF;

    -- Conversión de la cantidad escrita a kg
    SELECT factor_a_base, tipo INTO v_factor, v_tipo_u FROM unidades WHERE id = NEW.unidad_id;
    IF v_tipo_u <> 'MASA' THEN
        RAISE EXCEPTION 'La producción debe registrarse en una unidad de masa (kg, quintal, tonelada).';
    END IF;
    NEW.produccion_kg := round(NEW.cantidad_producida * v_factor, 2);

    -- Rendimiento en kg/ha
    NEW.rendimiento_kg_ha := round(NEW.produccion_kg / NEW.superficie_cosechada_ha, 2);

    -- Marca de revisión si el rendimiento es atípico (umbrales en parametros_sistema)
    IF TG_OP = 'INSERT'
       OR NEW.produccion_kg <> OLD.produccion_kg
       OR NEW.superficie_cosechada_ha <> OLD.superficie_cosechada_ha THEN
        SELECT valor::numeric INTO v_min FROM parametros_sistema WHERE clave = 'rendimiento_min_plausible';
        SELECT valor::numeric INTO v_max FROM parametros_sistema WHERE clave = 'rendimiento_max_plausible';

        IF (v_min IS NOT NULL AND NEW.rendimiento_kg_ha < v_min)
           OR (v_max IS NOT NULL AND NEW.rendimiento_kg_ha > v_max) THEN
            NEW.requiere_revision := TRUE;
            NEW.motivo_revision   := 'Rendimiento atípico: ' || NEW.rendimiento_kg_ha || ' kg/ha';
        ELSE
            NEW.requiere_revision := FALSE;
            NEW.motivo_revision   := NULL;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

FN_PRODUCION_POST = """
CREATE FUNCTION fn_produccion_post() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE campanias SET estado = 'COSECHADA'
     WHERE id = NEW.campania_id AND estado = 'EN_PRODUCCION';
    RETURN NULL;
END;
$$;
""".strip()

TRG_VALIDAR = """
CREATE TRIGGER trg_producciones_validar BEFORE INSERT OR UPDATE ON producciones
    FOR EACH ROW EXECUTE FUNCTION fn_validar_produccion();
""".strip()

TRG_POST = """
CREATE TRIGGER trg_producciones_post AFTER INSERT OR UPDATE ON producciones
    FOR EACH ROW EXECUTE FUNCTION fn_produccion_post();
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_producciones_actualizado BEFORE UPDATE ON producciones
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

# Reversión: triggers antes que sus funciones; fn_set_actualizado_en
# pertenece a productores.0002 y aquí no se toca.
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_producciones_actualizado ON producciones;"
)
DROP_TRG_POST = "DROP TRIGGER IF EXISTS trg_producciones_post ON producciones;"
DROP_TRG_VALIDAR = "DROP TRIGGER IF EXISTS trg_producciones_validar ON producciones;"
DROP_FN_POST = "DROP FUNCTION IF EXISTS fn_produccion_post();"
DROP_FN_VALIDAR = "DROP FUNCTION IF EXISTS fn_validar_produccion();"


class Migration(migrations.Migration):
    dependencies = [
        ("produccion", "0001_initial"),
        ("productores", "0004_funciones_y_triggers"),
        # fn_validar_produccion lee los umbrales de parametros_sistema
        ("sistema", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(
            [
                FN_VALIDAR_PRODUCION,
                TRG_VALIDAR,
                FN_PRODUCION_POST,
                TRG_POST,
                TRG_ACTUALIZADO,
            ],
            [
                DROP_TRG_ACTUALIZADO,
                DROP_TRG_POST,
                DROP_TRG_VALIDAR,
                DROP_FN_POST,
                DROP_FN_VALIDAR,
            ],
        ),
    ]
