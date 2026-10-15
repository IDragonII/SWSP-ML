# API de clima - Semana 10 (7-13 dic)

Referencia de los recursos añadidos en la Semana 10 desde
`backend/seguimiento/`: **el registro meteorológico diario por parcela**
(HU-76 a HU-83) y la **consulta a la API meteorológica Open-Meteo** (HU-84).
Además, el detalle de campañas gana `resumen_clima` (HU-82), el de parcelas
gana `clima` (HU-83) y `/api/parametros/` gana la clave `umbral_helada_c`.
Todo va bajo `/api/` (montado en `config/urls.py`; router `seguimiento/urls.py`).
La autenticación (cookies httpOnly o `Authorization: Bearer`) es la de la
Semana 2 y se describe en [`api_autenticacion.md`](api_autenticacion.md); las
decisiones de la semana, en
[`decisiones_semana10.md`](decisiones_semana10.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/clima/` | Lista (paginado, con filtros; HU-76) | `clima.ver` |
| POST | `/api/clima/` | Crea un registro manual (HU-78) | `clima.crear` |
| GET | `/api/clima/{id}/` | Detalle / ficha (HU-77) | `clima.ver` |
| PUT/PATCH | `/api/clima/{id}/` | Edita (recomendado PATCH; HU-79/80) | `clima.editar` |
| POST | `/api/clima/consulta-api/` | Consulta Open-Meteo y guarda el rango (HU-84) | `clima.crear` |

- **No existe `DELETE` de clima** → `405`: la tabla no tiene anulación ni
  borrado, solo edición (decisión 1 de `decisiones_semana10.md`).
- **Una fila por parcela y día** (`uq_clima_parcela_fecha`): el duplicado se
  responde con `400` en español **antes** de que choque la base; si la carrera
  llega a la restricción, la vista la traduce al mismo `400` (nunca 500).
- `fuente`, `registrado_por`, `temp_prom` calculado, `helada` derivada,
  `creado_en` y `actualizado_en` son **de solo lectura**: el cliente no puede
  forzarlos (ver «Lo que calcula el servidor»).
- La lista ordena por **fecha descendente**; la paginación es global
  (`API_PAGE_SIZE`, 20 por página).
- El **throttle `clima_consulta` (10/hora por usuario)** aplica **solo** a
  `POST /api/clima/consulta-api/`; el resto de acciones no consume cuota.

## Autenticación y permisos

Sin sesión → `401`; con sesión pero sin el permiso de la acción →
`403 {"detail": "No tienes permiso para realizar esta acción."}` (clase
`PermisosClima`, un permiso por acción). El permiso se comprueba **antes** que
el ámbito y que `get_object`: con un id inexistente responde `403`, no `404`.

| Rol | Sobre clima |
|---|---|
| Administrador | Todo: `clima.ver/crear/editar` (y `clima.desactivar`, sembrado **sin uso** porque no hay anulación) |
| Técnico de campo | `clima.ver/crear/editar` → lista, crea, edita y consulta **en sus productores asignados**; parcela ajena al crear → `400 {"parcela": ["La parcela indicada no existe."]}` y en la consulta-API también `400` (colecciones de la semana) |
| Coordinador | **Solo `clima.ver`**: crear, editar y `consulta-api/` → `403` |

**Ámbito del Técnico** (mismo `SoloSusProductores` que las semanas
anteriores, sobre `parcela__productor_id`): el queryset del listado se reduce
a sus productores con asignación activa y una parcela ajena responde **el
mismo mensaje que si no existiera** (403 > 404). Además, `registrado_por` se
**omite de las respuestas** para los roles con `limita_a_asignados`.

## Registros de clima

### Parámetros de consulta (`GET /api/clima/`)

| Parámetro | Valores | Efecto |
|---|---|---|
| `parcela`, `productor`, `comunidad`, `distrito`, `provincia` | id numérico | Filtran por el id (jerarquía de la parcela). No numérico → `400 {"…": "Debe ser un id numérico."}` |
| `fecha_desde`, `fecha_hasta` | `AAAA-MM-DD` | Rango de fechas (≥ / ≤) |
| `fuente` | `MANUAL`, `API` | Filtra por la fuente. Otro valor → `400 {"fuente": "Use MANUAL o API."}` |
| `heladas` | `1`, `0` | Con helada / sin helada (`1`, `true`, `si`, `sí` / `0`, `false`, `no`). Otro valor → `400 {"heladas": "Use 1 o 0."}` |
| `busqueda` | texto | Coincidencia parcial en código de parcela, apellidos/nombres del productor y nombre de comunidad |
| `page` | número | Paginación (20 por página) |

### Listado - `GET /api/clima/`

Fila (HU-76):

```json
{
  "id": 3,
  "fecha": "2026-10-10",
  "parcela": {
    "id": 1,
    "codigo": "P-001",
    "comunidad": {"id": 1, "nombre": "San Juan"},
    "productor": {"id": 1, "nombre_completo": "Quispe Ana"}
  },
  "temp_min": "5.0",
  "temp_max": "15.0",
  "temp_prom": "10.0",
  "precipitacion_mm": "3.5",
  "helada": false,
  "fuente": "MANUAL"
}
```

### Detalle - `GET /api/clima/{id}/`

Los campos del listado más: `temp_prom_calculado` (boolean: el guardado es el
punto medio de mínima y máxima), `humedad_pct`, `viento_ms`, `radiacion_mj`,
`helada_calculada` (boolean: hay mínima, así que la helada la derivó el
servidor), `registrado_por` (**nombre de usuario**; omitido para roles con
`limita_a_asignados`), `creado_en` y `actualizado_en`.

### Alta - `POST /api/clima/`

Campos de escritura: `parcela`, `fecha` y, al menos, **una medida o la
`helada`**: `temp_min`, `temp_max`, `temp_prom`, `precipitacion_mm`,
`humedad_pct`, `viento_ms`, `radiacion_mj` (todos opcionales y de 1 decimal)
y `helada` (booleano, por defecto `false`). Responde `201` con la ficha de
lectura (la fuente siempre `MANUAL`).

```json
{
  "parcela": 1,
  "fecha": "2026-10-10",
  "temp_min": "5.0",
  "temp_max": "15.0",
  "precipitacion_mm": "3.5"
}
```

**Lo que calcula el servidor al guardar:**

- `temp_prom`: si envías mínima y máxima sin promedio, guarda el **punto
  medio** (`(5.0 + 15.0) / 2 = 10.0`, `ROUND_HALF_UP` a 1 decimal) y la
  ficha lo marca `temp_prom_calculado: true`.
- `helada`: si hay `temp_min`, la deriva del umbral del sistema
  (`umbral_helada_c`, hoy `0 °C`: `temp_min ≤ umbral` → helada) y la ficha
  la marca `helada_calculada: true`; **sin mínima**, manda la casilla que
  envíe el cliente.

**Validaciones (cuerpos exactos):**

| Caso | Respuesta |
|---|---|
| Sin medida ni helada | `400 {"helada": ["Indica al menos una medida meteorológica o marca la helada."]}` |
| Mínima > máxima | `400 {"temp_min": ["La temperatura mínima no puede ser mayor que la máxima."]}` |
| Promedio fuera del rango mín–máx | `400 {"temp_prom": ["La temperatura promedio debe estar entre la mínima y la máxima."]}` |
| Temperatura fuera de [−30, 45] | `400 {"temp_min": ["La temperatura mínima debe estar entre -30 y 45 °C."]}` (idem `temp_max`, `temp_prom`) |
| Precipitación/viento/radiación negativos | `400 {"precipitacion_mm": ["La precipitación no puede ser negativa."]}` (idem `viento_ms`, `radiacion_mj`) |
| Humedad fuera de [0, 100] | `400 {"humedad_pct": ["La humedad debe estar entre 0 y 100 %."]}` |
| Fecha anterior a 2000 | `400 {"fecha": ["La fecha no puede ser anterior al 1 de enero de 2000."]}` |
| Fecha futura (hora de Lima) | `400 {"fecha": ["La fecha no puede ser futura."]}` |
| Parcela inactiva | `400 {"parcela": ["La parcela indicada no existe o está inactiva."]}` |
| Parcela ajena al Técnico | `400 {"parcela": ["La parcela indicada no existe."]}` |
| Duplicado (parcela + fecha) | `400 {"fecha": ["Ya existe un registro de clima para esta parcela en la fecha 2026-10-10."]}` |
| Demasiados decimales | `400 {"temp_min": ["La temperatura mínima admite como máximo 1 decimal."]}` (mismo patrón en todos los campos) |

### Edición - `PUT/PATCH /api/clima/{id}/`

Mismos campos y validaciones que el alta (recomendado `PATCH`, campos
parciales). Al editar:

- **Registro `MANUAL`**: cualquier cambio permitido; la fuente sigue
  `MANUAL`. (La API admite cambiar `parcela`; la UI la bloquea en el
  formulario para que nadie «mueva» un día de sitio sin darse cuenta.)
- **Registro `API`**: exige **`confirmar_reemplazo: true`** en el cuerpo; si
  falta →
  `400 {"confirmar_reemplazo": ["Este registro proviene de la API meteorológica: envía confirmar_reemplazo=true para reemplazarlo con valores manuales."]}`.
  Con confirmación, el registro **pasa a `MANUAL`** (la siguiente consulta de
  la API lo volverá a refrescar como `API` si hay dato nuevo).
- El `temp_prom` y la `helada` se recalculan con las mismas reglas del alta
  (si mueves temperaturas sin enviar promedio, se valida y guarda el nuevo
  punto medio).

### Sin `DELETE` - `DELETE /api/clima/{id}/`

`405` (el router no monta la acción). En la UI no hay botón de borrar.

## Consulta a la API meteorológica (HU-84) - `POST /api/clima/consulta-api/`

Baja las lecturas diarias de **Open-Meteo** (`archive-api.open-meteo.com`,
sin clave de API) para un rango de una parcela **con coordenadas** y las
guarda con `fuente = API`.

**Entrada:**

```json
{
  "parcela": 1,
  "fecha_desde": "2026-10-05",
  "fecha_hasta": "2026-10-12"
}
```

| Regla | Respuesta si falla |
|---|---|
| Rango de **92 días** como máximo (`(hasta - desde).days + 1 ≤ 92`) | `400 {"fecha_hasta": ["La consulta admite como máximo 92 días."]}` |
| `fecha_desde ≤ fecha_hasta` | `400 {"fecha_desde": ["La fecha inicial no puede ser posterior a la final."]}` |
| Sin fechas futuras (hora de Lima) ni anteriores a 2000 | `400 {"fecha_hasta": ["La fecha final no puede ser futura."]}` / `400 {"fecha_desde": ["La fecha no puede ser anterior al 1 de enero de 2000."]}` |
| Parcela con `latitud` y `longitud` | `400 {"parcela": ["La parcela no tiene coordenadas registradas."]}` |
| Parcela activa y del ámbito (mismos mensajes que el alta) | `400` como arriba |
| **10 consultas/hora por usuario** (`clima_consulta`) | `429` con `Retry-After` (mismo manejador que el rate limit de la Semana 2) |
| Open-Meteo sin respuesta, timeout (15 s) o JSON ilegible | **`502 {"detail": "El servicio meteorológico no está disponible en este momento."}`** (el detalle técnico nunca se expone) |

**Salida (`200`)** — informe con los 6 contadores más la consulta efectuada:

```json
{
  "consulta": {
    "parcela": 1,
    "fecha_desde": "2026-10-05",
    "fecha_hasta": "2026-10-12",
    "latitud": -13.52,
    "longitud": -71.95
  },
  "creados": 7,
  "actualizados": 0,
  "omitidos_manual": 1,
  "omitidos_api": 0,
  "sin_datos": 0,
  "descartados": 0
}
```

| Contador | Cuándo cuenta |
|---|---|
| `creados` | Día con datos que no tenía fila → alta nueva `API` |
| `actualizados` | Día con datos que ya tenía fila `API` → se refresca |
| `omitidos_manual` | Ya existía una fila **manual**: la mano del técnico **nunca se pisa** |
| `omitidos_api` | El servicio no trajo el día y ya había fila `API` → se conserva tal cual |
| `sin_datos` | El servicio no trajo el día y no había fila |
| `descartados` | El día llegó pero sus medidas no pasan las reglas del alta manual |

- Se cumple siempre
  `creados + actualizados + omitidos_manual + omitidos_api + sin_datos + descartados = días del rango`.
- **Todo el rango se guarda en una sola transacción** (`select_for_update` por
  día): si dos consultas simultáneas chocan con el índice único, se revierte
  entero y responde
  `400 "No se pudieron guardar los datos consultados: uno de los días ya tiene un registro para esta parcela."`.
- Coordenadas redondeadas a **2 decimales**; el adaptador cuantiza cada
  medida a **1 decimal** antes de validar (decisión 11 de la Semana 10).
- Las pruebas ejercitan el adaptador **simulado** (sin internet); el smoke de
  la semana verificó el camino real con coordenadas públicas.

## Cambios en campañas, parcelas y parámetros

### `resumen_clima` en `GET /api/campanias/{id}/` (HU-82)

Agregados del clima de la parcela **dentro de la ventana** de la campaña
(desde `fecha_inicio` o la primera actividad, hasta `fecha_cosecha` o hoy si
aún no cosecha — `provisional: true`):

```json
{
  "desde": "2025-09-01",
  "hasta": "2026-10-14",
  "provisional": true,
  "precipitacion_acum_mm": "4.4",
  "temp_prom_c": "14.2",
  "humedad_prom_pct": "53.3",
  "n_heladas": 0,
  "dias_con_clima": 8,
  "dias_ventana": 409,
  "cobertura_pct": "2.0"
}
```

Sin registros, `dias_con_clima = 0` y los acumulados en `null`.

### `clima` en `GET /api/parcelas/{id}/` (HU-83)

```json
"clima": {"registros": 8, "ultimo_dia": "2026-10-12"}
```

`ultimo_dia` es la fecha del registro más reciente (`null` si no hay).

### `umbral_helada_c` en `/api/parametros/` (HU-83, pregunta K)

Quinta clave del sistema (selección/edición igual que las de la Semana 8:
`GET /api/parametros/`, `GET|PATCH /api/parametros/{clave}/`; sin `POST` ni
`DELETE` → 405). **Única clave que admite negativos**, con rango **−10 a 5 °C**:

- No numérico → `400 {"valor": ["El umbral de helada debe ser un número entre -10 y 5 °C."}]`
- Fuera de rango → `400 {"valor": ["El umbral de helada debe estar entre -10 y 5 °C."}]`
- Cambiarlo **no recalcula** los registros ya guardados (la helada derivada
  se fija en cada guardado).

## Errores (formato general)

Heredado de las semanas previas: un error de **campo** de serializador es una
**lista** `{"campo": ["msg"]}`; un error de **vista/acción/filtro** es un
**string** `{"clave": "msg"}`; `404` → `{"detail": "No encontrado."}`; `403`
con el `detail` del manejador; `405` con el `detail` de DRF. Los mensajes
exactos de clima están tabulados arriba.

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (cookies httpOnly)
$base = "http://127.0.0.1:8000"
$login = Invoke-WebRequest -Uri "$base/api/auth/login/" -Method Post `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"SigpaGA2026!"}' -SessionVariable s

# 2. Alta manual (temp_prom y helada los calcula el servidor)
$alta = Invoke-RestMethod -Uri "$base/api/clima/" -Method Post -WebSession $s `
  -ContentType "application/json" `
  -Body '{"parcela":1,"fecha":"2026-10-10","temp_min":"5.0","temp_max":"15.0","precipitacion_mm":"3.5"}'
$alta.temp_prom   # "10.0"  (punto medio)
$alta.fuente      # "MANUAL"

# 3. DELETE → 405 (no existe)
try { Invoke-WebRequest -Uri "$base/api/clima/$($alta.id)/" -Method Delete -WebSession $s }
catch { [int]$_.Exception.Response.StatusCode }   # 405

# 4. Consulta a Open-Meteo (HU-84)
$consulta = Invoke-RestMethod -Uri "$base/api/clima/consulta-api/" -Method Post `
  -WebSession $s -ContentType "application/json" `
  -Body '{"parcela":1,"fecha_desde":"2026-10-05","fecha_hasta":"2026-10-12"}'
$consulta.creados           # días creados
$consulta.omitidos_manual   # días manuales que la API no pisa

# 5. Editar un registro API: primero 400, con confirmación pasa a MANUAL
try {
  Invoke-RestMethod -Uri "$base/api/clima/{id}/" -Method Patch -WebSession $s `
    -ContentType "application/json" -Body '{"temp_min":"4.0"}'
} catch { $_.ErrorDetails.Message }   # confirma con confirmar_reemplazo=true
Invoke-RestMethod -Uri "$base/api/clima/{id}/" -Method Patch -WebSession $s `
  -ContentType "application/json" `
  -Body '{"temp_min":"4.0","confirmar_reemplazo":true}'
```

## Colección de pruebas (Postman)

`docs/coleccion_api_semana10.json` — **validada en la fase F7: 270/270
peticiones en verde (269/269 obligatorias + 1 opcional) y 496/496
aserciones** contra el servidor, en la BD temporal `sigpa_ga_coleccion10`
(borrada al terminar). Son las **235** peticiones de la Semana 9 más **34**
nuevas numeradas 236–269 — 22 de registros de clima (alta con punto medio
y helada derivada, mensajes de validación, duplicado, `DELETE` → 405,
filtros y ámbitos), 5 de `consulta-api/` (401 sin sesión, 403 del
Coordinador, rango > 92 días, fecha futura y parcela sin coordenadas), 4 de
campañas (`resumen_clima`), 1 de parcelas (bloque `clima`) y 2 de
parámetros (`umbral_helada_c`) — más 1 petición **opcional** (270: el
informe real a Open-Meteo, la única que necesita red). Sufijo `SEMANA10`;
la ejecución se apoya en una siembra previa (parcela sin coordenadas y
registro de la API) y está pensada para **una ejecución por base de
datos**.
