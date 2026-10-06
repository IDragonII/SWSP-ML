"""fn_proteger_rol_sistema + trg_roles_proteger (02_reglas_y_vista.sql:69-81).

Impide eliminar en la base los roles con es_sistema = TRUE.
"""
from django.db import migrations

FN = """
CREATE FUNCTION fn_proteger_rol_sistema() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.es_sistema THEN
        RAISE EXCEPTION 'El rol "%" es un rol del sistema y no se puede eliminar.', OLD.nombre;
    END IF;
    RETURN OLD;
END;
$$;
""".strip()

TRG = """
CREATE TRIGGER trg_roles_proteger BEFORE DELETE ON roles
    FOR EACH ROW EXECUTE FUNCTION fn_proteger_rol_sistema();
""".strip()

DROP_TRG = "DROP TRIGGER IF EXISTS trg_roles_proteger ON roles;"
DROP_FN = "DROP FUNCTION IF EXISTS fn_proteger_rol_sistema();"


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0002_datos_iniciales")]
    operations = [
        migrations.RunSQL([FN, TRG], [DROP_TRG, DROP_FN]),
    ]
