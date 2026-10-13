# API de actividades - Semana 7 (16-22 nov)

Referencia del recurso añadido en la Semana 7 desde `backend/seguimiento/`:
**la actividad productiva (siembra, preparación, riego…) como registro
diario de una campaña**. Todo va bajo `/api/` (montado en `config/urls.py`).
La autenticación (cookies httpOnly o `Authorization: Bearer`) es la de la
Semana 2 y se describe en [`api_autenticacion.md`](api_autenticacion.md); las
decisiones de la semana, en [`decisiones_semana7.md`](decisiones_semana7.md);
la comparación con el diseño SQL, en [`comparacion_semana7.md`](comparacion_semana7.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/actividades/` | Lista (paginado, con filtros) | `actividades.ver` |
| POST | `/api/actividades/` | Crea (alta, HU-48) | `actividades.crear` |
| GET | `/api/actividades/{id}/` | Detalle (HU-49) | `actividades.ver` |
| PUT/PATCH | `/api/actividades/{id}/` | Edita (recomendado PATCH; HU-52) | `actividades.editar` |
| POST | `/api/actividades/{id}/anular/` | `→ ANULADA` con motivo (HU-50) | `actividades.desactivar` |
| POST | `/api/actividades/{id}/reactivar/` | `→ ACTIVA` (HU-51) | `actividades.desactivar` |

- **No existe `DELETE`** → `405`. Nada se borra: la anulación es la baja
  (decisión 2 de la Semana 7) y conserva la traza.
- **`anulada`, `motivo_anulacion` y `registrado_por` son de solo lectura**:
  no están en el formulario de escritura; `anulada` solo cambia con
  `anular/` y `reactivar/`, `registrado_por` lo pone el servidor.
- La lista ordena por **fecha descendente**; la paginación es global
  (`API_PAGE_SIZE`, 20 por página).

## Autenticación y permisos

Sin sesión → `401`; con sesión pero sin el permiso de la acción →
`403 {"detail": "No tienes permiso para realizar esta acción."}` (clase
`PermisosActividad`, un permiso por acción).

| Rol | Sobre actividades |
|---|---|
| Administrador | Los 4 permisos: `actividades.ver/crear/editar/desactivar` (anular y reactivar) |
| Técnico de campo | `ver/crear/editar` → lista, crea y edita **en sus productores asignados**; **no `desactivar`** → `anular/` y `reactivar/` → `403` (colección 155) |
| Coordinador | **Solo `actividades.ver`** → lectura (`200`); crear → `403` (colección 159) |

**Ámbito del Técnico** (mismo `SoloSusProductores` que las semanas
anteriores, sobre el productor de la parcela de la campaña): una campaña
ajena al crear responde **el mismo mensaje que si no existiera**
(`{"campania": ["La campaña indicada no existe."]}`) y una actividad ajena
en detalle o edición → **`404 {"detail": "No encontrado."}`** (el permiso se
comprueba antes que el ámbito: `403 > 404`). Además, `registrado_por` se
**omite de las respuestas** para los roles con `limita_a_asignados`
(el Técnico no lo ve; colección 153).

## Parámetros de consulta

| Parámetro | Valores | Efecto |
|---|---|---|
| `estado` | `ACTIVA`, `ANULADA` | Filtra por anulación. Otro valor → `400 {"estado": "Use ACTIVA o ANULADA."}` (colección 145) |
| `campania`, `tipo`, `productor`, `parcela`, `cultivo` | id numérico | Filtran por el id. No numérico → `400 {"…": "Debe ser un id numérico."}` |
| `fecha_desde`, `fecha_hasta` | `AAAA-MM-DD` | Rango de fechas (≥ / ≤) |
| `busqueda` | texto | Coincidencia parcial en código de parcela, apellidos/nombres del productor, método y observaciones |
| `page` | número | Paginación (20 por página) |

## Actividades

### Listado - `GET /api/actividades/`

Fila (HU-47):

```json
{
  "id": 1,
  "fecha": "2026-09-15",
  "tipo_actividad": {"id": 2, "codigo": "SIEMBRA", "nombre": "Siembra"},
  "campania": {
    "id": 4,
    "periodo": "2026-2027",
    "estado": "EN_PRODUCCION",
    "fecha_siembra": "2026-09-15",
    "cultivo": {"id": 1, "nombre": "Quinua"},
    "parcela": {"id": 3, "codigo": "P-003", "productor": {"id": 2, "nombre_completo": "Mamani Quispe, Rosa"}}
  },
  "metodo": "Siembra mecanizada",
  "horas": "7.5",
  "costo": "120.50",
  "anulada": false
}
```

### Detalle - `GET /api/actividades/{id}/`

Los campos del listado más: `densidad_siembra`, `densidad_unidad`,
`observaciones`, `motivo_anulacion`, `registrado_por` (**nombre de
usuario**; omitido para roles con `limita_a_asignados`), `creado_en` y
`actualizado_en` (que el trigger mantiene en cada `PUT`/`PATCH`).

### Alta - `POST /api/actividades/`

Campos de escritura: `campania`, `tipo_actividad`, `fecha` y, opcional,
`metodo`, `densidad_siembra` + `densidad_unidad`, `horas`, `costo` y
`observaciones`. **No se aceptan** `anulada`, `motivo_anulacion` ni
`registrado_por` (el cliente no puede forzarlos). Responde `201` con la
ficha de lectura; **la campaña viene anidada releída tras el guardado**
(los triggers pudieron cambiar su estado y fecha de siembra).

```json
{
  "campania": 4,
  "tipo_actividad": 2,
  "fecha": "2026-09-15",
  "metodo": "Siembra mecanizada",
  "densidad_siembra": "80.00",
  "densidad_unidad": "KG_HA",
  "horas": "7.5",
  "costo": "120.50"
}
```

| Situación | Cuerpo exacto (400) |
|---|---|
| Campaña sin enviar / id inexistente | `{"campania": ["La campaña es obligatoria."]}` / `{"campania": ["La campaña indicada no existe."]}` |
| Campaña fuera del ámbito del Técnico | `{"campania": ["La campaña indicada no existe."]}` (mismo mensaje que id inexistente) |
| Campaña en estado no activo | `{"campania": ["La campaña está CANCELADA y no admite nuevos registros."]}` (colección 142) |
| Tipo sin enviar / inexistente | `{"tipo_actividad": ["El tipo de actividad es obligatorio."]}` / `{"tipo_actividad": ["El tipo de actividad indicado no existe."]}` |
| Tipo inactivo | `{"tipo_actividad": ["El tipo de actividad indicado no existe o está inactivo."]}` |
| Fecha sin enviar / con formato inválido | `{"fecha": ["La fecha es obligatoria."]}` / `{"fecha": ["La fecha no es válida: usa el formato AAAA-MM-DD."]}` |
| Fecha futura (hora de Lima, pregunta H) | `{"fecha": ["La fecha no puede ser futura."]}` (colección 139) |
| Fecha fuera del período de la campaña | `{"fecha": ["La fecha 2026-05-01 está fuera del período de la campaña (2026-03-01 a 2026-11-30)."]}` (el trigger también la rechaza) |
| Densidad sin unidad / unidad sin densidad | `{"densidad_siembra": ["La densidad de siembra y su unidad deben ir juntas (o dejar ambas vacías)."]}` (colección 140) |
| Densidad en un tipo que no es SIEMBRA | `{"densidad_siembra": ["La densidad de siembra solo aplica a actividades de tipo SIEMBRA."]}` |
| Densidad ≤ 0 o unidad desconocida | `{"densidad_siembra": ["La densidad de siembra debe ser mayor que 0."]}` / `{"densidad_unidad": ["La unidad de densidad debe ser KG_HA o PLANTAS_M2."]}` |
| Horas o costo negativos | `{"horas": ["Las horas no pueden ser negativas."]}` / `{"costo": ["El costo no puede ser negativo."]}` (colección 141, los dos a la vez) |
| Horas/costo/densidad mal formados | `{"horas": ["Las horas deben ser un número."]}`, `…máximo 3 dígitos enteros y 1 decimal.`, `{"costo": ["El costo debe ser un número."]}`, `…máximo 8 dígitos enteros y 2 decimales.`, `{"densidad_siembra": ["La densidad de siembra debe ser un número."]}` |

**Efecto de la siembra** (decisión 4): si el tipo es `SIEMBRA`, el trigger
`fn_actividad_siembra` fija la campaña en **`EN_PRODUCCION`** con
`fecha_siembra` = la menor fecha entre las siembras activas; la respuesta
201 lo trae ya reflejado en `campania.estado` y `campania.fecha_siembra`
(colección 134). Si la base rechaza el `INSERT` (carrera entre la
validación y el trigger), la vista traduce el `IntegrityError` al **400**
`"No se pudo guardar la actividad: los datos chocan con una restricción de
la base de datos."` en lugar de un 500.

### Edición - `PUT/PATCH /api/actividades/{id}/`

Se puede ajustar `fecha`, `metodo`, `densidad_siembra` + `densidad_unidad`,
`horas`, `costo` y `observaciones`. **Campaña y tipo quedan bloqueados**:
anula y registra otra actividad.

| Situación | Cuerpo exacto (400) |
|---|---|
| Cambiar la campaña | `{"campania": ["La campaña de una actividad no se puede cambiar: anula y registra otra actividad."]}` (colección 138) |
| Cambiar el tipo | `{"tipo_actividad": ["El tipo de actividad no se puede cambiar: anula y registra otra actividad."]}` |

Las validaciones de fecha (futura y período), densidad y horas/costo se
repiten en la edición. Respuesta `200` con la ficha releída (como en el
alta).

### Anular - `POST /api/actividades/{id}/anular/`

`ACTIVA → ANULADA` (HU-50). Exige **motivo** y el permiso
`actividades.desactivar`; el motivo queda en `motivo_anulacion`. Si era
una **siembra activa**, el trigger recalcula `fecha_siembra` de la campaña
(puede quedar vacío) **sin retroceder su estado** (colección 148).

```json
{"motivo": "Se perdió por helada tardía."}
```

| Situación | Cuerpo exacto (400/403) |
|---|---|
| Sin motivo o en blanco | `{"motivo": "El motivo de anulación es obligatorio."}` (string; colección 147) |
| Ya anulada | `{"estado": "La actividad ya está anulada."}` |
| Sin permiso (Técnico, Coordinador) | `403 {"detail": "No tienes permiso para realizar esta acción."}` (colección 155) |

### Reactivar - `POST /api/actividades/{id}/reactivar/`

`ANULADA → ACTIVA` (HU-51): limpia `motivo_anulacion`, exige
`actividades.desactivar` y que la campaña **sigue abierta** y la fecha
**aún dentro del período** (los triggers son la red de seguridad). Si era
siembra, la fecha de siembra se recalcula otra vez (colección 150).

| Situación | Cuerpo exacto (400) |
|---|---|
| No estaba anulada | `{"estado": "La actividad no está anulada."}` |
| Campaña cerrada o cancelada | `{"estado": "La campaña está CANCELADA y no admite nuevos registros."}` |
| Fecha fuera del período | `{"fecha": "La fecha 2026-05-01 está fuera del período de la campaña (2026-03-01 a 2026-11-30)."}` (string) |

## Cambios en campañas y productores

- **Detalle de campaña** (`GET /api/campanias/{id}/`) añade
  **`actividades_activas`** (recuento de actividades no anuladas) y
  **`fecha_ultima_actividad`** (la mayor fecha entre ellas), ambos en la
  lista y en el detalle (HU-43/HU-54; colección 135).
- **`GET /api/campanias/?desplegable=1`**: lista corta **sin paginar**
  (array plano, no `{results}`) y **solo estados activos**
  (`PLANIFICADA`, `EN_PRODUCCION`, `COSECHADA`; colección 130).
- **`GET /api/productores/?desplegable=1`**: igual, **solo activos**, con
  `id`, `codigo` y `nombre_completo` (colección 131).

## Errores (cuerpos verificados)

La API mezcla **dos formas de 400** y ambas son válidas (decisión 8 de la
semana): el **serializador** responde **lista** `{"campo": ["mensaje"]}`;
las **vistas/acciones** (anular, reactivar, filtro `estado`) responden
**string** `{"clave": "mensaje"}`. El frontend acepta los dos
(`frontend/src/api/errores.js`) y en los tests se usa `str(...)`.

| Código | Cuerpo | Cuándo |
|---|---|---|
| 401 | `{"detail": "Las credenciales de autenticación no se proveyeron."}` | Sin sesión |
| 403 | `{"detail": "No tienes permiso para realizar esta acción."}` | Permiso faltante (p. ej. anular sin `actividades.desactivar`) |
| 400 | `{"<campo>": ["mensaje."]}` | Validaciones del serializador (tablas de arriba) |
| 400 | `{"motivo": "…"}`, `{"estado": "…"}`, `{"fecha": "…"}` | Acciones y filtro `estado` |
| 404 | `{"detail": "No encontrado."}` | Id inexistente o fuera del ámbito del Técnico (manejador de la Semana 4) |
| 405 | `{"detail": "Método \"DELETE\" no permitido."}` | Cualquier `DELETE` (colección 151) |
| 429 | `{"detail": ".", "retry_after": N}` | Rate limit global (Semana 2) |

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (sin espacios dentro del JSON)
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/

# 2. Alta de una siembra con densidad -> 201 (la campaña queda EN_PRODUCCION)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"campania":4,"tipo_actividad":2,"fecha":"2026-09-15","metodo":"Siembra mecanizada","densidad_siembra":"80.00","densidad_unidad":"KG_HA","horas":"7.5","costo":"120.50"}' `
  http://localhost:8000/api/actividades/

# 3. Editar el metodo (campania y tipo quedan bloqueados)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X PATCH -d '{"metodo":"Sistema de riego por goteo"}' http://localhost:8000/api/actividades/1/

# 4. Anular con motivo -> 200 ANULADA (y recalcula la fecha de siembra)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X POST -d '{"motivo":"Se perdio por helada."}' http://localhost:8000/api/actividades/1/anular/

# 5. Reactivar -> 200 ACTIVA
curl.exe -s -b cookies.txt -X POST http://localhost:8000/api/actividades/1/reactivar/

# 6. Filtros
curl.exe -s -b cookies.txt "http://localhost:8000/api/actividades/?campania=4&estado=ACTIVA"
curl.exe -s -b cookies.txt "http://localhost:8000/api/actividades/?fecha_desde=2026-09-01&fecha_hasta=2026-09-30"
```

## Colección de pruebas (Postman)

[`coleccion_api_semana7.json`](coleccion_api_semana7.json) - **159
peticiones** con pruebas `pm.test` embebidas (estado + textos clave), en un
solo nivel y numeradas de 001 a 159:

1. **001-127 · Semanas 4 a 6**: sesiones, ubicaciones, productores,
   parcelas, asignaciones, catálogos y campañas (se ejecutan tal cual,
   cerrando con la sesión del Coordinador).
2. **128-159 · Actividades (32 nuevas)**:
   - **128-143 · Administrador**: sesión → tipos de actividad y sus ids
     (129) → desplegables de campañas y productores (130-131) → cancelar la
     campaña del técnico porque solo hay una activa por parcela (132) →
     campaña `2026-2027` (133) → siembra con densidad y su efecto en la
     campaña (134) → resumen de campaña (135) y ficha (136) → edición del
     método y bloqueo de campaña/tipo (137-138) → rechazos de fecha futura,
     densidad sin unidad, horas y costo negativos, y campaña cancelada
     (139-142) → preparación válida (143).
   - **144-151 · Listado y ciclo de anulación**: filtro por campaña con
     orden descendente (144), estado inválido (145), búsqueda por método
     (146), anular sin motivo (147) y con motivo (148), filtro `ANULADA`
     (149), reactivar (150) y `DELETE` → 405 (151).
   - **152-156 · Técnico**: sesión, alta en la campaña de su productor
     (153, sin `registrado_por`), lista de las suyas (154), anular → 403
     (155) y cierre de sesión (156).
   - **157-159 · Coordinador**: sesión, listar `200` y crear `403`.

Variables: `base_url`; las claves (`clave_admin`, `clave_coordinador`,
`clave_tecnico`) salen de `.credenciales` (ignorado por Git; la colección no
contiene secretos). Crea además `sufijo=SEMANA7` y los ids que genera
(`tipo_siembra_id`, `tipo_prep_id`, `campania_s7_id`, `actividad_id`,
`actividad_prep_id`, …). El período (`2026-2027`), las fechas de actividad
(marzo–octubre 2026) y el `sufijo` son fijos, así que la colección está
pensada para **una ejecución por base de datos**: para repetir, restablece
la base de ensayo. La colección fue **validada contra el servidor:
159/159 peticiones y 286/286 aserciones con el código y los textos
esperados** (se usó una BD temporal que se borró al terminar).
