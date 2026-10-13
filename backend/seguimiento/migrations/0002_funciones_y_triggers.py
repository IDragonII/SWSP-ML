"""fn_validar_fecha_campania, fn_actividad_siembra (v2) y 3 triggers.

- fn_validar_fecha_campania (versión genérica del diseño, 02_reglas_y_vista.sql):
  la fecha debe caer dentro del período de la campaña y esta no puede estar
  CERRADA/CANCELADA. El argumento TG_ARGV[0] indica la columna de fecha; los
  sprints siguientes la reutilizan en uso_recursos, incidencias y etapas.
- trg_actividades_fecha: BEFORE INSERT OR UPDATE OF fecha, campania_id.
- fn_actividad_siembra (v2 Semana 7): recalcula campanias.fecha_siembra como
  la MÍNIMA fecha de las siembras NO anuladas y pasa PLANIFICADA →
  EN_PRODUCCION si queda alguna; si no queda, deja la fecha vacía pero la
  campaña NO vuelve a PLANIFICADA (decisión de la Semana 7).
- trg_actividades_siembra: AFTER INSERT OR UPDATE OF fecha,
  tipo_actividad_id, anulada, campania_id (se dispara también al
  anular/reactivar).
- trg_actividades_actualizado: BEFORE UPDATE fija actualizado_en con
  fn_set_actualizado_en (migración 0002 de productores: al revertir esta
  migración NO se dropea esa función, la usan todas las tablas).

La reversión dropea los 3 triggers y las 2 funciones en ese orden.
"""
from django.db import migrations

FN_VALIDAR_FECHA = """
CREATE FUNCTION fn_validar_fecha_campania() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_fecha  date;
    v_inicio date;
    v_fin    date;
    v_estado text;
BEGIN
    v_fecha := (to_jsonb(NEW) ->> TG_ARGV[0])::date;
    SELECT fecha_inicio, fecha_fin_prevista, estado
      INTO v_inicio, v_fin, v_estado
      FROM campanias WHERE id = NEW.campania_id;

    IF v_estado IN ('CERRADA','CANCELADA') THEN
        RAISE EXCEPTION 'La campaña está % y no admite nuevos registros.', v_estado;
    END IF;
    IF v_fecha < v_inicio OR v_fecha > v_fin THEN
        RAISE EXCEPTION 'La fecha % está fuera del período de la campaña (% a %).',
                        v_fecha, v_inicio, v_fin;
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_FECHA = """
CREATE TRIGGER trg_actividades_fecha BEFORE INSERT OR UPDATE OF fecha, campania_id ON actividades
    FOR EACH ROW EXECUTE FUNCTION fn_validar_fecha_campania('fecha');
""".strip()

FN_SIEMBRA_V2 = """
CREATE FUNCTION fn_actividad_siembra() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_siembra date;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tipos_actividad
                   WHERE id = NEW.tipo_actividad_id AND codigo = 'SIEMBRA') THEN
        RETURN NULL;
    END IF;

    SELECT MIN(a.fecha) INTO v_siembra
      FROM actividades a
      JOIN tipos_actividad t ON t.id = a.tipo_actividad_id
     WHERE a.campania_id = NEW.campania_id
       AND t.codigo = 'SIEMBRA'
       AND NOT a.anulada;

    UPDATE campanias
       SET fecha_siembra = v_siembra,
           estado = CASE WHEN estado = 'PLANIFICADA' AND v_siembra IS NOT NULL
                         THEN 'EN_PRODUCCION' ELSE estado END
     WHERE id = NEW.campania_id;
    RETURN NULL;
END;
$$;
""".strip()

TRG_SIEMBRA = """
CREATE TRIGGER trg_actividades_siembra
    AFTER INSERT OR UPDATE OF fecha, tipo_actividad_id, anulada, campania_id ON actividades
    FOR EACH ROW EXECUTE FUNCTION fn_actividad_siembra();
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_actividades_actualizado BEFORE UPDATE ON actividades
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

# Reversión: triggers antes que sus funciones; fn_set_actualizado_en
# pertenece a productores.0002 y aquí no se toca.
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_actividades_actualizado ON actividades;"
)
DROP_TRG_SIEMBRA = "DROP TRIGGER IF EXISTS trg_actividades_siembra ON actividades;"
DROP_TRG_FECHA = "DROP TRIGGER IF EXISTS trg_actividades_fecha ON actividades;"
DROP_FN_SIEMBRA = "DROP FUNCTION IF EXISTS fn_actividad_siembra();"
DROP_FN_FECHA = "DROP FUNCTION IF EXISTS fn_validar_fecha_campania();"


class Migration(migrations.Migration):
    dependencies = [
        ("seguimiento", "0001_initial"),
        ("productores", "0004_funciones_y_triggers"),
    ]
    operations = [
        migrations.RunSQL(
            [
                FN_VALIDAR_FECHA,
                TRG_FECHA,
                FN_SIEMBRA_V2,
                TRG_SIEMBRA,
                TRG_ACTUALIZADO,
            ],
            [
                DROP_TRG_ACTUALIZADO,
                DROP_TRG_SIEMBRA,
                DROP_FN_SIEMBRA,
                DROP_TRG_FECHA,
                DROP_FN_FECHA,
            ],
        ),
    ]
