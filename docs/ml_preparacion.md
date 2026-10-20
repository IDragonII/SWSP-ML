# Preparación de datos para Machine Learning (Semana 21)

Guía del flujo que lleva de las campañas cerradas de SIGPA-GA a un
dataset listo para entrenar (Sprint 13). **Ningún modelo se entrena en
esta semana**: aquí solo se exporta, se valida, se limpia, se prepara y
se mide la línea base. Los datos de ejemplo son **de demostración** y
así se marcan en todas partes.

---

## 1. La carpeta: `ML_EXPORT_DIR`

El dataset **nunca vive en el repositorio**. El comando escribe en la
carpeta que define la variable `ML_EXPORT_DIR` del `.env` (fuera de
Git y de carpetas sincronizadas en la nube):

```env
ML_EXPORT_DIR=D:\MLDatasetSigpa
```

El comando **rechaza** cualquier ruta que caiga dentro del repositorio
(raíz o subcarpeta) y también si la variable no está definida. El
archivo es dato sensible: sin nombres ni DNI, pero la combinación de
altitud, cultivo y período puede identificar una parcela.

## 2. Generar el dataset: `exportar_dataset`

```powershell
cd backend
# Ensayo: informa sin escribir nada
.\venv\Scripts\python.exe manage.py exportar_dataset `
    --usuario admin --origen-datos demostracion --dry-run

# Exportación real
.\venv\Scripts\python.exe manage.py exportar_dataset `
    --usuario admin --origen-datos demostracion
```

Requisitos:

- Usuario **existente, activo** y con el permiso **`ml.entrenar`**
  (hoy solo el Administrador).
- `--origen-datos` es **obligatorio**: `real` o `demostracion`. La
  respuesta queda en la ficha y en los notebooks.
- Campañas `CERRADA` con `incluir_en_entrenamiento` (la vista
  `vw_dataset_entrenamiento` decide qué filas entran).

Salida: un CSV (UTF-8 con BOM, punto decimal «.») y su ficha técnica
JSON. El orden es a prueba de fallos: el archivo se arma en memoria,
se calcula la huella, se registra el evento de auditoría `EXPORTAR`
(módulo «Machine Learning», con filas, origen y huella **sin
contenido**) y **solo entonces** se escribe el disco; si la auditoría
falla, no hay archivo.

Ejemplo de ficha:

```json
{
  "fecha": "2026-02-25T10:32:11-05:00",
  "filas": 13,
  "columnas": ["campania_id", "parcela_id", "..."],
  "sha256": "3f786850e387550fdab836ed7e6dc881de23001b",
  "origen_datos": "demostracion",
  "semilla": 42
}
```

## 3. El flujo en código (`backend/ml/`)

| Paso | Módulo | Qué hace |
|------|--------|----------|
| 1. Columnas | `columnas.py` | Lista fija de las 28 columnas exportadas (nunca `SELECT *`) y las prohibidas (DNI, nombres, teléfonos). |
| 2. Carga | `carga.py` | `cargar(ruta)` valida columnas y tipos, convierte y aplica la cobertura de clima. **Todos los consumidores pasan por aquí.** |
| 3. Limpieza | `limpieza.py` | `limpiar(datos)` aplica la tabla de exclusiones (abajo) y devuelve un resumen solo de conteos. |
| 4. Catálogo | `catalogo.py` | Las 28 variables con su rol y sus conjuntos; decide qué es predictor, qué es fuga y qué se descarta por faltantes. |
| 5. Pipeline | `preparacion.py` | `preparar(datos, conjunto)` separa el objetivo y arma el `ColumnTransformer` **sin ajustar** (la mediana y el escalado se aprenden dentro de cada pliegue). |
| 6. Validación | `validacion.py` | `particiones(datos)` reparte por **productor** (`GroupKFold`, semilla 42): un productor nunca está en entrenamiento y prueba a la vez. |
| 7. Línea base | `linea_base.py` | `predecir_media` + `evaluar` (MAE y RMSE en kg/ha): la barra que los modelos deben ganar. |

### Tabla de exclusiones (`limpieza.EXCLUSIONES`)

| Motivo | Condición |
|--------|-----------|
| Sin identificadores | Algún `campania_id`, `parcela_id` o `productor_id` vacío. |
| Superficie sin sentido | `superficie_sembrada_ha <= 0`. |
| Altitud fuera de rango | `altitud_msnm < 0` o `> 6000` m. |
| Sin objetivo | `rendimiento_kg_ha` vacío o `<= 0`. |

Solo eso. **Lo inusual no se excluye**: un rendimiento altísimo es un
dato, no un error. Si una fila incumple dos reglas, se lleva el motivo
de la primera de la tabla.

### Conjuntos de predictores

- **Conjunto 1 «Plan»**: todo lo que se conoce o se decide antes de
  cosechar (cultivo, variedad, superficie, altitud, suelo, pendiente,
  riego, semilla, fertilizante, jornales, agua).
- **Conjunto 2 «Plan + clima del ciclo»**: el plan más el clima del
  ciclo completo. **Advertencia**: al predecir de verdad ese clima no
  existe; sirve para comparar, no como predicción real (pendiente de la
  pregunta **U** de `decisiones_semana21.md`).
- **Nunca predictores**: identificadores, metadatos (`periodo`, año,
  `origen`), columnas de cobertura, seguimiento y **`dias_ciclo` (fuga:
  se calcula con la fecha de cosecha)**.

Supuestos del desarrollador (pendientes de confirmar): cobertura de
clima mínima **80 %** y faltantes máximos **40 %** por columna.

## 4. Los notebooks

En `notebooks/`, versionados **sin salidas**:

1. `01_exploracion.ipynb` — carga con `ml.carga`, faltantes, cobertura,
   catálogo y distribución del objetivo.
2. `02_preparacion.ipynb` — limpieza, Conjunto 1, pipeline, pliegues
   agrupados y línea base.

Los dos leen el CSV de `ML_EXPORT_DIR` (del `.env`), llevan la marca
de **datos de demostración** y **no entrenan modelos**. Para ejecutarlos
y ver resultados:

```powershell
cd backend
.\venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute `
    --output ..\notebooks\01_ejecutado.ipynb ..\notebooks\01_exploracion.ipynb
```

El archivo ejecutado queda **fuera del repositorio** (o se borra
después): en Git solo entra la versión limpia. Las carpetas
`.ipynb_checkpoints/` están en `.gitignore` (prueba 365).

## 5. Reproducibilidad y seguridad

- **Semilla 42** (`ml.exportacion.SEMILLA`): registrada en la ficha y
  usada por la validación; misma semana, mismos pliegues.
- La huella **SHA-256** de la ficha se calcula sobre los bytes exactos
  del CSV: sirve para comprobar que un archivo no cambió.
- El evento de auditoría **no contiene el dataset** (ni cultivos, ni
  valores, ni identificadores): solo filas, origen y huella.
- Sin permiso `ml.entrenar` no hay exportación; sin carpeta definida,
  tampoco.

## 6. Qué viene (Sprint 13)

Entrenar modelos sobre estos pliegues (árbol, Random Forest, …),
compararlos con la línea base en **cada** pliegue y discutir con el
responsable el error útil (pregunta **V** de
`docs/decisiones_semana21.md`). La API y la pantalla de predicción se
diseñan entonces, sobre este material.
