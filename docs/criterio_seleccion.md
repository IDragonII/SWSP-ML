# Criterio de selección del modelo de predicción

> **Escrito y commiteado ANTES de ejecutar el primer entrenamiento**
> (Semana 22, primer día). Este archivo es la regla que se aplica tal
> cual en la prueba 367; no se modifica después de ver resultados.

## Candidatos

Los tres algoritmos del diseño, con hiperparámetros **fijos** (sin
búsqueda) y la línea base (media del conjunto de entrenamiento):

| Candidato | Hiperparámetros fijos |
|-----------|----------------------|
| Regresión lineal | Con escalado (StandardScaler dentro del pliegue) |
| Random Forest | 300 árboles, `min_samples_leaf` ≥ 3 campañas |
| Gradient Boosting | 200 árboles, tasa 0.05, profundidad 2 |
| Línea base | Media del entrenamiento (no compite: es la barra) |

## Validación común

- **GroupKFold** por `productor_id`, 5 pliegues, semilla **42**
  (`ml.validacion.particiones`): las mismas particiones para los tres
  candidatos y para la línea base.
- Si hay 100 o más campañas reales: además, conjunto de prueba final
  del 20 % usado **una sola vez**. Con 30 a 99: validación cruzada
  repetida (5 × 5). **Con menos de 30 (tramo actual, 13 campañas de
  demostración): solo validación cruzada agrupada y las métricas no se
  presentan como resultado de la tesis.**

## Métricas

- **RMSE** (criterio principal), **MAE** y **R²** en kg/ha, siempre
  **frente a la línea base en cada pliegue**.
- MAPE solo si no hay rendimientos en cero.

## Regla de elección (en este orden)

1. Calcular el RMSE medio de cada candidato en los pliegues y su
   **desvío estándar entre particiones**.
2. **Gana el de menor RMSE medio.**
3. Si la diferencia entre el mejor y un candidato **más simple** es
   **menor que un desvío estándar entre particiones** (el del mejor),
   gana el más simple, en este orden de simplicidad:
   **regresión lineal → Random Forest → Gradient Boosting**.
4. **Requisito frente a la línea base:** el modelo elegido debe
   **mejorar el RMSE de la línea base**. Si ninguno la mejora, se
   declara en el informe que ningún modelo aporta y **no se activa
   ninguno** (los resultados quedan registrados como evidencia).

## Salida

El modelo elegido se guarda con su pipeline (incluida la preparación)
en `backend/ml_models/`, se registra con `registrar_modelo` y se
comprueba que carga en un proceso limpio (prueba 368).
