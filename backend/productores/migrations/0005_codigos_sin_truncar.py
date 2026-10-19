"""Códigos PROD-/P- sin truncar al pasar de 999 (bug latente S20).

lpad() de PostgreSQL REVELTA el texto al ancho indicado: con la secuencia
en 1000+, fn_codigo_parcela generaba 'P-100' otra vez y el INSERT moría
con «duplicate key value violates unique constraint parcelas_codigo_key»
(la importación histórica lo detectó al quemar secuencias de más de 999
valores en pruebas; los nextval no se revierten con el rollback). Se
sustituye por lpad(s, GREATEST(ancho, length(s)), '0'), que rellena a
lo mínimo y jamás trunca. Mismo fix para fn_codigo_productor (rompería
en 10000). CREATE OR REPLACE conserva el OID: los triggers no cambian.
Diseño actualizado en DB_sql/02_reglas_y_vista.sql.
"""
from django.db import migrations

FN_CODIGO_PRODUCTOR = """
CREATE OR REPLACE FUNCTION fn_codigo_productor() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    siguiente TEXT;
BEGIN
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        siguiente := nextval('seq_productor_codigo')::text;
        NEW.codigo := 'PROD-' || lpad(siguiente, GREATEST(4, length(siguiente)), '0');
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

FN_CODIGO_PARCELA = """
CREATE OR REPLACE FUNCTION fn_codigo_parcela() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    siguiente TEXT;
BEGIN
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        siguiente := nextval('seq_parcela_codigo')::text;
        NEW.codigo := 'P-' || lpad(siguiente, GREATEST(3, length(siguiente)), '0');
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

FN_CODIGO_PRODUCTOR_VIEJA = """
CREATE OR REPLACE FUNCTION fn_codigo_productor() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        NEW.codigo := 'PROD-' || lpad(nextval('seq_productor_codigo')::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

FN_CODIGO_PARCELA_VIEJA = """
CREATE OR REPLACE FUNCTION fn_codigo_parcela() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        NEW.codigo := 'P-' || lpad(nextval('seq_parcela_codigo')::text, 3, '0');
    END IF;
    RETURN NEW;
END;
$$;
""".strip()


class Migration(migrations.Migration):
    dependencies = [("productores", "0004_funciones_y_triggers")]
    operations = [
        migrations.RunSQL(
            [FN_CODIGO_PRODUCTOR, FN_CODIGO_PARCELA],
            [FN_CODIGO_PRODUCTOR_VIEJA, FN_CODIGO_PARCELA_VIEJA],
        ),
    ]
