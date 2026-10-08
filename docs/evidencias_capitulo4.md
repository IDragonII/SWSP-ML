# Evidencias para el Capítulo IV de la tesis — checklist

> Qué artefacto del repositorio respalda cada sección del Capítulo IV
> (Diseño e implementación del sistema), cómo se regeneró y qué **sigue
> pendiente**. Se actualiza al cierre de cada semana.
> **Estado: Semana 4 completada — 53 pruebas verdes.**

Leyenda: `[x]` disponible en el repositorio · `[ ]` pendiente.

## 4.3.2 Diagrama entidad-relación

- [ ] **Diagrama ER** de las 32 tablas (fuente disponible: `DB_sql/01_tablas.sql`
  y los `Meta.db_table`/`related_name` de los modelos Django).
- [x] Lista y descripción de las 32 tablas agrupadas por módulo →
  `CONTEXTO_PROYECTO.md` §5.
- Nota: hasta la Semana 4 existen **10 tablas** en la BD real (4 de usuarios +
  4 de ubicación/productores + `parcelas` y `asignaciones_tecnico`); el
  diagrama completo se dibuja con el diseño completo.

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
- [x] **Migraciones propias:** `backend/usuarios/migrations/` (0001–0003) y
  `backend/productores/migrations/` (0001–0004, las dos últimas reversibles).
  La creación del BD de pruebas en cada `manage.py test` aplica las 29
  migraciones desde cero.

## Reglas de negocio y triggers

- [x] Catálogo de las 13 funciones y 24 triggers del diseño →
  `CONTEXTO_PROYECTO.md` §6.
- [x] Triggers implementados hasta ahora (6 de 24): `trg_roles_proteger`,
  `trg_productores_actualizado`, `trg_productores_codigo`,
  `trg_parcelas_actualizado`, `trg_parcelas_codigo` y
  `trg_asignaciones_validar` — texto literal, verificados en
  `comparacion_sprint1.md` §4, `comparacion_semana3.md` §5 y
  `comparacion_semana4.md` §5.
- [x] **Migración desde cero como evidencia:** base vacía `sigpa_ga_migracion`
  → `manage.py migrate` aplicó 27 migraciones; seeds 55 permisos / 3 roles /
  101 asignaciones; 4 tablas nuevas; prueba funcional en SQL crudo generó
  `PROD-0001` y actualizó `actualizado_en` en otra transacción (Semana 3).
  Reproducible: crear BD, `DB_NAME=<nombre> python manage.py migrate`, borrar.
  Desde la Semana 4, la BD de pruebas que crea cada `manage.py test` vuelve a
  aplicar las 29 migraciones desde cero en cada ejecución.

## Requerimientos funcionales verificados (RF/RN)

- [x] Matriz de decisiones por semana → `docs/decisiones_seguridad.md`
  (Semana 2), `docs/decisiones_semana3.md` (Semana 3, 7 decisiones con sus
  preguntas abiertas) y `docs/decisiones_semana4.md` (Semana 4, 19
  decisiones, incluidas las de parcelas, asignaciones y CRUD en modales).
- [x] RN «el DNI debe ser único y tener 8 dígitos» → pruebas 23 y 24.
- [x] RN «no se eliminan físicamente; se desactivan» → sin `DELETE` (405),
  prueba 28, FK `PROTECT`; en la Semana 4 el mismo patrón para parcelas
  (prueba 41) y asignaciones (prueba 48).
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
  pruebas 29 y 30; parcelas 43; asignaciones 47; colección 033–036, 040.
- [x] Protección de datos personales (enmascarado por rol, Ley N.° 29733) →
  prueba 35 · **regla pendiente de confirmación** (decisión 4 de la Semana 3).

## API y pruebas

- [x] Contrato de la API de sesión → `docs/api_autenticacion.md`.
- [x] Contrato de la API de ubicación y productores →
  `docs/api_ubicacion_productores.md` (errores con cuerpos verificados;
  404 en español desde la Semana 4, decisión 11).
- [x] **Colecciones ejecutables** → `docs/coleccion_api_semana3.json`
  (36 peticiones) y `docs/coleccion_api_semana4.json`
  (**48 peticiones** con `pm.test`, validadas **48/48** contra el servidor;
  sin secretos: las claves se toman de `.credenciales`).
- [x] **Suite de pruebas:** `python manage.py test` → **53 verdes**
  (8 Semana 1 + 12 Semana 2 + 17 Semana 3 + 16 Semana 4); `manage.py check`
  en 0 issues; `makemigrations --check` sin cambios. Comandos en
  `comparacion_sprint1.md` §6, `comparacion_semana3.md` §6 y
  `comparacion_semana4.md` §6.
- [x] **Pantallas React:** `npm run lint` y `npm run build` en 0 problemas;
  checklist de ejecución manual en `docs/verificacion_ui_semana4.md`
  (decisión 16, **pendiente de ejecutar por el responsable**).

## Usuarios, roles y permisos (evidencia funcional)

- [x] Configuración inicial de los 3 roles y 55 permisos (101 asignaciones)
  como migración idempotente → `usuarios/0002_datos_iniciales`.
- [x] Panel de administración (roles protegidos, permisos con autocompletado,
  acción «Desbloquear acceso», catálogos de ubicación y productores con
  filtros) → `backend/usuarios/admin.py`, `backend/productores/admin.py`.
- [ ] **Capturas de pantalla** del panel y de la API en Postman (para el
  documento): ejecutar la colección y capturar respuestas 201/400/403/405.

## Bitácora de trabajo (Scrum)

- [x] Tablero con HU-15..HU-22 → `docs/tablero.md` (Semana 3) y HU-23..HU-28
  con estado y evidencias (Semana 4; HU-01..HU-14 resumidos ahí mismo:
  textos originales de HU no están en el repositorio: mapeo propuesto).
- [x] Calendario y orden de sprints → `CONTEXTO_PROYECTO.md` §13.
- [x] Contexto completo del proyecto (para que el responsable pueda defender
  cada decisión) → `CONTEXTO_PROYECTO.md` completo.

## Pendientes globales (para entregas posteriores)

- [ ] Diagramas ER y modelo lógico (4.3.2 / 4.3.3).
- [ ] Capturas de pantalla de pantallas y endpoints (incluye login de React).
- [ ] Ejecutar el checklist de UI de la Semana 4 en Chrome/Edge/móvil
  (`docs/verificacion_ui_semana4.md`) y anotar los resultados.
- [ ] Pantallas de los módulos en React (hoy: login, 403, 404, productores y
  parcelas con CRUD en modales; faltan los demás módulos del menú).
- [ ] Manual de usuario y evidencia de la demo.
- [ ] Copia de `DB_sql/` fuera del repositorio antes de cualquier entrega
  (está ignorado en Git).
