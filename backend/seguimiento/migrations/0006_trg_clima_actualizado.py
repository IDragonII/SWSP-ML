"""trg_clima_actualizado (Semana 10): actualizado_en de la tabla clima.

Reutiliza fn_set_actualizado_en (productores.0002), igual que las demás
tablas del sistema. Es el **único** trigger de clima en el diseño
(02_reglas_y_vista.sql): el resto de sus reglas son restricciones de la
tabla (CHECK + única) que ya crea la migración 0005. Con este, los
triggers implementados llegan a 19.

La reversión dropea solo el trigger; NO se dropea fn_set_actualizado_en,
porque la usan productores, parcelas, campanias, actividades,
uso_recursos, producciones y parametros_sistema.
"""
from django.db import migrations

TRG_ACTUALIZADO = """
CREATE TRIGGER trg_clima_actualizado BEFORE UPDATE ON clima
    FOR EACH ROW EXECUTE FUNCTION fn_set_actualizado_en();
""".strip()

DROP_TRG_ACTUALIZADO = (
    "DROP TRIGGER IF EXISTS trg_clima_actualizado ON clima;"
)


class Migration(migrations.Migration):
    dependencies = [
        ("seguimiento", "0005_clima"),
        # fn_set_actualizado_en (el trigger de esta tabla vive aquí)
        ("productores", "0004_funciones_y_triggers"),
    ]
    operations = [
        migrations.RunSQL([TRG_ACTUALIZADO], [DROP_TRG_ACTUALIZADO]),
    ]
