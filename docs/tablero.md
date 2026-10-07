# Tablero SIGPA-GA — Semana 3: ubicación y productores

> Tablero de la semana del **19 al 25 de octubre** (calendario referencial).
> Sustituye mientras tanto a Trello/GitHub Projects (decisión de metodología:
> se confirmará con el responsable qué herramienta usa él).
> Los textos originales de las historias de usuario **no están en este
> repositorio**: las descripciones siguientes son el **mapeo propuesto**
> (igual que en `api_autenticacion.md` para HU-07..HU-14), anclado a los
> RF/RN del documento de requerimientos.

## Semana 3 — 8/8 terminadas

| HU | Descripción (propuesta) | Origen | Estado | Evidencia |
|---|---|---|---|---|
| **HU-15** | Administrar provincias, distritos y comunidades (alta, edición, desactivación sin borrado) | RF: «administrará provincias, distritos y comunidades» | ✅ Hecha | API `ubicaciones/{provincias,distritos,comunidades}` + panel admin · pruebas 26, 27, 36 · colección 004–018 |
| **HU-16** | Cargar la lista de ubicación desde CSV o Excel (sin tocar código) | Decisión 2 (`decisiones_semana3.md`) | ✅ Hecha | Comando `cargar_ubicacion` (idempotente, informe de fallidas) · prueba 37 · `datos/ejemplo_ubicaciones.csv` |
| **HU-17** | Registrar un productor con código automático y validaciones (DNI 8 dígitos y único, comunidad obligatoria/activa) | RF: «registrar un productor con código generado automáticamente (PROD-0001)…» + RN: «el DNI debe ser único y tener 8 dígitos» | ✅ Hecha | `POST /api/productores/` + triggers `trg_productores_codigo` · pruebas 21, 23, 24, 25, 34 · colección 019–022 |
| **HU-18** | Modificar los datos de un productor (el código no cambia; `actualizado_en` lo rellena la BD) | RF: «modificar los datos de un productor» | ✅ Hecha | `PATCH /api/productores/{id}/` · pruebas 22, 33 · colección 028–029 |
| **HU-19** | Desactivar y reactivar un productor sin perder su historial (nada se borra) | RF: «desactivar y reactivar un productor sin perder su historial» + RN: «no se eliminan físicamente» | ✅ Hecha | `PATCH …/estado/`, `DELETE` → 405, FK `PROTECT` · prueba 28 · colección 030–032 |
| **HU-20** | Buscar y filtrar productores por código, nombre, DNI, comunidad, distrito y estado; consultarlos por rol | RF: «buscar y filtrar productores por código, nombre, DNI, comunidad, distrito y estado» | ✅ Hecha | `?busqueda=`, `?comunidad=`, `?distrito=`, `?provincia=`, `?estado=` + paginación y orden por apellidos · pruebas 29, 30, 31, 32, 36 · colección 023–026 |
| **HU-21** | Proteger los datos personales: DNI y teléfono se muestran completos solo a los roles autorizados | RN de protección de datos (Ley N.° 29733) · decisión 4 ⚠️ pendiente de confirmación | ✅ Hecha (regla por confirmar) | `ROLES_CON_DATOS_COMPLETOS` en serializadores · prueba 35 · colección 034 |
| **HU-22** | Ver la ficha del productor (parcial: datos + ubicación; parcelas y campañas se suman en la Semana 4) | RF: «mostrar una ficha del productor con sus parcelas, campañas e historial» | ✅ Hecha (parcial) | `GET /api/productores/{id}/` + `creado_por`/`creado_en`/`actualizado_en` · colección 027 |

**Cierre de la semana:** 37 pruebas verdes (`manage.py test`),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios, colección
de 36 peticiones validada 36/36, y documentación en
`decisiones_semana3.md`, `comparacion_semana3.md`,
`api_ubicacion_productores.md` y `coleccion_api_semana3.json`.

## Semanas anteriores (resumen)

| Semana | HU | Estado |
|---|---|---|
| 1 (5–11 oct) — roles, permisos y usuarios | HU-01..HU-06 (gestión de roles/permisos/usuarios, semilla y panel) | ✅ 8 pruebas |
| 2 (12–18 oct) — autenticación y permisos | HU-07..HU-14 (login, refresh, logout, `/me`, permisos, rate limit, sesión y menú en React) | ✅ 20 pruebas · `api_autenticacion.md` |

## Siguiente (Semana 4, 26 oct – 1 nov)

| Tema | Nota |
|---|---|
| Asignación de productores a técnicos (`asignaciones_tecnico`) | RF: «el técnico solo verá los productores que tenga asignados»; habilita el filtro «solo mis productores» (pregunta abierta C) |
| Parcelas (`parcelas`, código `P-001`, trigger `fn_codigo_parcela`) | Completa la ficha HU-22 |
| Catálogos (cultivos, unidades, tipos…) | Permisos `catalogos.*` ya usados esta semana |
| Pantallas React de ubicación y productores | El menú ya filtra por permiso; faltan las vistas |

## Preguntas abiertas que bloquean decisiones

1. **Lista real de ubicaciones** (decisión 1): hasta que llegue, rige
   `datos/ejemplo_ubicaciones.csv` (datos inventados, marcados).
2. **Regla de enmascarado por rol** (decisión 4 / HU-21): propuesta actual —
   Administrador y Técnico completos, Coordinador enmascarado.
3. **¿El productor que registra un técnico se le asigna automáticamente?**
   (pregunta abierta C, para la Semana 4).
