# API de alertas — `/api/alertas/` (RF-63/RF-64/RF-65, HU-124..HU-132)

> Documentación de la Semana 15. Ver `decisiones_semana15.md` para las
> decisiones de diseño, `evaluacion_alertas.md` para cómo se generan y
> cierran las alertas y `verificacion_ui_semana15.md` para el checklist de
> navegador. **La API no escribe alertas**: las crea y cierra solo el
> sistema (servicio de evaluación); la única escritura de usuario es
> atender (y reabrir) una alerta existente.

## 1. Endpoints

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/alertas/` | `alertas.ver` | 200 paginado (20/página; `count`, `results`) |
| GET | `/api/alertas/{id}/` | `alertas.ver` | 200 (detalle) / 404 |
| POST | `/api/alertas/` | — | **405** (las crea solo el sistema) |
| PATCH | `/api/alertas/{id}/` | — | **405** |
| PUT | `/api/alertas/{id}/` | — | **405** |
| DELETE | `/api/alertas/{id}/` | — | **405** |
| GET | `/api/alertas/resumen/` | `alertas.ver` | 200 `{"pendientes": n}` (insignia del menú) |
| GET | `/api/alertas/productores-en-riesgo/` | `alertas.ver` | 200 `{"results": […]}` (sin paginar) |
| GET | `/api/alertas/evaluacion/` | `alertas.ver` | 200 estado del proceso diario (§5) |
| POST | `/api/alertas/evaluar/` | `parametros.gestionar` | 200 `{"creadas", "cerradas", "dry_run"}` / **429** cada 5 min |
| POST | `/api/alertas/{id}/atender/` | `alertas.atender` | 200 (detalle) / 400 si ya está atendida |
| POST | `/api/alertas/{id}/reabrir/` | `alertas.atender` | 200 (detalle) / 400 si no aplica |

- Sin sesión → **401** `{"detail": "Las credenciales de autenticación no se proveyeron."}`.
- Con sesión pero sin el permiso de la acción → **403**
  `{"detail": "No tienes permiso para realizar esta acción."}` (p. ej. el
  Coordinador, que tiene `alertas.ver` pero no `alertas.atender`, ni
  `parametros.gestionar`).
- **Ámbito del Técnico**: en todos los endpoints solo alcanza a sus
  productores asignados; una alerta ajena responde **404**
  `{"detail": "No encontrado."}` — **nunca 403** por ámbito (prueba 253).
- **Los filtros de estado son solo del listado**: detalle, atender y
  reabrir ven cualquier estado (decisión 15).

## 2. Filtros del listado (solo en `GET /api/alertas/`)

| Parámetro | Tipo | Notas |
|---|---|---|
| `?estado=` | `PENDIENTES` · `ATENDIDAS` · `TODAS` | Por defecto **`PENDIENTES`**; otro valor → **400** «Use PENDIENTES, ATENDIDAS o TODAS.» |
| `?tipo=` | uno de los 3 | `INCIDENCIA_SEVERA` · `SIN_ACTIVIDAD` · `RENDIMIENTO_BAJO`; otro → **400** «Use INCIDENCIA_SEVERA, SIN_ACTIVIDAD o RENDIMIENTO_BAJO.» |
| `?campania=` | id numérico | Si no es numérico → **400** «Debe ser un id numérico.» |
| `?productor=` | id numérico | Ídem |
| `?busqueda=` | texto | Busca en **mensaje**, código, apellidos y nombres del productor |
| `?page=` | número | 20 por página (`API_PAGE_SIZE`) |

Orden por defecto: `atendida, -creada_en, -id` — **pendientes primero** y,
dentro de cada grupo, las más recientes arriba.

## 3. Fila y detalle

**Fila** (`results` en la lista):

```json
{
  "id": 7,
  "tipo": "SIN_ACTIVIDAD",
  "mensaje": "La campaña 2025-2026 (Quinua) no registra actividades desde el 2025-11-30.",
  "creada_en": "2026-01-12T08:15:41-05:00",
  "atendida": false,
  "atendida_en": null,
  "productor": 17,
  "productor_codigo": "PROD-0017",
  "productor_nombre": "Alfa Uno",
  "campania": 3,
  "campania_periodo": "2025-2026",
  "incidencia": null
}
```

- `mensaje` **nunca contiene datos personales** (RF-63/RF-64): solo
  periodo/cultivo de la campaña, tipo de incidencia y fechas; la fecha que
  lleva es la de referencia **fija** con la que se creó.
- `incidencia` es el id de la incidencia severa **solo** en las alertas
  `INCIDENCIA_SEVERA`; `null` en el resto (CHECK `ck_alerta_incidencia`).

**Detalle** (`GET /api/alertas/{id}/`) — la fila más:

```json
{
  "nota_atencion": "Visitada y avisada a coordinación.",
  "atendida_por": 4,
  "atendida_por_nombre": "María Quispe"
}
```

- La lista **no** expone `nota_atencion` ni `atendida_por` (HU-128).
- `atendida_por_nombre` es **`null`** cuando (a) el rol del que pide la
  ficha tiene `limita_a_asignados` (el Técnico no ve quién atendió) o
  (b) el cierre fue **automático** (`atendida_por = null`); si quien
  atendió no tiene nombre completo se muestra su `username`.
- Con el cierre automático, la ficha muestra además la nota de la UI:
  «Se cerró automáticamente: volverá a abrirse si la condición vuelve a
  cumplirse.» (solo frontend).

## 4. Acciones de escritura

### `POST /api/alertas/{id}/atender/` (HU-125, RF-65)

Cuerpo: `{"nota": "…"}` — **opcional**, `≤ 250` caracteres (en blanco o
ausente = sin nota; demasiado larga → 400 «La nota no puede superar los
250 caracteres.»). Responde **200** con el detalle de la alerta ya
atendida: `atendida=true`, `atendida_por` de la sesión, `atendida_en` y
`nota_atencion`. Ya atendida → **400** `{"estado": "La alerta ya está
atendida."}`. Deja evento **MODIFICAR** en auditoría
(`detalle={"operacion": "atender", "nota": …}`).

### `POST /api/alertas/{id}/reabrir/` (HU-125, RF-65)

Sin cuerpo. Devuelve **200** con la alerta otra vez pendiente (limpia
`atendida`, `atendida_por`, `atendida_en` y `nota_atencion`) y registra
`{"operacion": "reabrir"}` en auditoría. Errores:

- No está atendida → **400** `{"estado": "La alerta no está atendida."}`.
- Está atendida **automáticamente** → **400** `{"estado": "La alerta se
  cerró automáticamente: se reabre sola si la condición vuelve a
  cumplirse."}`.

### `POST /api/alertas/evaluar/` (HU-131)

Solo `parametros.gestionar` (Administrador). Cuerpo: `{"dry_run": true|`
`false}` (por defecto `false`; si no es booleano → 400 `{"dry_run":
"Debe ser true o false."}`). Responde **200**:

```json
{ "creadas": 1, "cerradas": 0, "dry_run": false }
```

**Límite: una cada 5 minutos.** La segunda en la ventana responde
**429** con la ventana restante (construido a mano, como el del cambio de
contraseña):

```json
{ "detail": "Espera 5 minutos entre evaluaciones manuales.", "retry_after": 243 }
```

más la cabecera `Retry-After: 243` (hallazgo de F6: lanzando `Throttled`
con mensaje propio, el manejador global lo sobrescribía). Ver
`evaluacion_alertas.md`.

## 5. Los tres GET de apoyo

| Ruta | Respuesta |
|---|---|
| `/api/alertas/resumen/` | `{"pendientes": 12}` — solo **pendientes** y del ámbito: la insignia del menú (HU-127); el Técnico solo cuenta las suyas (prueba 257) |
| `/api/alertas/productores-en-riesgo/` | `{"results": [ … ]}` — una fila por productor con alertas **pendientes**, ordenado por **más pendientes** (HU-126) |
| `/api/alertas/evaluacion/` | `{"ultima_evaluacion": ISO \| null, "atrasada": true, "umbral_horas": 36}` — estado del proceso diario (HU-132): `atrasada` si la última evaluación tiene **más de 36 horas** o **nunca** se ha ejecutado |

Fila de **productores en riesgo**:

```json
{
  "productor": 17,
  "productor_codigo": "PROD-0017",
  "productor_nombre": "Alfa Uno",
  "distrito": "Urbambamba",
  "provincia": "La Convención",
  "pendientes": 3,
  "tipos": ["INCIDENCIA_SEVERA", "SIN_ACTIVIDAD"],
  "ultima_alerta": "La campaña 2025-2026 (Quinua) no registra actividades desde el 2025-11-30.",
  "ultima_alerta_en": "2026-01-12T08:15:41-05:00"
}
```

- `tipos` son los tipos pendientes de ese productor (sin duplicados,
  ordenados alfabéticamente); `ultima_alerta` es el **mensaje** de su
  alerta más reciente (puede ser `null` junto con `ultima_alerta_en`).
- «Alerta activa» del RF-64 = **pendiente** (`atendida=false`).
- El Técnico solo recibe la fila de sus productores (prueba 256).

## 6. Permisos y privacidad por rol

| Qué | Administrador | Coordinador | Técnico |
|---|---|---|---|
| Consultar alertas, resumen, riesgo y evaluación (`alertas.ver`) | ✅ | ✅ | ✅ (sus productores) |
| Atender / reabrir (`alertas.atender`) | ✅ | ❌ 403 | ✅ (sus productores) |
| Evaluar ahora (`parametros.gestionar`) | ✅ | ❌ 403 | ❌ 403 |
| Ver quién atendió (`atendida_por_nombre`) | ✅ | ✅ | ❌ (`null`) |

`alertas.ver` y `alertas.atender` se sembraron en la Semana 2 (TECNICO los
tiene, COORD solo `ver`).

## 7. Errores (catálogo)

| Código | Cuerpo | Cuándo |
|---|---|---|
| 400 | `{"estado": "…"}`, `{"tipo": "…"}`, `{"campania": …}`, `{"dry_run": …}` | Valor de filtro/acción inválido (cadena, no lista) |
| 401 | `{"detail": "Las credenciales de autenticación no se proveyeron."}` | Sin sesión |
| 403 | `{"detail": "No tienes permiso para realizar esta acción."}` | Sin el permiso de la acción |
| 404 | `{"detail": "No encontrado."}` | Id inexistente **o alerta fuera del ámbito del Técnico** |
| 405 | `{"detail": "Método no permitido."}` | POST/PATCH/PUT/DELETE sobre las alertas |
| 429 | `{"detail": "Espera 5 minutos entre evaluaciones manuales.", "retry_after": N}` + `Retry-After` | Segunda evaluación manual en la ventana |

## Colección de pruebas (Postman)

`docs/coleccion_api_semana15.json` — **F7 cerrada: 488/488 en verde**
(486 obligatorias + 2 opcionales, 904/904 aserciones): parte de la de la
Semana 14 (**458**) y añade **30 peticiones nuevas (459–488)** = **488**
en total: listado con pestañas y filtros,
detalle con y sin privacidad, 404 de ámbito, 405 de escritura, 403 de
Coordinador (atender/evaluar), atender con y sin nota, 400 ya atendida,
reabrir (manual y 400 de automática), resumen, productores en riesgo,
estado de evaluación, evaluar (200 + 429) y los flujos de generación con
la evaluación. Validada en servidor temporal **8001** con BD
`sigpa_ga_coleccion15` y `LOGIN_RATE_IP=120/min`, borrada al terminar.
Dos matices aprendidos en la validación: la respuesta del alta de
incidencia trae `campania` anidada (`d.campania.id`), y la alerta fuera
del ámbito del Técnico se crea sobre `campania_s10_id` (la campaña de la
Semana 8 queda CERRADA al final de la S14 y no admite incidencias).
