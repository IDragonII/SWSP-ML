# Diccionario de variables del dataset (Semana 21)

Las 28 columnas de `vw_dataset_entrenamiento` con su rol y sus
conjuntos. **Fuente única de verdad: `backend/ml/catalogo.py`** —
este documento es su espejo; si cambia uno, cambian los dos (la
prueba 352 comprueba que la vista entera está clasificada y la 350
que la lista de exportación no admite columnas de más).

Ver también: `docs/ml_preparacion.md` (flujo completo) y
`docs/dataset.md` (la vista).

## Columnas

| # | Columna | Rol | Conjuntos | Cuándo se conoce | Observación |
|---|---------|-----|-----------|------------------|-------------|
| 1 | `campania_id` | identificador | — (nunca predictora) | Nunca | Identificador interno; solo para trazabilidad. |
| 2 | `parcela_id` | identificador | — (nunca predictora) | Nunca | Identificador interno; solo para trazabilidad. |
| 3 | `productor_id` | identificador | — (nunca predictora) | Nunca | No es predictor: agrupa la validación para que un productor no aparezca en entrenamiento y en prueba a la vez. |
| 4 | `periodo` | metadato | — (nunca predictora) | Al planificar | Solo para describir los datos; no predice. |
| 5 | `anio_campania` | metadato | — (nunca predictora) | Al planificar | Un año nuevo queda fuera del rango visto: no se usa. |
| 6 | `cultivo` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Al planificar | Categoría; las raras se agrupan en «otra». |
| 7 | `variedad` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Al planificar | Categoría; agrupa categorías raras por variedad. |
| 8 | `superficie_sembrada_ha` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Al planificar | — |
| 9 | `altitud_msnm` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Es de la parcela | Sale si pasa del umbral de faltantes. |
| 10 | `tipo_suelo` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Es de la parcela | Sale si pasa del umbral de faltantes. |
| 11 | `pendiente` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Es de la parcela | Sale si pasa del umbral de faltantes. |
| 12 | `sistema_riego` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Es de la parcela | Sale si pasa del umbral de faltantes. |
| 13 | `origen` | metadato | — (nunca predictora) | Metadato | SISTEMA/IMPORTADA: se usa para comparar y diagnosticar, nunca como predictor. |
| 14 | `precipitacion_acum_mm` | predictor | Conjunto 2 (Plan + clima) | Durante o después del ciclo | Conjunto 2 solo: al predecir de verdad habría que estimarla; cobertura mínima del 80 %. |
| 15 | `temp_prom_c` | predictor | Conjunto 2 (Plan + clima) | Durante o después del ciclo | Conjunto 2 solo; cobertura mínima del 80 %. |
| 16 | `humedad_prom_pct` | predictor | Conjunto 2 (Plan + clima) | Durante o después del ciclo | Conjunto 2 solo; cobertura mínima del 80 %. |
| 17 | `n_heladas` | predictor | Conjunto 2 (Plan + clima) | Durante o después del ciclo | Conjunto 2 solo; cobertura mínima del 80 %. |
| 18 | `dias_con_clima` | cobertura | — (nunca predictora) | Cobertura | Sirve para decidir si el clima del ciclo es válido; no es una variable predictiva. |
| 19 | `dias_ventana_clima` | cobertura | — (nunca predictora) | Cobertura | Denominador de la cobertura de clima. |
| 20 | `semilla_kg_ha` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Al sembrar | — |
| 21 | `fertilizante_kg_ha` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Total del ciclo (plan de manejo) | En campañas del sistema es lo aplicado; se trata como plan. |
| 22 | `jornales_ha` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Total del ciclo (plan de manejo) | En campañas del sistema es lo aplicado; se trata como plan. |
| 23 | `agua_m3_ha` | predictor | Conjunto 1 (Plan), Conjunto 2 (Plan + clima) | Total del ciclo (plan de manejo) | En campañas del sistema es lo aplicado; se trata como plan. |
| 24 | `n_incidencias` | seguimiento | — (nunca predictora) | Durante el ciclo | Reservada al futuro Conjunto 3 «Seguimiento»: ocurren durante el ciclo y solo las tienen las campañas del sistema. |
| 25 | `severidad_max` | seguimiento | — (nunca predictora) | Durante el ciclo | Reservada al futuro Conjunto 3 «Seguimiento». |
| 26 | `n_aplicaciones` | seguimiento | — (nunca predictora) | Durante el ciclo | Reservada al futuro Conjunto 3 «Seguimiento». |
| 27 | `dias_ciclo` | fuga | — (nunca predictora) | Después de cosechar | Fuga: se calcula con la fecha de cosecha, que es futuro al predecir. Nunca entra en ningún conjunto. |
| 28 | `rendimiento_kg_ha` | objetivo | — (nunca predictora) | Después de cosechar | Variable objetivo; se predice, nunca se imputa. |

## Notas

- **Datos personales**: la vista y la lista de exportación **no**
  traen DNI, nombres, apellidos ni teléfono (`COLUMNAS_PROHIBIDAS`
  en `ml/columnas.py`; pruebas 349 y 350).
- **Identificadores** (`campania_id`, `parcela_id`, `productor_id`):
  números internos para trazabilidad y para agrupar la validación;
  jamás son predictores.
- **Objetivo**: `rendimiento_kg_ha` (kg/ha). Se predice; **nunca**
  se imputa; una fila sin objetivo se excluye en la limpieza.
- **Fuga**: `dias_ciclo` se calcula con la fecha de cosecha, que al
  predecir es futuro — no entra en ningún conjunto.
- **Supuestos del desarrollador** (pendientes del responsable):
  cobertura de clima mínima **80 %** (`COBERTURA_CLIMA_MINIMA`) y
  faltantes máximos **40 %** por columna (`UMBRAL_FALTANTES`).
- **Semilla** de la semana: **42** (`ml.exportacion.SEMILLA`).
