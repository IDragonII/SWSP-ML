# Evidencias para el Capítulo IV de la tesis — checklist

> Qué artefacto del repositorio respalda cada sección del Capítulo IV
> (Diseño e implementación del sistema), cómo se regeneró y qué **sigue
> pendiente**. Se actualiza al cierre de cada semana.
> **Estado: Semana 8 completada — 120 pruebas verdes.**

Leyenda: `[x]` disponible en el repositorio · `[ ]` pendiente.

## 4.3.2 Diagrama entidad-relación

- [ ] **Diagrama ER** de las 32 tablas (fuente disponible: `DB_sql/01_tablas.sql`
  y los `Meta.db_table`/`related_name` de los modelos Django).
- [x] Lista y descripción de las 32 tablas agrupadas por módulo →
  `CONTEXTO_PROYECTO.md` §5.
- Nota: hasta la Semana 8 existen **22 tablas** en la BD real (4 de usuarios +
  4 de ubicación/productores + `parcelas` y `asignaciones_tecnico` + las
  **8 de catálogos** + `campanias` + `actividades` + **`producciones`** y
  **`parametros_sistema`**); el diagrama completo se dibuja con el diseño
  completo.

## 4.3.3 Modelo lógico

- [ ] **Modelo lógico** (entidades, atributos y cardinalidades) pendiente de
  levantar; equivalencia comprobada columna a columna en las comparaciones
  (4.3.4) para las 8 tablas ya creadas.

## 4.3.4 Modelo físico (SQL) y su implementación

- [x] **Diseño físico de referencia:** `DB_sql/01_tablas.sql`,
  `02_reglas_y_vista.sql`, `03_insert.sql` (32 tablas, 13 funciones,
  24 triggers, la vista del dataset). ⚠️ `DB_sql/` está **ignorado en Git**
  por decisión documentada (es documentación, no código desplegable):
  mantener una **copia fuera del repositorio** antes de cualquier entrega.
- [x] **Comparación diseño vs implementación — usuarios (Sprint 1):**
  `docs/comparacion_sprint1.md` (4 tablas columna por columna, 5 diferencias
  justificadas; verificado con `sqlmigrate` + `information_schema`).
- [x] **Comparación diseño vs implementación — ubicación y productores
  (Semana 3):** `docs/comparacion_semana3.md` (4 tablas + 2 triggers +
  5 índices del diseño; verificado con `pg_constraint`, `pg_indexes` y
  `pg_trigger` sobre la BD real).
- [x] **Comparación diseño vs implementación — parcelas y asignaciones
  (Semana 4):** `docs/comparacion_semana4.md` (2 tablas columna por columna +
  secuencia, 2 funciones y 3 triggers; verificado con `pg_constraint`,
  `pg_indexes`, `pg_sequences` y `pg_trigger` sobre la BD real).
- [x] **Comparación diseño vs implementación — catálogos (Semana 5):**
  `docs/comparacion_semana5.md` (8 tablas, **37/37 columnas, 28/28
  restricciones y 44/44 datos**; verificado con `pg_constraint`/`pg_indexes`
  sobre la BD real, más las dos pasadas idempotentes del comando).
- [x] **Comparación diseño vs implementación — campañas (Semana 6):**
  `docs/comparacion_semana6.md` (**14/14 columnas, 9/9 restricciones,
  6/6 índices** del diseño + 1 extra documentado, **2/2 triggers** y
  `fn_validar_campania` idéntica salvo el alcance parcial del Sprint 3;
  verificado con `sqlmigrate`, `pg_constraint`, `pg_indexes` y `pg_trigger`).
- [x] **Comparación diseño vs implementación — actividades (Semana 7):**
  `docs/comparacion_semana7.md` (**15/15 columnas** — incluidas `anulada` y
  `motivo_anulacion`, añadidas al diseño —, **10/10 restricciones, 2/2
  índices sin extras, 3/3 triggers** y las 2 funciones literales
  `fn_validar_fecha_campania` y `fn_actividad_siembra` v2; verificado con
  `sqlmigrate` e introspección en vivo sobre la BD real).
- [x] **Comparación diseño vs implementación — producción y parámetros
  (Semana 8):** `docs/comparacion_semana8.md` (**17 + 5 columnas, 11
  restricciones, 0 índices extra** de Django, **15 triggers** y las funciones
  `fn_validar_produccion`, `fn_produccion_post` parcial y
  `fn_validar_campania` v3; verificado con `sqlmigrate` e introspección en
  vivo sobre la BD real).
- [x] **Migraciones propias:** `backend/usuarios/migrations/` (0001–0003),
  `backend/productores/migrations/` (0001–0004, las dos últimas reversibles),
  `backend/catalogos/migrations/` (0001–0002; `0002` reversible sin borrar lo
  referenciado), `backend/campanias/migrations/` (0001–0003, todas
  reversibles), `backend/seguimiento/migrations/` (0001–0002, ambas
  reversibles), `backend/produccion/migrations/` (0001–0002, reversibles) y
  `backend/sistema/migrations/` (0001, reversible). La creación de la BD de
  pruebas en cada `manage.py test` aplica las **47 migraciones** desde cero
  (incluidas las de terceros).

## Reglas de negocio y triggers

- [x] Catálogo de las 13 funciones y 24 triggers del diseño →
  `CONTEXTO_PROYECTO.md` §6.
- [x] Triggers implementados hasta ahora (15 de 24): `trg_roles_proteger`,
  `trg_productores_actualizado`, `trg_productores_codigo`,
  `trg_parcelas_actualizado`, `trg_parcelas_codigo`,
  `trg_asignaciones_validar`, `trg_campanias_validar`,
  `trg_campanias_actualizado`, `trg_actividades_actualizado`,
  `trg_actividades_fecha`, `trg_actividades_siembra`,
  `trg_producciones_validar`, `trg_producciones_post`,
  `trg_producciones_actualizado` y `trg_parametros_sistema_actualizado` —
  texto literal, verificados en `comparacion_sprint1.md` §4,
  `comparacion_semana3.md` §5, `comparacion_semana4.md` §5,
  `comparacion_semana6.md` §4, `comparacion_semana7.md` §4 y
  `comparacion_semana8.md`.
- [x] **Migración desde cero como evidencia:** base vacía `sigpa_ga_migracion`
  → `manage.py migrate` aplicó 27 migraciones; seeds 55 permisos / 3 roles /
  101 asignaciones; 4 tablas nuevas; prueba funcional en SQL crudo generó
  `PROD-0001` y actualizó `actualizado_en` en otra transacción (Semana 3).
  Reproducible: crear BD, `DB_NAME=<nombre> python manage.py migrate`, borrar.
  Desde la Semana 4, la BD de pruebas que crea cada `manage.py test` vuelve a
  aplicar todas las migraciones desde cero en cada ejecución (hoy 47). En las
  Semanas 7 y 8 además se migraron BD temporales completas de validación de
  las colecciones (creadas, migradas y **borradas al terminar**).

## Requerimientos funcionales verificados (RF/RN)

- [x] Matriz de decisiones por semana → `docs/decisiones_seguridad.md`
  (Semana 2), `docs/decisiones_semana3.md` (Semana 3, 7 decisiones con sus
  preguntas abiertas), `docs/decisiones_semana4.md` (Semana 4, 19
  decisiones, incluidas las de parcelas, asignaciones y CRUD en modales),
  `docs/decisiones_semana5.md` (Semana 5, 17 decisiones: catálogos, datos
  CONFIRMAR por comando y pantalla con pestañas), `docs/decisiones_semana6.md`
  (Semana 6, 18 decisiones: campañas, con las preguntas abiertas F y G
  pendientes de confirmación), `docs/decisiones_semana7.md` (Semana 7, 17
  decisiones: actividades, con las preguntas abiertas H e I pendientes) y
  `docs/decisiones_semana8.md` (Semana 8, 20 decisiones: producción, cierre
  y parámetros, con las preguntas abiertas J y K pendientes).
- [x] RN «el DNI debe ser único y tener 8 dígitos» → pruebas 23 y 24.
- [x] RN «no se eliminan físicamente; se desactivan» → sin `DELETE` (405),
  prueba 28, FK `PROTECT`; en la Semana 4 el mismo patrón para parcelas
  (prueba 41) y asignaciones (prueba 48); en la Semana 5 para los **8
  catálogos** (colección 073) y `POST` de tipos de actividad → 405.
- [x] RN de catálogos: unidad base no se crea/convierte/desactiva, Siembra y
  Cosecha protegidas, etapas sin estado y unicidad normalizada en la API →
  pruebas 54–67 · colección 064, 065, 069, 076, 077, 081, 083.
- [x] RN de campañas: una campaña activa por parcela y período (la cancelada
  libera la parcela), un cultivo por parcela y período, variedad del cultivo
  elegido, fechas dentro del período, superficie ≤ superficie de la parcela y
  sin campañas en parcelas/productores inactivos → pruebas 68–74 ·
  colección 100–105.
- [x] RN «el ciclo de la campaña se gestiona por estados»: iniciar y cancelar
  con motivo, edición condicionada al estado (campos bloqueados al iniciar) y
  permisos `campanias.*` por acción → pruebas 75–77 y 83 · colección 106–109,
  122–123.
- [x] RN de bloqueos HU-45/HU-46 (**decisión pendiente de confirmar con el
  responsable**): no se desactiva un productor ni una parcela con campañas
  activas → pruebas 78 y 79 · colección 111–112.
- [x] RN de actividades: anulación con motivo obligatorio como borrado lógico
  (sin `DELETE` → 405; la campaña nunca vuelve a `PLANIFICADA`), fecha no
  futura según hora de Lima (**pregunta H**), densidad solo en siembras y con
  valor+unidad juntos, campaña y tipo inmodificables al editar y efecto
  siembra (`fn_actividad_siembra` v2: `EN_PRODUCCION` + `fecha_siembra`
  recalculada al anular/reactivar) → pruebas 87–96 · colección 134–146,
  154–157.
- [x] RN de ámbito y permisos de actividades: el Técnico solo ve y registra
  actividades de sus productores asignados (campaña ajena → mismo mensaje que
  si no existiera; actividad ajena → 404), `registrado_por` oculto a los
  roles con `limita_a_asignados`, Administrador con los 4 permisos,
  Técnico sin `desactivar` (anular → 403) y Coordinador solo `ver` →
  pruebas 97–102 · colección 153, 155, 158–159.
- [x] RN de producción: **una sola producción por campaña** (`OneToOne`,
  sin `DELETE` → 405 y «deshacer cosecha» como única excepción), unidad de
  **masa activa**, superficie cosechada ≤ sembrada, fecha ≥ siembra/inicio,
  kg y rendimiento **calculados por la base** (`fn_validar_produccion`) y
  campaña pasada a `COSECHADA` (`fn_produccion_post` parcial) → pruebas
  103–111 · colección 171–181, 185–186.
- [x] RN de revisión por umbrales (**pregunta K: CONFIRMAR**): rendimiento
  fuera de `[100, 5000]` kg/ha marca `requiere_revision` con motivo
  «Rendimiento atípico: …»; cambiar un umbral **no reevalúa** lo ya guardado;
  `revisar/` exige nota e inclusión booleana y conserva el motivo original →
  pruebas 107, 112, 113, 116 · colección 160–167, 193–195.
- [x] RN de deshacer y cerrar: `deshacer-cosecha/` con motivo borra la fila y
  devuelve la campaña a `EN_PRODUCCION`; `cerrar/` (`COSECHADA → CERRADA`)
  exige producción registrada y **sin revisión pendiente**, es irreversible y
  la campaña cerrada no admite actividades ni cambios en la producción →
  pruebas 114, 115, 117 · colección 183–184, 194, 196–197.
- [x] RF «registrar un productor con código automático (PROD-0001)» →
  triggers + pruebas 21 y 22.
- [x] RF «registrar parcelas con código automático (P-001)» y sus
  validaciones → triggers + pruebas 38, 39, 40 y 44.
- [x] RF «buscar y filtrar por código, nombre, DNI, comunidad, distrito y
  estado» → pruebas 31 y 32; parcelas → prueba 42.
- [x] RF «el técnico solo verá los productores que tenga asignados» →
  pruebas 50 y 51 (filtros, 404 del ámbito y pérdida de acceso al
  desactivar la asignación).
- [x] RN «404 en español y el permiso manda antes que el ámbito (403 > 404)»
  → pruebas 50 y 53 · colección 016, 044.
- [x] RF «administración de provincias, distritos y comunidades» →
  pruebas 26 y 27 + panel admin.
- [x] Permisos por rol en la API (401/403, coordinador solo lectura) →
  pruebas 29 y 30; parcelas 43; asignaciones 47; campañas 80 y 81 (ámbito del
  Técnico → 404, Coordinador solo lee); actividades 98 y 102; producción 118
  (Técnico sin `desactivar`, Coordinador sin `crear`) y parámetros
  (`parametros.gestionar` solo Administrador); colección 033–036, 040,
  117–127, 155, 158–159, 166–167, 198–205.
- [x] Protección de datos personales (enmascarado por rol, Ley N.° 29733) →
  prueba 35 · **regla pendiente de confirmación** (decisión 4 de la Semana 3).

## API y pruebas

- [x] Contrato de la API de sesión → `docs/api_autenticacion.md`.
- [x] Contrato de la API de ubicación y productores →
  `docs/api_ubicacion_productores.md` (errores con cuerpos verificados;
  404 en español desde la Semana 4, decisión 11).
- [x] Contrato de la API de catálogos → `docs/api_catalogos.md` (los 8
  recursos, mensajes 400 exactos, reordenado de etapas y desplegables).
- [x] Contrato de la API de campañas → `docs/api_campanias.md` (ciclo de vida,
  mensajes 400 exactos con las dos formas de cuerpo —lista y string—, filtros,
  bloqueos HU-45/46 y la sección de la colección).
- [x] Contrato de la API de actividades → `docs/api_actividades.md` (los 6
  endpoints, permisos por rol, filtros, cuerpos exactos, efecto siembra,
  guion de la colección 128–159 y curl).
- [x] Contrato de la API de producción y parámetros →
  `docs/api_produccion.md` (producciones con `revisar/` y
  `deshacer-cosecha/`, parámetros por clave, `cerrar/` en campañas, filtros,
  cuerpos exactos de los dos formatos de error, guion de la colección
  160–205 y curl).
- [x] **Colecciones ejecutables** → `docs/coleccion_api_semana3.json`
  (36 peticiones), `docs/coleccion_api_semana4.json`
  (**48 peticiones** con `pm.test`, validadas **48/48** contra el servidor),
  `docs/coleccion_api_semana5.json` (**93 peticiones** = 48 + 45 de catálogos,
  validadas **93/93**), `docs/coleccion_api_semana6.json`
  (**127 peticiones** = 93 + 34 de campañas, validadas **127/127** con
  **221/221 aserciones**), `docs/coleccion_api_semana7.json`
  (**159 peticiones** = 127 + 32 de actividades, validadas **159/159** con
  **286/286 aserciones**) y `docs/coleccion_api_semana8.json`
  (**205 peticiones** = 159 + 46 de parámetros y producción, validadas
  **205/205** con **374/374 aserciones**; sin secretos: las claves se toman
  de `.credenciales`).
- [x] **Suite de pruebas:** `python manage.py test` → **120 verdes**
  (8 Semana 1 + 12 Semana 2 + 17 Semana 3 + 16 Semana 4 + 14 Semana 5 +
  19 Semana 6 + 16 Semana 7 + 18 Semana 8); `manage.py check` en 0 issues;
  `makemigrations --check` sin cambios. Comandos en `comparacion_sprint1.md`
  §6, `comparacion_semana3.md` §6, `comparacion_semana4.md` §6,
  `comparacion_semana5.md` §6, `comparacion_semana6.md` §7,
  `comparacion_semana7.md` y `comparacion_semana8.md` («Cómo se verificó»).
- [x] **Pantallas React:** `npm run lint` y `npm run build` en 0 problemas;
  checklist de ejecución manual en `docs/verificacion_ui_semana4.md`,
  `docs/verificacion_ui_semana5.md`, `docs/verificacion_ui_semana6.md`,
  `docs/verificacion_ui_semana7.md` y `docs/verificacion_ui_semana8.md`
  (decisiones 15/16/17/19, **pendientes de ejecutar por el responsable**).
  De la Semana 5: pantalla `/catalogos` con CRUD en modales; de la Semana 6:
  pantalla `/campanias` con alta/edición en modal y las fichas de
  productor/parcela con su sección de campañas; de la Semana 7: pantalla
  `/actividades`, `ActividadFicha` (anular/reactivar) y `CampaniaFicha` con
  bloque de actividades; de la Semana 8: pantalla **`/parametros`**,
  `ProduccionFormulario` y `ProduccionFicha` (revisar/deshacer),
  `CampaniaFicha` con bloque «Producción» + cerrar y columna «Producción» en
  `ProductorFicha`.

## Usuarios, roles y permisos (evidencia funcional)

- [x] Configuración inicial de los 3 roles y 55 permisos (101 asignaciones)
  como migración idempotente → `usuarios/0002_datos_iniciales`.
- [x] Panel de administración (roles protegidos, permisos con autocompletado,
  acción «Desbloquear acceso», catálogos de ubicación y productores con
  filtros) → `backend/usuarios/admin.py`, `backend/productores/admin.py`.
  Desde la Semana 5, los **8 catálogos de campañas** y desde la Semana 6 la
  tabla **`campanias`** (con `estado`/`fecha_siembra` en solo lectura) también
  están registrados con listado, filtros y búsqueda → `backend/catalogos/admin.py`,
  `backend/campanias/admin.py`. Desde la Semana 7 la tabla **`actividades`**
  también está registrada (consulta y trazabilidad; la anulación es solo vía
  API) → `backend/seguimiento/admin.py`. Desde la Semana 8 las tablas
  **`producciones`** (los campos calculados se ven, no se tocan) y
  **`parametros_sistema`** (solo valor: sin altas ni bajas) →
  `backend/produccion/admin.py`, `backend/sistema/admin.py`.
- [ ] **Capturas de pantalla** del panel y de la API en Postman (para el
  documento): ejecutar la colección y capturar respuestas 201/400/403/405.

## Bitácora de trabajo (Scrum)

- [x] Tablero con HU-15..HU-22 → `docs/tablero.md` (Semana 3), HU-23..HU-28
  con estado y evidencias (Semana 4), las **8 fases F1–F8** de la Semana 5,
  las **7 fases F1–F7** de la Semana 6 (HU-38..HU-46), las **7 fases F1–F7**
  de la Semana 7 (HU-47..HU-55) y las **7 fases F1–F7** de la Semana 8
  (HU-56..HU-62 del mapeo propuesto; HU-01..HU-14 resumidos ahí mismo: textos
  originales de HU no están en el repositorio: mapeo propuesto).
- [x] Calendario y orden de sprints → `CONTEXTO_PROYECTO.md` §13.
- [x] Contexto completo del proyecto (para que el responsable pueda defender
  cada decisión) → `CONTEXTO_PROYECTO.md` completo.

## Pendientes globales (para entregas posteriores)

- [ ] Diagramas ER y modelo lógico (4.3.2 / 4.3.3).
- [ ] Capturas de pantalla de pantallas y endpoints (incluye login de React).
- [ ] Ejecutar los checklists de UI de las Semanas 4 a 8
  (`docs/verificacion_ui_semana4.md`, `docs/verificacion_ui_semana5.md`,
  `docs/verificacion_ui_semana6.md`, `docs/verificacion_ui_semana7.md` y
  `docs/verificacion_ui_semana8.md`) en Chrome/Edge/móvil y anotar los
  resultados.
- [ ] Pantallas de los módulos en React (hoy: login, 403, 404, productores,
  parcelas, **catálogos** con CRUD en modales, **campañas**,
  **actividades** con `CampaniaFicha` y **parámetros** con producción en las
  fichas; la entrada «Producción» del menú sigue siendo placeholder: faltan
  su pantalla y los demás módulos).
- [ ] Manual de usuario y evidencia de la demo.
- [ ] Copia de `DB_sql/` fuera del repositorio antes de cualquier entrega
  (está ignorado en Git).
