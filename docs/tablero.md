# Tablero SIGPA-GA — Semana 10: clima

> Tablero de la semana del **7 al 13 de diciembre** (calendario referencial).
> Sustituye mientras tanto a Trello/GitHub Projects (decisión de metodología:
> se confirmará con el responsable qué herramienta usa él).
> Los textos originales de las historias de usuario **no están en este
> repositorio**: las descripciones siguientes son el **mapeo propuesto**
> (igual que en semanas anteriores), anclado a los RF/RN del documento de
> requerimientos.

## Semana 10 — 7/7 fases terminadas

El tema «clima» (cierre del **Sprint 5**) corresponde al **mapeo HU-76 a
HU-84** de la semana; se ejecuta **por fases F1–F7** acordadas con el
responsable (**F7 cerrada**: colección de Postman validada 270/270; el
commit semanal único se ejecuta tras el visto bueno).

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-76** | Listar registros de clima con 10 filtros (parcela, productor, comunidad, distrito, provincia, rango de fechas, fuente, heladas y búsqueda) y orden por fecha descendente | ✅ Hecha | `GET /api/clima/` · prueba 147 |
| **HU-77** | Ver la ficha del registro (medidas, trazabilidad y los dos cálculos del servidor: `temp_prom_calculado` y `helada_calculada`; `registrado_por` oculto al ámbito) | ✅ Hecha | `GET /api/clima/{id}/` · pruebas 144, 146 |
| **HU-78** | Registrar clima a mano: al menos una medida o la helada, temperaturas coherentes y en rango, fechas no futuras (hora de Lima), parcela activa y **una fila por parcela y día**; el servidor guarda el punto medio y deriva la helada del umbral | ✅ Hecha | `POST /api/clima/` · pruebas 138–144, 151 |
| **HU-79** | Editar un registro (medidas, fechas y helada; `confirmar_reemplazo` según la fuente; sin `DELETE` → 405) | ✅ Hecha | `PATCH /api/clima/{id}/` · pruebas 145, 148 |
| **HU-80** | Fuente MANUAL/API: editar un registro que vino de la API exige `confirmar_reemplazo=true` y lo **pasa a MANUAL**; los registros manuales nunca los pisa la API | ✅ Hecha | validación en `ClimaEscrituraSerializer` · pruebas 145, 153 |
| **HU-81** | Permisos por acción y ámbito: Administrador los 4 `clima.*`; Técnico `ver/crear/editar` solo en sus productores (parcela ajena → «no existe»); Coordinador solo `ver` | ✅ Hecha | `PermisosClima` + `SoloSusProductores` · prueba 146 |
| **HU-82** | Resumen de clima en la ficha de campaña (`resumen_clima`: precipitación acumulada, temperaturas, heladas y cobertura de la ventana; nota de provisionalidad) | ✅ Hecha | `campanias/serializers.py` · pruebas 149, 150 |
| **HU-83** | Bloque «Clima» en la ficha de parcela (registros y último día) y clave `umbral_helada_c` en `/api/parametros/` (−10 a 5 °C) | ✅ Hecha | `parcelas/serializers.py`, `sistema/` · pruebas 150, 155 |
| **HU-84** | Consultar la API meteorológica Open-Meteo por parcela y rango (≤ 92 días, throttle 10/hora, informe de 6 contadores, 502 si el servicio cae) | ✅ Hecha | `POST /api/clima/consulta-api/` + `servicio_meteorologico.py` · pruebas 152–154 · smoke E2E 15/15 |

> **Nota:** el mapeo HU-76..HU-84 es el **mapeo propuesto** de la semana (los
> textos originales no están en el repositorio); la numeración de la colección
> (236–269, más la 270 opcional) se validó en F7.

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: tabla **`clima`** en `seguimiento/` (15 columnas, `parcela`+`fecha` únicos, check de temperaturas, `fuente` MANUAL/API, sin anulación ni borrado) + **3 migraciones reversibles** (`seguimiento/0005_clima.py`, `0006_trg_clima_actualizado.py`, `sistema/0002_umbral_helada_c.py`); diseño SQL actualizado (CTE `clima_c` del dataset, índice `ix_clima_fecha`, fila `umbral_helada_c`); **19 triggers** en total; migración verificada desde cero en BD temporal | ✅ Hecha | `backend/seguimiento/models.py`, `migrations/0005`, `0006` · `backend/sistema/` · `DB_sql/01_tablas.sql`, `02_reglas_y_vista.sql`, `03_insert.sql` |
| **F2** | API completa: listado con 10 filtros, detalle, alta, edición, sin `DELETE` (405); `resumen_clima` en el detalle de campaña, bloque `clima` en el detalle de parcela y `umbral_helada_c` en parámetros; permisos `clima.*` por acción, ámbito del Técnico, `registrado_por` oculto al ámbito | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` + `campanias/`, `parcelas/`, `sistema/` · pruebas 138–151, 155 |
| **F3** | HU-84: servicio Open-Meteo (`urllib`, sin clave, `timezone=America/Lima`), acción `consulta-api/` con throttle `clima_consulta` (10/hora), `select_for_update` por día en una sola transacción, 502 en español si cae y el par `confirmar_reemplazo` 400/200 | ✅ Hecha | `servicio_meteorologico.py`, `views.py` · pruebas 152–154 |
| **F4** | Pantallas: **`/clima`** (10 filtros en URL, `Tabla`+`Paginacion`), alta/edición en modal (`ClimaFormulario`, casilla de reemplazo solo para registros API), ficha en modal (`ClimaFicha`), **modal HU-84** (`ClimaConsulta` con informe), secciones **«Clima»** en `ParcelaFicha` y **«Resumen de clima»** en `CampaniaFicha`; entrada «Clima» en el menú | ✅ Hecha | `pages/Climas.jsx`, `ClimaFormulario.jsx`, `ClimaFicha.jsx`, `ClimaConsulta.jsx`, `ParcelaFicha.jsx`, `CampaniaFicha.jsx`, `api/clima.js` · checklist `verificacion_ui_semana10.md` |
| **F5** | Verificación integral: **155 pruebas** (18 nuevas) + `check` en 0 issues + `makemigrations --check` sin cambios + `npm run lint`/`build` en 0 problemas; **smoke E2E 15/15** contra un `runserver` temporal y la BD `sigpa_ga_sm10` con Open-Meteo **real** (borrada al terminar); hallazgo corregido: cuantización a 1 decimal (`ROUND_HALF_UP`) en el adaptador | ✅ Hecha | `seguimiento/tests.py` · `servicio_meteorologico.py` (decisión 11 de `decisiones_semana10.md`) |
| **F6** | Documentación de la semana | ✅ Hecha | `decisiones_semana10.md` (20 decisiones + preguntas K, L y M), `api_clima.md`, `verificacion_ui_semana10.md` |
| **F7** | Cierre: colección de Postman (235 de la Semana 9 + 34 nuevas = **269 obligatorias** + 1 opcional), verificación final y commit semanal único | ✅ Hecha | `docs/coleccion_api_semana10.json` (236–270) — **validada 270/270 (496/496 aserciones)** en la BD temporal `sigpa_ga_coleccion10`, borrada al terminar · `evidencias_capitulo4.md` + `CONTEXTO_PROYECTO.md` §3/§6 · commit único: nombre entregado |

**Cierre (7/7 fases):** 155 pruebas verdes (`manage.py test`;
18 nuevas), `manage.py check` en 0 issues, `makemigrations --check` sin
cambios, `npm run lint` y `npm run build` en 0 problemas, smoke E2E **15/15**,
colección S10 **validada 270/270** (269 obligatorias + 1 opcional,
496/496 aserciones) y documentación en `decisiones_semana10.md` (20
decisiones), `verificacion_ui_semana10.md` y `api_clima.md`.

## Semana 9 — 7/7 fases terminadas

El tema «Recursos e insumos» corresponde al **mapeo HU-67 a HU-75** de la
semana (Sprint 4); se ejecutó **por fases F1–F7** acordadas con el responsable.

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-67** | Listar usos de recursos con filtros (campaña, actividad, recurso, categoría, estado, rango de fechas y búsqueda) y orden por fecha descendente | ✅ Hecha | `GET /api/usos-recursos/` · pruebas 121, 122 · colección 217, 234 |
| **HU-68** | Registrar el recurso usado en una actividad (siembra, fertilización…), ver los usos en la ficha de actividad y **anular en cascada** al anular la actividad (`recursos_anulados` en el resumen) | ✅ Hecha | `POST /api/actividades/{id}/anular/` + sección «Recursos usados» · pruebas 128, 129, 133 · colección 224–227 |
| **HU-69** | Registrar y editar un uso de recurso: campaña y actividad inmutables al editar, cantidad > 0, costo ≥ 0, fecha no futura y dentro del período; la conversión a unidad base la calcula la base | ✅ Hecha | `POST` y `PATCH /api/usos-recursos/{id}/` + `fn_uso_recurso` · pruebas 123–127 · colección 214–221 |
| **HU-70** | Que la unidad admisible dependa del tipo del recurso (masa, volumen, labor, tiempo): unidad de otro tipo → 400; el desplegable de recursos trae `tipo_unidad` | ✅ Hecha | validación de `unidad_id` + `?desplegable=1` · pruebas 123, 124 · colección 212, 213, 218 |
| **HU-71** | Permisos por acción y ámbito: Administrador los 4 `recursos.*`; Técnico `ver/crear/editar` (anular → 403) solo en sus productores; Coordinador solo `ver` | ✅ Hecha | `PermisosUsoRecurso` + `SoloSusProductores` · pruebas 134–137 · colección 206, 234, 235 |
| **HU-72** | Anular un uso de recurso con motivo obligatorio (borrado lógico: `ANULADA`, sin `DELETE` → 405) | ✅ Hecha | `POST …/anular/` · prueba 130 · colección 221, 222 |
| **HU-73** | Reactivar un uso de recurso (limpia el motivo y devuelve el estado a activo) | ✅ Hecha | `POST …/reactivar/` · prueba 131 · colección 223 |
| **HU-74** | Resumen de recursos en la ficha de campaña (`resumen_recursos`: suma por categoría, excluyendo anulados) y bloque en `CampaniaFicha` | ✅ Hecha | `campanias/serializers.py` · pruebas 132, 135 · colección 228, 233 |
| **HU-75** | Que las unidades con usos no se puedan convertir ni desactivar (factor/tipo protegidos) y que la campaña de un uso no se pueda cambiar al editar | ✅ Hecha | protección en `catalogos/` + edición inmutable · pruebas 136 · colección 219, 229, 232 |

> **HU-48 (completada):** la anulación de una actividad ahora arrastra en
> cascada sus usos de recursos activos (decisión 4 de `decisiones_semana9.md`).

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: tabla **`uso_recursos`** en `seguimiento/` (13 columnas, `anulada`+`motivo_anulacion`, checks) + **2 migraciones reversibles** (`0003_uso_recursos.py`, `0004_funciones_y_triggers_uso_recursos.py` con `fn_uso_recurso`, `fn_validar_fecha_uso` y 3 triggers); diseño SQL actualizado (anuladas fuera del dataset); **18 triggers** en total; migración verificada desde cero en BD temporal | ✅ Hecha | `backend/seguimiento/models.py`, `migrations/0003`, `0004` · `DB_sql/01_tablas.sql`, `02_reglas_y_vista.sql` |
| **F2** | API completa: listado con filtros, detalle, alta, edición, `anular/` y `reactivar/` (sin `DELETE` → 405); cascada atómica en `ActividadViewSet.anular`; `resumen_recursos` en el detalle de campaña; protección de unidades con usos; permisos `recursos.*` por acción, ámbito del Técnico (404), `registrado_por` oculto al ámbito | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` + `campanias/` y `catalogos/` · pruebas 121–137 · colección 206–235 |
| **F3** | Colección de Postman: 205 de la Semana 8 + 30 nuevas (206–235) | ✅ Hecha | `docs/coleccion_api_semana9.json` — **validada 235/235 (431/431 aserciones)** |
| **F4** | Pantallas: **`/recursos`** (filtros en URL, `Tabla`+`Paginacion`), alta/edición en modal (`RecursoFormulario`), ficha en modal (`RecursoFicha` con anular/reactivar), sección **«Recursos usados»** en `ActividadFicha` y sección **«Resumen de recursos»** en `CampaniaFicha`; entrada «Recursos» en el menú | ✅ Hecha | `pages/Recursos.jsx`, `RecursoFormulario.jsx`, `RecursoFicha.jsx`, `ActividadFicha.jsx`, `CampaniaFicha.jsx`, `api/usosRecursos.js` · checklist `verificacion_ui_semana9.md` |
| **F5** | Verificación de pantallas | ✅ Hecha | `docs/verificacion_ui_semana9.md` (Chrome 1366×768, Edge 1024×768, Móvil 360×780) |
| **F6** | Documentación de la semana | ✅ Hecha | `decisiones_semana9.md` (20 decisiones + pregunta L), `api_recursos.md`, `verificacion_ui_semana9.md` |
| **F7** | Cierre y verificación | ✅ Hecha | este tablero + `evidencias_capitulo4.md` + `CONTEXTO_PROYECTO.md` §3/§5/§6 |

**Cierre de la semana:** 137 pruebas verdes (`manage.py test`; 17 nuevas),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de **235 peticiones validada 235/235 (431/431 aserciones)** contra el servidor
(estados y textos clave), `npm run lint` y `npm run build` en 0 problemas, y
documentación en `decisiones_semana9.md` (20 decisiones),
`verificacion_ui_semana9.md`, `api_recursos.md` y
`coleccion_api_semana9.json`.

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

## Siguiente (Semana 11, 14–20 dic)

| Tema | Nota |
|---|---|
| Incidencias y línea de tiempo | **Sprint 6** del roadmap (`CONTEXTO_PROYECTO.md` §13); empieza el siguiente ciclo (el «Clima» queda cerrado salvo hallazgos de la verificación en navegador) |
| Preguntas abiertas A, B, D, F, G, H, I, J, K, L y M | Lista de ubicaciones real, enmascarado, botón «usar mi ubicación», fechas vs período, bloqueo de desactivación, fechas futuras en actividades, unidad de densidad, producción bruta/neta, umbrales del sistema, costo de recursos y fuente meteorológica |
| Checklists de UI de las Semanas 4 a 10 | Ejecutar en navegador (Chrome/Edge/móvil) y anotar los resultados en cada documento |
| Demo 1 (cierre del Sprint 4) | Primera fila del dataset con producción y recursos; las predicciones quedan para los Sprints 13–14 (`fn_produccion_post` completa) |

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
11. **¿Costo de los recursos: registro o cálculo?** (Semana 9, pregunta L):
     rige que `costo` se **registra por cada uso** y no se agrega en ningún
     resumen (decisión 19 de `decisiones_semana9.md`); si el responsable quiere
     un costo total de campaña o por hectárea se añade al `resumen_recursos` —
     **CONFIRMAR**.
12. **¿Open-Meteo como fuente del clima?** (Semana 10, pregunta M — la plan
     la citaba como «L»): implementado con `archive-api` (sin clave,
     decisión 19 de `decisiones_semana10.md`); el adaptador es un solo archivo
     (`servicio_meteorologico.py`) por si se prefiere otra fuente (p. ej. NASA
     POWER) — **CONFIRMAR**.
