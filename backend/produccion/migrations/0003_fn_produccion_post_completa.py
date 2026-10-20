"""fn_produccion_post completa (Sprint 14, decisión 218) — reemplaza la
versión parcial de produccion.0002.

- fn_produccion_post (02_reglas_y_vista.sql:349-367, texto literal):
  además de pasar la campaña de EN_PRODUCCION a COSECHADA, rellena
  `rendimiento_real`, `error_abs` y `error_pct` de las predicciones de
  esa campaña (comparación predicho vs. real, HU-176).
- trg_producciones_post se recrea apuntando a la función nueva (el
  nombre del trigger no cambia y el total sigue en 25).
- La reversión restaura la VERSIÓN PARCIAL de produccion.0002 (nunca se
  edita una migración aplicada): se dropea el trigger, se reemplaza la
  función por el texto de 0002 y se recrea el trigger. Al revertir NO
  se elimina fn_set_actualizado_en (pertenece a productores.0002).
"""
from django.db import migrations

# Texto completo del diseño (02_reglas_y_vista.sql:349-365).
FN_PRODUCION_POST_COMPLETA = """
CREATE FUNCTION fn_produccion_post() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE campanias SET estado = 'COSECHADA'
     WHERE id = NEW.campania_id AND estado = 'EN_PRODUCCION';

    UPDATE predicciones
       SET rendimiento_real = NEW.rendimiento_kg_ha,
           error_abs        = round(abs(NEW.rendimiento_kg_ha - rendimiento_predicho), 2),
           error_pct        = CASE WHEN NEW.rendimiento_kg_ha > 0
                                   THEN round(abs(NEW.rendimiento_kg_ha - rendimiento_predicho)
                                              / NEW.rendimiento_kg_ha * 100, 2)
                              END
     WHERE campania_id = NEW.campania_id;
    RETURN NULL;
END;
$$;
""".strip()

# Versión parcial de produccion.0002 (se restaura al revertir).
FN_PRODUCION_POST_PARCIAL = """
CREATE FUNCTION fn_produccion_post() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE campanias SET estado = 'COSECHADA'
     WHERE id = NEW.campania_id AND estado = 'EN_PRODUCCION';
    RETURN NULL;
END;
$$;
""".strip()

TRG_POST = """
CREATE TRIGGER trg_producciones_post AFTER INSERT OR UPDATE ON producciones
    FOR EACH ROW EXECUTE FUNCTION fn_produccion_post();
""".strip()

DROP_TRG_POST = "DROP TRIGGER IF EXISTS trg_producciones_post ON producciones;"
DROP_FN_POST = "DROP FUNCTION IF EXISTS fn_produccion_post();"


class Migration(migrations.Migration):
    dependencies = [
        ("produccion", "0002_funciones_y_triggers"),
        # la función completa actualiza la tabla predicciones (su cuerpo
        # se resuelve al ejecutar; la dependencia ordena el revertir)
        ("ml", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(
            [
                DROP_TRG_POST,
                DROP_FN_POST,
                FN_PRODUCION_POST_COMPLETA,
                TRG_POST,
            ],
            [
                DROP_TRG_POST,
                DROP_FN_POST,
                FN_PRODUCION_POST_PARCIAL,
                TRG_POST,
            ],
        ),
    ]
