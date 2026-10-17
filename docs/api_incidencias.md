# API de incidencias - Semana 11 (14-20 dic)

Referencia de los recursos añadidos en la Semana 11 desde
`backend/seguimiento/`: el **CRUD de incidencias de la campaña** (HU-85 a
HU-90), su **anulación lógica** (HU-88) y los agregados que enganchan en
otras fichas: `resumen_incidencias` en campañas (HU-89), `incidencias`
agrupado por campaña en parcelas (HU-89) e `incidencias_activas` /
`ultima_incidencia` en el productor (HU-89). El catálogo de tipos de
incidencia y de agentes vive en [`api_catalogos.md`](api_catalogos.md)
(`/api/tipos-incidencia/`, `/api/agentes/`). Todo va bajo `/api/`
(montado en `config/urls.py`; router `seguimiento/urls.py`). La
autenticación (cookies httpOnly o `Authorization: Bearer`) es la de la
Semana 2 y se describe en [`api_autenticacion.md`](api_autenticacion.md);
las decisiones de la semana, en
[`decisiones_semana11.md`](decisiones_semana11.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/incidencias/` | Lista (paginado, con filtros y búsqueda; HU-85) | `incidencias.ver` |
| POST | `/api/incidencias/` | Crea una incidencia (HU-85/86) | `incidencias.crear` |
| GET | `/api/incidencias/{id}/` | Detalle / ficha (HU-85) | `incidencias.ver` |
| PUT/PATCH | `/api/incidencias/{id}/` | Edita (recomendado PATCH; HU-85/86) | `incidencias.editar` |
| POST | `/api/incidencias/{id}/anular/` | Anula con motivo (HU-88) | `incidencias.desactivar` |
| POST | `/api/incidencias/{id}/reactivar/` | Reactiva una anulada (HU-88) | `incidencias.desactivar` |

- **No existe `DELETE` de incidencias** → `405`: nada se borra; lo que deja
  de contar se **anula con motivo** (decisión 1 de
  `decisiones_semana11.md`).
- `anulada`, `motivo_anulacion`, `registrado_por`, `creado_en` y
  `actualizado_en` son **de solo lectura**: no están en el serializador de
  escritura, así que el cliente **no puede forzarlos** (se ignoran si los
  envía). La anulación pasa por la acción `anular/`.
- La lista ordena por **fecha descendente** (y `id`); la paginación es
  global (`API_PAGE_SIZE`, 20 por página).
- **Una campaña puede tener varias incidencias el mismo día y del mismo
  tipo**: no hay restricción de unicidad (a diferencia del clima).

## Autenticación y permisos

Sin sesión → `401`; con sesión pero sin el permiso de la acción →
`403 {"detail": "No tienes permiso para realizar esta acción."}` (clase
`PermisosIncidencia`, un permiso por acción). El permiso se comprueba
**antes** que el ámbito y que `get_object`.

| Rol | Sobre incidencias |
|---|---|
| Administrador | Todo: `incidencias.ver/crear/editar/desactivar` (único que anula y reactiva) |
| Técnico de campo | `incidencias.ver/crear/editar` → lista, crea y edita **en sus productores asignados**; anular/reactivar → `403` |
| Coordinador | **Solo `incidencias.ver`**: crear, editar y anular/reactivar → `403` |

**Ámbito del Técnico** (mismo `SoloSusProductores` de las semanas
previas, sobre `campania__parcela__productor_id`): el queryset del listado
se reduce a sus productores con asignación activa y un objeto ajeno
responde **404** (detalle y edición), nunca 403. Al crear, una campaña
ajena responde `400 {"campania": ["La campaña indicada no existe."]}` (403
> 404: mismo mensaje que si no existiera). Los filtros **no abren la
puerta**: `?campania=` ajena devuelve `count: 0`. Además, `registrado_por`
se **omite de las respuestas** para los roles con `limita_a_asignados`
(el Coordinador sí lo ve).

## Registros de incidencias

### Parámetros de consulta (`GET /api/incidencias/`)

| Parámetro | Valores | Efecto |
|---|---|---|
| `busqueda` | texto | Coincidencia parcial en código de parcela, apellidos/nombres del productor, descripción y nombre del agente |
| `estado` | `ACTIVA`, `ANULADA` | Filtra por el estado de anulación. Otro valor → `400 {"estado": "Use ACTIVA o ANULADA."}` |
| `campania` | id numérico | Incidencias de esa campaña. No numérico → `400 {"campania": "Debe ser un id numérico."}` |
| `tipo` | id numérico | Tipo de incidencia (mismo 400 con la clave `tipo`) |
| `categoria` | `CLIMATICA`, `BIOLOGICA`, `OTRA` | Categoría del tipo. Otro valor → `400 {"categoria": "Use CLIMATICA, BIOLOGICA u OTRA."}` |
| `severidad` | `BAJA`, `MEDIA`, `ALTA` | Otro valor → `400 {"severidad": "Use BAJA, MEDIA o ALTA."}` |
| `agente` | id numérico | Agente causante (mismo 400 con la clave `agente`) |
| `fecha_desde`, `fecha_hasta` | `AAAA-MM-DD` | Rango de fechas (≥ / ≤) |
| `productor`, `parcela`, `cultivo`, `distrito` | id numérico | Filtran por la jerarquía de la parcela de la campaña (mismo 400 con la clave del filtro) |
| `page` | número | Paginación (20 por página) |

### Listado - `GET /api/incidencias/`

Fila (HU-85):

```json
{
  "id": 12,
  "fecha": "2025-10-10",
  "tipo_incidencia": {"id": 2, "nombre": "Helada", "categoria": "CLIMATICA"},
  "severidad": "ALTA",
  "agente": null,
  "superficie_afectada_ha": "3.50",
  "campania": {
    "id": 4,
    "periodo": "2025-2026",
    "estado": "EN_PRODUCCION",
    "fecha_siembra": "2025-09-01",
    "cultivo": {"id": 1, "nombre": "Papa"},
    "parcela": {
      "id": 1,
      "codigo": "P-001",
      "productor": {"id": 1, "nombre_completo": "Quispe, Ana"}
    }
  },
  "anulada": false
}
```

- `tipo_incidencia.categoria` permite decidir en cliente si se muestra el
  campo de agente (solo `BIOLOGICA`).
- `agente` es `null` o `{id, nombre, tipo}`.
- `superficie_afectada_ha` llega como **cadena** de 2 decimales (`"3.50"`)
  o `null` (es un campo del modelo); en los **agregados** (`resumen` e
  historial) los decimales crudos salen como **número**.

### Detalle - `GET /api/incidencias/{id}/`

Los campos del listado más: `descripcion`, `producto_aplicado`,
`motivo_anulacion` (texto del «por qué» si está anulada, `null` si no),
`registrado_por` (**nombre de usuario**; omitido para roles con
`limita_a_asignados`), `creado_en` y `actualizado_en`. `anulada`,
`motivo_anulacion` y las fechas de trazabilidad son **solo lectura**.

### Alta - `POST /api/incidencias/`

Campos de escritura: `campania`, `tipo_incidencia`, `fecha`, `severidad`
(`BAJA`/`MEDIA`/`ALTA`) y `descripcion` (obligatorios);
`superficie_afectada_ha` (opcional, ≥ 0, ≤ sembrada), `agente` (opcional,
solo tipos biológicos) y `producto_aplicado` (opcional, ≤ 100). Responde
`201` con la ficha de lectura (`anulada: false`, `registrado_por` = quien
crea).

```json
{
  "campania": 4,
  "tipo_incidencia": 2,
  "fecha": "2025-10-10",
  "severidad": "ALTA",
  "descripcion": "Helada de madrugada con helada negativa",
  "superficie_afectada_ha": "3.50"
}
```

**Validaciones (cuerpos exactos):**

| Caso | Respuesta |
|---|---|
| Sin campaña | `400 {"campania": ["La campaña es obligatoria."]}` |
| Campaña inexistente | `400 {"campania": ["La campaña indicada no existe."]}` |
| Campaña ajena al Técnico | `400 {"campania": ["La campaña indicada no existe."]}` |
| Campaña CERRADA/CANCELADA | `400 {"campania": ["La campaña está CERRADA y no admite nuevos registros."]}` |
| Tipo inexistente / sin tipo | `400 {"tipo_incidencia": ["El tipo de incidencia indicado no existe."]}` / `["El tipo de incidencia es obligatorio."]` |
| Tipo inactivo | `400 {"tipo_incidencia": ["El tipo de incidencia indicado no existe o está inactivo."]}` |
| Sin fecha / formato inválido | `400 {"fecha": ["La fecha es obligatoria."]}` / `["La fecha no es válida: usa el formato AAAA-MM-DD."]` |
| Fecha futura (hora de Lima) | `400 {"fecha": ["La fecha no puede ser futura."]}` |
| Fecha fuera del período | `400 {"fecha": ["La fecha 2025-11-30 está fuera del período de la campaña (2025-09-01 a 2025-12-15)."]}` |
| Sin severidad / valor distinto | `400 {"severidad": ["La severidad es obligatoria."]}` / `["La severidad solo puede ser BAJA, MEDIA o ALTA."]` |
| Sin descripción | `400 {"descripcion": ["La descripción es obligatoria."]}` |
| Superficie negativa | `400 {"superficie_afectada_ha": ["La superficie afectada no puede ser negativa."]}` |
| Superficie > sembrada | `400 {"superficie_afectada_ha": ["La superficie afectada (3.50 ha) supera la sembrada (2.00 ha)."]}` |
| Superficie con más de 2 decimales / dígitos | `400 {"superficie_afectada_ha": ["La superficie afectada admite como máximo 2 decimales."]}` / `["La superficie admite como máximo 6 dígitos enteros y 2 decimales."]` |
| Agente inexistente / inactivo | `400 {"agente": ["El agente indicado no existe."]}` / `["El agente indicado no existe o está inactivo."]` |
| Agente en tipo no biológico | `400 {"agente": ["El agente solo puede indicarse en incidencias de tipo biológico (plaga o enfermedad)."]}` |
| Producto con más de 100 caracteres | `400 {"producto_aplicado": ["El producto aplicado admite como máximo 100 caracteres."]}` |
| Carrera con la base (`IntegrityError`) | **400** `"No se pudo guardar la incidencia: los datos chocan con una restricción de la base de datos."` (mensaje único, en lugar de un 500) |

Las mismas reglas están **duplicadas en la base** (`trg_incidencias_fecha`
y `trg_incidencias_superficie` con `fn_validar_incidencia`): si alguien
inserta con SQL crudo, PostgreSQL responde con los mensajes literales del
diseño («La superficie afectada (% ha) supera la sembrada (% ha).» / «Solo
las incidencias de tipo biológico (plaga, enfermedad) pueden indicar un
agente.» / «La campaña está % y no admite nuevos registros.» / «La fecha %
está fuera del período de la campaña (% a %).»).

### Edición - `PUT/PATCH /api/incidencias/{id}/`

Mismos campos y validaciones que el alta (recomendado `PATCH`, campos
parciales). Además:

- **La campaña no cambia al editar**: `400 {"campania": ["La campaña de
  una incidencia no se puede cambiar: anula y registra otra incidencia."]}`.
- **Los registros anulados no se editan desde la UI** (el botón no aparece);
  la API no lo prohíbe, la reactivación es el camino.
- `anulada`/`motivo_anulacion`/`registrado_por` siguen siendo de solo
  lectura.

### Sin `DELETE` - `DELETE /api/incidencias/{id}/`

`405` con sesión (`401` sin ella) y la fila **no se toca**. En la UI no
hay botón de borrar.

## Anulación lógica (HU-88)

### `POST /api/incidencias/{id}/anular/`

```json
{"motivo": "Se atendió el parte técnico"}
```

| Caso | Respuesta |
|---|---|
| Sin `motivo` o en blanco (se recorta) | `400 {"motivo": "El motivo de anulación es obligatorio."}` |
| Ya estaba anulada | `400 {"estado": "La incidencia ya está anulada."}` |
| Campaña CERRADA/CANCELADA | `400 {"estado": "La campaña está CERRADA y no admite nuevos registros."}` |
| Sin `incidencias.desactivar` (Técnico/Coordinador) | `403` (el permiso se niega **antes** de mirar el objeto) |
| Sin sesión | `401` |

Con `200`, la ficha completa con `anulada: true` y
`motivo_anulacion: "…"` (además fija `actualizado_en` por trigger). El
CHECK `ck_incidencia_anulacion` de la base garantiza que **anulada ⇒
motivo** también con SQL crudo.

### `POST /api/incidencias/{id}/reactivar/`

Sin cuerpo. La incidencia vuelve `anulada: false` y
`motivo_anulacion: null`.

| Caso | Respuesta |
|---|---|
| No estaba anulada | `400 {"estado": "La incidencia no está anulada."}` |
| Campaña CERRADA/CANCELADA | `400 {"estado": "La campaña está CERRADA y no admite nuevos registros."}` |
| Fecha ya fuera del período de la campaña | `400 {"fecha": "La fecha 2025-10-10 está fuera del período de la campaña (2025-10-01 a 2025-10-05)."}` |
| Sin `incidencias.desactivar` | `403` |

## Catálogos para el formulario (HU-85/86)

- `GET /api/tipos-incidencia/` — lista normal con `id, nombre, categoria,
  activo` (la **categoría** decide si aparece el campo de agente);
  `?desplegable=1` → lista corta sin paginar y solo `id, nombre` (solo
  activos).
- `GET /api/agentes/` — lista normal con `id, nombre, tipo, activo`;
  `?desplegable=1` → `id, nombre`.
- `GET /api/campanias/?desplegable=1` — selector de campaña del alta/filtros
  (ámbito del Técnico incluido). **No trae `superficie_sembrada_ha`**: la
  validación «superficie afectada ≤ sembrada» es **solo del servidor**.

## Cambios en campañas, parcelas y productores

### `resumen_incidencias` en `GET /api/campanias/{id}/` (HU-89)

```json
{
  "total": 3,
  "por_severidad": {"baja": 1, "media": 1, "alta": 1},
  "severidad_maxima": "ALTA",
  "ultima_fecha": "2025-10-15",
  "mayor_superficie_ha": 3.5
}
```

- Solo cuentan las **activas** (`anulada = false`); `severidad_maxima` es
  un orden (`ALTA > MEDIA > BAJA`), no un promedio, y se devuelve como
  texto.
- **Sin incidencias: bloque con ceros** (`total: 0`,
  `por_severidad` en 0, `severidad_maxima`/`ultima_fecha`/
  `mayor_superficie_ha` en `null`), nunca un error.
- `mayor_superficie_ha` sale como **número** (o `null`); los mismos
  números que `n_incidencias`/`severidad_max` de `inc_c` en
  `vw_dataset_entrenamiento` (HU-91).

### `incidencias` en `GET /api/parcelas/{id}/` (HU-89)

Historial **agrupado por campaña**, más reciente primero (el grupo lleva
`campania` con `id`, `periodo`, `cultivo` y `estado`; cada elemento, `id`,
`fecha`, `tipo` con categoría, `severidad`, `agente`,
`superficie_afectada_ha`, `descripcion` y `anulada`):

```json
[
  {
    "campania": {"id": 4, "periodo": "2025-2026", "cultivo": {"id": 1, "nombre": "Papa"}, "estado": "EN_PRODUCCION"},
    "incidencias": [
      {
        "id": 12,
        "fecha": "2025-10-10",
        "tipo": {"id": 2, "nombre": "Helada", "categoria": "CLIMATICA"},
        "severidad": "ALTA",
        "agente": null,
        "superficie_afectada_ha": 3.5,
        "descripcion": "Helada de madrugada",
        "anulada": false
      }
    ]
  }
]
```

- **Las anuladas se ocultan** por defecto; se piden con
  `GET /api/parcelas/{id}/?incluir_anuladas=1` (solo en la ficha de
  parcela; el listado general usa `?estado=`).
- El enlace «Ver todas» de la ficha de campaña lleva a
  `/api/incidencias/?campania={id}` (la pantalla `/incidencias` filtra con
  ese parámetro).

### `incidencias_activas` y `ultima_incidencia` en `GET /api/productores/{id}/`

Dentro del bloque `resumen` del productor:

```json
"resumen": {
  "parcelas_activas": 2,
  "superficie_total_ha": 5.25,
  "campanias_activas": 1,
  "incidencias_activas": 3,
  "ultima_incidencia": "2025-10-15"
}
```

Cuenta las incidencias **activas** de todas sus parcelas (cualquier
campaña); `ultima_incidencia` es la fecha más reciente (`null` si no hay).
El detalle está en la ficha de cada parcela.

## Errores (formato general)

Heredado de las semanas previas: un error de **campo** de serializador es
una **lista** `{"campo": ["msg"]}`; un error de **vista/acción/filtro**
es un **string** `{"clave": "msg"}`; `404` → `{"detail": "No encontrado."}`;
`403` con el `detail` del manejador; `405` con el `detail` de DRF. Los
mensajes exactos de incidencias están tabulados arriba (los dos únicos
errores sin clave son el `IntegrityError` y los mensajes de los triggers,
que solo se ven con SQL crudo).

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (cookies httpOnly)
$base = "http://127.0.0.1:8000"
$login = Invoke-WebRequest -Uri "$base/api/auth/login/" -Method Post `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"SigpaGA2026!"}' -SessionVariable s

# 2. Alta
$inc = Invoke-RestMethod -Uri "$base/api/incidencias/" -Method Post -WebSession $s `
  -ContentType "application/json" `
  -Body '{"campania":4,"tipo_incidencia":2,"fecha":"2025-10-10","severidad":"ALTA","descripcion":"Helada","superficie_afectada_ha":"3.50"}'
$inc.anulada          # False (registrado_por = admin…)

# 3. Superficie > sembrada → 400 en español
try {
  Invoke-RestMethod -Uri "$base/api/incidencias/" -Method Post -WebSession $s `
    -ContentType "application/json" `
    -Body '{"campania":4,"tipo_incidencia":2,"fecha":"2025-10-10","severidad":"ALTA","descripcion":"x","superficie_afectada_ha":"999"}'
} catch { $_.ErrorDetails.Message }   # "…supera la sembrada…"

# 4. Anular: primero 400 por el motivo, luego 200
try {
  Invoke-RestMethod -Uri "$base/api/incidencias/$($inc.id)/anular/" -Method Post -WebSession $s `
    -ContentType "application/json" -Body '{}'
} catch { $_.ErrorDetails.Message }   # El motivo de anulación es obligatorio.
$anulada = Invoke-RestMethod -Uri "$base/api/incidencias/$($inc.id)/anular/" -Method Post `
  -WebSession $s -ContentType "application/json" -Body '{"motivo":"duplicado"}'
$anulada.anulada      # True

# 5. Fuera del dataset: el listado con ?estado= y el resumen sin ella
$activas = Invoke-RestMethod -Uri "$base/api/incidencias/?estado=ACTIVA" -WebSession $s
$resumen = Invoke-RestMethod -Uri "$base/api/campanias/4/" -WebSession $s
$resumen.resumen_incidencias.total

# 6. Reactivar y DELETE → 405
Invoke-RestMethod -Uri "$base/api/incidencias/$($inc.id)/reactivar/" -Method Post -WebSession $s
try { Invoke-WebRequest -Uri "$base/api/incidencias/$($inc.id)/" -Method Delete -WebSession $s }
catch { [int]$_.Exception.Response.StatusCode }   # 405
```

## Colección de pruebas (Postman)

`docs/coleccion_api_semana11.json` — **validada en la fase F7 contra el
servidor: 311/311 peticiones con código y aserciones en verde
(574/574 aserciones)**. Son las 270 de la Semana 10 (269 obligatorias + 1
opcional) más las 41 nuevas de incidencias (numeradas **271–311**: CRUD,
validaciones, anular/reactivar, permisos y ámbitos, los doce filtros,
`resumen_incidencias`, historial de parcela y contadores del productor).
Se ejecutó con el pipeline habitual (BD temporal propia
`sigpa_ga_coleccion11`, borrada al terminar, servidor temporal en el
puerto 8001): una ejecución por base de datos, sin secretos (las claves
salen de `.credenciales`), y la petición 270 (informe real a Open-Meteo)
es la única opcional.
