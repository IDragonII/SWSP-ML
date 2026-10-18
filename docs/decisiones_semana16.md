# Decisiones — Semana 16: panel de indicadores (dashboard)

> Sprint 8 (en curso), semana del **18 al 24 de enero** (calendario
> referencial; sin feriados). Alcance aprobado: **RF-62** (reportes y
> panel de indicadores; esta semana el **panel de indicadores**, los
> reportes descargables quedan fuera), con el mapeo **HU-133..HU-140**
> propuesto (los textos originales de los HU no están en el
> repositorio; los RF se verificaron leyendo `requerimientos.tex` del
> documento real, **fuera del repositorio y sin modificarlo** — el
> `.tex` queda en su v1.0; los cambios propuestos se documentan aquí).
> **Sin commitear** (continúa la decisión de las semanas 11-15: el
> commit único lo hace el responsable). Ver también:
> `api_dashboard.md`, `verificacion_ui_semana16.md`,
> `evidencias_semana16.md` y el cierre en `tablero.md`.
> Estado: **F1..F7 ejecutadas (7/7); colección 506/506 validada en F7
> — 504 obligatorias + 2 opcionales, 939/939 aserciones —; suite 279/279.**

## 1. Decisiones

### 1.1 Reglas de negocio

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 29 | **Panel de indicadores (RF-62, HU-133..HU-140)** | Pantalla única en **`/`** (Inicio) con cuatro bloques de **solo lectura** y sin escritura de ningún tipo: (a) tarjetas de resumen (productores activos/inactivos/con campaña activa, superficie sembrada de campañas activas, campañas aptas para entrenar, revisiones pendientes y alertas), (b) campañas por estado (los 5 estados, con `?periodo=`), (c) producción agrupada por cultivo o distrito con los filtros del listado de producciones y (d) opciones de filtro (períodos, cultivos y ubicación). Todo respeta el **alcance del usuario**: el Técnico solo ve sus productores asignados (mismo filtro que desde la Semana 4). |
| 30 | **Rendimiento ponderado manda (HU-136)** | El rendimiento del panel es **ponderado** (kg ÷ superficie cosechada), el mismo que se calcula al cerrar la campaña; el promedio simple (`rendimiento_promedio_kg_ha`) se muestra **solo como comparación**, siempre al lado. Cada fila marca **`provisional`** si queda alguna campaña sin cerrar y **`pocos_datos`** con menos de 3 campañas (HU-139). Las producciones con `requiere_revision=true` **quedan fuera** del agregado hasta revisarse. |
| 31 | **Aptas para entrenar = la vista del dataset** | `aptas_entrenar` cuenta campañas **CERRADA** cuya producción mantiene `incluir_en_entrenamiento` — **las mismas condiciones del WHERE** de `vw_dataset_entrenamiento` (`DB_sql/02_reglas_y_vista.sql:463-464`, prueba 266). Si el diseño de la vista cambia, este conteo debe cambiar con él. |
| 32 | **Cifras sin datos: `null`, nunca cero falso** | Los decimales del panel salen como **texto con 2 decimales** (convención global de la API) y los agregados vacíos son **`null`** (p. ej. totales de producción sin filas): la interfaz los pinta como «—». Los conteos de campañas por estado sí llevan **ceros explícitos** (los 5 estados siempre) porque la serie tiene que estar completa para graficar. |
| 33 | **Alertas por tipo en el panel (HU-138)** | `GET /api/alertas/resumen/` mantiene `pendientes` (la insignia del menú **no cambia**) y añade **`por_tipo`** con ceros para los 3 tipos, para la franja del dashboard. Franja y listado usan el mismo ámbito que el resto de alertas (`alertas.ver`); un rol con `dashboard.ver` pero sin `alertas.ver` no ve la franja. |

### 1.2 Decisiones técnicas

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 34 | **App `backend/dashboard/`: solo lectura, sin modelos** | App Django nueva (`DashboardConfig`) **sin `models.py`, sin migraciones y sin tablas**: las cuatro acciones son agregados de las tablas de negocio existentes. Permiso **`dashboard.ver`** (sembrado en la Semana 2, `usuarios/migrations/0002_datos_iniciales.py:31`) asignado a Administrador, Técnico y Coordinador → **cero migraciones nuevas** (`makemigrations --check` sin cambios). ViewSet `GenericViewSet` con `@action(detail=False)` GET; **POST/PUT/PATCH/DELETE → 405**, sin sesión → 401 y sin permiso → 403 (con el portón de cambio obligatorio de contraseña por delante). |
| 35 | **`filtrar_asignados` compartida** | La función pura `filtrar_asignados(queryset, usuario, campo="pk")` se extrajo de `SoloSusProductores._filtrar_asignados` en `productores/views.py` (los 54 tests de `productores` y `alertas` siguen en verde) y **la reutiliza el dashboard** en las 4 acciones: productores, campañas (`parcela__productor_id`), producciones (`campania__parcela__productor_id`) y alertas (`productor_id`). |
| 36 | **Endpoints y errores** | `GET /api/dashboard/resumen/`, `…/campanias-estado/` (`?periodo=`), `…/produccion/` (`?agrupar=cultivo\|distrito` por defecto cultivo; otro → 400 «Use cultivo o distrito.»; filtros `periodo`/`cultivo`/`provincia`/`distrito`/`comunidad` con la misma lectura numérica que el listado: no numérico → 400 «Debe ser un id numérico.») y `…/filtros/` (`?provincia=`/`?distrito=` estrechan los niveles inferiores; id inexistente → 400 «La provincia indicada no existe.» / «El distrito indicado no existe.»). `generado_en` es la hora de **America/Lima** con huso. Contrato completo en `api_dashboard.md`. |
| 37 | **Presupuesto de consultas fijo** | Cada lectura tiene número fijo de consultas SQL, fijado por prueba (275): `resumen` **12**, `campanias-estado` **4**, `produccion` **5** y `filtros` **8**. Si alguien añade un `Count` de más, la prueba grita. Hallazgo del entorno: **DRF ejecuta `initial()` (autenticación) antes de comprobar el método** → sin sesión un POST a una acción responde **401**, no 405; con sesión, 405 (pruebas 276 y 278). |
| 38 | **Frontend: Recharts en Inicio, bloques independientes** | **Recharts 3.10.1** (instalado en F4; el bundle supera el aviso de 500 kB de Vite — aceptado: es la librería de gráficos decidida en el plan). `Inicio.jsx` se reescribe conservando saludo y módulos, y añade el panel **solo si el rol tiene `dashboard.ver`**: tarjetas (`dl.tarjetas`), franja de alertas (solo con `alertas.ver`), filtros en URL (`useSearchParams`; la ubicación es **en cascada**: cambiar provincia limpia distrito y comunidad), gráficos de barras con `role="img"` + etiqueta narrada, tabla con el componente `Tabla` (pasada a tarjetas ≤ 860 px) y estados vacíos/error **por bloque** (un bloque caído no tumbar el panel). La ruta `/` no exige permiso: un rol sin `dashboard.ver` ve la página de siempre. |
| 39 | **Verificación: 279 pruebas verdes** | Pruebas **263–279** (17, `backend/dashboard/tests.py`): resumen 263–266, producción 267–269 y 271–273, alcance/filtros/consultas/rutas 270 y 274–279; **total 279/279 en verde**, `manage.py check` en 0 issues, `makemigrations --check` sin cambios y `npm run lint` / `npm run build` en 0. **Hallazgos corregidos durante F3**: (a) el listado de producciones vive en **`/api/producciones/`** (plural); (b) Django 5 exige `values(clave=F("campo"))` para alias; (c) `fn_validar_produccion` exige `superficie_cosechada ≤ superficie_sembrada` (datos de prueba ajustados); (d) `requiere_revision` vive en **Produccion**, no en Campania; (e) tras cortar la salida del runner con `Select-String -First` la BD de pruebas quedaba sin destruir → soltar `test_sigpa_ga` a mano y redirigir la salida a fichero. |
| 40 | **Datos de demostración mínimos (F7)** | Comando nuevo **`datos_demostracion`** (`backend/sistema/management/commands/`, idempotente): crea **lo mínimo** para que el panel se vea con datos — un puñado de productores/parcelas/campañas/producciones/actividades **inventados y marcados como tales** con la marca «Datos de demostración inventados (Semana 16)» (decisión de la Semana 4: nada de datos reales). No sustituye a la lista real de ubicaciones ni se usa en pruebas ni en la colección. Probado en F7: la primera ejecución siembra y la segunda informa «ya existen» sin duplicar. |

### 1.3 Proceso y calidad

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 41 | **Sin commitear** | Continúa la decisión de las Semanas 11-15: la Semana 16 se entrega **entera sin commitear**; el commit único (Semanas 13, 14, 15 y 16 juntas) lo hace el responsable tras el visto bueno. |
| 42 | **Documentación de la semana** | **Documentos separados** (criterio del responsable): `decisiones_semana16.md` (este), `api_dashboard.md`, `verificacion_ui_semana16.md` y `evidencias_semana16.md`, más la actualización de `tablero.md` y `CONTEXTO_PROYECTO.md`. El `requerimientos.tex` **sigue sin tocarse** (solo lectura, v1.0): cualquier cambio propuesto queda anotado en estos documentos. |
| 43 | **Responsive, ruedas y permisos en el botón** | Continúan las decisiones de UI de semanas anteriores: tablas con el componente `Tabla` (tarjetas ≤ 860 px), rueda dentro del botón en toda operación (el panel es de solo lectura: solo aplica a los formularios existentes), «sin botón, sin modal» y checklist en Chrome 1366×768, Edge 1024×768 y Móvil 360×780. |
| 44 | **Sin datos reales; BD temporales** | Continúa la decisión de la Semana 4: ni pruebas ni colección usan datos reales; `.credenciales` nunca en la colección; las BD temporales y el servidor del 8001 se borran/detienen al terminar cada fase. |
| 45 | **Colección Postman y corte del HU-123** | `docs/coleccion_api_semana16.json`: parte de la de la Semana 15 (**488**) y añade los ítems del panel (**18 nuevos**, todos obligatorios, numerados 489–506 → **506 en total: 504 obligatorias + 2 opcionales**). Validada end-to-end con el pipeline habitual de F7 (BD temporal `sigpa_ga_coleccion16` con migrate + usuarios + **siembra previa** de F7, servidor **8001** con `LOGIN_RATE_IP=120/min` y `validador/validar.js`): **506/506 peticiones y 939/939 aserciones**; la BD temporal se borró al terminar y el servidor se detuvo. El **panel de calidad HU-123** (pruebas 280–284 y +10 peticiones) quedó **opcional con holgura** según el responsable: el corte mínimo de la semana es **279 pruebas / 506 peticiones** y no se alcanzó la holgura para las 5 pruebas extra. |

### 1.4 Preguntas abiertas

| # | Pregunta | Estado / para cuándo |
|---|----------|----------------------|
| U | **Reglas de la semana (5 respuestas del responsable)** | **Resueltas al abrir la Semana 16**: (a) la semana se entrega **sin commitear**; (b) el `requerimientos.tex` es de **solo lectura** y los cambios propuestos se documentan en `docs/`; (c) el panel de calidad HU-123 es **opcional con corte claro** (279/506 como mínimo); (d) las preguntas de esta semana usan la **letra U**; (e) los datos de demostración se crean pero **mínimos** y marcados como inventados. Sin preguntas nuevas que bloquear. |
| — | **Nota de letras** | Las letras **A..T están usadas** (`cierre_semana12.md` §1.4, `decisiones_semana13.md` §1.4, `decisiones_semana15.md` §1.4). **Siguiente letra libre: V.** |
| A–T | (las heredadas de semanas anteriores) | Siguen anotadas en `cierre_semana12.md` §1.4, `decisiones_semana13.md` §1.4 y `decisiones_semana15.md` §1.4; ninguna cambia con esta semana. |

### 1.5 Notas de contexto

- **Mapeo HU de la semana** (mapeo propuesto, anclado al RF-62 del `.tex`): **HU-133** (tarjetas de resumen del panel), **HU-134** (superficie sembrada de campañas activas), **HU-135** (campañas agrupadas por estado, con período opcional), **HU-136** (producción agrupada por cultivo/distrito con rendimiento ponderado y filtros), **HU-137** (opciones de filtro dentro del alcance, con cascada), **HU-138** (alertas pendientes por tipo), **HU-139** (señales `provisional` y `pocos_datos`) y **HU-140** (`generado_en` en hora de Lima). Los docstrings del código usan ese rango (`backend/dashboard/views.py`, `tests.py`).
- **Qué ve cada rol**: los tres roles del sistema (Administrador, Técnico y Coordinador) tienen **`dashboard.ver`** desde el seed de la Semana 2; cada bloque aplica el **alcance** del usuario: el Técnico solo ve sus productores, su superficie, sus producciones y sus alertas (pruebas 270, 274 y 277).
- **Pruebas**: 279 en total (`manage.py test`); las de la semana son la 263 a la 279 (`backend/dashboard/tests.py`, 17 pruebas). Constantes de consultas: 12 / 4 / 5 / 8 (prueba 275).
- **Rendimiento ponderado vs simple**: el ponderado (kg ÷ superficie cosechada) es el que se calcula en el cierre de campaña (`fn_validar_produccion`); el promedio simple (media de `rendimiento_kg_ha` redondeado por fila) se muestra solo para comparar y nunca manda (pruebas 268 y 269).
- **Numeración de sprint**: Semana 16 = segunda semana del **Sprint 8** (lo abrió la Semana 15).
- **`.tex` sin tocar**: el RF-62 y los HU-133..HU-140 se leyeron de `requerimientos.tex` **solo para verificar**; el documento real queda en su v1.0, fuera del repositorio (decisión del responsable).
