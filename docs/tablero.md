# Tablero SIGPA-GA — Semana 5: catálogos de campañas

> Tablero de la semana del **2 al 8 de noviembre** (calendario referencial).
> Sustituye mientras tanto a Trello/GitHub Projects (decisión de metodología:
> se confirmará con el responsable qué herramienta usa él).
> Los textos originales de las historias de usuario **no están en este
> repositorio**: las descripciones siguientes son el **mapeo propuesto**
> (igual que en semanas anteriores), anclado a los RF/RN del documento de
> requerimientos.

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

## Siguiente (Semana 6, 9–15 nov)

| Tema | Nota |
|---|---|
| Esqueleto de campañas (`campanias`, ciclo por parcela) | Tabla central del diseño; ya **no bloqueada**: los catálogos están terminados (Semana 5) |
| Preguntas abiertas A, B y D | Lista de ubicaciones real, regla de enmascarado y botón «usar mi ubicación» |
| Checklists de UI de las Semanas 4 y 5 | Ejecutar en navegador (Chrome/Edge/móvil) y anotar los resultados en cada documento |

## Preguntas abiertas que bloquean decisiones

1. **Lista real de ubicaciones** (decisión 1): hasta que llegue, rige
   `datos/ejemplo_ubicaciones.csv` (datos inventados, marcados).
2. **Regla de enmascarado por rol** (decisión 4 de la Semana 3 / HU-21):
   propuesta actual — Administrador y Técnico completos, Coordinador enmascarado.
3. ~~¿El productor que registra un técnico se le asigna automáticamente?~~
   **Cerrada en la Semana 4: sí** (decisión 4 de `decisiones_semana4.md`,
   prueba 49: se asigna en la misma operación y de forma atómica).
4. **Botón «usar mi ubicación actual»** (item *estirada*): solo funciona en
   `https://` o `localhost`; decidir en la demo si se implementa (no entró en F7).
