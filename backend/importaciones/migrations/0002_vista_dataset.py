"""Semana 20: materializa vw_dataset_entrenamiento en la BD de Django.

Antes la vista solo existía en el diseño (DB_sql/02_reglas_y_vista.sql)
por decisión S10/S11; la comprobación de la tarjeta «aptas» (prueba 266)
ejecutaba el texto del archivo. Ahora la BD tiene su propia copia con
los cambios de la S20:

- columna origen (SISTEMA/IMPORTADA) de campanias;
- dias_ventana_clima = (fecha_cosecha - COALESCE(fecha_siembra,
  fecha_inicio)) + 1, la misma fórmula que dias_ventana de resumen_clima;
- las variables que la importación no conoce quedan VACÍAS (NULL), no en
  cero: n_incidencias, severidad_max y n_aplicaciones para IMPORTADA, y
  n_heladas cuando una importada no tiene clima. Las SISTEMA conservan
  el comportamiento anterior (COALESCE a 0).

El WHERE no cambia (CERRADA + incluir_en_entrenamiento): la tarjeta
aptas_entrenar del dashboard sigue cuadrando con la vista.
"""
from django.db import migrations

VISTA = """
CREATE VIEW vw_dataset_entrenamiento AS
WITH recursos_c AS (
    SELECT ur.campania_id,
           SUM(ur.cantidad_base) FILTER (WHERE r.categoria = 'SEMILLA')                 AS semilla_kg,
           SUM(ur.cantidad_base) FILTER (WHERE r.categoria IN ('FERTILIZANTE','ABONO')) AS fertilizante_kg,
           SUM(ur.cantidad_base) FILTER (WHERE r.categoria = 'MANO_OBRA')               AS jornales,
           SUM(ur.cantidad_base) FILTER (WHERE r.categoria = 'AGUA')                    AS agua_m3
      FROM uso_recursos ur
      JOIN recursos r ON r.id = ur.recurso_id
     WHERE NOT ur.anulada
     GROUP BY ur.campania_id
),
clima_c AS (
    SELECT c.id AS campania_id,
           SUM(cl.precipitacion_mm)                  AS precipitacion_acum_mm,
           AVG(cl.temp_prom)                         AS temp_prom_c,
           AVG(cl.humedad_pct)                       AS humedad_prom_pct,
           COUNT(*) FILTER (WHERE cl.helada)         AS n_heladas,
           COUNT(*)                                  AS dias_con_clima
      FROM campanias c
      JOIN producciones pr ON pr.campania_id = c.id
      JOIN clima cl ON cl.parcela_id = c.parcela_id
                   AND cl.fecha BETWEEN COALESCE(c.fecha_siembra, c.fecha_inicio) AND pr.fecha_cosecha
     GROUP BY c.id
),
inc_c AS (
    SELECT i.campania_id,
           COUNT(*) AS n_incidencias,
           MAX(CASE i.severidad WHEN 'ALTA' THEN 3 WHEN 'MEDIA' THEN 2 ELSE 1 END) AS severidad_max
      FROM incidencias i
     WHERE NOT i.anulada
     GROUP BY i.campania_id
),
act_c AS (
    SELECT a.campania_id,
           COUNT(*) FILTER (WHERE ta.codigo IN ('FERTILIZACION','FITOSANITARIO')) AS n_aplicaciones
      FROM actividades a
      JOIN tipos_actividad ta ON ta.id = a.tipo_actividad_id
     WHERE NOT a.anulada
     GROUP BY a.campania_id
)
SELECT
    c.id                                            AS campania_id,
    c.periodo,
    CAST(LEFT(c.periodo, 4) AS integer)             AS anio_campania,
    cu.nombre                                       AS cultivo,
    va.nombre                                       AS variedad,
    c.superficie_sembrada_ha,
    pa.altitud_msnm,
    pa.tipo_suelo,
    pa.pendiente,
    pa.sistema_riego,
    c.origen,
    cc.precipitacion_acum_mm,
    ROUND(cc.temp_prom_c, 1)                        AS temp_prom_c,
    ROUND(cc.humedad_prom_pct, 1)                   AS humedad_prom_pct,
    CASE WHEN c.origen = 'IMPORTADA' AND cc.dias_con_clima IS NULL
         THEN NULL ELSE COALESCE(cc.n_heladas, 0) END AS n_heladas,
    cc.dias_con_clima,
    (pr.fecha_cosecha - COALESCE(c.fecha_siembra, c.fecha_inicio)) + 1
                                                    AS dias_ventana_clima,
    ROUND(rc.semilla_kg      / c.superficie_sembrada_ha, 2) AS semilla_kg_ha,
    ROUND(rc.fertilizante_kg / c.superficie_sembrada_ha, 2) AS fertilizante_kg_ha,
    ROUND(rc.jornales        / c.superficie_sembrada_ha, 2) AS jornales_ha,
    ROUND(rc.agua_m3         / c.superficie_sembrada_ha, 2) AS agua_m3_ha,
    CASE WHEN c.origen = 'IMPORTADA'
         THEN NULL ELSE COALESCE(ic.n_incidencias, 0) END AS n_incidencias,
    CASE WHEN c.origen = 'IMPORTADA'
         THEN NULL ELSE COALESCE(ic.severidad_max, 0) END AS severidad_max,
    CASE WHEN c.origen = 'IMPORTADA'
         THEN NULL ELSE COALESCE(ac.n_aplicaciones, 0) END AS n_aplicaciones,
    (pr.fecha_cosecha - c.fecha_siembra)            AS dias_ciclo,
    pr.rendimiento_kg_ha                            AS rendimiento_kg_ha
FROM campanias c
JOIN producciones pr ON pr.campania_id = c.id
JOIN parcelas     pa ON pa.id = c.parcela_id
JOIN cultivos     cu ON cu.id = c.cultivo_id
JOIN variedades   va ON va.id = c.variedad_id
LEFT JOIN recursos_c rc ON rc.campania_id = c.id
LEFT JOIN clima_c    cc ON cc.campania_id = c.id
LEFT JOIN inc_c      ic ON ic.campania_id = c.id
LEFT JOIN act_c      ac ON ac.campania_id = c.id
WHERE c.estado = 'CERRADA'
  AND pr.incluir_en_entrenamiento;
"""

BORRAR = "DROP VIEW IF EXISTS vw_dataset_entrenamiento;"


class Migration(migrations.Migration):
    dependencies = [
        ("importaciones", "0001_initial"),
        ("campanias", "0004_campania_origen_campania_ck_campania_origen"),
        ("catalogos", "0003_recursos_genericos"),
        ("produccion", "0002_funciones_y_triggers"),
        ("seguimiento", "0010_fn_trg_seguimiento"),
        ("productores", "0004_funciones_y_triggers"),
    ]

    operations = [
        migrations.RunSQL(sql=VISTA, reverse_sql=BORRAR),
    ]
