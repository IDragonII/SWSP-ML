# API de Machine Learning - Sprint 14 (Semana 22)

Referencia de los cuatro recursos añadidos en `backend/ml/` (decisión 235
de [`decisiones_semana22.md`](decisiones_semana22.md)): **predicciones**
de rendimiento (HU-173, HU-177), **modelos** entrenados con activación
(HU-172), **modelo activo** (banner de demostración, 239) y **campañas
predecibles** (selector de la pantalla Predicción). Todo va bajo
`/api/` (montado en `config/urls.py`); la autenticación es la de la
Semana 2 ([`api_autenticacion.md`](api_autenticacion.md)).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/ml/predicciones/` | Historial (paginado) | `ml.ver_predicciones` |
| POST | `/api/ml/predicciones/` | Predice y guarda (HU-173) | `ml.predecir` |
| GET | `/api/ml/predicciones/{id}/` | Ficha completa (HU-177) | `ml.ver_predicciones` |
| GET | `/api/ml/modelos/` | Modelos con métricas (HU-172) | `ml.ver_modelos` |
| POST | `/api/ml/modelos/{id}/activar/` | Activa (un solo activo; 222) | `ml.activar_modelo` |
| GET | `/api/ml/modelo-activo/` | Modelo vigente (banner; 239) | `ml.ver_modelos` |
| GET | `/api/ml/campanas-predecibles/` | Selector de campañas (227) | `ml.predecir` |

- **No existe escritura de predicciones**: `PUT`/`PATCH`/`DELETE` en
  detalle → `405` (232). Los campos que el servidor controla — `modelo`,
  `rendimiento_predicho`, `error_abs`, `error_pct` y `creado_por` — no se
  aceptan en el `POST`: si el cliente los envía, se ignoran y manda el
  servicio (prueba 381).
- La **lista** ordena por fecha descendente y la paginación es global
  (`API_PAGE_SIZE`, 20 por página).
- El modelo activo se carga en **cada predicción** verificando la huella
  del `.joblib` contra `ml_models/manifiesto.json` (226).

## Autenticación y permisos

Sin sesión → `401`; con sesión pero sin el permiso →
`403 {"detail": "No tienes permiso para realizar esta acción."}`
(`PermisosML`, un permiso por acción). Los permisos `ml.*` nacieron en
`usuarios.0002_datos_iniciales.py`:

| Rol | Sobre ML |
|---|---|
| Administrador | Todo: `ml.entrenar`, `ml.activar_modelo`, `ml.ver_modelos`, `ml.predecir`, `ml.ver_predicciones` |
| Técnico de campo | `ml.predecir` y `ml.ver_predicciones` → predice y consulta **solo en sus productores asignados**; `modelos/` y `modelo-activo/` → `403` (colección 214) |
| Coordinador | **Solo `ml.ver_predicciones`**: consulta el historial; predecir → `403` (211), modelos y campañas predecibles → `403` (214) |

**Ámbito del Técnico** (mismo `filtrar_asignados` que el resto de la
API): una campaña ajena o inexistente en el `POST` responde **el mismo
`404 {"detail": "No encontrado."}`** que un id inexistente (227), y una
predicción ajena en el detalle también es `404`. Además `creado_por` se
**omite** de lista y ficha para los roles con `limita_a_asignados` (233).

## Límite de predicciones (232)

`POST /api/ml/predicciones/` usa `ScopedRateThrottle` con el scope
`ml_prediccion`: **30 por hora y por usuario** (`.env`
`ML_PREDICCION_RATE`, por defecto `30/hour`). El listado, el detalle y
el resto de recursos no están limitados. Al agotarse el cupo:

```json
{
  "detail": "Demasiadas solicitudes. Intenta de nuevo en 3600 segundos.",
  "retry_after": 3600
}
```

con cabecera `Retry-After: 3600` (429).

## Predicciones

### Listado - `GET /api/ml/predicciones/`

Fila del historial (sin `variables_entrada`; llega en la ficha):

```json
{
  "id": 3,
  "fecha": "2026-10-20T00:50:46-05:00",
  "campania": {
    "id": 7,
    "periodo": "2026-2027",
    "estado": "EN_PRODUCCION",
    "cultivo": {"id": 1, "nombre": "Quinua"},
    "parcela": {
      "id": 4,
      "codigo": "P-004",
      "productor": {"id": 2, "nombre_completo": "Prueba, Uno"}
    }
  },
  "modelo": {"algoritmo": "REGRESION_LINEAL", "version": "1"},
  "dias_ciclo": 60,
  "rendimiento_predicho": "185.40",
  "produccion_estimada_kg": "278.10",
  "confiabilidad": "BAJA",
  "datos_demostracion": true,
  "rendimiento_real": "1620.00",
  "error_abs": "40.00",
  "error_pct": "2.47"
}
```

`rendimiento_real`, `error_abs` y `error_pct` llegan en `null` hasta que
`fn_produccion_post` (produccion.0003) completa el comparativo al
cosechar (236); deshacer la cosecha los vacía (prueba 378).

### Alta - `POST /api/ml/predicciones/`

Cuerpo: la campaña y, opcionalmente, los cuatro valores planificados de
la decisión 228 (≥ 0, hasta 2 decimales). Todo lo demás lo pone el
servidor.

```json
{
  "campania": 7,
  "semilla": 45,
  "fertilizante": 120,
  "mano_de_obra": 30,
  "agua": 200
}
```

Respuesta `201`: la ficha completa (igual que el detalle, con
`creado_por`). El estado de la campaña debe ser `PLANIFICADA` o
`EN_PRODUCCION` (227); en otro caso `400`:

```json
{"estado": "La campaña está CERRADA: solo se puede predecir con una campaña PLANIFICADA o EN_PRODUCCION."}
```

Sin modelo activo → `409 {"detail": "No hay ningún modelo activo: activa un modelo antes de predecir."}`; un valor planificado no válido →
`400 {"planificados": "…"}`.

### Detalle - `GET /api/ml/predicciones/{id}/`

Ficha completa (HU-177). A lo que ya trae la lista se añaden:

| Campo | Contenido |
|---|---|
| `intervalo_inferior`, `intervalo_superior` | Siempre `null`: el intervalo de estos modelos no es válido (230) |
| `confiabilidad` | `ALTA` o `BAJA` (BAJA con 2 o más de las 4 variables de manejo ausentes; 229) |
| `avisos` | Lista de textos: valor imputado con la mediana, categoría nunca vista, fuera del rango de entrenamiento, negativo ajustado a 0 (229-230) |
| `negativo_ajustado` | `true` si el valor bruto era negativo y se guardó en 0 |
| `datos_demostracion` | `true` si el modelo activo se entrenó con datos de demostración (231) |
| `texto_estimacion` | «Es una estimación basada en datos históricos, no una medición.» (fijo, 231) |
| `variables_entrada` | Copia de lo que se envió al modelo: `valores`, `origenes` (campaña/parcela/registrado/planificado/imputada/ausente), `planificados`, `avisos`, `confiabilidad`, `negativo_ajustado` (228-229) |
| `modelo` | `id`, `algoritmo`, `version`, `activo`, `mae` y `rmse` del modelo usado |
| `creado_por` | Username de quien predijo; **omitido** para el Técnico (233). La ficha nunca incluye DNI ni teléfono |

## Modelos

### Listado - `GET /api/ml/modelos/`

Solo `ml.ver_modelos` (Administrador). Fila:

```json
{
  "id": 1,
  "algoritmo": "REGRESION_LINEAL",
  "version": "1",
  "mae": "4.50",
  "rmse": "5.48",
  "r2": "0.9465",
  "activo": true,
  "archivo": "regresion_lineal_v1.joblib",
  "creado_en": "2026-10-20T00:45:00-05:00",
  "entrenamiento": {
    "id": 1,
    "fecha": "2026-10-20T00:45:00-05:00",
    "n_registros": 48,
    "origen_datos": "demostración",
    "semilla": 42
  },
  "datos_demostracion": true
}
```

La línea base no es una fila (224): sus métricas viven en
`hiperparametros` de cada modelo (no se exponen por la API).

### Activar - `POST /api/ml/modelos/{id}/activar/`

`ml.activar_modelo`; llama a `registro.activar_modelo` con los mismos
controles que el comando `registrar_modelo` (222): el archivo debe
existir y su huella coincidir con el manifiesto, y una predicción de
prueba debe funcionar **antes** de tocar la base. En una sola
transacción desactiva el anterior (eventos `DESACTIVAR`) y activa el
nuevo (`ACTIVAR`); un solo modelo puede quedar activo. Respuesta `200`
con la fila del modelo recién activado.

Errores: sin permiso → `403`; modelo sin archivo (los no elegidos por
el criterio) o con huella fallida → `400 {"detail": "…"}`; `GET` sobre
la acción → `405`.

## Modelo activo - `GET /api/ml/modelo-activo/`

La fila del modelo vigente (mismo formato del listado) para el banner
de demostración de las pantallas Predicción, Historial y Modelos (239).
Si no hay ninguno activo → `404 {"detail": "No hay ningún modelo activo."}`.

## Campañas predecibles - `GET /api/ml/campanas-predecibles/`

`ml.predecir` (el selector solo sirve para predecir): lista paginada de
campañas `PLANIFICADA` o `EN_PRODUCCION` (227), reducida a los
productores asignados del Técnico. Fila:

```json
{
  "id": 7,
  "periodo": "2026-2027",
  "estado": "EN_PRODUCCION",
  "fecha_inicio": "2026-08-20",
  "fecha_siembra": "2026-08-25",
  "superficie_sembrada_ha": "1.50",
  "cultivo": "Quinua",
  "variedad": "Blanca",
  "parcela": {
    "id": 4,
    "codigo": "P-004",
    "productor": {"id": 2, "nombre_completo": "Prueba, Uno"}
  }
}
```

## Códigos de estado

| Código | Cuándo |
|---|---|
| `200` | Listados, ficha, modelo activo y activación |
| `201` | Predicción guardada |
| `400` | Valor planificado inválido, campaña en estado no elegible, activar sin archivo o con huella fallida |
| `401` | Sin sesión |
| `403` | Permiso insuficiente (incluye el bloqueo por cambio obligatorio de contraseña, HU-112) |
| `404` | Id inexistente o fuera del ámbito del Técnico (el mismo «No encontrado.»); modelo activo inexistente |
| `405` | `PUT`/`PATCH`/`DELETE` en predicciones y `GET` en `activar/` |
| `409` | Sin modelo activo o el archivo del activo no pasa la huella |
| `429` | Límite de predicciones por hora (scope `ml_prediccion`) |

## Pruebas

`ml/tests.py`: `Bloque2dTests`, pruebas 381-387 (colección con permisos
y 405, ficha sin datos personales, ámbito del Técnico, permisos del
Coordinador, límite por hora, modelo activo y campañas predecibles, y
activar con los mismos controles). Servicio y registro: pruebas 369-380.
