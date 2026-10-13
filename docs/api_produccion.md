# API de producciones y parámetros - Semana 8 (23-29 nov)

Referencia de los recursos añadidos en la Semana 8 desde
`backend/produccion/` y `backend/sistema/`: **la cosecha y el rendimiento de
una campaña** (HU-56 a HU-60) y **los parámetros configurables del sistema**
(umbrales de revisión). Además la API de campañas gana la acción **`cerrar/`**
(HU-61) y el bloque de producción en sus fichas (HU-62; ver también
[`api_campanias.md`](api_campanias.md)). Todo va bajo `/api/` (montado en
`config/urls.py`). La autenticación (cookies httpOnly o `Authorization:
Bearer`) es la de la Semana 2 y se describe en
[`api_autenticacion.md`](api_autenticacion.md); las decisiones de la semana,
en [`decisiones_semana8.md`](decisiones_semana8.md); la comparación con el
diseño SQL, en [`comparacion_semana8.md`](comparacion_semana8.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/producciones/` | Lista (paginado, con filtros) | `produccion.ver` |
| POST | `/api/producciones/` | Crea (alta de la cosecha, HU-58) | `produccion.crear` |
| GET | `/api/producciones/{id}/` | Detalle (HU-57) | `produccion.ver` |
| PUT/PATCH | `/api/producciones/{id}/` | Edita (recomendado PATCH; HU-58) | `produccion.editar` |
| POST | `/api/producciones/{id}/revisar/` | Marca la revisión como resuelta (HU-59) | `produccion.desactivar` |
| POST | `/api/producciones/{id}/deshacer-cosecha/` | Borra la producción y devuelve la campaña a `EN_PRODUCCION` (HU-60) | `produccion.desactivar` |
| GET | `/api/parametros/` | Lista de parámetros (paginado) | `parametros.gestionar` |
| GET | `/api/parametros/{clave}/` | Detalle de un parámetro por su clave | `parametros.gestionar` |
| PATCH | `/api/parametros/{clave}/` | Cambia el `valor` de una clave fija | `parametros.gestionar` |
| POST | `/api/campanias/{id}/cerrar/` | `COSECHADA → CERRADA` (HU-61) | `campanias.desactivar` |

- **No existe `DELETE` de producciones** → `405`: la única excepción al
  «nada se borra» es la acción `deshacer-cosecha/`, que elimina la fila
  (decisión 2 de la Semana 8).
- **Parámetros sin `POST` ni `DELETE`** → `405`: las claves son fijas,
  nacidas con la migración `sistema.0001`; por la API solo cambia el valor.
- **Una sola producción por campaña** (`OneToOne`): registrar la primera
  deja la campaña en `COSECHADA` (trigger `fn_produccion_post`); la respuesta
  trae los kg, el rendimiento y la marca de revisión **calculados por la
  base** y la campaña **releída** tras el guardado.
- `produccion_kg`, `rendimiento_kg_ha`, `requiere_revision`,
  `incluir_en_entrenamiento` y `registrado_por` son **de solo lectura**: el
  cliente no puede forzarlos.
- La lista ordena por **fecha de cosecha descendente**; la paginación es
  global (`API_PAGE_SIZE`, 20 por página).

## Autenticación y permisos

Sin sesión → `401`; con sesión pero sin el permiso de la acción →
`403 {"detail": "No tienes permiso para realizar esta acción."}` (clases
`PermisosProduccion` y `PermisosParametro`, un permiso por acción). El
permiso se comprueba **antes** que el ámbito y que `get_object`: con un id
inexistente responde `403`, no `404`.

| Rol | Sobre producciones y parámetros |
|---|---|
| Administrador | Todo: `produccion.ver/crear/editar/desactivar`, `parametros.gestionar` y `campanias.desactivar` (revisar, deshacer y cerrar) |
| Técnico de campo | `produccion.ver/crear/editar` → lista, crea y edita **en sus productores asignados**; **no `desactivar`** → `revisar/` y `deshacer-cosecha/` → `403` (colecciones 200–201). Sin `parametros.gestionar` ni `campanias.desactivar` |
| Coordinador | **Solo `produccion.ver`** (y `campanias.ver`): crea → `403` (colección 205); parámetros → `403` (colección 166–167); cerrar → `403` |

**Ámbito del Técnico** (mismo `SoloSusProductores` que las semanas
anteriores, sobre el productor de la parcela de la campaña): una campaña
ajena al crear responde **el mismo mensaje que si no existiera**
(`{"campania": ["La campaña indicada no existe."]}`) y una producción ajena
en detalle o edición → **`404 {"detail": "No encontrado."}`** (403 > 404).
Además, `registrado_por` se **omite de las respuestas** para los roles con
`limita_a_asignados` (el Técnico no lo ve; colección 199).

## Producciones

### Parámetros de consulta (`GET /api/producciones/`)

| Parámetro | Valores | Efecto |
|---|---|---|
| `campania`, `productor`, `parcela`, `cultivo` | id numérico | Filtran por el id. No numérico → `400 {"…": "Debe ser un id numérico."}` |
| `periodo` | `AAAA-AAAA` | Filtra por el período de la campaña |
| `distrito`, `provincia` | id numérico | Filtran por la ubicación de la parcela |
| `estado` | `PLANIFICADA`, `EN_PRODUCCION`, `COSECHADA`, `CERRADA`, `CANCELADA` | Filtra por el estado de la campaña. Otro valor → `400 {"estado": "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, CERRADA o CANCELADA."}` |
| `requiere_revision` | `true`, `false` | Filtra por la marca de revisión. Otro valor → `400 {"requiere_revision": "Use true o false."}` |
| `fecha_desde`, `fecha_hasta` | `AAAA-MM-DD` | Rango de fechas de cosecha (≥ / ≤) |
| `busqueda` | texto | Coincidencia parcial en código de parcela, apellidos/nombres del productor y cultivo |
| `page` | número | Paginación (20 por página) |

### Listado - `GET /api/producciones/`

Fila (HU-56):

```json
{
  "id": 12,
  "fecha_cosecha": "2026-10-10",
  "campania": {
    "id": 7,
    "periodo": "2026-2027",
    "estado": "COSECHADA",
    "fecha_siembra": "2026-09-15",
    "superficie_sembrada_ha": "1.00",
    "cultivo": {"id": 1, "nombre": "Quinua"},
    "parcela": {"id": 3, "codigo": "P-003", "productor": {"id": 2, "nombre_completo": "Mamani Quispe, Rosa"}}
  },
  "produccion_kg": "3220.00",
  "superficie_cosechada_ha": "1.00",
  "rendimiento_kg_ha": "3220.00",
  "requiere_revision": false
}
```

### Detalle - `GET /api/producciones/{id}/`

Los campos del listado más: `cantidad_producida`, `unidad` (`{id, nombre,
simbolo}`), `perdida_kg`, `calidad` (`PRIMERA`/`SEGUNDA`/`TERCERA` o
`null`), `motivo_revision`, `incluir_en_entrenamiento`, `observaciones`,
`registrado_por` (**nombre de usuario**; omitido para roles con
`limita_a_asignados`), `creado_en` y `actualizado_en` (que el trigger
mantiene).

### Alta - `POST /api/producciones/`

Campos de escritura: `campania`, `fecha_cosecha`, `superficie_cosechada_ha`,
`cantidad_producida`, `unidad` y, opcional, `perdida_kg`, `calidad` y
`observaciones`. **No se aceptan** los campos calculados (arriba). Responde
`201` con la ficha de lectura; **la campaña viene anidada releída tras el
guardado** (el trigger pudo pasarla a `COSECHADA` y recalcular kg y
rendimiento).

```json
{
  "campania": 7,
  "fecha_cosecha": "2026-10-10",
  "superficie_cosechada_ha": "1.00",
  "cantidad_producida": "70",
  "unidad": 5,
  "calidad": "PRIMERA",
  "observaciones": "Cosecha de la Semana 8"
}
```

| Situación | Cuerpo exacto (400) |
|---|---|
| Campaña sin enviar / id inexistente | `{"campania": ["La campaña es obligatoria."]}` / `{"campania": ["La campaña indicada no existe."]}` |
| Campaña fuera del ámbito del Técnico | `{"campania": ["La campaña indicada no existe."]}` (mismo mensaje que id inexistente) |
| Campaña en estado no válido | `{"campania": ["La campaña está PLANIFICADA y no admite nuevos registros."]}` (solo `EN_PRODUCCION` y `COSECHADA` admiten) |
| Campaña sin siembra registrada | `{"campania": ["La campaña no tiene siembra registrada: registra la actividad de siembra antes de la producción."]}` (colección 190) |
| Ya tiene producción | `{"campania": ["Ya existe una producción para esta campaña (id 12)."]}` (colección 175; también desde el `IntegrityError` del UNIQUE) |
| Fecha sin enviar / mal formada | `{"fecha_cosecha": ["La fecha de cosecha es obligatoria."]}` / `{"fecha_cosecha": ["La fecha de cosecha no es válida: usa el formato AAAA-MM-DD."]}` |
| Fecha anterior a la siembra o al inicio | `{"fecha_cosecha": ["La fecha de cosecha no puede ser anterior a la fecha de siembra (2026-09-15)."]}` / `…al inicio de la campaña (2026-03-01).` (colección 186) |
| Superficie sin enviar / ≤ 0 | `{"superficie_cosechada_ha": ["La superficie cosechada es obligatoria."]}` / `…debe ser mayor que 0.` (colección 179) |
| Superficie > sembrada | `{"superficie_cosechada_ha": ["La superficie cosechada no puede superar la sembrada (1.00 ha)."]}` (colección 185) |
| Cantidad sin enviar / negativa | `{"cantidad_producida": ["La cantidad producida es obligatoria."]}` / `…no puede ser negativa.` (colección 180) |
| Unidad sin enviar / inexistente | `{"unidad": ["La unidad es obligatoria."]}` / `{"unidad": ["La unidad indicada no existe."]}` |
| Unidad que no es masa activa | `{"unidad": ["La unidad debe ser de masa (kg, quintal o tonelada) y estar activa."]}` (colección 178; usa `?tipo=MASA&activo=true` en `/api/unidades/`) |
| Pérdida negativa | `{"perdida_kg": ["La pérdida no puede ser negativa."]}` |
| Calidad desconocida | `{"calidad": ["La calidad debe ser PRIMERA, SEGUNDA o TERCERA."]}` |
| Límites decimales | superficie `…máximo 6 dígitos enteros y 2 decimales.`, cantidad `…9 dígitos enteros y 3 decimales.`, pérdida `…8 dígitos enteros y 2 decimales.` |

**Lo que calcula la base** (`fn_validar_produccion`): `produccion_kg` =
cantidad × factor de conversión de la unidad (quintal = 46 kg);
`rendimiento_kg_ha` = kg / superficie cosechada. Si el rendimiento cae
**fuera** de `[rendimiento_min_plausible, rendimiento_max_plausible]`
(parametros_sistema), la producción nace con `requiere_revision = true` y
`motivo_revision = "Rendimiento atípico: 0.50 kg/ha"` (colección 193). La
campaña queda en **`COSECHADA`** (`fn_produccion_post`), ya reflejado en
`campania.estado` de la respuesta. Si la base rechaza el `INSERT` (carrera
del UNIQUE), la vista traduce el `IntegrityError` al 400 nombrando la
producción existente en lugar de un 500.

### Edición - `PUT/PATCH /api/producciones/{id}/`

Mismos campos de escritura que el alta **salvo la campaña**: se puede
ajustar fecha, superficie, cantidad, unidad, pérdida, calidad y
observaciones; los kg y el rendimiento se recalculan. `PATCH` es parcial.

| Situación | Cuerpo exacto (400) |
|---|---|
| Cambiar la campaña | `{"campania": ["La campaña de una producción no se puede cambiar: usa «deshacer cosecha» y registra otra producción."]}` |
| Campaña cerrada | `{"non_field_errors": ["La campaña cerrada no admite cambios en la producción."]}` (colección 197; string en `non_field_errors`) |

Las validaciones de fecha, superficie, cantidad, unidad y calidad se
repiten en la edición. Respuesta `200` con la ficha releída (editar la
cantidad de 70 a 60 qq deja los kg en 2760, colección 176).

### Revisar - `POST /api/producciones/{id}/revisar/`

Resolución de la marca de revisión (HU-59): quita `requiere_revision`,
**añade la nota al motivo original** («{original} — Revisión: {nota}»,
truncado a 200 caracteres; conserva la traza) y registra la decisión de
`incluir_en_entrenamiento`. Exige `produccion.desactivar` y producción
**aún marcada**.

```json
{"nota": "Rendimiento confirmado con el productor", "incluir_en_entrenamiento": false}
```

| Situación | Cuerpo exacto (400) |
|---|---|
| No requiere revisión | `{"estado": "La producción no requiere revisión."}` |
| Sin nota o en blanco | `{"nota": "La nota de revisión es obligatoria."}` |
| Inclusión no booleana | `{"incluir_en_entrenamiento": "Debe indicar si se incluye en el entrenamiento (true o false)."}` |

Respuesta `200` con la ficha releída: `requiere_revision = false` y
`motivo_revision` concatenado (colección 195).

### Deshacer cosecha - `POST /api/producciones/{id}/deshacer-cosecha/`

Única excepción al «nada se borra» (HU-60): **elimina la fila** de
producción, devuelve la campaña a **`EN_PRODUCCION`** (transición que
admite `fn_validar_campania` v3) y responde un resumen. Exige
`produccion.desactivar` y motivo; la campaña queda libre para registrar
otra producción. No vale en campañas `CERRADA`.

```json
{"motivo": "Registro equivocado: repetir la cosecha."}
```

| Situación | Cuerpo exacto (400) |
|---|---|
| Sin motivo o en blanco | `{"motivo": "El motivo es obligatorio."}` (colección 183) |
| Campaña cerrada | `{"estado": "No se puede deshacer la cosecha: la campaña está cerrada."}` |

Respuesta `200`: `{"campania": 7, "estado": "EN_PRODUCCION", "motivo": "…"}`
(colección 184). **DELETE general → `405`** (colección 181).

## Parámetros del sistema

Cuatro claves fijas (migración `sistema.0001`; decision 7 de la Semana 8):

| Clave | Valor por defecto | Para qué sirve |
|---|---|---|
| `dias_sin_actividad` | `30` | Días sin actividad antes de marcar seguimiento pendiente |
| `umbral_rendimiento_bajo` | `800` | Rendimiento bajo que debe atender el técnico (kg/ha) |
| `rendimiento_min_plausible` | `100` | Por debajo, la producción se marca para revisión (kg/ha) |
| `rendimiento_max_plausible` | `5000` | Por encima, la producción se marca para revisión (kg/ha) |

### Listado - `GET /api/parametros/`

Paginado como el resto; cada fila:

```json
{
  "clave": "rendimiento_min_plausible",
  "valor": "100",
  "descripcion": "Rendimiento mínimo plausible (kg/ha)",
  "actualizado_en": "2026-11-23T10:00:00-05:00"
}
```

### Detalle - `GET /api/parametros/{clave}/`

Igual que la fila; la clave va en la URL
(`…/parametros/rendimiento_min_plausible/`). Id inexistente →
`404 {"detail": "No encontrado."}` (colección 165).

### Edición - `PATCH /api/parametros/{clave}/`

Solo cambia el `valor` (la clave y la descripción son de solo lectura).
Respuesta `200` con la fila releída (el trigger `trg_parametros_sistema_actualizado`
fija `actualizado_en`).

```json
{"valor": "120"}
```

| Situación | Cuerpo exacto (400) |
|---|---|
| Sin valor | `{"valor": ["El valor es obligatorio."]}` |
| No numérico o ≤ 0 | `{"valor": ["El valor debe ser un número mayor que 0."]}` (colección 163) |
| Mínimo ≥ máximo vigente | `{"valor": ["El rendimiento mínimo debe ser menor que el máximo."]}` (lista: el `validate` del serializador usa esa forma; colección 164) |
| `POST` o `DELETE` | `405 {"detail": "Método \"POST\" no permitido."}` |

**Importante**: `fn_validar_produccion` lee los umbrales en cada
`INSERT`/`UPDATE` de producciones; cambiar un valor **no reevalúa** las
producciones ya marcadas (solo afecta a las siguientes; decisión 4).

## Cambios en campañas y productores (HU-61, HU-62)

- **Detalle de campaña** (`GET /api/campanias/{id}/`) añade el bloque
  **`produccion`**: `null` si aún no hay cosecha, o
  `{id, fecha_cosecha, produccion_kg, rendimiento_kg_ha, requiere_revision,
  incluir_en_entrenamiento}` (colección 174 y 186).
- **La ficha del productor** (`GET /api/productores/{id}/`) incluye ese
  mismo bloque mini en cada campaña de su lista `campanias`
  (colección 182).
- **`GET /api/campanias/?produccion=1`**: desplegable del formulario de
  producción (array plano, sin paginar): **solo `EN_PRODUCCION`, con
  `fecha_siembra` y sin producción todavía** (colección 172; con las dos
  campañas libres, colección 192).
- **`POST /api/campanias/{id}/cerrar/`** (HU-61, `campanias.desactivar`):
  `COSECHADA → CERRADA`. Sin cuerpo. Respuesta `200` con el detalle de la
  campaña (incluido su bloque `produccion`).

| Situación | Cuerpo exacto (400) |
|---|---|
| Estado distinto de COSECHADA | `{"estado": "Solo se puede cerrar una campaña cosechada."}` |
| Sin producción registrada | `{"estado": "No se puede cerrar la campaña: no tiene producción registrada."}` |
| Producción con revisión pendiente | `{"estado": "No se puede cerrar la campaña: la producción requiere revisión pendiente. Revísala antes de cerrar."}` (colección 194) |

Cerrada, la campaña **no admite actividades ni cambios en la producción**
(los triggers son la red de seguridad); no hay acción de reapertura.

## Errores (cuerpos verificados)

Mismo contrato que las Semanas 6-7: el **serializador** responde **lista**
`{"campo": ["mensaje"]}`; las **vistas/acciones** (revisar, deshacer,
cerrar, filtros `estado` y `requiere_revision`) responden **string**
`{"clave": "mensaje"}`. El frontend acepta los dos
(`frontend/src/api/errores.js`).

| Código | Cuerpo | Cuándo |
|---|---|---|
| 401 | `{"detail": "Las credenciales de autenticación no se proveyeron."}` | Sin sesión |
| 403 | `{"detail": "No tienes permiso para realizar esta acción."}` | Permiso faltante (p. ej. revisar sin `produccion.desactivar`) |
| 400 | `{"<campo>": ["mensaje."]}` | Validaciones del serializador (tablas de arriba) |
| 400 | `{"motivo": "…"}`, `{"estado": "…"}`, `{"nota": "…"}` | Acciones y filtros |
| 404 | `{"detail": "No encontrado."}` | Id inexistente o fuera del ámbito del Técnico |
| 405 | `{"detail": "Método \"DELETE\" no permitido."}` | `DELETE` de producciones y `POST`/`DELETE` de parámetros |
| 429 | `{"detail": ".", "retry_after": N}` | Rate limit global (Semana 2) |

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (sin espacios dentro del JSON)
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/

# 2. Umbral mínimo de revisión -> 200 (valor "120")
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X PATCH -d '{"valor":"120"}' http://localhost:8000/api/parametros/rendimiento_min_plausible/

# 3. Alta de la cosecha: 70 qq -> 3220 kg, campaña a COSECHADA
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"campania":7,"fecha_cosecha":"2026-10-10","superficie_cosechada_ha":"1.00","cantidad_producida":"70","unidad":5,"calidad":"PRIMERA"}' `
  http://localhost:8000/api/producciones/

# 4. Editar solo la cantidad (los kg y el rendimiento se recalculan)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X PATCH -d '{"cantidad_producida":"60"}' http://localhost:8000/api/producciones/12/

# 5. Revisar una atípica (requiere produccion.desactivar)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X POST -d '{"nota":"Confirmado con el productor","incluir_en_entrenamiento":false}' `
  http://localhost:8000/api/producciones/13/revisar/

# 6. Deshacer la cosecha (borra la fila y devuelve la campaña a EN_PRODUCCION)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X POST -d '{"motivo":"Registro equivocado."}' http://localhost:8000/api/producciones/12/deshacer-cosecha/

# 7. Cerrar la campaña (requiere campanias.desactivar; irreversible)
curl.exe -s -b cookies.txt -X POST http://localhost:8000/api/campanias/8/cerrar/

# 8. Filtros
curl.exe -s -b cookies.txt "http://localhost:8000/api/producciones/?requiere_revision=true"
curl.exe -s -b cookies.txt "http://localhost:8000/api/producciones/?estado=COSECHADA&fecha_desde=2026-10-01"
```

## Colección de pruebas (Postman)

[`coleccion_api_semana8.json`](coleccion_api_semana8.json) - **205
peticiones** con pruebas `pm.test` embebidas (estado + textos clave), en un
solo nivel y numeradas de 001 a 205:

1. **001-159 · Semanas 4 a 7**: sesiones, ubicaciones, productores,
   parcelas, asignaciones, catálogos, campañas y actividades (se ejecutan
   tal cual, cerrando con la sesión del Coordinador).
2. **160-205 · Parámetros y producción (46 nuevas)**:
   - **160-167 · Parámetros del sistema**: sesión de Administrador → las 4
     claves con sus valores (160) → editar `rendimiento_min_plausible` a
     120 (161) → rechazos: valor no numérico, mínimo ≥ máximo y clave
     inexistente (162-165) → Coordinador sin `parametros.gestionar`:
     listar y editar → 403 (166-167).
   - **168-170 · Unidades**: desplegable (Kilogramo, Hectárea) y creación
     del **Quintal (46 kg)** que usará la cosecha.
   - **171-182 · HU-56/58 sobre la campaña de la Semana 7**: listado vacío
     y desplegable `?produccion=1` (171-172) → alta de 70 qq → **3 220 kg
     sobre 1,00 ha**, campaña a `COSECHADA` (173) → ficha de campaña con el
     bloque `produccion` (174) → duplicada (175) → edición a 60 qq →
     2 760 kg (176) → rechazos: campaña `PLANIFICADA`, unidad de
     superficie, superficie 0, cantidad negativa y `DELETE` → 405
     (177-181) → ficha del productor con el bloque (182).
   - **183-186 · HU-60 deshacer cosecha**: sin motivo → 400; con motivo →
     200 y campaña de vuelta a `EN_PRODUCCION` (183-184). Con la campaña
     libre se prueban los dos controles que el duplicado tapaba:
     superficie > sembrada y fecha anterior a la siembra (185-186).
   - **187-197 · Campaña de la Semana 8, atípicas y cierre**: cancelar una
     campaña que estorba → crear parcela y campaña `2026-2027` → iniciar →
     rechazo sin siembra → siembra → desplegable con las dos libres →
     producción **atípica** (1 kg sobre 2 ha → 0,50 kg/ha, marcada para
     revisión) → cerrar con revisión pendiente → 400 → **revisar** con nota
     e inclusión (HU-59) → **cerrar** → `CERRADA` (HU-61) → editar la
     producción de la cerrada → 400.
   - **198-205 · Permisos**: Técnico crea en la campaña de su productor
     (sin `registrado_por` en la respuesta), lista solo la suya, revisar y
     deshacer → 403; Coordinador lista (incluye la del Técnico) y crear →
     403.

Variables: `base_url`; las claves (`clave_admin`, `clave_coordinador`,
`clave_tecnico`) salen de `.credenciales` (ignorado por Git; la colección no
contiene secretos). Crea además `sufijo=SEMANA8` y los ids que genera
(`unidad_kg_id`, `unidad_ha_id`, `quintal_id`, `campania_s7_id`,
`campania_s8_id`, `produccion_id`, `produccion_baja_id`,
`produccion_tec_id`, …). La autenticación es **por sesión** (cookie); no usa
cabecera `Authorization`. El período (`2026-2027`) y la cosecha de
referencia (70 qq del 2026-10-10) son fijos, así que la colección está
pensada para **una ejecución por base de datos**: para repetir, restablece
la base de ensayo. La colección fue **validada contra el servidor:
205/205 peticiones y 374/374 aserciones con el código y los textos
esperados** (se usó la BD temporal `sigpa_ga_coleccion8`, que se borró al
terminar).
