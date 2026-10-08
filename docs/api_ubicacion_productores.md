# API de ubicación y productores — Semana 3 (19–25 oct)

Referencia de los 4 recursos añadidos en la Semana 3 desde `backend/productores/`:
**provincias, distritos, comunidades y productores**. Todo va bajo `/api/`
(montado en `config/urls.py`). La autenticación (cookies httpOnly o
`Authorization: Bearer`) es la de la Semana 2 y se describe en
[`api_autenticacion.md`](api_autenticacion.md); las decisiones de la semana, en
[`decisiones_semana3.md`](decisiones_semana3.md); la comparación con el diseño
SQL, en [`comparacion_semana3.md`](comparacion_semana3.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/ubicaciones/provincias/` | Lista provincias (paginado) | `catalogos.ver` |
| POST | `/api/ubicaciones/provincias/` | Crea una provincia | `catalogos.crear` |
| GET | `/api/ubicaciones/provincias/{id}/` | Detalle | `catalogos.ver` |
| PUT/PATCH | `/api/ubicaciones/provincias/{id}/` | Edita (recomendado PATCH) | `catalogos.editar` |
| PATCH | `/api/ubicaciones/provincias/{id}/estado/` | `{"activo": true\|false}` | `catalogos.desactivar` |
| GET | `/api/ubicaciones/distritos/` | Lista (`?provincia=`) | `catalogos.ver` |
| POST | `/api/ubicaciones/distritos/` | Crea (`nombre` + `provincia` id) | `catalogos.crear` |
| PUT/PATCH | `/api/ubicaciones/distritos/{id}/` | Edita | `catalogos.editar` |
| PATCH | `/api/ubicaciones/distritos/{id}/estado/` | Activa/desactiva | `catalogos.desactivar` |
| GET | `/api/ubicaciones/comunidades/` | Lista (`?distrito=`) | `catalogos.ver` |
| POST | `/api/ubicaciones/comunidades/` | Crea (`nombre` + `distrito` id) | `catalogos.crear` |
| PUT/PATCH | `/api/ubicaciones/comunidades/{id}/` | Edita | `catalogos.editar` |
| PATCH | `/api/ubicaciones/comunidades/{id}/estado/` | Activa/desactiva | `catalogos.desactivar` |
| GET | `/api/productores/` | Listado paginado + búsqueda y filtros | `productores.ver` |
| POST | `/api/productores/` | Alta (el código lo genera la BD) | `productores.crear` |
| GET | `/api/productores/{id}/` | Ficha | `productores.ver` |
| PUT/PATCH | `/api/productores/{id}/` | Edita la ficha | `productores.editar` |
| PATCH | `/api/productores/{id}/estado/` | `{"estado": "ACTIVO"\|"INACTIVO"}` | `productores.desactivar` |

**No existe `DELETE` en ningún recurso** → `405`. Nada se borra: se desactiva
(decisión 6). Las rutas de detalle siempre llevan barra final (`/{id}/`).

## Autenticación y permisos

Misma que la Semana 2: sin sesión → `401`; con sesión pero sin el permiso de la
acción → `403` (clase `TienePermiso`, `permiso_requerido` por acción en
`views.py`). La paginación es global (`API_PAGE_SIZE`, 20 por página).

| Rol | Sobre estos recursos |
|---|---|
| Administrador | Las 4 acciones (55 permisos) |
| Técnico de campo | Ver, crear y editar productores; **no** desactivar (32 permisos). Desde la **Semana 4 (F5)** solo ve y edita **sus** productores (los demás responden 404) |
| Coordinador | Solo lectura (14 permisos): `*.ver`; `POST`/`PATCH` → `403` |

## Parámetros de consulta

**Ubicaciones** (provincias, distritos, comunidades):

| Parámetro | Valores | Efecto |
|---|---|---|
| `activo` | `true` / `false` (admite `1`, `si`, `sí`, `0`, `no`…) | Filtra; **sin parámetro muestra todas** (para poder reactivar). Otro valor → `400 {"activo": "Use true o false."}` |
| `busqueda` | texto | Coincidencia parcial en `nombre` |
| `provincia` | id numérico | Solo en distritos |
| `distrito` | id numérico | Solo en comunidades |

**Productores:**

| Parámetro | Valores | Efecto |
|---|---|---|
| `busqueda` | texto | Coincidencia parcial en `codigo`, `nombres`, `apellidos` o `dni` |
| `comunidad` / `distrito` / `provincia` | id numérico | Filtra por la jerarquía del productor |
| `estado` | `ACTIVO` / `INACTIVO` | Otro valor → `400 {"estado": "Use ACTIVO o INACTIVO."}` |

Un id no numérico responde `400 {"<campo>": "Debe ser un id numérico."}`.

**Formato paginado** (idéntico al resto de la API):

```json
{ "count": 1, "next": null, "previous": null, "results": [ … ] }
```

El listado de productores va **ordenado por apellidos** (y luego por nombres).

## Ubicaciones: lectura y escritura

La lectura **anida el nivel superior** (jerarquía completa, para el desplegable
en cascada); la escritura recibe el **id del padre**. `POST` y `PUT/PATCH`
responden con la lectura (incluye `id`).

```json
// POST /api/ubicaciones/distritos/  → 201
{ "nombre": "San Román", "provincia": 1, "activo": true }

// GET /api/ubicaciones/comunidades/3/  → 200
{ "id": 3, "nombre": "Asentamiento 12 de Octubre", "activo": true,
  "distrito": { "id": 2, "nombre": "Juliaca", "activo": true,
                "provincia": { "id": 1, "nombre": "San Román", "activo": true } } }
```

Unicidad por diseño: `uq_distrito (provincia, nombre)` y
`uq_comunidad (distrito, nombre)` → repetir el nombre **en el mismo nivel**
responde `400` con `non_field_errors` (en otra provincia/distrito sí cabe).

## Productores

### Alta — `POST /api/productores/`

```json
{ "nombres": "María Elena", "apellidos": "Colque Quispe", "dni": "77889900",
  "telefono": "987654321", "comunidad": 3, "referencia_ubicacion": "a 2 km de…",
  "fecha_incorporacion": "2026-10-19" }
```

- **201** → ficha completa con `codigo` (trigger `PROD-000N`) y
  `creado_por` = usuario autenticado (**no se puede forzar** en el cuerpo).
- Solo estos campos son de escritura: `nombres`, `apellidos`, `dni`,
  `telefono`, `comunidad`, `referencia_ubicacion`, `fecha_incorporacion`
  (este último con `hoy` por defecto). `codigo`, `estado`, `creado_por`,
  `creado_en` y `actualizado_en` son de solo lectura.

**Validaciones (400):**

| Campo | Mensaje exacto |
|---|---|
| `nombres`, `apellidos`, `dni` | `Este campo es obligatorio.` |
| `dni` con menos/más dígitos o letras | `El DNI debe tener exactamente 8 dígitos numéricos.` |
| `dni` repetido | `Ya existe un productor con ese DNI.` |
| `comunidad` vacía | `La comunidad es obligatoria.` |
| `comunidad` inexistente | `La comunidad indicada no existe.` |
| `comunidad` desactivada | `La comunidad indicada no existe o está inactiva.` |

### Listado y ficha

- **`GET /api/productores/`** → por fila: `id`, `codigo`, `nombre_completo`
  (`"Apellidos, Nombres"`), `comunidad`/`distrito`/`provincia` como
  `{id, nombre}`, `estado` y `dni`.
- **`GET /api/productores/{id}/`** → todos los campos de la ficha:
  `nombres`, `apellidos`, `dni`, `telefono`, `comunidad` (**como id**),
  `referencia_ubicacion`, `fecha_incorporacion`, `estado`, `creado_por`
  (username), `creado_en`, `actualizado_en`. Parcelas y campañas se sumarán
  en la Semana 4 (HU-22 parcial).

### Edición y estado

- **`PATCH /api/productores/{id}/`** → solo los campos enviados. El
  `codigo` se ignora (prueba 22 y petición 029 de la colección);
  `actualizado_en` lo rellena el trigger (`now()`), `creado_en` no cambia.
- **`PATCH /api/productores/{id}/estado/`** con `{"estado": "INACTIVO"}` o
  `{"estado": "ACTIVO"}` → desactiva/reactiva **sin tocar ningún otro dato**
  (otros valores → `400 {"estado": "Use ACTIVO o INACTIVO."}`).

### DNI y teléfono según el rol (decisión 4, pendiente de confirmación)

En **listado y ficha**, los roles no autorizados ven `****` + fin del valor:

| Rol | `dni` | `telefono` |
|---|---|---|
| Administrador, Técnico de campo | `77889900` | `987654321` |
| Coordinador | `****9900` | `****321` |

La lista de roles con datos completos es la constante
`ROLES_CON_DATOS_COMPLETOS` en `productores/serializers.py`.

## Errores (cuerpos verificados)

| Código | Cuerpo | Cuándo |
|---|---|---|
| 401 | `{"detail": "Las credenciales de autenticación no se proveyeron."}` | Sin sesión |
| 403 | `{"detail": "No tienes permiso para realizar esta acción."}` | Permiso faltante |
| 400 | `{"<campo>": ["mensaje…"]}` o `{"non_field_errors": […]}` | Validaciones (tabla anterior) |
| 404 | `{"detail": "No encontrado."}` | Id inexistente o recurso fuera del ámbito del técnico *(decisión 11 de la Semana 4: handler propio; antes devolvía el mensaje por defecto de DRF en inglés)* |
| 405 | `{"detail": "Método \"DELETE\" no permitido."}` | Cualquier `DELETE` |
| 429 | `{"detail": "…", "retry_after": N}` | Rate limit global (Semana 2) |

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (sin espacios dentro del JSON)
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/

# 2. Ubicación en cascada
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"nombre":"San Roman","activo":true}' http://localhost:8000/api/ubicaciones/provincias/
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"nombre":"Distrito Norte","provincia":1}' http://localhost:8000/api/ubicaciones/distritos/
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"nombre":"Comunidad Ejemplo","distrito":1}' http://localhost:8000/api/ubicaciones/comunidades/

# 3. Alta de productor (el código sale solo)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"nombres":"Ana","apellidos":"Zambrano","dni":"11111111","comunidad":1}' `
  http://localhost:8000/api/productores/

# 4. Búsqueda y filtros
curl.exe -s -b cookies.txt "http://localhost:8000/api/productores/?busqueda=PROD-0001"
curl.exe -s -b cookies.txt "http://localhost:8000/api/productores/?comunidad=1&estado=ACTIVO"
```

## Colección de pruebas (Postman)

[`coleccion_api_semana3.json`](coleccion_api_semana3.json) — 36 peticiones en
4 carpetas con pruebas `pm.test` embebidas (estado + textos clave):

1. **Sesión:** 401 sin token, login de administrador y `/me`.
2. **Ubicaciones:** CRUD sin `DELETE`, desactivar/reactivar, unicidad,
   filtros inválidos y desplegables.
3. **Productores:** alta con código `PROD-NNNN`, validaciones de DNI y
   comunidad, búsqueda, filtros, edición, estado y `DELETE` → 405.
4. **Coordinador:** sesión, listado enmascarado (`****`) y `403` al crear/editar.

Variables: `base_url`; las claves (`clave_admin`, `clave_coordinador`) se
definen en Postman y **salen de `.credenciales`** (ignorado por Git; la
colección no contiene secretos). Si repites la ejecución, cambia `sufijo` y
`dni_productor`. La colección fue **validada contra el servidor: 36/36
peticiones con el código y los textos esperados.**

## Cobertura de HU-15 a HU-22

El mapeo completo (con evidencias) está en [`tablero.md`](tablero.md); los
textos originales de los HU no están en este repositorio, así que ese mapeo es
el propuesto, igual que en la Semana 2.
