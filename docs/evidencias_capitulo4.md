# Evidencias para el Capítulo IV de la tesis — checklist

> Qué artefacto del repositorio respalda cada sección del Capítulo IV
> (Diseño e implementación del sistema), cómo se regeneró y qué **sigue
> pendiente**. Se actualiza al cierre de cada semana.
> **Estado: Semana 15 (apertura del Sprint 8) — F1..F7 cerradas (7/7)
> — 262 pruebas verdes; colección de la Semana 15 validada en F7
> (488/488: 459–488); sin commitear (el commit único lo hace el
> responsable).**

Leyenda: `[x]` disponible en el repositorio · `[ ]` pendiente.

## 4.3.2 Diagrama entidad-relación

- [ ] **Diagrama ER** de las 33 tablas (fuente disponible: `DB_sql/01_tablas.sql`
  y los `Meta.db_table`/`related_name` de los modelos Django).
- [x] Lista y descripción de las 33 tablas agrupadas por módulo →
  `CONTEXTO_PROYECTO.md` §5.
- Nota: hasta la Semana 15 existen **28 tablas** en la BD real (4 de usuarios +
  4 de ubicación/productores + `parcelas` y `asignaciones_tecnico` + las
  **8 de catálogos** + `campanias` + `actividades` + `uso_recursos` +
  `producciones` y `parametros_sistema` + `clima` + **`incidencias`** +
  **`seguimiento_etapas`** + **`auditoria`** + **`alertas`**); el
  diagrama completo se dibuja con el diseño completo.

## 4.3.3 Modelo lógico

- [ ] **Modelo lógico** (entidades, atributos y cardinalidades) pendiente de
  levantar; equivalencia comprobada columna a columna en las comparaciones
  (4.3.4) para todas las tablas ya creadas.

## 4.3.4 Modelo físico (SQL) y su implementación

- [x] **Diseño físico de referencia:** `DB_sql/01_tablas.sql`,
  `02_reglas_y_vista.sql`, `03_insert.sql` (33 tablas, 13 funciones,
  25 triggers, la vista del dataset). ⚠️ `DB_sql/` está **ignorado en Git**
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
- [x] **Comparación diseño vs implementación — usos de recursos (Semana 9):**
  `docs/decisiones_semana9.md` §2 (decisión 8: **13 columnas** de `uso_recursos`
  + `anulada`/`motivo_anulacion`, checks, y **3 triggers** `trg_uso_recursos_base`,
  `trg_uso_recursos_fecha`, `trg_uso_recursos_actualizado` con `fn_uso_recurso`
  y `fn_validar_fecha_uso`); verificado con `sqlmigrate` e introspección en
  vivo sobre la BD real (la Semana 9 no genera documento de comparación aparte).
- [x] **Comparación diseño vs implementación — clima (Semana 10):**
  `docs/decisiones_semana10.md` §2 (decisiones 8–10: **15 columnas** de `clima`,
  `uq_clima_parcela_fecha` + `ck_clima_temp`, índice `ix_clima_fecha` y el
  trigger **`trg_clima_actualizado`** con `fn_set_actualizado_en`, más la quinta
  clave `umbral_helada_c` en `parametros_sistema` y la CTE `clima_c` del
  dataset en `02_reglas_y_vista.sql`, decisión 15); verificado con `sqlmigrate`
  e introspección en vivo sobre la BD real y con el smoke E2E (la Semana 10 no
  genera documento de comparación aparte).
- [x] **Comparación diseño vs implementación — incidencias (Semana 11):**
  `docs/comparacion_semana11.md` (**14/14 columnas** — incluidas `anulada` y
  `motivo_anulacion` con su CHECK —, **8/8 restricciones, 0 índices extra** de
  Django, **3/3 triggers** `trg_incidencias_actualizado`,
  `trg_incidencias_fecha` y `trg_incidencias_superficie` con la función
  `fn_validar_incidencia` literal y la CTE `inc_c` del dataset; sin
  `COMMENT ON TABLE` → documentado); verificado con `sqlmigrate` e
   introspección en vivo sobre la BD real (el diseño local `DB_sql/` está
   actualizado en los 3 archivos).
- [x] **Comparación diseño vs implementación — seguimiento_etapas (Semana 12):**
   `docs/cierre_semana12.md` §1 (Opción A: sin documento de comparación
   aparte): **14 columnas** (las 13 del diseño), `uq_seguimiento_etapa` y
   `ck_seguimiento_fechas` con su índice, **2/2 triggers**
   `trg_seguimiento_etapa`/`trg_seguimiento_fecha` y `fn_validar_etapa`
   literal; verificado con `check`, `makemigrations --check`, las pruebas
   120/137/172 (recuento 24) y F5 (diseño = migraciones = pruebas).
- [x] **Comparación diseño vs implementación — auditoría y
  `debe_cambiar_clave` (Semana 13):** `docs/decisiones_semana13.md` §1.2
  (diseño = migraciones): tabla `auditoria` (**11 columnas**: `usuario`,
  `accion` con CHECK de 15 valores en `VARCHAR(20)`, `modulo`, `tabla`,
  `registro_id`, `detalle` JSON, `ip`, `fecha`…), **4 índices**
  (`ix_auditoria_usuario/modulo/fecha` y `ix_auditoria_tabla_registro`),
  trigger **`trg_auditoria_inmutable`** (25.º) con `fn_auditoria_inmutable`
  literal y columna `debe_cambiar_clave` en `usuarios`; verificado con
   `check`, `makemigrations --check`, `sqlmigrate` (las 3 migraciones) y
   las pruebas 198–220.
- [x] **Comparación diseño vs implementación — alertas (Semana 15):**
  `docs/decisiones_semana15.md` §1.1 (decisión 1) y §1.2 (decisión 14)
  (diseño = migración): tabla **`alertas`** con sus **11 columnas** (incluido
  `id`; `incidencia_id` y `nota_atencion` añadidas al diseño en F1),
  CHECKs con nombre (`ck_alerta_atendida`, `ck_alerta_nota`,
  `ck_alerta_incidencia` y `ck_alerta_tipo`), **2 restricciones únicas**
  (`uq_alerta_incidencia`; `uq_alerta_pendiente_campania_tipo` parcial:
  pendientes de SIN_ACTIVIDAD/RENDIMIENTO_BAJO por campaña+tipo) y **2
  índices** (`ix_alertas_pendientes` parcial y `ix_alertas_campania`), y
  **0 triggers nuevos**; verificado con `check`, `makemigrations --check`
  y `sqlmigrate` (las 21 pruebas de la semana, 242–262).
- [x] **Migraciones propias:** `backend/usuarios/migrations/` (0001–**0004**),
  `backend/productores/migrations/` (0001–0004, las dos últimas reversibles),
  `backend/catalogos/migrations/` (0001–0002; `0002` reversible sin borrar lo
  referenciado), `backend/campanias/migrations/` (0001–0003, todas
  reversibles), `backend/seguimiento/migrations/` (0001–**0010**, todas
  reversibles), `backend/produccion/migrations/` (0001–0002, reversibles),
  `backend/sistema/migrations/` (0001–**0002**, reversibles),
  `backend/auditoria/migrations/` (**0001–0002**, reversibles) y
  `backend/alertas/migrations/` (**0001**, la Semana 15). La creación de la
  BD de pruebas en cada `manage.py test` aplica las **60 migraciones** desde
  cero (30 propias; verificado con
  `manage.py showmigrations --plan | Measure-Object -Line`).

## Reglas de negocio y triggers

- [x] Catálogo de las 13 funciones y 25 triggers del diseño →
  `CONTEXTO_PROYECTO.md` §6.
- [x] Triggers implementados hasta ahora (**25 de 25**): `trg_roles_proteger`,
  `trg_productores_actualizado`, `trg_productores_codigo`,
  `trg_parcelas_actualizado`, `trg_parcelas_codigo`,
  `trg_asignaciones_validar`, `trg_campanias_validar`,
  `trg_campanias_actualizado`, `trg_actividades_actualizado`,
  `trg_actividades_fecha`, `trg_actividades_siembra`,
  `trg_producciones_validar`, `trg_producciones_post`,
  `trg_producciones_actualizado`, `trg_parametros_sistema_actualizado`,
  `trg_uso_recursos_base`, `trg_uso_recursos_fecha`,
  `trg_uso_recursos_actualizado`, `trg_clima_actualizado`,
  **`trg_incidencias_actualizado`**, **`trg_incidencias_fecha`**,
  **`trg_incidencias_superficie`**, los de la Semana 12
  **`trg_seguimiento_etapa`** y **`trg_seguimiento_fecha`**, y el de la
  Semana 13 **`trg_auditoria_inmutable`** — texto literal, verificados en
  `comparacion_sprint1.md` §4, `comparacion_semana3.md` §5,
  `comparacion_semana4.md` §5, `comparacion_semana6.md` §4,
  `comparacion_semana7.md` §4, `comparacion_semana8.md`,
  `decisiones_semana9.md` §2, `decisiones_semana10.md` §2,
   `comparacion_semana11.md`, `cierre_semana12.md` §1 (F5: diseño =
  migraciones = pruebas 120/137/172, que pasaron a contar 24),
  `decisiones_semana13.md` §1.2 (pruebas 198–210: UPDATE/DELETE sobre
  `auditoria` responden la excepción del trigger) y
  `decisiones_semana15.md` (pruebas 242–262: **la Semana 15 no añade
  triggers** — se cubre por la aplicación y sus ganchos `on_commit`).
- [x] **Migración desde cero como evidencia:** base vacía `sigpa_ga_migracion`
  → `manage.py migrate` aplicó 27 migraciones; seeds 55 permisos / 3 roles /
  101 asignaciones; 4 tablas nuevas; prueba funcional en SQL crudo generó
  `PROD-0001` y actualizó `actualizado_en` en otra transacción (Semana 3).
  Reproducible: crear BD, `DB_NAME=<nombre> python manage.py migrate`, borrar.
  Desde la Semana 4, la BD de pruebas que crea cada `manage.py test` vuelve a
  aplicar todas las migraciones desde cero en cada ejecución (hoy 60). En las
  Semanas 7 a 12 además se migraron BD temporales completas de validación de
   las colecciones y del smoke (creadas, migradas y **borradas al terminar**;
   Semanas 7 a 13).

## Requerimientos funcionales verificados (RF/RN)

- [x] Matriz de decisiones por semana → `docs/decisiones_seguridad.md`
  (Semana 2), `docs/decisiones_semana3.md` (Semana 3, 7 decisiones con sus
  preguntas abiertas), `docs/decisiones_semana4.md` (Semana 4, 19
  decisiones, incluidas las de parcelas, asignaciones y CRUD en modales),
  `docs/decisiones_semana5.md` (Semana 5, 17 decisiones: catálogos, datos
  CONFIRMAR por comando y pantalla con pestañas), `docs/decisiones_semana6.md`
  (Semana 6, 18 decisiones: campañas, con las preguntas abiertas F y G
  pendientes de confirmación), `docs/decisiones_semana7.md` (Semana 7, 17
  decisiones: actividades, con las preguntas abiertas H e I pendientes),
  `docs/decisiones_semana8.md` (Semana 8, 20 decisiones: producción, cierre
  y parámetros, con las preguntas abiertas J y K pendientes),
  `docs/decisiones_semana9.md` (Semana 9, 20 decisiones: recursos e insumos,
  con la pregunta abierta L pendiente) y
  `docs/decisiones_semana10.md` (Semana 10, 20 decisiones: clima y HU-84, con
  las preguntas abiertas K actualizada — `umbral_helada_c` —, L y la nueva M
  —fuente meteorológica— pendientes) y
   `docs/decisiones_semana11.md` (Semana 11, 20 decisiones: incidencias y
   anulación sin `DELETE`, con la nueva pregunta abierta N —criterio de
   severidad— pendiente) y, en la Semana 12 (Opción A), el documento único
   `docs/cierre_semana12.md` (23 decisiones: línea de tiempo y usuarios, con
   las nuevas preguntas abiertas O —relajar coherencia de etapas— y
   P —restablecer la propia clave—), y en la Semana 13 (vuelta a docs
   separados) `docs/decisiones_semana13.md` (21 decisiones: auditoría y
   cambio de contraseña, con la pregunta P **cerrada** y las nuevas Q
   —auditar lecturas—, R —purgado— y S —XFF tras proxy—); la **Semana 14 no tiene documento de decisiones** (F6 cancelada) y, en la Semana 15, `docs/decisiones_semana15.md` (28 filas: alertas y productores en riesgo, con **RF-63, RF-64, RF-65** y **RF-15** verificados leyendo `requerimientos.tex` **sin modificarlo**, la decisión de que `RENDIMIENTO_BAJO` no se genera hasta el modelo de regresión, el hallazgo del 429 de «Evaluar ahora» y la nueva pregunta **T** —`limita_a_asignados` con usuarios— con su nota de letras).
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
- [x] RN de recursos e insumos: **la categoría del recurso fija el tipo de
  unidad** (masa, volumen, labor o tiempo; unidad de otro tipo → 400), la
  **conversión a la unidad base la calcula la base** (`fn_uso_recurso`), la
  **anulación de una actividad arrastra en cascada** sus usos activos en la
  misma transacción y con el mismo motivo (`recursos_anulados` en el
  resumen), y **no hay `DELETE`** → 405 (anulación lógica con motivo
  obligatorio) → pruebas 123, 124, 128–131 · colección 212, 218, 221–223, 226.
- [x] RN de resumen y protección de recursos: `resumen_recursos` en el detalle
  de campaña (suma por categoría, **excluyendo anulados**), unidades con usos
  protegidas contra cambio de factor/tipo y **campaña de un uso inmutable**
  al editar → pruebas 132, 135, 136 · colección 228–229, 232–233.
- [x] RN de ámbito y permisos de recursos: el Técnico solo ve y registra usos
  de sus productores asignados (uso ajeno → 404), `registrado_por` oculto a
  los roles con `limita_a_asignados`, Administrador con los 4 permisos,
  Técnico sin `desactivar` (anular → 403) y Coordinador solo `ver` (crear →
  403) → pruebas 134–137 · colección 206, 234–235.
- [x] RN de clima: **una fila por parcela y día** (`uq_clima_parcela_fecha`;
  duplicado → 400 en español, también en la carrera), al menos una medida o la
  helada, temperaturas coherentes (`temp_min ≤ temp_max` y promedio dentro del
  rango) y en `[−30, 45]`, precipitación/viento/radiación ≥ 0, humedad en
  `[0, 100]`, fecha no futura en **hora de Lima** ni anterior a 2000, y
  **`DELETE` → 405** (sin anulación: solo edición) → pruebas 138–143, 148,
  151.
- [x] RN de cálculos del servidor: el **punto medio** de mínima y máxima se
  guarda como `temp_prom` (`ROUND_HALF_UP` a 1 decimal) y la **helada** se
  deriva del umbral `umbral_helada_c` (pregunta K: CONFIRMAR) cuando hay
  `temp_min`; los campos `fuente`, `registrado_por`, `creado_en` y
  `actualizado_en` no los acepta el cliente → pruebas 144, 155.
- [x] RN de fuente MANUAL/API: editar un registro **API** exige
  `confirmar_reemplazo=true` y lo **pasa a MANUAL**; la consulta nunca pisa
  registros manuales → pruebas 145, 153.
- [x] RN de consulta a la API meteorológica (**HU-84**): rango **≤ 92 días**,
  parcela con coordenadas, throttle `clima_consulta` 10/hora, informe de
  **6 contadores** que suman los días consultados, todo el rango en **una
  transacción** (`select_for_update`) y **502 en español** si Open-Meteo cae →
  pruebas 152–154 · **smoke E2E 15/15** con el servicio real (8 días → 7
  creados + 1 omitido manual).
- [x] RN de ámbito y permisos de clima: el Técnico solo ve y registra clima
  de sus productores asignados (parcela ajena → «no existe»), `registrado_por`
  oculto a los roles con `limita_a_asignados`, Administrador con los 4
  permisos, Técnico sin `desactivar` (sin uso: no hay anulación) y Coordinador
  solo `ver` (crear y `consulta-api/` → 403) → pruebas 146 · smoke E2E.
- [x] RN de agregados de clima: `resumen_clima` en el detalle de campaña
  (ventana siembra–cosecha, **nota de provisionalidad** sin fecha de cosecha;
  la CTE `clima_c` del dataset se compara literal en la prueba 149), bloque
  `clima` en el detalle de parcela (registros y último día) y
  `umbral_helada_c` editable en `/api/parametros/` (−10 a 5 °C; cambiarlo no
  recalcula) → pruebas 149, 150, 155.
- [x] RN de registro de incidencias: campaña en `PLANIFICADA`,
  `EN_PRODUCCION` o `COSECHADA` (**admiten registros**), fecha dentro del
  período de la campaña y **no futura en hora de Lima**, severidad de las
  tres, descripción obligatoria, superficie ≥ 0 y ≤ sembrada (2 decimales),
  agente **solo en tipos biológicos** y activo, producto ≤ 100 informativo,
  `registrado_por` oculto a `limita_a_asignados`, campaña y tipo
  inmodificables al editar y **`DELETE` → 405** → pruebas 156–161, 163, 167,
  172.
- [x] RN de anulación de incidencias: `anular/` con motivo obligatorio (borrado
  lógico `anulada`), `reactivar/` solo con la campaña abierta y la fecha en su
  período, anuladas fuera de resúmenes, dataset (`inc_c`) e historial →
  pruebas 162, 165, 170.
- [x] RN de ámbito y permisos de incidencias: Administrador con los 4
  `incidencias.*`; Técnico `ver/crear/editar` solo en sus productores (objeto
  ajeno → 404, **anular sin permiso → 403 global** porque el permiso se
  comprueba antes que el objeto); Coordinador solo `ver` → pruebas 164–166,
  171.
- [x] RN de agregados de incidencias: `resumen_incidencias` en el detalle de
  campaña (total, por severidad, severidad máxima, última fecha y mayor
  superficie; **vacío = ceros, no error**), historial de la parcela agrupado
  por campaña (`?incluir_anuladas=1`) e `incidencias_activas` /
   `ultima_incidencia` en el productor → pruebas 168, 169.
- [x] RN de etapas de campaña (**Semana 12**): **una sola etapa en curso** por
  campaña (el alta cierra la anterior en curso), la etapa debe ser del
  cultivo y **del catálogo de la campaña** («etapa existente» anidable),
  orden coherente (la nueva no puede ser anterior a la en curso, salto hacia
  adelante permitido solo en API — pregunta O), fechas `inicio ≤ fin` y fin
  ≥ inicio de campaña, campaña `CERRADA`/`CANCELADA` → 400, sin `DELETE` →
  405, filtros (campaña, etapa, estado, fechas, búsqueda) y `etapa_actual`
  en el listado/detalle de campaña → pruebas 173–185 y **197** (listado
  paginado con los 6 filtros y el ámbito antes que los filtros); la **línea
  de tiempo** (`GET /api/campanias/{id}/linea-tiempo/`) agrega etapas,
  actividades, incidencias y la cosecha con tope 500 → pruebas 183–185.
- [x] RN de usuarios (**Semana 12**): **sin `DELETE`** (desactivar con motivo
  y reactivar), username **inmutable** y único (`usuario_existente`
  anidable), nombres/apellidos obligatorios, clave débil → 400, rol
  obligatorio y activo, **cuenta propia protegida** (no autodesactivarse, no
  cambiar rol, no restablecer clave — Sprint 7), **último gestor de roles**
  nunca perdido, restablecer/desactivar con **marca de sesión** (cierra
  access y refresh abiertos), desbloquear reinicia el contador de fallos,
  listado con búsqueda y `GET /api/roles/` solo con `usuarios.ver` →
  pruebas 186–196.
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
  (`parametros.gestionar` solo Administrador); recursos 134–137 (Técnico sin
  `desactivar`, Coordinador sin `crear`); clima 146 (Coordinador solo `ver`);
  colección 033–036, 040,
  117–127, 155, 158–159, 166–167, 198–205, 206, 234–235.
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
- [x] Contrato de la API de recursos e insumos → `docs/api_recursos.md`
  (usos de recursos con `anular/` y `reactivar/`, cascada, `resumen_recursos`,
  permisos por rol, filtros, unidades por categoría y cuerpos exactos de los
  dos formatos de error). ⚠️ **Hallazgo de la Semana 10:** este archivo está
  **citado pero no existe** en `docs/` (revisar antes de la entrega).
- [x] Contrato de la API de clima → `docs/api_clima.md` (registros con los 10
  filtros, sin `DELETE` → 405, cálculos del servidor, `confirmar_reemplazo`,
  HU-84 con el informe de 6 contadores, `resumen_clima`, bloque `clima` de la
  parcela, `umbral_helada_c`, cuerpos exactos de los dos formatos de error,
  guion de la colección 236–270 y curl).
- [x] Contrato de la API de incidencias → `docs/api_incidencias.md` (listado
  con 12 filtros + búsqueda, alta/edición sin `DELETE` → 405, `anular/` y
  `reactivar/`, mensajes 400 exactos, permisos por rol y ámbito,
   `resumen_incidencias`, historial de parcela, contadores del productor,
   catálogos desplegables, sección de errores y curl).
- [x] Contrato de la API de etapas, línea de tiempo y usuarios (Semana 12) →
   `docs/cierre_semana12.md` §2 (Opción A: en un solo documento con las
   decisiones y el checklist de UI): `/api/etapas-campania/` con sus 8
   filtros y errores anidables, `linea-tiempo/`, `/api/usuarios/` (alta 201,
   acciones `restablecer-clave/`, `desactivar/`, `reactivar/`,
   `desbloquear/`, sin `DELETE` → 405), `/api/roles/` y las tablas de
    errores 400 de los dos módulos).
- [x] Contrato de la API de auditoría y del cambio de contraseña (Semana 13) →
   `docs/api_auditoria.md` (`GET /api/auditoria/` con 7 filtros, fila con
   `usuario` anulable, 15 acciones auditadas por módulo, inmutabilidad y
   solo lectura → 405) y `docs/api_cambio_clave.md`
   (   `POST /api/auth/cambiar-clave/` con `password_actual`, validadores con
   el usuario, 429 con `Retry-After`, rutas libres de la puerta
   `DebeCambiarClave` y el hallazgo del `iat` de segundo).
- [x] Contrato de la API de alertas y del estado de evaluación (Semana 15) →
   `docs/api_alertas.md` (listado con pestañas y filtros **solo en `list`**,
   fila y ficha, `atender/` y `reabrir/`, `evaluar/` con **429 propio** y
   `retry_after`, `resumen/`, `productores-en-riesgo/`, `evaluacion/`,
   matriz de permisos por rol y catálogo de errores) y
   `docs/evaluacion_alertas.md` (tipos y condiciones, los 13 ganchos,
   `evaluar_todo()` paso a paso, ciclo de vida y cierre automático,
   comando `evaluar_alertas`, privacidad y la tabla de pruebas 242–262).
- [x] **Colecciones ejecutables** → `docs/coleccion_api_semana3.json`
  (36 peticiones), `docs/coleccion_api_semana4.json`
  (**48 peticiones** con `pm.test`, validadas **48/48** contra el servidor),
  `docs/coleccion_api_semana5.json` (**93 peticiones** = 48 + 45 de catálogos,
  validadas **93/93**), `docs/coleccion_api_semana6.json`
  (**127 peticiones** = 93 + 34 de campañas, validadas **127/127** con
  **221/221 aserciones**), `docs/coleccion_api_semana7.json`
  (**159 peticiones** = 127 + 32 de actividades, validadas **159/159** con
  **286/286 aserciones**), `docs/coleccion_api_semana8.json`
  (**205 peticiones** = 159 + 46 de parámetros y producción, validadas
  **205/205** con **374/374 aserciones**) y `docs/coleccion_api_semana9.json`
  (**235 peticiones** = 205 + 30 de recursos e insumos, validadas
  **235/235** con **431/431 aserciones**; sin secretos: las claves se toman
  de `.credenciales`) y `docs/coleccion_api_semana10.json`
  (**270 peticiones** = 269 obligatorias (235 + 34 de clima — 22 de
  registros, 5 de consulta-API, 4 de campañas, 1 de parcelas y 2 de
  parámetros) + 1 opcional (informe real a Open-Meteo), validadas
   **270/270** con **496/496 aserciones** contra el servidor en la BD
   temporal `sigpa_ga_coleccion10`, borrada al terminar; sin secretos: las
   claves se toman de `.credenciales`) y `docs/coleccion_api_semana11.json`
   (**311 peticiones** = 270 de la Semana 10 + 41 de incidencias — numeradas
   271–311: CRUD, validaciones, anular/reactivar, permisos/ámbitos, filtros,
   `resumen_incidencias`, historial y contadores —, validadas **311/311**
   con **574/574 aserciones** contra el servidor en la BD temporal
   `sigpa_ga_coleccion11`, borrada al terminar; sin secretos: las claves se
   toman de `.credenciales`) y `docs/coleccion_api_semana12.json`
   (**392 peticiones** = 311 de la Semana 11 + 81 de etapas/línea de
   tiempo y usuarios — numeradas 312–392 —, validadas **392/392** con
   **726/726 aserciones** contra el servidor en la BD temporal
   `sigpa_ga_coleccion12`, borrada al terminar; el servidor de validación
   usa `LOGIN_RATE_IP=120/min` por la cantidad de logins; sin secretos:
    las claves se toman de `.credenciales`) — y `docs/coleccion_api_semana13.json`
    (**430 peticiones** = 392 de la Semana 12 + 38 de auditoría y cambio de
    contraseña — numeradas 393–430: auditoría con sus filtros, historial de
    ficha y solo-lectura, y cambio de contraseña con puerta, validadores,
    cookies nuevas, evento CAMBIAR_CLAVE y límite 5/hora —, obligatorias
    **429/429** + 1 opcional, validadas **430/430** con **793/793
    aserciones** contra el servidor en la BD temporal
     `sigpa_ga_coleccion13`, borrada al terminar; el servidor de validación
     usa `LOGIN_RATE_IP=120/min` por la cantidad de logins; sin secretos:
     las claves se toman de `.credenciales`).
- [x] **Colección de la Semana 15 (F7 cerrada):** `docs/coleccion_api_semana15.json` (**488 peticiones** = 458 de la Semana 14 + 30 de alertas — numeradas **459–488**: filtros y pestañas, ficha, `atender/`, `reabrir/`, `evaluar/` con su 429, `resumen/`, `productores-en-riesgo/`, `evaluacion/` y parámetros —, obligatorias **486** + 2 opcionales), **validada 488/488** (904/904 aserciones) contra la BD temporal `sigpa_ga_coleccion15` en el puerto 8001 con `LOGIN_RATE_IP=120/min` (BD borrada al terminar). Ajustes de la validación: la respuesta del alta de incidencia trae `campania` anidada y la alerta fuera del ámbito del Técnico se genera en `campania_s10_id` (la campaña de la Semana 8 queda CERRADA al final de la S14, como espera la prueba 274).
- [x] **Suite de pruebas:** `python manage.py test` → **262 verdes**
  (8 Semana 1 + 12 Semana 2 + 17 Semana 3 + 16 Semana 4 + 14 Semana 5 +
  19 Semana 6 + 16 Semana 7 + 18 Semana 8 + 17 Semana 9 +
  18 Semana 10 + 17 Semana 11 + 25 Semana 12 + 23 Semana 13 +
  **21 Semana 14** — 15 de roles/permisos (221–235, `usuarios/tests.py`) y
  6 de reglas de calidad (236–241, `sistema/tests_calidad.py`) — +
  **21 Semana 15** — alertas (242–262, `alertas/tests.py` —);
  `manage.py check`
  en 0 issues; `makemigrations --check` sin cambios. Comandos en
  `comparacion_sprint1.md` §6, `comparacion_semana3.md` §6,
  `comparacion_semana4.md` §6, `comparacion_semana5.md` §6,
  `comparacion_semana6.md` §7, `comparacion_semana7.md`,
  `comparacion_semana8.md`, `decisiones_semana9.md` §2 («Cómo se verificó»),
  `decisiones_semana10.md` §2 (decisión 14, con el smoke E2E de 15 pasos),
  `comparacion_semana11.md` §7,
  `cierre_semana12.md` §1 (F3 y F6),
  `decisiones_semana13.md` §1.2 (D16) y
  `decisiones_semana15.md` (F4).
- [x] **Pantallas React:** `npm run lint` y `npm run build` en 0 problemas;
  checklist de ejecución manual en `docs/verificacion_ui_semana4.md`,
  `docs/verificacion_ui_semana5.md`, `docs/verificacion_ui_semana6.md`,
  `docs/verificacion_ui_semana7.md`, `docs/verificacion_ui_semana8.md`,
  `docs/verificacion_ui_semana9.md`,
  `docs/verificacion_ui_semana10.md`,
  `docs/verificacion_ui_semana11.md`, el §3 de
  `docs/cierre_semana12.md`,
  `docs/verificacion_ui_semana13.md` y
  `docs/verificacion_ui_semana15.md`
  (decisiones 15/16/17/19, **pendientes de ejecutar por el responsable**).
  De la Semana 5: pantalla `/catalogos` con CRUD en modales; de la Semana 6:
  pantalla `/campanias` con alta/edición en modal y las fichas de
  productor/parcela con su sección de campañas; de la Semana 7: pantalla
  `/actividades`, `ActividadFicha` (anular/reactivar) y `CampaniaFicha` con
  bloque de actividades; de la Semana 8: pantalla **`/parametros`**,
  `ProduccionFormulario` y `ProduccionFicha` (revisar/deshacer),
  `CampaniaFicha` con bloque «Producción» + cerrar y columna «Producción» en
  `ProductorFicha`; de la Semana 9: pantalla **`/recursos`**,
  `RecursoFormulario` y `RecursoFicha` (anular/reactivar), «Recursos usados»
  en `ActividadFicha` y «Resumen de recursos» en `CampaniaFicha`;
   de la Semana 10: pantalla **`/clima`**, `ClimaFormulario`,
   `ClimaFicha`, `ClimaConsulta` (HU-84), sección «Clima» en `ParcelaFicha`
   y «Resumen de clima» en `CampaniaFicha`; de la Semana 11: pantalla
   **`/incidencias`** (10 filtros en URL, incluido el de campaña que enlaza
   «Ver todas»), `IncidenciaFormulario` (agente solo en tipos biológicos,
   campaña inmutable), `IncidenciaFicha` (anular/reactivar con motivo),
    sección «Incidencias» en `CampaniaFicha`, historial en `ParcelaFicha` y
    contadores en `ProductorFicha`; de la Semana 12: componente
    **`LineaTiempo`** + sección «Línea de tiempo» y tabla de etapas (con
    edición) en `CampaniaFicha`, `EtapaFormulario`, columna «Etapa» en
     `/campanias`, pantalla **`/usuarios`** con `UsuarioFormulario` y
     `UsuarioFicha` (restablecer, desbloquear, desactivar/reactivar) y ruta
     `/usuarios` protegida por `usuarios.ver`; de la Semana 13: pantalla
     **`/auditoria`** (7 filtros en URL, «Actualizar», chips de acción,
     detalle en `<code>` y paginación 20), **«Ver historial»** en
     `ProductorFicha`, `ParcelaFicha` y `UsuarioFicha` (solo con
     `auditoria.ver`), pantalla **`/cambiar-clave`** (fuera del Layout,
     redirección con la marca `debe_cambiar_clave` desde `RutaProtegida` y
     `Login`, rueda «Guardando…») y `actualizarUsuario` en `SesionProvider`;
     de la Semana 15: pantallas **`/alertas`** (pestañas
     Pendientes/Atendidas/Todas, filtros en URL, aviso de atraso de 36 h,
     «Evaluar ahora», ficha, atender con nota ≤ 250 y reabrir) y
     **`/productores-riesgo`**, **insignia** de pendientes en `Layout`,
     sección «Alertas» en `CampaniaFicha` y `ProductorFicha`, y panel
     «Evaluación de alertas» (chip ATRASADA/AL DÍA) en `/parametros`.

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
  `backend/produccion/admin.py`, `backend/sistema/admin.py`. Desde la Semana 9
  la tabla **`uso_recursos`** (consulta y trazabilidad; la anulación y la
  reactivación son solo vía API) también está registrada →
  `backend/seguimiento/admin.py`. Desde la Semana 10 la tabla **`clima`**
  (alta y corrección en admin: `save_model` fuerza `fuente = MANUAL` y
  recalcula `temp_prom` y `helada` con el umbral; los campos calculados y la
  trazabilidad son de solo lectura; el borrado físico solo existe en el admin
   de Django, la API no expone `DELETE`) también está registrada →
   `backend/seguimiento/admin.py`. Desde la Semana 11 la tabla
   **`incidencias`** (consulta y trazabilidad; el alta/edición y la
   anulación son solo vía API) también está registrada →
    `backend/seguimiento/admin.py`. Desde la Semana 12 la tabla
    **`seguimiento_etapas`** (alta y edición con validación de orden; sin
    borrado físico) también está registrada → `backend/seguimiento/admin.py`,
    y la **pantalla `/usuarios`** de React cubre la gestión que antes solo
    existía en el panel. Desde la Semana 13 la tabla **`auditoria`** **no
    está registrada en el panel a propósito**: la protege el trigger 25 y
    la única consulta es la API (solo Administrador) o la pantalla
    `/auditoria`.
- [ ] **Capturas de pantalla** del panel y de la API en Postman (para el
  documento): ejecutar la colección y capturar respuestas 201/400/403/405.

## Bitácora de trabajo (Scrum)

- [x] Tablero con HU-15..HU-22 → `docs/tablero.md` (Semana 3), HU-23..HU-28
  con estado y evidencias (Semana 4), las **8 fases F1–F8** de la Semana 5,
  las **7 fases F1–F7** de la Semana 6 (HU-38..HU-46), las **7 fases F1–F7**
  de la Semana 7 (HU-47..HU-55), las **7 fases F1–F7** de la Semana 8
  (HU-56..HU-62), las **7 fases F1–F7**   de la Semana 9 (HU-67..HU-75 del
  mapeo propuesto, más HU-48 completada), las **7 fases F1–F7** de la
  Semana 10 (HU-76..HU-84, **7/7**), las **7 fases F1–F7** de la Semana 11
   (HU-85..HU-92, **7/7**), las **7 fases F1–F7** de la Semana 12
   (HU-93..HU-104, **7/7**; HU-01..HU-14 resumidos
    ahí mismo: textos originales de HU no están en el repositorio: mapeo
   propuesto) y las **7 fases F1–F7** de la Semana 13
   (HU-105..HU-113, **7/7**); la **Semana 14** (HU-114..HU-122, 241
   pruebas, colección 458/458) no dejó documento de decisiones (F6
   cancelada) y las **7 fases F1–F7 de la Semana 15** (HU-124..HU-132,
   **7/7**, 262 pruebas, colección 488/488).
- [x] Calendario y orden de sprints → `CONTEXTO_PROYECTO.md` §13.
- [x] Contexto completo del proyecto (para que el responsable pueda defender
  cada decisión) → `CONTEXTO_PROYECTO.md` completo.

## Pendientes globales (para entregas posteriores)

- [ ] Diagramas ER y modelo lógico (4.3.2 / 4.3.3).
- [ ] Capturas de pantalla de pantallas y endpoints (incluye login de React).
- [ ] Ejecutar los checklists de UI de las Semanas 4 a 15
  (`docs/verificacion_ui_semana4.md` … `docs/verificacion_ui_semana11.md`,
  el §3 de `docs/cierre_semana12.md`,
  `docs/verificacion_ui_semana13.md` y
  `docs/verificacion_ui_semana15.md`)
  en Chrome/Edge/móvil y anotar los resultados.
- [ ] Pantallas de los módulos en React (hoy: login, 403, 404, productores,
  parcelas, **catálogos** con CRUD en modales, **campañas** con su
  línea de tiempo, **actividades** con `CampaniaFicha`, **parámetros**,
  **recursos**, **clima**, **incidencias**,
  **usuarios** y **auditoría** con **cambiar-clave**,
  **alertas** y **productores-riesgo**, con producción,
  recursos, clima, incidencias, etapas y alertas
  dentro de las fichas; la entrada
  «Producción» del menú sigue siendo placeholder: faltan su pantalla y los
  demás módulos).
- [ ] Manual de usuario y evidencia de la demo.
- [ ] Copia de `DB_sql/` fuera del repositorio antes de cualquier entrega
  (está ignorado en Git).
