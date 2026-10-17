"""fn_auditoria_inmutable y su trigger (Semana 13): el trigger 25.

- fn_auditoria_inmutable (02_reglas_y_vista.sql, texto literal):
  cualquier UPDATE o DELETE sobre la auditoría se rechaza con un 500
  claro; los eventos solo se insertan desde la API.
- trg_auditoria_inmutable: BEFORE UPDATE OR DELETE, FOR EACH ROW.

Con este trigger los triggers implementados llegan a 25 (el total del
diseño tras la Semana 13). La reversión dropea el trigger y la función.
"""
from django.db import migrations

FN_AUDITORIA_INMUTABLE = """
CREATE FUNCTION fn_auditoria_inmutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los registros de auditoría no se pueden modificar ni eliminar.';
END;
$$;
""".strip()

TRG_INMUTABLE = """
CREATE TRIGGER trg_auditoria_inmutable BEFORE UPDATE OR DELETE ON auditoria
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria_inmutable();
""".strip()

DROP_TRG = (
    "DROP TRIGGER IF EXISTS trg_auditoria_inmutable ON auditoria;"
)
DROP_FN = "DROP FUNCTION IF EXISTS fn_auditoria_inmutable();"


class Migration(migrations.Migration):
    dependencies = [
        ("auditoria", "0001_auditoria"),
    ]
    operations = [
        migrations.RunSQL(
            [
                FN_AUDITORIA_INMUTABLE,
                TRG_INMUTABLE,
            ],
            [
                DROP_TRG,
                DROP_FN,
            ],
        ),
    ]
