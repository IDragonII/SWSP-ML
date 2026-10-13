# Tablero SIGPA-GA — Semana 8: producción, rendimiento y cierre de campañas

> Tablero de la semana del **23 al 29 de noviembre** (calendario referencial).
> Sustituye mientras tanto a Trello/GitHub Projects (decisión de metodología:
> se confirmará con el responsable qué herramienta usa él).
> Los textos originales de las historias de usuario **no están en este
> repositorio**: las descripciones siguientes son el **mapeo propuesto**
> (igual que en semanas anteriores), anclado a los RF/RN del documento de
> requerimientos.

## Semana 8 — 7/7 fases terminadas

El tema «Producción, rendimiento y cierre de campañas» (cierre del Sprint 4)
corresponde al **mapeo HU-56 a HU-62** de la semana; se ejecutó **por fases
F1–F7** acordadas con el responsable.

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-56** | Listar producciones con filtros (campaña, productor, parcela, cultivo, período, distrito/provincia, estado de campaña, revisión pendiente, rango de fechas de cosecha y búsqueda) y orden por fecha descendente | ✅ Hecha | `GET /api/producciones/` · pruebas 119 · colección 171 |
| **HU-57** | Ver la ficha de la producción (datos de la cosecha, kg y kg/ha calculados por la base, revisión y trazabilidad; `registrado_por` oculto al ámbito del Técnico) | ✅ Hecha | `GET /api/producciones/{id}/` · pruebas 103, 104 · colección 174, 182 |
| **HU-58** | Registrar y editar la cosecha: una sola por campaña (`OneToOne`), unidad de masa activa, superficie ≤ sembrada, fecha ≥ siembra; los kg y el rendimiento los calcula la base y la campaña pasa a `COSECHADA`; sin `DELETE` → 405 | ✅ Hecha | `POST` y `PATCH /api/producciones/{id}/` + `fn_validar_produccion` · pruebas 103–111 · colección 173, 175–181, 185–186 |
| **HU-59** | Revisión de rendimiento atípico: umbrales configurables en `/api/parametros/` (4 claves fijas, solo valor), marca automática con motivo y `revisar/` con nota + decisión de inclusión en el dataset | ✅ Hecha | `revisar/`, `PATCH /api/parametros/{clave}/` · pruebas 107, 112, 113, 116 · colección 160–167, 193–195 |
| **HU-60** | Deshacer cosecha con motivo: borra la fila (única excepción del «nada se borra») y devuelve la campaña a `EN_PRODUCCION` | ✅ Hecha | `POST …/deshacer-cosecha/` · prueba 114 · colección 183–184 |
| **HU-61** | Cerrar campaña: `COSECHADA → CERRADA` con `campanias.desactivar`, exige producción registrada y sin revisión pendiente; irreversible (no hay reapertura) | ✅ Hecha | `POST /api/campanias/{id}/cerrar/` + `fn_validar_campania` v3 · pruebas 115, 117 · colección 194, 196 |
| **HU-62** | Bloque de producción en las fichas: el detalle de campaña y la ficha del productor lo incluyen por API; en la UI, bloque «Producción» en `CampaniaFicha` y columna «Producción» en `ProductorFicha` | ✅ Hecha | `campanias/serializers.py`, `productores/serializers.py` · colección 174, 182 · checklist `verificacion_ui_semana8.md` |

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: apps **`produccion/`** y **`sistema/`** con los modelos (`producciones`, 17 columnas con `OneToOne` a campañas; `parametros_sistema`, 5 columnas) y **4 migraciones reversibles** (`produccion.0001`, `sistema.0001`, `produccion.0002` con `fn_validar_produccion`, `fn_produccion_post` **parcial** y 3 triggers, `campanias.0003` con `fn_validar_campania` **v3 completa**); **15 triggers** en total; migración verificada desde cero en BD temporal | ✅ Hecha | `backend/produccion/`, `backend/sistema/` · `DB_sql/01_tablas.sql`, `02_reglas_y_vista.sql`, `03_insert.sql` |
| **F2** | API completa: listado con filtros, detalle, alta, edición, `revisar/` y `deshacer-cosecha/` (sin `DELETE` → 405); `/api/parametros/` (GET lista/detalle y PATCH por clave; sin `POST`/`DELETE` → 405); `cerrar/` en campañas; permisos por acción y ámbito del Técnico (404); desplegables `?produccion=1` y `?tipo=MASA&activo=true`; bloques `produccion` en las fichas de campaña y productor | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` + `campanias/` · pruebas 103–120 · colección 160–205 |
| **F3** | Comparación con el diseño SQL + colección de Postman | ✅ Hecha | `docs/comparacion_semana8.md` (**17 + 5 columnas, 11 restricciones, 0 índices extra, 15 triggers**) y `docs/coleccion_api_semana8.json` — **validada 205/205 (374/374 aserciones)** |
| **F4** | Pantallas: **`/parametros`** (tabla de las 4 claves + edición en modal), **`CampaniaFicha`** con bloque «Producción» y botones «Registrar producción» y «Cerrar campaña», **`ProduccionFormulario`** (alta/edición en modal) y **`ProduccionFicha`** (revisar/deshacer), columna «Producción» en `ProductorFicha`; entrada «Parámetros» en el menú | ✅ Hecha | `pages/Parametros.jsx`, `ProduccionFormulario.jsx`, `ProduccionFicha.jsx`, `CampaniaFicha.jsx`, `ProductorFicha.jsx`, `api/produccion.js`, `api/parametros.js` · checklist `verificacion_ui_semana8.md` |
| **F5** | Documentación de la semana | ✅ Hecha | `decisiones_semana8.md` (20 decisiones + preguntas J y K), `api_produccion.md`, `verificacion_ui_semana8.md` (+ nota de cierre en `api_campanias.md`) |
| **F6** | Cierre y verificación | ✅ Hecha | este tablero + `evidencias_capitulo4.md` + `CONTEXTO_PROYECTO.md` §3/§6 |
| **F7** | Commit semanal único (decisión 17): el agente entrega el **nombre del commit** al cierre y lo ejecuta el responsable | ✅ Hecha | nombre del commit entregado al cierre de la semana |

**Cierre de la semana:** 120 pruebas verdes (`manage.py test`; 18 nuevas),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de **205 peticiones validada 205/205 (374/374 aserciones)** contra el servidor
(estados y textos clave), `npm run lint` y `npm run build` en 0 problemas, y
documentación en `decisiones_semana8.md` (20 decisiones),
`comparacion_semana8.md`, `verificacion_ui_semana8.md`, `api_produccion.md` y
`coleccion_api_semana8.json`.

## Semana 7 — 7/7 fases terminadas

El tema «Actividades productivas» corresponde al **mapeo HU-47 a HU-55** de la
semana (Sprint 4); se ejecutó **por fases F1–F7** acordadas con el responsable.

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-47** | Listar actividades con filtros (campaña, tipo, productor/parcela/cultivo, rango de fechas, estado, búsqueda) y orden por fecha descendente | ✅ Hecha | `GET /api/actividades/` · pruebas 94, 99 · colección 147–152 |
| **HU-48** | Registrar actividad con validaciones (campaña activa, fecha no futura según hora de Lima, fecha dentro del período, densidad solo en siembra y con su unidad, horas/costo ≥ 0); la siembra fija `fecha_siembra` y pasa la campaña a `EN_PRODUCCION` | ✅ Hecha | `POST /api/actividades/` + `fn_actividad_siembra` v2 · pruebas 87, 88, 90–92 · colección 134–136, 142–146 |
| **HU-49** | Ver la ficha de la actividad (datos, densidad, motivo, trazabilidad; `registrado_por` oculto al ámbito) y el detalle de campaña con `actividades_activas` y `fecha_ultima_actividad` | ✅ Hecha | `GET /api/actividades/{id}/` · pruebas 97, 100 · colección 137–139, 153 |
| **HU-50** | Anular actividad con motivo obligatorio (borrado lógico: `ANULADA`, sin `DELETE`); la siembra anulada recalcula `fecha_siembra` | ✅ Hecha | `POST …/anular/` · pruebas 89, 96, 101 · colección 154–156 |
| **HU-51** | Reactivar actividad (limpia el motivo y recalcula el efecto siembra) | ✅ Hecha | `POST …/reactivar/` · pruebas 96, 101 · colección 157 |
| **HU-52** | Editar actividad (método, fechas, horas, costo, densidad y observaciones; campaña y tipo inmodificables) | ✅ Hecha | `PATCH /api/actividades/{id}/` · pruebas 93, 95 · colección 140–141 |
| **HU-53** | Permisos por acción y ámbito: Administrador los 4 `actividades.*`; Técnico `ver/crear/editar` (anular → 403) solo en sus productores; Coordinador solo `ver` | ✅ Hecha | `PermisosActividad` + `SoloSusProductores` · pruebas 98, 102 · colección 155, 158–159 |
| **HU-54** | Desplegables (`?desplegable=1` en campañas activas y productores activos) y resumen de campaña en la ficha | ✅ Hecha | `campanias/serializers.py`, `productores/serializers.py` · colección 130–131, 139 |
| **HU-55** | Menú y pantalla `/actividades` con `actividades.ver`, alta/edición en modal, ficha con anular/reactivar y `CampaniaFicha` con bloque de actividades | ✅ Hecha | `opcionesMenu.js`, `App.jsx`, `pages/Actividades.jsx`, `ActividadFormulario.jsx`, `ActividadFicha.jsx`, `CampaniaFicha.jsx` · checklist `verificacion_ui_semana7.md` |

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: app **`seguimiento/`** con el modelo `Actividad` (15 columnas, `anulada`+`motivo_anulacion`, 6 checks) y 2 migraciones (`0001` la tabla, `0002` con `fn_validar_fecha_campania`, `fn_actividad_siembra` v2 y 3 triggers); diseño SQL actualizado (anuladas fuera del dataset); migración verificada **desde cero** en BD temporal | ✅ Hecha | `backend/seguimiento/` · `DB_sql/01_tablas.sql` y `02_reglas_y_vista.sql` |
| **F2** | API completa: listado con filtros, detalle, alta, edición, `anular/` y `reactivar/`; permisos `actividades.*` por acción, ámbito del Técnico (404), `registrado_por` oculto al ámbito, sin `DELETE` (405); `?desplegable=1` en campañas y productores | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` + `campanias/` y `productores/` · pruebas 87–102 · colección 128–159 |
| **F3** | Comparación con el diseño SQL | ✅ Hecha | `docs/comparacion_semana7.md` — **15/15 columnas, 10/10 restricciones, 2/2 índices (0 extra), 3/3 triggers** + 2 funciones literales |
| **F4** | Pantallas: **`/actividades`** (filtros en URL, `Tabla`+`Paginacion`), alta/edición en modal (densidad solo si el tipo es SIEMBRA, `max` = hoy en hora Lima), **`ActividadFicha`** con «Anular actividad»/«Reactivar» y **`CampaniaFicha`** con bloque de actividades y «Registrar actividad» preseleccionada; entrada en el menú; bug de `listarTodo` corregido | ✅ Hecha | `pages/Actividades.jsx`, `ActividadFormulario.jsx`, `ActividadFicha.jsx`, `CampaniaFicha.jsx`, `api/actividades.js` · checklist `verificacion_ui_semana7.md` |
| **F5** | Colección de Postman: 127 de la Semana 6 + 32 nuevas (128–159) | ✅ Hecha | `docs/coleccion_api_semana7.json` — **validada 159/159 (286/286 aserciones)** |
| **F6** | Documentación de la semana | ✅ Hecha | `decisiones_semana7.md` (17 decisiones + preguntas H e I), `api_actividades.md`, `verificacion_ui_semana7.md` |
| **F7** | Cierre y verificación | ✅ Hecha | este tablero + `evidencias_capitulo4.md` + `CONTEXTO_PROYECTO.md` §3/§6 |

**Cierre de la semana:** 102 pruebas verdes (`manage.py test`; 16 nuevas),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de **159 peticiones validada 159/159 (286/286 aserciones)** contra el servidor
(estados y aserciones), `npm run lint` y `npm run build` en 0 problemas, y
documentación en `decisiones_semana7.md` (17 decisiones),
`comparacion_semana7.md`, `verificacion_ui_semana7.md`, `api_actividades.md` y
`coleccion_api_semana7.json`.

## Semana 6 — 7/7 fases terminadas

El tema «Campañas de producción» corresponde al **mapeo HU-38 a HU-46** de la
semana; al igual que en la Semana 5, se ejecutó **por fases F1–F7**
acordadas con el responsable.

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: app **`campanias/`** con el modelo `Campania` (5 estados, constraints del diseño) y 2 migraciones (`0001` con la tabla y la clave compuesta, `0002` con `fn_validar_campania` **parcial** y sus 2 triggers) | ✅ Hecha | `backend/campanias/models.py`, `migrations/0001_initial.py`, `0002_funciones_y_triggers.py` |
| **F2** | API completa: listado con filtros, detalle, alta, edición por estado, `iniciar/` y `cancelar/`; permisos `campanias.*` por acción, ámbito del Técnico (404) y bloqueos de desactivación en productor/parcela | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` + bloqueos en `productores/views.py` · pruebas 68–86 · colección 094–127 |
| **F3** | Comparación con el diseño SQL (columnas, constraints, índices, reglas y datos) | ✅ Hecha | `docs/comparacion_semana6.md` — **14/14 columnas, 9/9 restricciones, 6/6 índices** (+1 extra documentado), 2/2 triggers |
| **F4** | Pantallas: **`/campanias`** (listado con filtros en URL y `Tabla`), alta/edición en modal con iniciar/cancelar, y sección **Campañas** en las fichas de productor y parcela (HU-44) | ✅ Hecha | `pages/Campanias.jsx`, `CampaniaFormulario.jsx`, edición de `ProductorFicha.jsx`, `ParcelaFicha.jsx`, `api/campanias.js` · checklist `verificacion_ui_semana6.md` |
| **F5** | Colección de Postman: 93 de las semanas anteriores + 34 nuevas de campañas | ✅ Hecha | `docs/coleccion_api_semana6.json` — **validada 127/127 (221/221 aserciones)** |
| **F6** | Documentación de la semana | ✅ Hecha | `decisiones_semana6.md` (18 decisiones), `api_campanias.md`, `verificacion_ui_semana6.md` |
| **F7** | Cierre y verificación | ✅ Hecha | este tablero + `evidencias_capitulo4.md` + `CONTEXTO_PROYECTO.md` §3/§6 |

**Cierre de la semana:** 86 pruebas verdes (`manage.py test`; 19 nuevas),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de **127 peticiones validada 127/127** contra el servidor (estados y
aserciones), `npm run lint` y `npm run build` en 0 problemas, y documentación
en `decisiones_semana6.md` (18 decisiones), `comparacion_semana6.md`,
`verificacion_ui_semana6.md`, `api_campanias.md` y
`coleccion_api_semana6.json`.

## Semana 5 — 8/8 fases terminadas

El tema «Catálogos de campañas» no tiene HU propia en el mapeo propuesto, así
que esta semana se ejecutó **por fases F1–F8** acordadas con el responsable.

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: app **`catalogos/`** con 8 modelos y 2 migraciones (`0001` con los constraints del diseño, `0002` con las 26 filas fijas) | ✅ Hecha | `backend/catalogos/models.py`, `migrations/0001_initial.py`, `0002_datos_iniciales.py` |
| **F2** | API de los 8 catálogos (listado, detalle, alta, edición, estado, desplegables y reordenado de etapas) con los permisos `catalogos.*` y pruebas | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` · pruebas 54–67 · colección 049–093 |
| **F3** | Comando **`cargar_catalogos`** con los 18 datos CONFIRMAR, idempotente y sin pisar ediciones (44 filas en total) | ✅ Hecha | `management/commands/cargar_catalogos.py` · prueba 67 |
| **F4** | Comparación con el diseño SQL (columnas, constraints y datos) | ✅ Hecha | `docs/comparacion_semana5.md` — **37/37 columnas, 28/28 restricciones, 44/44 datos** |
| **F5** | Pantalla **`/catalogos`** con 8 pestañas, filtros en URL, alta/edición en modal y permisos en el botón | ✅ Hecha | `pages/Catalogos.jsx`, `CatalogoFormulario.jsx`, `catalogosConfig.js`, `api/catalogos.js` · checklist `verificacion_ui_semana5.md` |
| **F6** | Colección de Postman: 48 de la Semana 4 + 45 nuevas de catálogos | ✅ Hecha | `docs/coleccion_api_semana5.json` — **validada 93/93** |
| **F7** | Documentación de la semana | ✅ Hecha | `decisiones_semana5.md` (17 decisiones), `api_catalogos.md`, `verificacion_ui_semana5.md` |
| **F8** | Cierre y verificación | ✅ Hecha | este tablero + `evidencias_capitulo4.md` |

**Cierre de la semana:** 67 pruebas verdes (`manage.py test`),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de **93 peticiones validada 93/93** contra el servidor (estados y aserciones),
`npm run lint` y `npm run build` en 0 problemas, y documentación en
`decisiones_semana5.md` (17 decisiones), `comparacion_semana5.md`,
`verificacion_ui_semana5.md`, `api_catalogos.md` y
`coleccion_api_semana5.json`.

## Semana 4 — 6/6 terminadas

| HU | Descripción (propuesta) | Origen | Estado | Evidencia |
|---|---|---|---|---|
| **HU-23** | Registrar parcelas con código automático (`P-001`), validaciones (superficie > 0, altitud 0–6500, coordenadas las dos o ninguna, listas cerradas) y productor obligatorio/activo | RF: «registrar parcelas… superficie, altitud, coordenadas» + RN de parcelas | ✅ Hecha | `POST /api/parcelas/` + triggers `trg_parcelas_codigo` · pruebas 38, 39, 40, 44 · colección 009–021 |
| **HU-24** | Buscar y filtrar parcelas por código, productor, comunidad, distrito, provincia y estado | RF: «buscar y filtrar parcelas» | ✅ Hecha | `?busqueda=`, `?productor=`, `?comunidad=`, `?estado=ACTIVA\|INACTIVA` + paginación · prueba 42 · colección 017–018 |
| **HU-25** | Asignar productores a técnicos: alta, lista de técnicos disponibles, desactivar/reactivar sin borrado y reasignar = desactivar + crear otra | RF: «el técnico solo verá los productores que tenga asignados» | ✅ Hecha | `POST /api/asignaciones/`, `PATCH …/estado/`, `GET …/tecnicos-disponibles/`; red del trigger `trg_asignaciones_validar` · pruebas 45–49, 51 · colección 022–031, 041–048 |
| **HU-26** | Ver la ficha completa del productor: datos + ubicación + parcelas con resumen + técnicos asignados (estos dos últimos solo para admin/coordinador) | RF: «mostrar una ficha del productor con sus parcelas, campañas e historial» (completa HU-22) | ✅ Hecha | `GET /api/productores/{id}/` con `parcelas`, `resumen` y `tecnicos_asignados` · pruebas 50, 52 · colección 010, 038 |
| **HU-27** | Pantalla de productores: listado paginado con filtros por URL y ficha/alta/edición en ventanas flotantes (modales), responsive y por permisos | RF: interface de gestión de productores · decisiones 14, 16 y 19 | ✅ Hecha | `frontend/src/pages/Productores.jsx`, `ProductorFicha.jsx`, `ProductorFormulario.jsx` + `components/Tabla.jsx`, `Modal.jsx` · checklist `verificacion_ui_semana4.md` |
| **HU-28** | Pantalla de parcelas: listado paginado con filtros y alta/edición en modales (misma fórmula que HU-27) | RF: interface de gestión de parcelas · decisiones 14, 16 y 19 | ✅ Hecha | `frontend/src/pages/Parcelas.jsx`, `ParcelaFormulario.jsx` · checklist `verificacion_ui_semana4.md` |

**Cierre de la semana:** 53 pruebas verdes (`manage.py test`),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de **48 peticiones validada 48/48** contra el servidor (estados y aserciones),
`npm run lint` y `npm run build` en 0 problemas, y documentación en
`decisiones_semana4.md` (19 decisiones), `comparacion_semana4.md`,
`verificacion_ui_semana4.md` y `coleccion_api_semana4.json`.

## Semanas anteriores (resumen)

| Semana | HU | Estado |
|---|---|---|
| 1 (5–11 oct) — roles, permisos y usuarios | HU-01..HU-06 (gestión de roles/permisos/usuarios, semilla y panel) | ✅ 8 pruebas |
| 2 (12–18 oct) — autenticación y permisos | HU-07..HU-14 (login, refresh, logout, `/me`, permisos, rate limit, sesión y menú en React) | ✅ 20 pruebas · `api_autenticacion.md` |
| 3 (19–25 oct) — ubicación y productores | HU-15..HU-22 (ubicación con `cargar_ubicacion`, productor con código PROD-000N, filtros, enmascarado, ficha parcial) | ✅ 37 pruebas · `api_ubicacion_productores.md` |

## Siguiente (Semana 9, 30 nov–6 dic)

| Tema | Nota |
|---|---|
| Recursos e insumos / clima | Siguiente sprint del roadmap (`CONTEXTO_PROYECTO.md` §13); fertilización y fitosanitarios aún sin cantidades de insumos (decisión 17 de la Semana 7) |
| Preguntas abiertas A, B, D, F, G, H, I, J y K | Lista de ubicaciones real, enmascarado, botón «usar mi ubicación», fechas vs período, bloqueo de desactivación, fechas futuras en actividades, unidad de densidad, producción bruta/neta y umbrales del sistema |
| Checklists de UI de las Semanas 4 a 8 | Ejecutar en navegador (Chrome/Edge/móvil) y anotar los resultados en cada documento |
| Demo 1 (cierre del Sprint 4) | Primera fila del dataset con producción; las predicciones quedan para los Sprints 13–14 (`fn_produccion_post` completa) |

## Preguntas abiertas que bloquean decisiones

1. **Lista real de ubicaciones** (decisión 1): hasta que llegue, rige
   `datos/ejemplo_ubicaciones.csv` (datos inventados, marcados).
2. **Regla de enmascarado por rol** (decisión 4 de la Semana 3 / HU-21):
   propuesta actual — Administrador y Técnico completos, Coordinador enmascarado.
3. ~~¿El productor que registra un técnico se le asigna automáticamente?~~
   **Cerrada en la Semana 4: sí** (decisión 4 de `decisiones_semana4.md`,
   prueba 49: se asigna en la misma operación y de forma atómica).
4. **Botón «usar mi ubicación actual»** (item *estirada*): solo funciona en
   `https://` o `localhost`; decidir en la demo.
5. **¿Las fechas de una campaña deben caer dentro de su período?** (Semana 6,
   pregunta F): rige el rango 1 ene año₁ – 31 dic año₂ validado solo en la API;
   pendiente de confirmar con el responsable.
6. **¿Bloquear la desactivación de productor/parcela con campañas activas?**
   (Semana 6, pregunta G / HU-45 y HU-46): implementado con mensaje de error;
   pendiente de confirmar con el responsable.
7. **¿Rechazar fechas futuras en actividades?** (Semana 7, pregunta H):
   implementado (`fecha ≤ hoy` en hora de **America/Lima**, y `max = hoy` en el
   formulario); si el responsable admite planificar a futuro se retira la
   comprobación (afecta a la colección, que usa fechas pasadas por ello).
8. **¿Cuál es la unidad de densidad de siembra?** (Semana 7, pregunta I):
   implementadas **las dos** del diseño (`KG_HA` y `PLANTAS_M2`); la API exige
   valor+unidad juntos y el frontend trae `UNIDADES_DENSIDAD` para fijar la
   medida cuando el responsable decida.
9. **¿La producción registrada es bruta o neta de la pérdida?** (Semana 8,
   pregunta J): rige **bruta** — `produccion_kg` = cantidad × factor;
   `perdida_kg` se guarda aparte y **no descuenta** (decisión 20);
   pendiente de confirmar.
10. **¿Umbrales de revisión y factor del quintal?** (Semana 8, pregunta K):
    rigen los del diseño (`rendimiento_min_plausible = 100`,
    `rendimiento_max_plausible = 5000`, `umbral_rendimiento_bajo = 800`,
    `dias_sin_actividad = 30` y **quintal = 46 kg**) — **CONFIRMAR**; se
    cambian sin tocar código desde `/parametros` (y el catálogo de unidades).
