# `backend/ml` — preparación de datos (Semana 21)

Paquete **plano** (no es una app de Django: sin `models.py` ni
migraciones) con toda la lógica de preparación del dataset de
entrenamiento. La consola que lo usa es
`sistema/management/commands/exportar_dataset.py`; la guía completa
está en `docs/ml_preparacion.md` y las decisiones en
`docs/decisiones_semana21.md`.

| Módulo | Responsabilidad |
|--------|-----------------|
| `columnas.py` | Lista fija de las 28 columnas exportadas y la consulta (`SELECT` explícito, nunca `*`). |
| `catalogo.py` | Catálogo de variables: rol, conjuntos (`plan`, `plan_clima`), cuándo se conoce; control de fuga y umbral de faltantes. |
| `carga.py` | `cargar(ruta)`: valida esquema y tipos del CSV y aplica la cobertura de clima. |
| `limpieza.py` | `limpiar(datos)`: tabla de exclusiones declarativa + resumen solo de conteos. |
| `preparacion.py` | `preparar(datos, conjunto)`: (X, y, pipeline, fuera); el pipeline imputa/escala **dentro del pliegue** y codifica categorías sin inventar. |
| `validacion.py` | `particiones(datos)`: `GroupKFold` por `productor_id` con la semilla 42 (sin productor compartido). |
| `linea_base.py` | `predecir_media` + `evaluar`: la barra a batir (MAE/RMSE en kg/ha). |
| `exportacion.py` | Bytes del CSV, SHA-256, ficha técnica, marca de tiempo y validación de la carpeta (fuera del repo). |
| `tests.py` | Pruebas **346–365** de la Semana 21 (total del repo: 365). |

Reglas del paquete:

1. **Lo que no está en el catálogo no se usa** (anti-fuga).
2. **Nada de datos personales**: ni la vista ni el archivo traen DNI,
   nombres ni teléfono.
3. **Nada de modelos**: aquí no se entrena nada; eso es Sprint 13.
4. **Semilla única**: `exportacion.SEMILLA = 42` (ficha y pliegues).
5. **Los datos viven en `ML_EXPORT_DIR`**, nunca en el repositorio.

Orden típico de llamadas:

```python
from ml.carga import cargar
from ml.limpieza import limpiar
from ml.preparacion import preparar
from ml.validacion import particiones
from ml.linea_base import predecir_media, evaluar
from ml.catalogo import CONJUNTO_PLAN

datos = cargar("D:\\MLDatasetSigpa\\dataset_demostracion_20260225_103211.csv")
limpio, resumen = limpiar(datos)
X, y, pipeline, fuera = preparar(limpio, CONJUNTO_PLAN)
for train, test in particiones(limpio, n_pliegues=5):
    media = predecir_media(limpio["rendimiento_kg_ha"].iloc[train])
    metricas = evaluar(limpio["rendimiento_kg_ha"].iloc[test], [media] * len(test))
```
