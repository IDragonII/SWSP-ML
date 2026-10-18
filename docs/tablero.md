# Tablero SIGPA-GA — Semana 16: panel de indicadores (dashboard)

> Tablero de la semana del **18 al 24 de enero** (calendario
> referencial; sin feriados).
> Sustituye mientras tanto a Trello/GitHub Projects (decisión de metodología:
> se confirmará con el responsable qué herramienta usa él).
> Los textos originales de las historias de usuario **no están en este
> repositorio**: las descripciones siguientes son el **mapeo propuesto**
> (igual que en semanas anteriores), anclado a los RF/RN del documento de
> requerimientos.

## Semana 16 — F1..F7 terminadas (7/7)

El tema «panel de indicadores» (segunda semana del **Sprint 8**)
corresponde al **mapeo HU-133 a HU-140** de la semana (RF-62, panel de
indicadores; los reportes descargables quedan fuera); se ejecutó **por
fases F1–F7** acordadas con el responsable: **F1–F7 cerradas** (suite
**279/279**, documentación de la semana escrita, frontend en
`lint`/`build` en 0, colección **506/506 con 939/939 aserciones
validadas**). La Semana 16 se
entrega **íntegra sin commitear**, decisión del responsable: el commit
único (con las semanas 13, 14 y 15) lo hace él al cierre.

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-133** | Tarjetas de resumen del panel: productores (activos, inactivos y con campaña activa), aptas para entrenar, revisiones pendientes y alertas | ✅ Hecha | `GET /dashboard/resumen/` · pruebas 263, 264 · `pages/Inicio.jsx` |
| **HU-134** | Superficie sembrada de las campañas activas del alcance (texto con 2 decimales, `null` sin datos) | ✅ Hecha | `GET /dashboard/resumen/` · prueba 264 |
| **HU-135** | Campañas agrupadas por estado (los 5 siempre, con `?periodo=` opcional) con gráfico de barras | ✅ Hecha | `GET /dashboard/campanias-estado/` · pruebas 265, 272 · `Inicio.jsx` |
| **HU-136** | Producción agrupada por cultivo o distrito con rendimiento **ponderado** (kg ÷ superficie cosechada) más el promedio simple y totales | ✅ Hecha | `GET /dashboard/produccion/` · pruebas 267–269, 271, 273 |
| **HU-137** | Opciones de filtro (períodos, cultivos y ubicación en cascada) dentro del alcance del usuario | ✅ Hecha | `GET /dashboard/filtros/` · pruebas 274–276 |
| **HU-138** | Franja de alertas pendientes por tipo (`por_tipo` con ceros en `/alertas/resumen/`) | ✅ Hecha | `alertas/views.py` · pruebas 263, 279 · `Inicio.jsx` |
| **HU-139** | Señales `provisional` (campaña sin cerrar) y `pocos_datos` (< 3 campañas) por fila | ✅ Hecha | `dashboard/views.py` · pruebas 267, 268 |
| **HU-140** | `generado_en` en hora de Lima (`America/Lima` con huso) | ✅ Hecha | `dashboard/views.py:48` · prueba 263 |

> **Nota:** el mapeo HU-133..HU-140 es el **mapeo propuesto** de la semana
> (los textos originales no están en el repositorio; el RF-62 se verificó
> leyendo `requerimientos.tex` **sin modificarlo** — solo lectura,
> decisión del responsable). Los docstrings del código usan los mismos
> rangos (`backend/dashboard/views.py`, `tests.py`).

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: app **`dashboard/`** (sin modelos ni migraciones, `dashboard.ver` ya sembrado) + `filtrar_asignados` extraída y compartida + `GET /dashboard/resumen/` | ✅ Hecha | `backend/dashboard/`, `productores/views.py` |
| **F2** | `GET /dashboard/produccion/` (agrupar + filtros + ponderado + `provisional`/`pocos_datos`), `GET /dashboard/filtros/` (cascada), `GET /dashboard/campanias-estado/` y `por_tipo` en `/alertas/resumen/` | ✅ Hecha | `backend/dashboard/views.py`, `alertas/views.py` |
| **F3** | Pruebas **263–279** (17): resumen, producción, alcance, filtros, presupuesto de consultas (12/4/5/8) y recorrido de rutas 405; **total 279/279**; hallazgos corregidos (`/producciones/` plural, `values(F())`, cosechada ≤ sembrada, `requiere_revision` en Produccion, 401 antes que 405, BD de pruebas huérfana) | ✅ Hecha | `backend/dashboard/tests.py` · `manage.py test` 279/279 |
| **F4** | Frontend: **Recharts 3.10.1** + `Inicio.jsx` reescrito (tarjetas, franja de alertas, filtros en URL con cascada, 2 gráficos, `Tabla` con señales, estados por bloque) + estilos `.tarjetas`/`.grafico-envoltura` | ✅ Hecha | `frontend/src/{api/dashboard.js,pages/Inicio.jsx,App.css}` · `lint`/`build` en 0 |
| **F5** | Documentación: `decisiones_semana16.md` (17 decisiones + pregunta **U** con nota de letras), `api_dashboard.md`, `verificacion_ui_semana16.md` y la actualización de este tablero y `CONTEXTO_PROYECTO.md` | ✅ Hecha | `docs/decisiones_semana16.md`, `api_dashboard.md`, `verificacion_ui_semana16.md` |
| **F6** | Colección de Postman: **488** de la Semana 15 + **18 nuevas** = **506** (numeradas 489–506) | ✅ Hecha | `docs/coleccion_api_semana16.json` |
| **F7** | Cierre: colección validada end-to-end con el pipeline habitual (BD temporal `sigpa_ga_coleccion16` con migrate + usuarios + **siembra previa** de F7, servidor 8001 con `LOGIN_RATE_IP=120/min`, `validador/validar.js`): **506/506 peticiones (504 obligatorias + 2 opcionales) y 939/939 aserciones**; BD borrada y servidor detenido; comando **`datos_demostracion`** mínimo e idempotente (inventado y marcado, probado); el panel de calidad HU-123 (pruebas 280–284) **no se aplicó** por falta de holgura (corte mínimo acordado: 279/506) | ✅ Hecha | `backend/sistema/management/commands/datos_demostracion.py` · `docs/evidencias_semana16.md` |

**Estado (7/7 fases):** **279 pruebas verdes** (`manage.py test`; las 17
de la semana son la 263–279), `manage.py check` en 0 issues,
`makemigrations --check` sin cambios, `npm run lint` y `npm run build` en
0 problemas, colección **506/506 (939/939 aserciones)**, comando
`datos_demostracion` creado y documentación escrita en
`decisiones_semana16.md`, `api_dashboard.md`,
`verificacion_ui_semana16.md`, `evidencias_semana16.md` y
`CONTEXTO_PROYECTO.md`. Único pendiente: el commit único del
responsable (semanas 13–16).

## Semana 15 — F1..F7 terminadas (7/7)

El tema «alertas y productores en riesgo» (apertura del **Sprint 8**)
corresponde al **mapeo HU-124 a HU-132** de la semana (RF-63, RF-64,
RF-65 y RF-15); se ejecutó **por fases F1–F7** acordadas con el
responsable: **F1–F7 cerradas** (suite **262/262**, documentación de la
semana escrita, frontend en `lint`/`build` en 0, colección
**488/488 validada**). La Semana 15 se entrega
**íntegra sin commitear**, decisión del responsable: el commit único lo
hace él al cierre (las semanas 13 y 14 siguen pendientes también).

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-124** | Generación automática de alertas: `INCIDENCIA_SEVERA` única por incidencia con su ciclo anular→cierra / reactivar→reabre; mensajes en español sin datos personales; `RENDIMIENTO_BAJO` reservado al modelo de regresión | ✅ Hecha | `alertas/servicio.py` · pruebas 242, 243, 261 |
| **HU-125** | Atención manual (`alertas.atender`, nota opcional ≤ 250 y evento MODIFICAR) y reapertura solo de lo atendido a mano (lo automático → 400); 401 sin sesión y 403 sin permiso | ✅ Hecha | `POST /alertas/{id}/atender/`, `…/reabrir/` · pruebas 251, 252, 254 |
| **HU-126** | Productores en riesgo: agrupación de pendientes por productor con código, ubicación, conteo, tipos y última alerta | ✅ Hecha | `GET /alertas/productores-en-riesgo/` · prueba 256 · `pages/ProductoresRiesgo.jsx` |
| **HU-127** | Listado con pestañas (Pendientes/Atendidas/Todas), filtros y orden «pendientes primero»; resumen para la insignia del menú y sección «Alertas» en las fichas de campaña y productor | ✅ Hecha | `GET /alertas/`, `…/resumen/` · pruebas 255, 257 · `Alertas.jsx`, `Layout.jsx` |
| **HU-128** | Ámbito del Técnico (solo sus productores; detalle ajeno → 404) y privacidad del atendiente (`atendida_por_nombre` solo para roles sin `limita_a_asignados`) | ✅ Hecha | `SoloSusProductores` + serializador · prueba 253 |
| **HU-129** | Alerta de campaña sin actividad con umbral `dias_sin_actividad` (entero 1–365, por defecto 30) y aviso «el cambio se aplica en la siguiente evaluación» | ✅ Hecha | `alertas/servicio.py`, `sistema/` · pruebas 244, 246, 260 |
| **HU-130** | Cierre automático al cambiar el estado de la campaña (cancelar/cerrar/cosechar) más la red de seguridad del barrido | ✅ Hecha | ganchos en `campanias`, `produccion` · prueba 247 |
| **HU-131** | Evaluación: comando diario idempotente (`--dry-run`, `--hoy` solo en DEBUG), evaluación manual con `parametros.gestionar` (una cada 5 min) y gracia tras la atención manual | ✅ Hecha | `evaluar_alertas`, `views.evaluar` · pruebas 245, 248, 249, 258 |
| **HU-132** | Evento resumen de cada evaluación en auditoría y estado del proceso (`ultima_evaluacion`, atraso de 36 h) en `/alertas` y `/parametros` | ✅ Hecha | `GET /alertas/evaluacion/` · pruebas 250, 259 |

> **Nota:** el mapeo HU-124..HU-132 es el **mapeo propuesto** de la semana
> (los textos originales no están en el repositorio; los RF-63/64/65 y
> RF-15 se verificaron leyendo `requerimientos.tex` **sin modificarlo**).
> Los docstrings del código usan los mismos rangos (`alertas/models.py`,
> `views.py`, `servicio.py`, `tests.py`).

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: app **`alertas/`** con el modelo `Alerta` (3 tipos, CHECKs e índices únicos del diseño, **sin triggers nuevos**: 25 intactos) + migración **`0001_alertas.py`**; `DB_sql/01_tablas.sql` actualizado (columnas `incidencia_id`, `nota_atencion`); verificado con `check`, `makemigrations --check` y `sqlmigrate` | ✅ Hecha | `backend/alertas/` · `DB_sql/01_tablas.sql` |
| **F2** | Servicio de evaluación (`evaluar_incidencia`, `evaluar_campania`, `evaluar_todo`, gracia, cierres automáticos) + **13 ganchos** `transaction.on_commit` (seguimiento, campanias, produccion) + comando **`evaluar_alertas`** (`--dry-run`, `--hoy` solo en DEBUG) | ✅ Hecha | `alertas/servicio.py`, `management/commands/evaluar_alertas.py` |
| **F3** | API: `AlertasViewSet` (listado con pestañas/filtros **solo en `list`**, detalle, 405 en escritura), `atender`, `reabrir`, `evaluar` (429 propio), `resumen`, `productores-en-riesgo`, `evaluacion`; validación 1–365 de `dias_sin_actividad` + aviso en `sistema/` | ✅ Hecha | `alertas/{views,serializers}.py`, `sistema/` · pruebas en verde |
| **F4** | Pruebas **242–262** (21): evaluación, API, parámetros y restricciones de la tabla; **total 262/262**; hallazgos corregidos en el código (filtros solo en `list`, errores como cadena, datos de prueba) | ✅ Hecha | `alertas/tests.py` · `manage.py test` 262/262 |
| **F5** | Frontend: pantallas **`/alertas`** y **`/productores-riesgo`**, insignia en `Layout`, sección «Alertas» en las fichas de campaña/productor, panel «Evaluación de alertas» + ayuda en `/parametros` | ✅ Hecha | `frontend/src/pages/{Alertas,ProductoresRiesgo}.jsx`, `Layout.jsx`, `App.css` · `lint`/`build` en 0 |
| **F6** | Documentación: `decisiones_semana15.md` (28 decisiones + pregunta **T** con nota de letras), `api_alertas.md`, `evaluacion_alertas.md`, `verificacion_ui_semana15.md` y la actualización de este tablero, `CONTEXTO_PROYECTO.md`, `evidencias_capitulo4.md` y `matriz_reglas_calidad.md`; **hallazgo de F6 corregido** (el 429 de «Evaluar ahora» perdió su mensaje en el manejador global de `Throttled`) | ✅ Hecha | `docs/decisiones_semana15.md`, `api_alertas.md`, `evaluacion_alertas.md`, `verificacion_ui_semana15.md` |
| **F7** | Cierre: colección de Postman (**458** de la Semana 14 + **30 nuevas** = **488**: 486 obligatorias + 2 opcionales, numeradas 459–488), validada end-to-end en la BD temporal `sigpa_ga_coleccion15` con `LOGIN_RATE_IP=120/min` y borrada al terminar: **488/488 en verde (904/904 aserciones)**; dos ajustes de la propia F7 (respuesta de incidencia con `campania` anidada; la alerta fuera del ámbito se genera en `campania_s10_id` porque la campaña de la S8 queda CERRADA) | ✅ Hecha | `docs/coleccion_api_semana15.json` (459–488) |

**Estado (7/7 fases):** **262 pruebas verdes** (`manage.py test`; las 21 de
la semana son la 242–262), `manage.py check` en 0 issues,
`makemigrations --check` sin cambios, `npm run lint` y `npm run build` en
0 problemas, colección **488/488** y documentación escrita en
`decisiones_semana15.md`,
`api_alertas.md`, `evaluacion_alertas.md`, `verificacion_ui_semana15.md`,
`CONTEXTO_PROYECTO.md` y `evidencias_capitulo4.md`. Único pendiente:
el commit único del responsable.

## Semana 14 — nota (sin documento de decisiones)

La Semana 14 (4–10 de enero) trató **roles y permisos + reglas de
calidad** (mapeo **HU-114 a HU-122**): pruebas 221–241 (**241/241** en su
momento, 824 s), matriz de reglas de calidad RN-01..RN-16 y colección
**458/458** validada en su F7 (457 obligatorias + 1 opcional). Su **F6
se canceló**: no existe `decisiones_semana14.md`, y las dudas que dejó —
en especial la de roles sobre `limita_a_asignados` (prueba 227) —
quedan recogidas en `decisiones_semana15.md` §1.4 como **pregunta T**.

## Semana 13 — 7/7 fases terminadas

El tema «auditoría de acciones sensibles y cambio de contraseña propio»
(apertura del **Sprint 7**) corresponde al **mapeo HU-105 a HU-113** de la
semana; se ejecutó **por fases F1–F7** acordadas con el responsable
(**7/7 cerradas**: la suite está en **220/220**, la documentación de la
semana está escrita, el frontend en `lint`/`build` en 0 y la colección de
Postman validada **430/430** —793/793 aserciones—; la Semana 13 se entrega
**íntegra sin commitear**, decisión del responsable: el commit único lo
hace él al cierre).

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-105** | Registro de eventos de auditoría en todas las escrituras de la API: altas, ediciones, estados, anulaciones con motivo, asignaciones, reordenar etapas, sesión (LOGIN/LOGOUT/BLOQUEAR) y mantenimiento de cuentas; punto único `registrar_evento` y auditoría transaccional (sin eventos huérfanos) | ✅ Hecha | `auditoria/registrar.py`, `mixins.py` · pruebas 198–204, 209 |
| **HU-106** | API de consulta de la auditoría: listado paginado con filtros (`usuario`, `modulo`, `accion`, `tabla`, `registro`, rango de fechas y búsqueda) y detalle; **solo lectura** (POST/PATCH/PUT/DELETE → 405) | ✅ Hecha | `GET /api/auditoria/` · pruebas 204–206, 208 |
| **HU-107** | Permisos de consulta: `auditoria.ver` (en el catálogo actual solo el Administrador); sin permiso → 403 «No tienes permiso…», sin sesión → 401; la propia lectura no deja eventos | ✅ Hecha | `AuditoriaViewSet` + `PermisosAuditoria` · pruebas 205, 209 |
| **HU-108** | Inmutabilidad de la traza: trigger 25 (`fn_auditoria_inmutable`) que rechaza UPDATE y DELETE con «Los registros de auditoría no se pueden modificar ni eliminar.» | ✅ Hecha | `auditoria/0002_fn_trg_auditoria.py` · prueba 207 |
| **HU-109** | Pantalla `/auditoria` responsive: `Tabla` + `Paginacion`, filtros en URL (búsqueda, módulo, acción con las 15 etiquetas, fechas), chip de acción, detalle en `<code>` y estado vacío con nota; permiso en el menú y en la ruta | ✅ Hecha | `frontend/src/pages/Auditoria.jsx`, `api/auditoria.js` · checklist `verificacion_ui_semana13.md` |
| **HU-110** | Historial por ficha: botón **«Ver historial»** en las fichas de productor, parcela y usuario (solo con `auditoria.ver`) que llega a `/auditoria?tabla=…&registro=…` con el chip «Quitar historial de X #id» | ✅ Hecha | `ProductorFicha.jsx`, `ParcelaFicha.jsx`, `UsuarioFicha.jsx` · checklist |
| **HU-111** | Accesibilidad de la UI de auditoría: rueda en «Actualizar», botones ≥ 44 px en móvil, tablas en tarjetas ≤ 860 px y respuestas de error/permiso legibles | ✅ Hecha | checklist móvil §3 · `lint`/`build` en 0 |
| **HU-112** | Cambio de la propia contraseña: `POST /api/auth/cambiar-clave/` con contraseña actual y nueva (validadores de Django con el usuario, similitud incluida), límite de 5 intentos/hora (429 con `Retry-After`), puerta `DebeCambiarClave` (403 «Debes cambiar tu contraseña antes de continuar.» en toda la API salvo las rutas libres) y pantalla `/cambiar-clave` con redirección desde el login y `RutaProtegida` | ✅ Hecha | `usuarios/views.py`, `permisos.py`, `ratelimit.py`, `pages/CambiarClave.jsx` · pruebas 211–217, 219–220 |
| **HU-113** | Al cambiar: cierre de las demás sesiones (marca de sesión), evento CAMBIAR_CLAVE, cookies/tokens nuevos en la misma respuesta (sin relogin) y espera del segundo siguiente a la marca para no invalidar los tokens recién emitidos | ✅ Hecha | `CambiarClaveView`, `esperar_tras_marca` · pruebas 211, 217, 218 |

> **Nota:** el mapeo HU-105..HU-113 es el **mapeo propuesto** de la semana
> (los textos originales no están en el repositorio; es el que fijó el
> tablero de la Semana 12). Los docstrings del código usan los mismos
> rangos (`usuarios/views.py`, `permisos.py`, `ratelimit.py`,
> `usuarios/tests.py`).

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: app **`auditoria/`** con el modelo `Auditoria` (15 acciones en CHECK, 4 índices, sin acciones de escritura) + **2 migraciones reversibles** (`0001_auditoria.py`, `0002_fn_trg_auditoria.py` con el trigger 25) y **`usuarios/0004_debe_cambiar_clave.py`** (hoja 0004); diseño SQL actualizado (**33 tablas, 25 triggers**); verificada con `check`, `makemigrations --check` y `sqlmigrate` | ✅ Hecha | `backend/auditoria/`, `backend/usuarios/migrations/0004` · `DB_sql/01_tablas.sql`, `02_reglas_y_vista.sql` |
| **F2** | Registro en los módulos: `registrar_evento` + `AuditoriaMixin`/`_registrar_auditoria` en catalogos, productores (productores/parcelas/ubicación/asignaciones), campanias, seguimiento (actividades, incidencias, uso y reordenar etapas), produccion, sistema y usuarios (CRUD, estados, LOGIN/LOGOUT/BLOQUEAR/DESBLOQUEAR/RESTABLECER_CLAVE); IP = solo `REMOTE_ADDR` | ✅ Hecha | `auditoria/registrar.py`, `mixins.py` · 197/197 verdes en su momento |
| **F3** | Consulta y cambio de clave: `AuditoriaViewSet` (solo lectura, filtros, `auditoria.ver`), `DebeCambiarClave` con rutas libres (primera en `DEFAULT_PERMISSION_CLASSES`, antepuesta en `PermisosPorAccion.get_permissions()` y `RolViewSet`), `POST /api/auth/cambiar-clave/` con validadores, límite 5/hora, evento y cookies nuevas; marca expuesta en `login` y `/me` | ✅ Hecha | `auditoria/views.py`, `usuarios/{permisos,views,serializers,ratelimit}.py`, `config/settings.py` |
| **F4** | Pruebas **198–220** (13 de auditoría + 10 de cambio de clave): eventos por módulo, API de consulta, inmutabilidad, solo-lectura, ciclo restablecer→entrar→cambiar, puerta 403, 429 con `Retry-After`, validadores con usuario y limpieza del contador; **total 220/220 en verde**; hallazgos corregidos en el código (puerta en `get_permissions`, errores como cadena, `user` en `validate_password`, iat de segundo) | ✅ Hecha | `auditoria/tests.py`, `usuarios/tests.py` (`CambioClaveApiTests`) · `manage.py test` 220/220 (~492 s) |
| **F5** | Frontend: pantallas **`/auditoria`** y **`/cambiar-clave`**, «Ver historial» en las tres fichas, `cambiarClave` en `api/auth.js`, redirecciones en `RutaProtegida`/`Login`, `actualizarUsuario` en `SesionProvider` | ✅ Hecha | `frontend/src/pages/…`, `api/{auditoria,auth}.js`, `routes/RutaProtegida.jsx` · `lint`/`build` en 0 |
| **F6** | Documentación de la semana: `decisiones_semana13.md` (21 decisiones + preguntas Q, R, S), `api_auditoria.md`, `api_cambio_clave.md` y este checklist de navegador | ✅ Hecha | `docs/decisiones_semana13.md`, `api_auditoria.md`, `api_cambio_clave.md`, `verificacion_ui_semana13.md` |
| **F7** | Cierre: colección de Postman (392 de la Semana 12 + **38 nuevas** = **430**: 429 obligatorias + 1 opcional), validada end-to-end en la BD temporal `sigpa_ga_coleccion13` (**430/430, 793/793 aserciones**; `LOGIN_RATE_IP=120/min` por el número de logins) y borrada al terminar | ✅ Hecha | `docs/coleccion_api_semana13.json` (393–430) |

**Cierre (7/7 fases):** **220 pruebas verdes** (`manage.py test`; 23 nuevas:
13 de auditoría — 198–210— y 10 de cambio de clave — 211–220—),
`manage.py check` en 0 issues, `makemigrations --check` sin cambios,
`npm run lint` y `npm run build` en 0 problemas, colección validada
**430/430** (429 obligatorias + 1 opcional, **793/793 aserciones**) y
documentación en `decisiones_semana13.md`, `api_auditoria.md`,
`api_cambio_clave.md`, `verificacion_ui_semana13.md`,
`CONTEXTO_PROYECTO.md` y `evidencias_capitulo4.md`. **Pendiente:** solo el
commit único del responsable.


## Semana 12 — 7/7 fases terminadas

El tema «línea de tiempo de la campaña y gestión de usuarios» (cierre del
**Sprint 6**) corresponde al **mapeo HU-93 a HU-104** de la semana; se ejecutó
**por fases F1–F7** acordadas con el responsable (**F7 cerrada**: colección de
Postman validada **392/392** —726/726 aserciones—; la Semana 12 se entrega
**íntegra sin commitear**, decisión del responsable: el commit único lo hace
él al cierre).

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-93** | CRUD de etapas fenológicas por campaña: alta y edición en modal, **una etapa por campaña**, sin `DELETE` (→ 405) y sin anulación; registrar (o dejar en curso) una etapa **cierra la anterior** con su fecha de inicio, en la misma transacción con la campaña bloqueada | ✅ Hecha | `POST/PATCH /api/etapas-campania/` · pruebas 173, 175, 178, 181 · checklist `cierre_semana12.md` §3 |
| **HU-94** | Línea de tiempo de la campaña: etapas (registradas y pendientes), actividades, incidencias y cosecha en una sola cronología, con desempate etapa → actividad → incidencia → cosecha, tope de 500 y aviso `truncado` | ✅ Hecha | `GET /api/campanias/{id}/linea-tiempo/` · pruebas 182–183 · componente `LineaTiempo.jsx` |
| **HU-95** | Validaciones de etapas: etapa del cultivo de la campaña (con la lista de válidas en el mensaje), fechas dentro del período y no futuras (hora de Lima), fin ≥ inicio y coherencia cronológica por orden del catálogo (saltos permitidos) | ✅ Hecha | `EtapaCampaniaEscrituraSerializer` + `fn_validar_etapa`/triggers · pruebas 174–177, 185 |
| **HU-96** | Permisos y ámbito: `campanias.ver` para consultar y `campanias.editar` para registrar; Técnico solo en sus productores (campaña ajena → 400 «no existe», línea de tiempo ajena → 404, `registrado_por` oculto); Coordinador solo consulta | ✅ Hecha | `PermisosEtapaCampania` + `SoloSusProductores` · pruebas 180–181, 183, 197 |
| **HU-97** | Filtros del listado de etapas: campaña, etapa, cultivo, parcela, productor, `en_curso`, búsqueda y rango de fechas, con paginación y el ámbito del Técnico aplicado **antes** que los filtros | ✅ Hecha | `GET /api/etapas-campania/` · prueba **197** (añadida en F6: el listado no tenía prueba) |
| **HU-98** | Pantallas de etapas: alta/edición en modal (`EtapaFormulario`) y bloque de etapas en la ficha de campaña | ✅ Hecha | `frontend/src/pages/EtapaFormulario.jsx`, `CampaniaFicha.jsx` · checklist §3 |
| **HU-99** | `etapa_actual` en la tabla y la ficha de campaña (la última registrada; `en_curso` si no tiene fecha de fin) | ✅ Hecha | `campanias/serializers.py` (`_etapa_actual`) · prueba 184 |
| **HU-100** | Alta y edición de usuarios: username obligatorio e inmutable, nombres obligatorios, contraseña con validadores de Django, rol activo obligatorio; duplicado enlaza el registro (`usuario_existente`) | ✅ Hecha | `POST/PATCH /api/usuarios/` · pruebas 187–189 |
| **HU-101** | Desactivar y reactivar sin borrado: nunca la cuenta propia, nunca perder al último gestor de roles; desactivar cierra las sesiones abiertas | ✅ Hecha | `…/desactivar/` y `…/reactivar/` · pruebas 190–192 |
| **HU-102** | Pantalla `/usuarios` responsive: listado con búsqueda, ficha y alta/edición en modales, permisos en los botones y desplegable de roles activos | ✅ Hecha | `pages/Usuarios.jsx`, `UsuarioFicha.jsx`, `UsuarioFormulario.jsx` · checklist §3 |
| **HU-103** | Bloqueo y desbloqueo de cuenta: 5 fallos → 429 con minutos a esperar, desbloqueo manual que aclara si había bloqueo, y el «último gestor de roles» protegido en rol y estado | ✅ Hecha | `usuarios/ratelimit.py`, `…/desbloquear/` · pruebas 191, 194 |
| **HU-104** | Restablecer contraseña: acción administrativa que cierra las sesiones del usuario (marca de sesión que invalida los tokens), limpia el bloqueo y nunca actúa sobre la cuenta propia (apunta al cambio propio del Sprint 7) | ✅ Hecha | `…/restablecer-clave/` · prueba 193 |

> **Nota:** el mapeo HU-93..HU-104 es el **mapeo propuesto** de la semana (los
> textos originales no están en el repositorio). Los docstrings del código
> usan los mismos rangos (`seguimiento/views.py`, `campanias/serializers.py`,
> `usuarios/views.py`).

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: tabla **`seguimiento_etapas`** en `seguimiento/` (campania + etapa + fechas + observaciones + registrado_por, `uq_seguimiento_etapa`, `ck_seguimiento_fechas`, sin `DELETE`) + **2 migraciones reversibles** (`0009_seguimiento_etapas.py`, `0010_fn_trg_seguimiento.py` con `fn_validar_etapa` literal y **2 triggers** → **24**); diseño SQL actualizado; verificada con `sqlmigrate` | ✅ Hecha | `backend/seguimiento/models.py`, `migrations/0009`, `0010` · `DB_sql/01_tablas.sql`, `02_reglas_y_vista.sql` |
| **F2** | API de etapas: alta y edición con **cierre atómico** de la etapa en curso (`select_for_update`), validaciones en español (cultivo con lista de válidas, unicidad con enlace `etapa_existente`, período, futuro, cronología), línea de tiempo con desempate, permisos `campanias.*` y ámbito del Técnico | ✅ Hecha | `seguimiento/views.py`, `serializers.py`, `campanias/views.py` |
| **F3** | API de usuarios: `UsuarioViewSet` completo (lista con `?busqueda=`, alta 201 + ficha, edición, desactivar/reactivar, restablecer-clave, desbloquear; sin `DELETE` → 405), «último gestor de roles», `RolViewSet` para el desplegable y **marca de sesión** que invalida todos los tokens al cambiar credenciales | ✅ Hecha | `usuarios/views.py`, `serializers.py`, `autenticacion.py` |
| **F4** | Frontend: modal **`EtapaFormulario`**, componente **`LineaTiempo`** en `CampaniaFicha`, columna `etapa_actual` en tabla y ficha de campañas, pantalla **`/usuarios`** completa (ficha, formulario, permisos) y entrada en el menú | ✅ Hecha | `frontend/src/pages/…`, `components/LineaTiempo.jsx`, `api/etapasCampania.js`, `api/usuarios.js` · `lint`/`build` en 0 |
| **F5** | Verificación UI en navegador (Chrome/Edge/móvil 360 px, tres roles, estados de carga/vacío/error) — §3 del cierre | ✅ Hecha | `docs/cierre_semana12.md` §3 |
| **F6** | Documentación de la semana + **prueba 197** (listado de etapas con filtros: al revisar F5 se detectó sin cobertura; mueve el total de 196 a **197**) | ✅ Hecha | `decisiones` en `cierre_semana12.md` (18 decisiones), `verificacion_ui` en §3 |
| **F7** | Cierre: colección de Postman (311 de la Semana 11 + **81 nuevas** = **392**), validada end-to-end en la BD temporal `sigpa_ga_coleccion12` (**392/392, 726/726 aserciones**; `LOGIN_RATE_IP=120/min` por el número de logins) y borrada al terminar | ✅ Hecha | `docs/coleccion_api_semana12.json` (312–392) |

**Cierre (7/7 fases):** **197 pruebas verdes** (`manage.py test`; 25 nuevas:
14 de etapas — 173–185 y 197— y 11 de usuarios — 186–196—), `manage.py check`
en 0 issues, `makemigrations --check` sin cambios, `npm run lint` y
`npm run build` en 0 problemas, colección S12 **validada 392/392** (391
obligatorias + 1 opcional, **726/726 aserciones**) y documentación en
`cierre_semana12.md`, `api_autenticacion.md`, `CONTEXTO_PROYECTO.md` y
`evidencias_capitulo4.md`. **Pendiente:** el commit único del responsable.

## Semana 11 — 7/7 fases terminadas

El tema «incidencias» (apertura del **Sprint 6**) corresponde al **mapeo
HU-85 a HU-92** de la semana; se ejecutó **por fases F1–F7** acordadas con
el responsable (**F7 cerrada**: colección de Postman validada 311/311
—574/574 aserciones—; el commit semanal único lo cierra **el responsable
al final de la semana**; decisión 16: no commitea el agente; los commits
de F1–F3 —`2125af9`, `74ed665`, `dc81057`— quedaron de antes de esa
indicación y el responsable puede reorganizarlos).

| HU | Descripción (propuesta) | Estado | Evidencia |
|---|---|---|---|
| **HU-85** | Listar, ver, registrar y editar incidencias: listado con filtros y búsqueda, ficha completa con trazabilidad y alta/edición en modal; campaña inmutable al editar y sin `DELETE` → 405 | ✅ Hecha | `GET/POST/PATCH /api/incidencias/` · pruebas 156, 161, 163, 167 · checklist `verificacion_ui_semana11.md` |
| **HU-86** | Validaciones del registro: campaña que admite registros, fecha dentro del período y no futura (hora de Lima), severidad de las tres, descripción obligatoria, superficie ≥ 0 y ≤ sembrada, agente activo y solo en tipos biológicos, producto ≤ 100; duplicadas en serializador (400) y triggers | ✅ Hecha | `IncidenciaEscrituraSerializer` + `fn_validar_incidencia`/`trg_incidencias_fecha` · pruebas 157–160, 172 |
| **HU-87** | Permisos por acción y ámbito: Administrador los 4 `incidencias.*`; Técnico `ver/crear/editar` solo en sus productores (objeto ajeno → 404; `registrado_por` oculto); Coordinador solo `ver` | ✅ Hecha | `PermisosIncidencia` + `SoloSusProductores` · pruebas 164–166, 171 |
| **HU-88** | Anular con motivo obligatorio y reactivar (solo si la campaña sigue abierta y la fecha en su período); anuladas fuera de resúmenes, dataset e historial | ✅ Hecha | `POST …/anular/` y `…/reactivar/` · pruebas 162, 165 · checklist (ficha con panel de anulación) |
| **HU-89** | Resumen de incidencias en la ficha de campaña (`resumen_incidencias`: total, por severidad, severidad máxima, última fecha y mayor superficie; vacío = ceros), historial agrupado por campaña en la parcela (`?incluir_anuladas=1`) e `incidencias_activas`/`ultima_incidencia` en el productor | ✅ Hecha | `campanias/serializers.py`, `productores/serializers.py` · pruebas 168, 169 |
| **HU-90** | Pantalla `/incidencias` responsive: 10 filtros en la URL (incluido el de campaña que enlaza «Ver todas»), `Tabla`+`Paginacion`, modales de alta/ficha y permisos en los botones; entrada «Incidencias» en el menú | ✅ Hecha | `pages/Incidencias.jsx`, `IncidenciaFormulario.jsx`, `IncidenciaFicha.jsx`, `opcionesMenu.js`, `App.jsx` · checklist `verificacion_ui_semana11.md` |
| **HU-91** | Que las incidencias anuladas **no cuenten** en el dataset: CTE `inc_c` con `WHERE NOT i.anulada` y `n_incidencias`/`severidad_max` idénticos a `resumen_incidencias` | ✅ Hecha | `DB_sql/02_reglas_y_vista.sql` (`inc_c`) · prueba 170 |
| **HU-92** | Verificación de la semana: checklist de UI en navegador y colección de Postman | ✅ Hecha | checklist `verificacion_ui_semana11.md` (F5) · `coleccion_api_semana11.json` (F7) — **validada 311/311 (574/574 aserciones)** |

> **Nota:** el mapeo HU-85..HU-92 es el **mapeo propuesto** de la semana (los
> textos originales no están en el repositorio). Los docstrings del código
> usan HU-85 (CRUD), HU-88 (anular/reactivar) y HU-89 (resumen/historial).

| Fase | Contenido | Estado | Evidencia |
|---|---|---|---|
| **F1** | Estructura: tabla **`incidencias`** en `seguimiento/` (14 columnas, `anulada`+`motivo_anulacion` con CHECK «anulada ⇒ motivo», 2 índices) + **2 migraciones reversibles** (`seguimiento/0007_incidencias.py`, `0008_fn_trg_incidencias.py` con `fn_validar_incidencia` literal y **3 triggers**); diseño SQL actualizado (función, triggers y CTE `inc_c` con `WHERE NOT i.anulada`); **22 triggers** en total; verificada con `sqlmigrate` | ✅ Hecha | `backend/seguimiento/models.py`, `migrations/0007`, `0008` · `DB_sql/01_tablas.sql`, `02_reglas_y_vista.sql` · commit `2125af9` (ver decisión 16) |
| **F2** | API completa: listado con **12 filtros + búsqueda**, detalle, alta, edición, `anular/` y `reactivar/` (sin `DELETE` → 405); `resumen_incidencias` en el detalle de campaña, `incidencias` agrupado por campaña en parcela e `incidencias_activas`/`ultima_incidencia` en el productor; permisos `incidencias.*` por acción, ámbito del Técnico (404; anular sin permiso → 403), `registrado_por` oculto | ✅ Hecha | `views.py`, `serializers.py`, `urls.py` + `campanias/`, `productores/` · commit `74ed665` |
| **F3** | Pruebas de la semana: **17 nuevas (156–172)** — validaciones, edición, anular/reactivar, 405, permisos/ámbitos, filtros, resumen/historial/dataset, `registrado_por` oculto y triggers/reversibilidad; hallazgos ajustados (403 ≠ 404 en anular, decimales crudos con `float()`, fecha SQL entrecomillada) | ✅ Hecha | `seguimiento/tests.py` · **172 en verde** · commit `dc81057` |
| **F4** | Pantallas: **`/incidencias`** (10 filtros en URL, `Tabla`+`Paginacion`), alta/edición en modal (`IncidenciaFormulario`, agente solo biológicos, campaña inmutable), ficha en modal (`IncidenciaFicha` con anular/reactivar), secciones **«Incidencias»** en `CampaniaFicha`, historial en `ParcelaFicha` y contadores en `ProductorFicha`; entrada en el menú; **corrección:** la pantalla ahora lee y filtra por `?campania=` (el enlace «Ver todas») | ✅ Hecha | `pages/Incidencias.jsx`, `IncidenciaFormulario.jsx`, `IncidenciaFicha.jsx`, `CampaniaFicha.jsx`, `ParcelaFicha.jsx`, `ProductorFicha.jsx`, `api/incidencias.js` · `lint`/`build` en 0 |
| **F5** | Verificación integral: **172 pruebas** + `check` en 0 issues + `makemigrations --check` sin cambios + checklist de UI (Chrome/Edge/móvil, permisos por rol, estados) | ✅ Hecha | `seguimiento/tests.py` · `docs/verificacion_ui_semana11.md` |
| **F6** | Documentación de la semana | ✅ Hecha | `decisiones_semana11.md` (20 decisiones + pregunta N), `api_incidencias.md`, `comparacion_semana11.md` (14 columnas, 8 restricciones, 0 índices extra, 22 triggers) |
| **F7** | Cierre: colección de Postman (270 de la Semana 10 + 41 nuevas = **311**), verificación final y entrega para el commit único del responsable | ✅ Hecha | `docs/coleccion_api_semana11.json` (271–311) — **validada 311/311 (574/574 aserciones)** en la BD temporal `sigpa_ga_coleccion11`, borrada al terminar · `evidencias_capitulo4.md` + `CONTEXTO_PROYECTO.md` §3/§6 |

**Cierre (7/7 fases):** 172 pruebas verdes (`manage.py test`;
17 nuevas), `manage.py check` en 0 issues, `makemigrations --check` sin
cambios, `npm run lint` y `npm run build` en 0 problemas, colección S11
**validada 311/311** (310 obligatorias + 1 opcional, **574/574
aserciones**) y documentación en `decisiones_semana11.md` (20
decisiones), `api_incidencias.md`, `comparacion_semana11.md` y
`verificacion_ui_semana11.md`. **Pendiente:** el commit único del
responsable.

## Semana 10 — 7/7 fases terminadas

El tema «clima» (cierre del **Sprint 5**) corresponde al **mapeo HU-76 a
HU-84** de la semana; se ejecutó **por fases F1–F7** acordadas con el
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

## Siguiente (Semana 17, 25–31 ene)

Continúa el **Sprint 8 en curso** (lo abrieron las semanas 15 y 16).
Reparto provisional a confirmar con el responsable:

| Tema | Nota |
|---|---|
| **Commit único de las Semanas 13, 14, 15 y 16** | El responsable ejecuta el commit al visto bueno (las cuatro semanas entregadas sin commitear; sus colecciones ya están validadas: 430/430, 458/458, 488/488 y 506/506) |
| Reportes descargables (RF-62, resto del dashboard) + ML (modelo de regresión: rendimiento predicho, `RENDIMIENTO_BAJO` y predicciones) | Temas grandes del backlog; el ML libera además la fila 1 y la decisión 2 de `decisiones_semana15.md` §1.1; el panel de indicadores ya está (Semana 16) |
| Olvido de contraseña / recuperación de cuenta | Pendiente desde semanas anteriores |
| Preguntas pendientes del responsable | F, G, H, densidad, I, umbrales y quintal, J, K, L, M, etapas fenológicas, N (conservación y acceso a la auditoría), Q/R/S de `decisiones_semana13.md` (lecturas, purga, XFF) y la **T** de `decisiones_semana15.md` (`limita_a_asignados`): enviar en un solo mensaje con fecha límite |

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
13. **¿Criterio para asignar la severidad de la incidencia?** (Semana 11,
     pregunta N): implementado que **quien registra elige** (BAJA, MEDIA o
     ALTA, solo exige uno de los tres); si el responsable fija un criterio
     (p. ej. % de la superficie afectada) se añade como ayuda en el
     formulario o como cálculo — **CONFIRMAR**.
