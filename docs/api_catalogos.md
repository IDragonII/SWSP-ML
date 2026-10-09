# API de catálogos — Semana 5 (2–8 nov)

Referencia de los 8 recursos añadidos en la Semana 5 desde `backend/catalogos/`:
**cultivos, variedades, etapas fenológicas, unidades, tipos de actividad,
recursos, tipos de incidencia y agentes**. Todo va bajo `/api/` (montado en
`config/urls.py`). La autenticación (cookies httpOnly o `Authorization: Bearer`)
es la de la Semana 2 y se describe en [`api_autenticacion.md`](api_autenticacion.md);
las decisiones de la semana, en [`decisiones_semana5.md`](decisiones_semana5.md);
la comparación con el diseño SQL, en [`comparacion_semana5.md`](comparacion_semana5.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/{recurso}/` | Lista (paginado) | `catalogos.ver` |
| POST | `/api/{recurso}/` | Crea | `catalogos.crear` |
| GET | `/api/{recurso}/{id}/` | Detalle | `catalogos.ver` |
| PUT/PATCH | `/api/{recurso}/{id}/` | Edita (recomendado PATCH) | `catalogos.editar` |
| PATCH | `/api/{recurso}/{id}/estado/` | `{"activo": true\|false}` | `catalogos.desactivar` |
| POST | `/api/etapas-fenologicas/reordenar/` | Reordena las etapas de un cultivo | `catalogos.editar` |

`{recurso}` es **`cultivos`, `variedades`, `etapas-fenologicas`, `unidades`,
`tipos-actividad`, `recursos`, `tipos-incidencia` o `agentes`**, con dos salvedades:

- **No existe `DELETE` en ningún recurso** → `405`. Nada se borra: se desactiva
  (decisión 3). Las rutas de detalle siempre llevan barra final (`/{id}/`).
- **`tipos-actividad` no admite `POST`** (ni `DELETE`) → `405`: los códigos son
  fijos (los 7 sembrados). Solo lectura y edición de `nombre`/`activo`.
- **`etapas-fenologicas` no tiene `…/estado/`** (ni campo `activo`): se ocultan
  desactivando su cultivo.

## Autenticación y permisos

Misma que las semanas anteriores: sin sesión → `401`; con sesión pero sin el
permiso de la acción → `403` (clase `PermisosCatalogo` con
`permiso_requerido` por acción). La paginación es global (`API_PAGE_SIZE`,
20 por página).

| Rol | Sobre estos recursos |
|---|---|
| Administrador | Los 4 permisos: `catalogos.ver/crear/editar/desactivar` |
| Técnico de campo | **Solo `catalogos.ver`** → `POST`/`PATCH` → `403` |
| Coordinador | **Solo `catalogos.ver`** → `POST`/`PATCH` → `403` (colección 093) |

En la interfaz, el menú y la ruta `/catalogos` exigen además `catalogos.editar`:
**solo el Administrador ve y entra en la pantalla** (los otros roles, al no tener
el permiso, ni siquiera la ven en el menú).

## Parámetros de consulta

| Parámetro | Rutas | Valores | Efecto |
|---|---|---|---|
| `activo` | todos **menos etapas** | `true` / `false` (admite `1`, `yes`, `si`, `sí`, `verdadero`, `0`, `no`, `falso`) | Filtra; **sin parámetro muestra todos** (para poder reactivar). Otro valor → `400 {"activo": "Use true o false."}` |
| — | **solo etapas** | cualquier `activo` | `400 {"activo": "Las etapas no tienen estado."}` |
| `busqueda` | todos | texto | Coincidencia parcial en `nombre` (en tipos de actividad también en `codigo`) |
| `desplegable` | todos | `1` / `true` / … | Lista corta **sin paginar** y **solo activos**, con pocos campos (ver abajo) |
| `cultivo` | variedades, etapas | id numérico | Filtra por cultivo. No numérico → `400 {"cultivo": "Debe ser un id numérico."}` |
| `tipo` | unidades, agentes | código | Filtra por tipo |
| `categoria` | recursos, tipos de incidencia | código | Filtra por categoría |

Un valor fuera de una lista cerrada en el **filtro** (p. ej.
`?categoria=NOPE`) **no da error**: devuelve lista vacía con `200`.

**Formato paginado** (idéntico al resto de la API):

```json
{ "count": 1, "next": null, "previous": null, "results": [ … ] }
```

**Formato desplegable** (`?desplegable=1`): lista plana **sin `count`** ni
paginación, solo filas activas (y, en variedades/etapas, de **cultivo activo**):

```json
[ { "id": 4, "nombre": "Quinua" } ]
```

Los desplegables de variedades y etapas añaden `"cultivo": <id>`; el de unidades
incluye además `"simbolo"` y `"tipo"`.

## Cultivos

- **Lectura:** `id`, `nombre` (60), `descripcion` (texto, `null` opcional) y `activo`.
- **Escritura:** `nombre`, `descripcion`, `activo` (solo estos).

**Validaciones (400):**

| Situación | Mensaje exacto |
|---|---|
| `nombre` vacío o ausente | `Este campo es obligatorio.` / `Este campo no puede quedar vacío.` |
| Nombre repetido (normalizado: mayúsculas y espacios dobles no duplican) | `Ya existe un cultivo con ese nombre.` |
| `estado` con otro valor que no sea booleano | `Debe ser true o false.` |

```json
// POST /api/cultivos/  → 201
{ "nombre": "Maíz", "descripcion": "Variedad dulce", "activo": true }

// PATCH /api/cultivos/4/estado/  → 200
{ "activo": false }
```

## Variedades

- **Lectura:** `id`, `cultivo` **anidado** `{id, nombre}`, `nombre` (80),
  `descripcion`, `activo`.
- **Escritura:** `cultivo` (**id**), `nombre`, `descripcion`, `activo`.

| Situación | Mensaje exacto |
|---|---|
| Sin `cultivo` | `Este campo es obligatorio.` |
| Cultivo inexistente | `El registro indicado no existe.` |
| Cultivo **inactivo** | `El cultivo indicado no existe o está inactivo.` |
| Nombre repetido **para ese cultivo** (normalizado) | `Ya existe una variedad con ese nombre para ese cultivo.` |

## Etapas fenológicas

- **Lectura:** `id`, `cultivo` **anidado** `{id, nombre}`, `nombre` (60), `orden`.
  **No lleva `activo`.**
- **Escritura:** `cultivo` (id), `nombre`, `orden` (1–1000).

| Situación | Mensaje exacto |
|---|---|
| `orden` fuera de 1–1000 | `El orden debe ser un número entre 1 y 1000.` |
| Nombre repetido para ese cultivo | `Ya existe una etapa con ese nombre para ese cultivo.` |
| Orden repetido para ese cultivo | `Ya existe otra etapa con el orden 1 para ese cultivo.` |
| Cultivo inactivo | `El cultivo indicado no existe o está inactivo.` |
| `?activo=…` | `Las etapas no tienen estado.` |

### Reordenar — `POST /api/etapas-fenologicas/reordenar/`

Reordena **todas** las etapas de un cultivo de forma atómica (exige
`catalogos.editar`):

```json
{ "cultivo": 4, "orden": [13, 14, 15] }
```

- **200** → la lista de etapas del cultivo ya reordenada (posiciones 1, 2, 3…).
- Internamente primero todas pasan a `orden + 10000` y después recibe cada una
  su posición (dentro de una transacción), así `uq_etapa_orden` no choca nunca.

| Situación | Mensaje exacto |
|---|---|
| `orden` ausente, vacío o no lista | `Debe ser la lista completa de ids de etapas.` |
| Algún id no numérico | `Cada id debe ser un número.` |
| Ids repetidos | `No puede repetir etapas.` |
| Lista ≠ etapas exactas del cultivo | `Debe incluir exactamente las etapas del cultivo.` |
| Cultivo inexistente | `El cultivo indicado no existe.` |
| `cultivo` no numérico | `Debe ser un id numérico.` |

## Unidades

- **Lectura:** `id`, `nombre` (40), `simbolo` (10), `tipo`, `factor_a_base`,
  `es_base`, `activo`.
- **Escritura:** `nombre`, `simbolo`, `tipo`, `factor_a_base`, `es_base`, `activo`.
- `tipo` ∈ `MASA`, `SUPERFICIE`, `VOLUMEN`, `LABOR`, `TIEMPO`.

| Situación | Mensaje exacto |
|---|---|
| Nombre repetido | `Ya existe una unidad con ese nombre.` |
| `factor_a_base ≤ 0` | `El factor debe ser mayor que 0.` |
| Crear con `es_base: true` | `No se pueden crear unidades base: cada tipo ya tiene la suya.` |
| Convertir una existente en base | `No se puede convertir una unidad existente en base.` |
| Base con `factor ≠ 1` | `La unidad base debe tener factor 1.` |
| Dos bases del mismo tipo | `Ya existe una unidad base para ese tipo.` |
| Desactivar una base (por `activo` o por `…/estado/`) | `Las unidades base no se pueden desactivar.` |

## Tipos de actividad

- **Lectura:** `id`, `codigo` (fijo), `nombre`, `activo`.
- **Escritura (solo PATCH/PUT):** `nombre`, `activo`. **El `codigo` no se envía.**
- `POST` y `DELETE` → `405`.

| Código fijo | Nombre |
|---|---|
| `PREPARACION` | Preparación del terreno |
| `SIEMBRA` | Siembra |
| `FERTILIZACION` | Fertilización |
| `FITOSANITARIO` | Control fitosanitario |
| `RIEGO` | Riego |
| `DESHIERBO` | Deshierbo |
| `COSECHA` | Cosecha |

| Situación | Mensaje exacto |
|---|---|
| Desactivar `SIEMBRA` o `COSECHA` | `Siembra y Cosecha no se pueden desactivar.` |

## Recursos

- **Lectura:** `id`, `nombre` (80), `categoria`, `tipo_unidad`, `activo`.
- **Escritura:** los mismos sin `id`.
- `categoria` ∈ `SEMILLA`, `FERTILIZANTE`, `ABONO`, `FITOSANITARIO`, `AGUA`,
  `MAQUINARIA`, `MANO_OBRA`, `COMBUSTIBLE`.
- `tipo_unidad` ∈ `MASA`, `VOLUMEN`, `LABOR`, `TIEMPO`.

| Situación | Mensaje exacto |
|---|---|
| Nombre repetido | `Ya existe un recurso con ese nombre.` |
| Opción fuera de lista | `«NOPE» no es una opción válida.` |

## Tipos de incidencia

- **Lectura:** `id`, `nombre` (60), `categoria`, `activo`.
- `categoria` ∈ `CLIMATICA`, `BIOLOGICA`, `OTRA`.

| Situación | Mensaje exacto |
|---|---|
| Nombre repetido | `Ya existe un tipo de incidencia con ese nombre.` |

## Agentes

- **Lectura:** `id`, `nombre` (100), `tipo`, `activo`.
- `tipo` ∈ `PLAGA`, `ENFERMEDAD`.

| Situación | Mensaje exacto |
|---|---|
| Nombre repetido | `Ya existe un agente con ese nombre.` |

## Errores (cuerpos verificados)

| Código | Cuerpo | Cuándo |
|---|---|---|
| 401 | `{"detail": "Las credenciales de autenticación no se proveyeron."}` | Sin sesión |
| 403 | `{"detail": "No tienes permiso para realizar esta acción."}` | Permiso faltante |
| 400 | `{"<campo>": ["mensaje…"]}` o `{"non_field_errors": […]}` | Validaciones (tablas anteriores) |
| 404 | `{"detail": "No encontrado."}` | Id inexistente (manejador propio de la Semana 4) |
| 405 | `{"detail": "Método \"DELETE\" no permitido."}` | Cualquier `DELETE` o `POST` sobre tipos de actividad |
| 429 | `{"detail": "…", "retry_after": N}` | Rate limit global (Semana 2) |

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (sin espacios dentro del JSON)
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/

# 2. Cultivo y variedad (la lectura anida el cultivo)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"nombre":"Maiz criollo","activo":true}' http://localhost:8000/api/cultivos/
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"cultivo":4,"nombre":"Amarillo","activo":true}' http://localhost:8000/api/variedades/

# 3. Etapas y reordenado atómico
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"cultivo":4,"nombre":"Siembra","orden":1}' http://localhost:8000/api/etapas-fenologicas/
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"cultivo":4,"orden":[1,2,3]}' http://localhost:8000/api/etapas-fenologicas/reordenar/

# 4. Desplegables y filtros
curl.exe -s -b cookies.txt "http://localhost:8000/api/unidades/?desplegable=1"
curl.exe -s -b cookies.txt "http://localhost:8000/api/cultivos/?activo=true&busqueda=quin"
curl.exe -s -b cookies.txt "http://localhost:8000/api/variedades/?cultivo=4"
```

## Colección de pruebas (Postman)

[`coleccion_api_semana5.json`](coleccion_api_semana5.json) — **93 peticiones**
con pruebas `pm.test` embebidas (estado + textos clave), en un solo nivel y
numeradas de 001 a 093:

1. **001–048 · Semana 4** (copiadas tal cual de `coleccion_api_semana4.json`):
   sesión, ubicaciones, productores, parcelas y asignaciones; terminan con la
   sesión del Técnico.
2. **049–093 · Catálogos**: cierra la sesión del técnico (049), comprueba el
   `401` sin sesión (050), entra como administrador y recorre los 8 catálogos:
   cultivos (alta, edición, duplicado, desactivación y `?activo=`), variedades
   (cultivo anidado y unicidad por cultivo), etapas (orden, reordenado atómico
   y rechazo de `?activo=`), unidades (reglas de la base y desplegable),
   tipos de actividad (`405` en POST, Siembra protegida), recursos, tipos de
   incidencia y agentes; cierra con el Coordinador (`200` en lectura, `403`
   al crear).

Variables: `base_url`; las claves (`clave_admin`, `clave_coordinador`,
`clave_tecnico`) se definen en Postman y **salen de `.credenciales`** (ignorado
por Git; la colección no contiene secretos). Si repites la ejecución sobre una
BD ya usada, cambia `sufijo` (por defecto `SEMANA5`) y `dni_productor`. La
colección fue **validada contra el servidor: 93/93 peticiones con el código y
los textos esperados.**
