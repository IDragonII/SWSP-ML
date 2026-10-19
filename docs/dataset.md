# Dataset de entrenamiento — `vw_dataset_entrenamiento` (RF-51)

Vista de una fila por **campaña cerrada con producción** que alimenta el
módulo de Machine Learning. Definida en
`backend/importaciones/migrations/0002_vista_dataset.py` (Semana 20,
con los cambios de la Semana 21 en `0003_vista_dataset_ids.py`) y
replicada en `DB_sql/02_reglas_y_vista.sql` como referencia del diseño.

```sql
SELECT … FROM vw_dataset_entrenamiento;   -- vista regular, sin REFRESH
```

## Fuentes

| CTE / JOIN | Aporta |
|------------|--------|
| `campanias` + `producciones` | fila base, periodo, superficies, rendimiento |
| `parcelas`, `cultivos`, `variedades` | altitud, suelo, riego, cultivo, variedad |
| `recursos_c` (uso_recursos × recursos) | semilla/fertilizante/jornales/agua por ha (FILTER por categoría, excluye anuladas) |
| `clima_c` (clima entre siembra y cosecha) | precipitación acumulada, temp/humedad promedio, heladas, días con clima |
| `inc_c` (incidencias) | nº de incidencias y severidad máxima |
| `act_c` (actividades) | nº de aplicaciones (FERTILIZACION/FITOSANITARIO) |

**WHERE**: `estado = 'CERRADA'` **y** `incluir_en_entrenamiento` — igual
que siempre; las campañas atípicas marcadas para revisión no entran hasta
que alguien las revisa y cierra.

## Columnas

`campania_id`, **`parcela_id`**, **`productor_id`**, `periodo`,
`anio_campania`, `cultivo`, `variedad`,
`superficie_sembrada_ha`, `altitud_msnm`, `tipo_suelo`, `pendiente`,
`sistema_riego`, **`origen`**, `precipitacion_acum_mm`, `temp_prom_c`,
`humedad_prom_pct`, `n_heladas`, `dias_con_clima`,
**`dias_ventana_clima`**, `semilla_kg_ha`, `fertilizante_kg_ha`,
`jornales_ha`, `agua_m3_ha`, `n_incidencias`, `severidad_max`,
`n_aplicaciones`, `dias_ciclo`, `rendimiento_kg_ha` (etiqueta).

## Semana 21: identificadores y momento de predicción

- **`parcela_id` y `productor_id`** (migración
  `importaciones/0003_vista_dataset_ids`, reversible a la versión de la
  Semana 20): números internos, no datos personales. Sin ellos no se
  puede validar agrupando por productor y una parcela con varias
  campañas aparecería en entrenamiento y en prueba a la vez.
- **Momento de predicción**: el primer modelo se define como
  «rendimiento esperado dado el plan de manejo» y predice **al
  planificar o sembrar** (pregunta U del responsable, pendiente). El
  clima del ciclo solo entra en el Conjunto 2 declarado como techo.
- El total de filas sigue cuadrando con la tarjeta «aptas para
  entrenar» del dashboard (prueba 349): el WHERE no cambia.

## Semana 20: cambios

1. **`origen`** (SISTEMA / IMPORTADA) viene de `campanias.origen`.
2. **NULL = desconocido**: en filas `IMPORTADA`, `n_incidencias`,
   `severidad_max` y `n_aplicaciones` quedan **vacíos, no 0** (la
   importación no trae esas variables); `n_heladas` queda NULL cuando la
   campaña importada no tiene clima. Las `SISTEMA` conservan el
   COALESCE a 0 de siempre. Cero significa «ninguno»; vacío, «no sé».
3. **`dias_ventana_clima`** = `(fecha_cosecha − COALESCE(fecha_siembra,
   fecha_inicio)) + 1`, la misma fórmula que `dias_ventana` de
   `resumen_clima`.

## Notas

- Es una **vista regular** (no materializada): refleja cada importación
  al instante; no hay nada que refrescar.
- Sin `refresh=True`: la prueba 266 (tarjeta «aptas» del dashboard) y el
  entrenamiento leen la misma vista.
- El archivo `importar_historico` la alimenta indirectamente: cada
  campaña importada que llega a CERRADA aparece aquí con `origen=IMPORTADA`.
