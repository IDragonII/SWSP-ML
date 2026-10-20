# Informe de resultados de los modelos de rendimiento

> **Semana 22 — generación automática de `entrenar_modelos` (versión 1).**
> Criterio de selección: `docs/criterio_seleccion.md`, escrito antes de entrenar.

## Datos

- Archivo: `dataset_demostracion_ml_20261019_230939.csv`
- Origen declarado: **demostración**
- Filas usadas: **48** (tramo: 30 a 99 reales)
- Estrategia: cv_repetida (5 pliegues × 5 repetición(es), semilla 42, agrupado por productor)

## Tabla comparativa (validación agrupada)

| Algoritmo | MAE (kg/ha) | RMSE (kg/ha) | Desvío entre pliegues | R² | MAPE |
|---|---:|---:|---:|---:|---:|
| REGRESION_LINEAL | 4.50 | 5.48 | 1.24 | 0.947 | 1.42 % |
| RANDOM_FOREST | 8.95 | 11.17 | 2.25 | 0.780 | 2.81 % |
| GRADIENT_BOOSTING | 7.25 | 8.78 | 1.82 | 0.864 | 2.28 % |
| Línea base (media) | 20.90 | 24.47 | 3.80 | -0.043 | 6.60 % |

## Criterio aplicado

**Resultado:** REGRESION_LINEAL gana con el menor RMSE (5.48); la diferencia con los demás supera el desvío (1.24).

**Modelo elegido:** REGRESION_LINEAL

## Métricas por cultivo (elegido)

| Cultivo | Filas | MAE | RMSE |
|---|---:|---:|---:|
| Cañihua | 120 | 5.28 | 6.57 |
| Quinua | 120 | 3.73 | 4.47 |

## Qué se puede afirmar

- **Los datos son de demostración o menores de 30 campañas:** estas métricas son una **verificación técnica del flujo**, NO un resultado de la tesis.
- El sistema está comprobado: entrena, compara, elige con el criterio escrito y guarda el modelo.
- Ningún modelo se activa si no mejora a la línea base.

---

Limitaciones y mejoras futuras: `docs/limitaciones_conocidas.md`.
