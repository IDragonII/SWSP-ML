"""seq_parcela_codigo, fn_codigo_parcela, fn_validar_asignacion y los
3 triggers de la Semana 4 (02_reglas_y_vista.sql:29-97).

- trg_parcelas_actualizado: reutiliza fn_set_actualizado_en, creada en la
  migración 0002: al revertir esta migración NO se dropea esa función.
- trg_parcelas_codigo: antes de INSERT arma el código P-00N si llega vacío
  (la secuencia no se reinicia: mismas reglas que PROD-000N).
- trg_asignaciones_validar: exige un rol con limita_a_asignados, con el
  mensaje literal del diseño; la API valida antes y responde 400 en español
  (decisión 8 de docs/decisiones_semana4.md).
"""
from django.db import migrations

SEQ = "CREATE SEQUENCE seq_parcela_codigo;"

FN_CODIGO_PARCELA = """
CREATE FUNCTION fn_codigo_parcela() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        NEW.codigo := 'P-' || lpad(nextval('seq_parcela_codigo')::text, 3, '0');
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_parcelas_actualizado BEFORE UPDATE ON parcelas
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

TRG_CODIGO = """
CREATE TRIGGER trg_parcelas_codigo BEFORE INSERT ON parcelas
    FOR EACH ROW EXECUTE FUNCTION fn_codigo_parcela();
""".strip()

FN_VALIDAR = """
CREATE FUNCTION fn_validar_asignacion() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM usuarios u JOIN roles r ON r.id = u.rol_id
        WHERE u.id = NEW.tecnico_id AND r.limita_a_asignados
    ) THEN
        RAISE EXCEPTION 'El usuario % no tiene un rol que trabaje con productores asignados.',
                        NEW.tecnico_id;
    END IF;
    RETURN NEW;
END;
$$;
""".strip()

TRG_VALIDAR = """
CREATE TRIGGER trg_asignaciones_validar BEFORE INSERT OR UPDATE ON asignaciones_tecnico
    FOR EACH ROW EXECUTE FUNCTION fn_validar_asignacion();
""".strip()

# Reversión: triggers antes que sus funciones; fn_set_actualizado_en
# pertenece a 0002 y aquí no se toca.
DROP_TRG_VALIDAR = (
    "DROP TRIGGER IF EXISTS trg_asignaciones_validar ON asignaciones_tecnico;"
)
DROP_TRG_CODIGO = "DROP TRIGGER IF EXISTS trg_parcelas_codigo ON parcelas;"
DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_parcelas_actualizado ON parcelas;"
)
DROP_FN_VALIDAR = "DROP FUNCTION IF EXISTS fn_validar_asignacion();"
DROP_FN_CODIGO_PARCELA = "DROP FUNCTION IF EXISTS fn_codigo_parcela();"
DROP_SEQ = "DROP SEQUENCE IF EXISTS seq_parcela_codigo;"


class Migration(migrations.Migration):
    dependencies = [("productores", "0003_parcelas_y_asignaciones")]
    operations = [
        migrations.RunSQL(
            [SEQ, FN_CODIGO_PARCELA, TRG_ACTUALIZADO, TRG_CODIGO, FN_VALIDAR, TRG_VALIDAR],
            [
                DROP_TRG_VALIDAR,
                DROP_TRG_CODIGO,
                DROP_TRG_ACTUALIZADO,
                DROP_FN_VALIDAR,
                DROP_FN_CODIGO_PARCELA,
                DROP_SEQ,
            ],
        ),
    ]
