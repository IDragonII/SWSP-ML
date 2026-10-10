# API de campañas - Semana 6 (9-15 nov)

Referencia del recurso central añadido en la Semana 6 desde
`backend/campanias/`: **la campaña (parcela + cultivo + variedad + período)
como entidad con ciclo de vida**. Todo va bajo `/api/` (montado en
`config/urls.py`). La autenticación (cookies httpOnly o `Authorization:
Bearer`) es la de la Semana 2 y se describe en
[`api_autenticacion.md`](api_autenticacion.md); las decisiones de la semana,
en [`decisiones_semana6.md`](decisiones_semana6.md); la comparación con el
diseño SQL, en [`comparacion_semana6.md`](comparacion_semana6.md).

## Resumen

| Método | Ruta | Qué hace | Permiso |
|---|---|---|---|
| GET | `/api/campanias/` | Lista (paginado, con filtros) | `campanias.ver` |
| POST | `/api/campanias/` | Crea (siempre en `PLANIFICADA`) | `campanias.crear` |
| GET | `/api/campanias/{id}/` | Detalle | `campanias.ver` |
| PUT/PATCH | `/api/campanias/{id}/` | Edita (recomendado PATCH) | `campanias.editar` |
| POST | `/api/campanias/{id}/iniciar/` | `PLANIFICADA → EN_PRODUCCION` (HU-39) | `campanias.editar` |
| POST | `/api/campanias/{id}/cancelar/` | `→ CANCELADA` con motivo (HU-40) | `campanias.desactivar` |

- **No existe `DELETE`** → `405`. Nada se borra: las campañas se cancelan
  (decisión 3 de la Semana 3). Las rutas de detalle llevan barra final.
- **El estado es de solo lectura**: no está en el formulario de escritura;
  solo cambia con `iniciar/` y `cancelar/` (y, más adelante, con el módulo de
  producción: `COSECHADA` y `CERRADA` aún no se llegan por API).
- La lista ordena por **período descendente**; la paginación es global
  (`API_PAGE_SIZE`, 20 por página).

## Autenticación y permisos

Misma que las semanas anteriores: sin sesión → `401`; con sesión pero sin el
permiso de la acción → `403 {"detail": "No tienes permiso para realizar esta
acción."}` (clase `PermisosCampania`, un permiso por acción).

| Rol | Sobre campañas |
|---|---|
| Administrador | Los 4 permisos: `campanias.ver/crear/editar/desactivar` |
| Técnico de campo | `ver/crear/editar` → puede listar, crear y editar **en sus productores asignados**; **no `desactivar`** → `cancelar/` → `403` (colección 123) |
| Coordinador | **Solo `campanias.ver`** → lectura (`200`); crear/editar/iniciar/cancelar → `403` (colección 125–127) |

**Ámbito del Técnico** (reutiliza `SoloSusProductores` de la Semana 4): solo
ve las campañas cuya parcela pertenece a un productor con asignación activa.
Una campaña ajena responde **`404 {"detail": "No encontrado."}`**, nunca
`403` — y el permiso se comprueba **antes** que el ámbito (`403 > 404`).
Al crear, si la parcela no está en su ámbito, la API responde el **mismo
mensaje que si no existiera**: `{"parcela": ["La parcela indicada no
existe."]}` (colección 120). En la interfaz, el menú y la ruta `/campanias`
exigen `campanias.ver`.

## Parámetros de consulta

| Parámetro | Valores | Efecto |
|---|---|---|
| `estado` | `PLANIFICADA`, `EN_PRODUCCION`, `COSECHADA`, `CERRADA`, `CANCELADA` | Filtra por estado. Otro valor → `400 {"estado": "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, CERRADA o CANCELADA."}` (colección 116) |
| `cultivo`, `variedad`, `parcela`, `productor`, `comunidad`, `distrito`, `provincia` | id numérico | Filtran por el id. No numérico → `400 {"…": "Debe ser un id numérico."}` |
| `periodo` | `AAAA-AAAA` | Filtra por período exacto |
| `busqueda` | texto | Coincidencia parcial en código de parcela, apellidos/nombres del productor, nombre de cultivo y de variedad |
| `page` | número | Paginación (20 por página) |

Un valor fuera de una lista cerrada en el **filtro** no es error de
formato: se valida `estado` (arriba) y el resto espera ids numéricos.

## Campañas

### Listado - `GET /api/campanias/`

Fila (HU-42):

```json
{
  "id": 1,
  "periodo": "2027-2028",
  "parcela": {
    "id": 3,
    "codigo": "P-003",
    "superficie_ha": "2.00",
    "productor": {"id": 2, "codigo": "PROD-0002", "nombre_completo": "Mamani Quispe, Rosa"}
  },
  "cultivo": {"id": 1, "nombre": "Quinua"},
  "variedad": {"id": 1, "nombre": "Real"},
  "estado": "PLANIFICADA"
}
```

Sin DNI ni teléfono (enmascarado por rol como en el resto del sistema).

### Detalle - `GET /api/campanias/{id}/`

Los campos de la lista más: `fecha_inicio`, `fecha_fin_prevista`,
`fecha_siembra`, `superficie_sembrada_ha`, `observaciones`, `creado_por`
(**nombre de usuario**, `StringRelatedField`), `creado_en` y `actualizado_en`
(que el trigger mantiene en cada `PUT`/`PATCH`).

### Alta - `POST /api/campanias/`

Campos de escritura: `periodo`, `parcela`, `cultivo`, `variedad`,
`fecha_inicio`, `fecha_fin_prevista` y, opcional, `superficie_sembrada_ha`
y `observaciones`. **No se aceptan** `estado`, `fecha_siembra` ni
`creado_por` (el cliente no puede forzarlos, prueba 83); si la superficie se
omite, **se toma la de la parcela**. Responde `201` con la ficha de lectura
(estado `PLANIFICADA`).

```json
{
  "periodo": "2027-2028",
  "parcela": 3,
  "cultivo": 1,
  "variedad": 1,
  "fecha_inicio": "2027-03-01",
  "fecha_fin_prevista": "2027-08-15"
}
```

| Situación | Cuerpo exacto (400) |
|---|---|
| Parcela sin enviar / id inexistente | `{"parcela": ["La parcela es obligatoria."]}` / `{"parcela": ["La parcela indicada no existe."]}` |
| Parcela desactivada | `{"parcela": ["La parcela indicada no existe o está inactiva."]}` |
| Productor de la parcela inactivo | `{"parcela": ["El productor de la parcela está inactivo: no admite campañas nuevas."]}` |
| Parcela fuera del ámbito del Técnico | `{"parcela": ["La parcela indicada no existe."]}` (mismo mensaje que id inexistente) |
| Cultivo/variedad inexistente o inactivo | `{"cultivo": ["El cultivo indicado no existe o está inactivo."]}` / `{"variedad": ["La variedad indicada no existe o está inactiva."]}` |
| Variedad de otro cultivo | `{"variedad": ["La variedad indicada no pertenece al cultivo elegido."]}` (HU-38; colección 101) |
| Período mal formado | `{"periodo": ["El período debe tener el formato AAAA-AAAA (por ejemplo 2025-2026)."]}` (colección 102) |
| Período sin años consecutivos | `{"periodo": ["El segundo año del período debe ser uno más que el primero (por ejemplo 2025-2026)."]}` |
| Fecha fuera del período | `{"fecha_inicio": ["La fecha de inicio debe caer dentro del período 2027-2028: entre el 1 de enero de 2027 y el 31 de diciembre de 2028."]}` (idem con `fecha_fin_prevista`; colección 103) |
| Fin prevista anterior al inicio | `{"fecha_fin_prevista": ["La fecha de fin prevista no puede ser anterior a la fecha de inicio."]}` |
| Superficie ≤ 0 o mal formada | `{"superficie_sembrada_ha": ["La superficie sembrada debe ser mayor que 0."]}` (también `…debe ser un número.`, `…máximo 6 dígitos enteros y 2 decimales.`, `…máximo 2 decimales.`) |
| Superficie mayor que la parcela | `{"superficie_sembrada_ha": ["La superficie sembrada no puede superar la superficie de la parcela (2.00 ha)."]}` (colección 104) |
| Campaña repetida (parcela + período) | `{"parcela": ["Ya existe una campaña de Quinua en esta parcela para el período 2027-2028 (id 5)."], "campania_existente": "5"}` (colección 105) |
| Ya hay campaña activa en la parcela | `{"parcela": ["Ya existe una campaña activa en esta parcela (id 5, 2027-2028, Quinua)."], "campania_existente": "5"}` — la cancelada **no** cuenta |
| Fechas con formato inválido | `{"fecha_inicio": ["La fecha de inicio no es válida: usa el formato AAAA-MM-DD."]}` |

Las dos reglas únicas se comprueban **antes de guardar** (con el nombre de la
campaña existente) y, si aun así la base rechaza el `INSERT` (carrera), la
vista traduce el `IntegrityError` al **mismo 400** en lugar de un 500.

### Edición - `PUT/PATCH /api/campanias/{id}/`

La edición depende del estado (HU-41):

| Estado | Qué se puede editar |
|---|---|
| `PLANIFICADA` | Todo salvo `estado`, `fecha_siembra`, `creado_*` y `actualizado_*` |
| `EN_PRODUCCION` | Solo `fecha_fin_prevista`, `superficie_sembrada_ha` y `observaciones`. `parcela`, `cultivo`, `variedad`, `periodo` y `fecha_inicio` están **bloqueados**: `{"fecha_inicio": ["El campo «fecha_inicio» está bloqueado al iniciar la campaña: para corregirlo, cancela esta campaña y crea otra nueva."]}` (colección 108) |
| `CANCELADA` | Nada: `400 ["Una campaña cancelada no admite cambios."]` |

Las validaciones de período, fechas, superficie y duplicados se repiten en la
edición (con la campaña excluida de la comprobación de duplicados).

### Iniciar - `POST /api/campanias/{id}/iniciar/`

`PLANIFICADA → EN_PRODUCCION` (HU-39). Responde `200` con la ficha ya en
`EN_PRODUCCION` (colección 107). Si no está planificada:
`{"estado": ["Solo se puede iniciar una campaña planificada."]}`. Al
iniciar quedan bloqueados los 5 campos de la tabla anterior.

### Cancelar - `POST /api/campanias/{id}/cancelar/`

`PLANIFICADA` o `EN_PRODUCCION → CANCELADA` (HU-40). Exige **motivo** y el
permiso `campanias.desactivar`; el motivo se **suma a `observaciones`** y la
parcela queda libre (los índices parciales no cuentan las canceladas).
Responde `200` con la ficha en `CANCELADA` (colección 109).

```json
{"motivo": "Sin agua para riego en la temporada."}
```

| Situación | Cuerpo exacto (400/403) |
|---|---|
| Sin motivo o en blanco | `{"motivo": ["El motivo de cancelación es obligatorio."]}` (colección 106) |
| Ya cancelada | `{"estado": ["La campaña ya está cancelada."]}` |
| `COSECHADA` o `CERRADA` | `{"estado": ["Solo se puede cancelar una campaña planificada o en producción."]}` |
| Sin permiso (Técnico, Coordinador) | `403 {"detail": "No tienes permiso para realizar esta acción."}` (colección 123) |

## Errores (cuerpos verificados)

La API mezcla **dos formas de 400** y ambas son válidas (decisión 10 de la
semana): el **serializador** responde **lista** `{"campo": ["mensaje"]}`; las
**vistas/acciones** (estado, filtros, bloqueos) y la traducción de
integridad responden **string** `{"clave": "mensaje"}`. El frontend acepta
los dos (`frontend/src/api/errores.js`) y en los tests se usa `str(...)`.

| Código | Cuerpo | Cuándo |
|---|---|---|
| 401 | `{"detail": "Las credenciales de autenticación no se proveyeron."}` | Sin sesión |
| 403 | `{"detail": "No tienes permiso para realizar esta acción."}` | Permiso faltante (p. ej. cancelar sin `campanias.desactivar`) |
| 400 | `{"<campo>": ["mensaje."]}` | Validaciones del serializador (tabla de arriba) |
| 400 | `{"estado": "mensaje."}`, `{"motivo": "…"}`, `{"campania_existente": "5"}` | Acciones, filtros y traducción de integridad |
| 404 | `{"detail": "No encontrado."}` | Id inexistente o fuera del ámbito del Técnico (manejador de la Semana 4) |
| 405 | `{"detail": "Método \"DELETE\" no permitido."}` | Cualquier `DELETE` |
| 429 | `{"detail": ".", "retry_after": N}` | Rate limit global (Semana 2) |

## Cambios en productores y parcelas (HU-44 a HU-46)

- **Ficha del productor** (`GET /api/productores/{id}/`) añade:
  - `campanias`: lista de `{id, periodo, cultivo, variedad, parcela:{id,
    codigo}, estado}` ordenada por período descendente, **sin `creado_por`
    ni datos de otros usuarios** (HU-44);
  - `resumen.campanias_activas`: recuento de campañas activas (junto a
    `parcelas_activas` y `superficie_total_ha`).
- **Ficha de la parcela** (`GET /api/parcelas/{id}/`) añade el mismo bloque
  `campanias` (HU-44).
- **Desactivación bloqueada** (decisión pendiente de confirmar, preguntas
  F y G de `decisiones_semana6.md`):
  - `PATCH /api/productores/{id}/estado/` con `INACTIVO` y campañas activas
    → `400 {"estado": "No se puede desactivar el productor: tiene 1 campaña(s)
    activa(s) (id 7, 2027-2028). Cancela o cierra esas campañas primero."}`
    (HU-46, colección 112);
  - `PATCH /api/parcelas/{id}/estado/` con `INACTIVA` y campaña activa →
    `400 {"estado": "No se puede desactivar la parcela: tiene una campaña
    activa (id 7, 2027-2028, Quinua). Cancela esa campaña primero."}`
    (HU-45, colección 111);
  - con **solo campañas canceladas** sí se puede desactivar (prueba 78/79).

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Sesión (sin espacios dentro del JSON)
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/

# 2. Alta válida (sustituye los ids por los tuyos; sin superficie usa la parcela)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -d '{"periodo":"2027-2028","parcela":3,"cultivo":1,"variedad":1,"fecha_inicio":"2027-03-01","fecha_fin_prevista":"2027-08-15"}' `
  http://localhost:8000/api/campanias/

# 3. Iniciar (queda EN_PRODUCCION y bloquea 5 campos)
curl.exe -s -b cookies.txt -X POST http://localhost:8000/api/campanias/7/iniciar/

# 4. Editar un campo bloqueado -> 400
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X PATCH -d '{"fecha_inicio":"2027-03-05"}' http://localhost:8000/api/campanias/7/

# 5. Cancelar con motivo -> 200 CANCELADA (y libera la parcela)
curl.exe -s -b cookies.txt -H "Content-Type: application/json" `
  -X POST -d '{"motivo":"Sin agua para riego."}' http://localhost:8000/api/campanias/7/cancelar/

# 6. Filtros
curl.exe -s -b cookies.txt "http://localhost:8000/api/campanias/?estado=PLANIFICADA"
curl.exe -s -b cookies.txt "http://localhost:8000/api/campanias/?periodo=2027-2028"
```

## Colección de pruebas (Postman)

[`coleccion_api_semana6.json`](coleccion_api_semana6.json) - **127
peticiones** con pruebas `pm.test` embebidas (estado + textos clave), en un
solo nivel y numeradas de 001 a 127:

1. **001-048 · Semana 4**: sesiones, ubicaciones, productores, parcelas y
   asignaciones.
2. **049-093 · Catálogos**: los 8 recursos de la Semana 5 (las 93 se
   ejecutan tal cual, cerrando con la sesión del Coordinador).
3. **094-127 · Campañas (34 nuevas)**:
   - **094-116 · Administrador**: sesión → cultivo y variedad propios de la
     semana → segundo productor (`dni_productor2`) y su parcela → alta
     válida (100) y los rechazos de variedad ajena, período mal formado,
     fecha fuera del período, superficie mayor y duplicado (101-105) →
     cancelar sin motivo (106) → iniciar (107) y bloqueo de `fecha_inicio`
     (108) → cancelar con motivo (109) → segunda parcela/productor para los
     bloqueos HU-45 y HU-46 (110-112) → fichas de productor y parcela con
     su bloque de campañas (113-114) → detalle de campaña (115) → filtro
     por estado (116).
   - **117-124 · Técnico**: sesión, lista solo de sus productores (118),
     `404` en campaña ajena (119), `400` al crear en parcela ajena (120),
     alta propia `201` con su `creado_por` (121), iniciar `200` (122),
     cancelar `403` (123) y cierre de sesión (124).
   - **125-127 · Coordinador**: sesión, listar `200` y crear `403`.

Variables: `base_url`; las claves (`clave_admin`, `clave_coordinador`,
`clave_tecnico`) se definen en Postman y **salen de `.credenciales`**
(ignorado por Git; la colección no contiene secretos). Crea además
`sufijo=SEMANA6`, `dni_productor2=91827365` y los ids que genera
(`cultivo_s6_id`, `variedad_s6_id`, `productor2_id`, `parcela2_id`,
`campania_id`, `campania3_id`, `campania_tec_id`, …). El **período es fijo
(`2027-2028`) y los DNI también**, así que la colección está pensada para
**una ejecución por base de datos**: para repetir, cambia `sufijo` y
`dni_productor2` (con el mismo sufijo, las altas se declaran
duplicadas; precedente `SEMANA4R2`). La colección fue **validada contra el
servidor: 127/127 peticiones y 221/221 aserciones con el código y los textos
esperados** (se usó una BD temporal que se borró al terminar).
