"""fn_set_actualizado_en, seq_productor_codigo, fn_codigo_productor y los
2 triggers de productores (02_reglas_y_vista.sql:13-55).

- trg_productores_actualizado: antes de cada UPDATE fija actualizado_en = now()
- trg_productores_codigo: antes de INSERT arma el código PROD-000N si llega
  vacío o nulo (la secuencia no se reinicia: los saltos tras errores son
  normales y no se corrigen; docs/decisiones_semana3.md).
"""
from django.db import migrations

FN_FECHAS = """
CREATE FUNCTION fn_set_actualizado_en() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$;
""".strip()

SEQ = "CREATE SEQUENCE seq_productor_codigo;"

FN_CODIGO = """
CREATE FUNCTION fn_codigo_productor() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        NEW.codigo := 'PROD-' || lpad(nextval('seq_productor_codigo')::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_productores_actualizado BEFORE UPDATE ON productores
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

TRG_CODIGO = """
CREATE TRIGGER trg_productores_codigo BEFORE INSERT ON productores
    FOR EACH ROW EXECUTE FUNCTION fn_codigo_productor();
""".strip()

DROP_TRG_CODIGO = "DROP TRIGGER IF EXISTS trg_productores_codigo ON productores;"
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_productores_actualizado ON productores;"
)
DROP_FN_CODIGO = "DROP FUNCTION IF EXISTS fn_codigo_productor();"
DROP_FN_FECHAS = "DROP FUNCTION IF EXISTS fn_set_actualizado_en();"
DROP_SEQ = "DROP SEQUENCE IF EXISTS seq_productor_codigo;"


class Migration(migrations.Migration):
    dependencies = [("productores", "0001_initial")]
    operations = [
        migrations.RunSQL(
            [FN_FECHAS, SEQ, FN_CODIGO, TRG_ACTUALIZADO, TRG_CODIGO],
            [
                DROP_TRG_CODIGO,
                DROP_TRG_ACTUALIZADO,
                DROP_FN_CODIGO,
                DROP_FN_FECHAS,
                DROP_SEQ,
            ],
        ),
    ]
