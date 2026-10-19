"""Semana 21: la vista del dataset trae productor_id y parcela_id (RF-51).

Sin identificadores no se puede validar agrupando por productor: una
parcela con varias campañas acabaría en entrenamiento y en prueba a la
vez y las métricas se inflarían (prueba 349). Son números internos, no
datos personales.

Cambio de diseño registrado en decisiones_semana21.md: las dos columnas
nuevas de vw_dataset_entrenamiento y el módulo de auditoría «Machine
Learning» (este último sin migración: auditoria.modulo es texto libre).

Reversible: al revertir vuelve exactamente a la vista de la Semana 20
(sin las dos columnas). El WHERE no cambia, así que el total sigue
cuadrando con la tarjeta «aptas para entrenar» del dashboard.
"""
from django.db import migrations

# Encabezado de filas: con los identificadores (S21) y sin ellos (S20).
CON_IDS = """    c.id                                            AS campania_id,
    c.parcela_id,
    pa.productor_id,
    c.periodo,"""

SIN_IDS = """    c.id                                            AS campania_id,
    c.periodo,"""

# Vista de la Semana 21 (mismos CTE, joins y WHERE que la de la S20).
VISTA_S21 = """
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
    c.parcela_id,
    pa.productor_id,
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

# Versión de la Semana 20: idéntica, solo sin las dos columnas de ids.
VISTA_S20 = VISTA_S21.replace(CON_IDS, SIN_IDS)

BORRAR = "DROP VIEW IF EXISTS vw_dataset_entrenamiento;"


class Migration(migrations.Migration):
    dependencies = [("importaciones", "0002_vista_dataset")]

    operations = [
        migrations.RunSQL(
            sql=BORRAR + VISTA_S21,
            reverse_sql=BORRAR + VISTA_S20,
        ),
    ]
