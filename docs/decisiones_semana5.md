# Decisiones — Semana 5: catálogos de campañas

> Sprint 2, semana del 2 al 8 de noviembre. Documento análogo a
> `decisiones_semana4.md`: recoge lo acordado con el responsable y las reglas
> que guían la implementación de esta semana.
> Estado: **aprobadas en el plan de la semana** (el responsable dio el «ok»
> al plan por fases F1–F8, que incluía estas decisiones).

## 1. Reglas de negocio (catálogos)

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 1 | **Alcance: los 8 catálogos, nada más** | Cultivos, variedades, etapas fenológicas, unidades, tipos de actividad, recursos, tipos de incidencia y agentes (tablas 46–115 del diseño). Los permisos `catalogos.ver/crear/editar/desactivar` **ya existían** (sembrados en `usuarios/0002`, dentro de los 55): no toca migrar permisos. El **esqueleto de campañas** (`campanias`) queda para la semana siguiente: estaba bloqueado por los catálogos. |
| 2 | **Los datos CONFIRMAR entran solo por comando** | `python manage.py cargar_catalogos`: los 18 datos marcados CONFIRMAR en el diseño (quintal, etapas, agentes, variedades y recursos) **nunca se sembran por migración**; la migración `catalogos.0002` aporta las **26 filas fijas** (3 cultivos, 7 tipos de actividad, 8 tipos de incidencia y 8 unidades) y el comando **es idempotente** (no pisa filas ya editadas). Total **44 filas**. Verificado con dos pasadas seguidas: `18 creadas · 26 existían` → `0 creadas · 44 existían`. |
| 3 | **Nada se borra** | `DELETE` responde **405** en los 8 recursos (misma regla 6 de la Semana 3): solo `PATCH /{recurso}/{id}/estado/` con `{"activo": true\|false}`. Los **tipos de actividad además no admiten altas** (`POST` → 405): su código es fijo, los 7 sembrados. |
| 4 | **Las etapas no tienen estado** | Lectura y escritura **sin campo `activo`** y sin acción `…/estado/`: las etapas se ocultan **desactivando su cultivo**. `?activo=` responde `400 {"activo": "Las etapas no tienen estado."}`. Unicidad **(cultivo, nombre)** y **(cultivo, orden)** con `orden` entre 1 y 1000. |
| 5 | **La unidad base está protegida** | Cada tipo de unidad ya tiene la suya sembrada (Kilogramo, Hectárea, Metro cúbico, Jornal y Hora): **no se puede crear** otra (`No se pueden crear unidades base: cada tipo ya tiene la suya.`), **no se puede convertir** una existente (`No se puede convertir una unidad existente en base.`), **no se desactiva** (`Las unidades base no se pueden desactivar.`) y su `factor_a_base` debe ser 1. |
| 6 | **Siembra y Cosecha no se desactivan** | El `PATCH …/estado/` de tipos de actividad con `activo: false` sobre `SIEMBRA` o `COSECHA` responde `400 Siembra y Cosecha no se pueden desactivar.` (validado en la API y en el serializador). El código no se envía al editar: solo `nombre` y `activo`. |
| 7 | **Variedad y etapa dependen del cultivo activo** | Dar de alta una variedad/etapa sobre un cultivo inactivo responde `400 El cultivo indicado no existe o está inactivo.` El desplegable de **variedades** exige además `cultivo__activo=True`; el de **etapas**, cultivo activo. Los desplegables (`?desplegable=1`) muestran **solo activos** y en lista corta. |

## 2. Decisiones técnicas

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 8 | **App nueva `catalogos/` con 2 migraciones** | `catalogos.0001_initial.py` (8 tablas con los constraints del diseño: únicos, checks y `uq_unidad_base_tipo`) y `catalogos.0002_datos_iniciales.py` (las 26 filas fijas, idempotente y **reversible sin borrar lo referenciado**). Se cumplen las «2 migraciones propias» de la semana. |
| 9 | **Una vista base para los 8 catálogos** | `VistaCatalogo` (list/retrieve/create/update **sin DELETE**) y `VistaCatalogoConEstado` (más `…/estado/`) en `catalogos/views.py`, reutilizando `PermisosCatalogo`, `BusquedaPorNombre` e `_id_numerico` de `productores`. `?desplegable=1` devuelve la **lista corta sin paginar** (respeta `_BOOLEANOS_SI`: `1`, `true`, `si`, `sí`…) y `POST`/`PATCH` responden con el **serializador de lectura** (incluye `id` y la jerarquía anidada). |
| 10 | **Unicidad normalizada en la API, en español** | Sin `UniqueValidator` de DRF (responde en inglés y no normaliza): la unicidad de `nombre` se resuelve en `validate_nombre` con **`casefold` + colapso de espacios** (mayúsculas y espacios dobles no crean duplicados) y con mensajes **por recurso** («Ya existe un cultivo con ese nombre.», «Ya existe una unidad…», etc.). Las unicidades compuestas (cultivo+nombre, cultivo+orden) van en `validate()`. |
| 11 | **Reordenado de etapas atómico** | `POST /api/etapas-fenologicas/reordenar/` con `{"cultivo": id, "orden": [ids]}`: primero todas las etapas pasan a `orden + 10000` y después cada una recibe su posición, dentro de `transaction.atomic()` — así `uq_etapa_orden` **nunca choca a mitad**. La lista debe ser exacta (mensaje `Debe ser la lista completa de ids de etapas.`) y la acción exige **`catalogos.editar`** (no basta `catalogos.ver`). |
| 12 | **Una sola pantalla de catálogos, con pestañas** | `/catalogos` con las 8 pestañas en la URL (`?catalogo=`), configuración **declarativa** en `pages/catalogosConfig.js` (columnas, campos y etiquetas en español de las listas cerradas), listado con `Tabla` + `Paginacion` (20), filtros en la URL, alta y edición en **modal** (decisión 19 de la Semana 4), confirmación de estado en `Modal` y feedback con **toast** (decisión 20). **Los permisos se ven en el botón** (sin botón, sin modal): el menú y la ruta exigen `catalogos.editar` —solo el Administrador entra—, y crear/editar/desactivar sus respectivos `catalogos.*`. **Config `alta:false`** en tipos de actividad y **`estado:false`** en etapas: la config manda, sin casos especializados en la vista. |
| 13 | **Colección de Postman: 93 peticiones** | `docs/coleccion_api_semana5.json` = las **48 de la Semana 4 + 45 nuevas** de los catálogos (049–093: sesión → cultivos → variedades → etapas con reordenado → unidades → tipos de actividad → recursos/incidencias/agentes → Coordinador 200/403). **Validada 93/93** contra el servidor. En el camino se corrigió el **validador** de la Semana 4 (los regex `eql/match/above` no casaban con `pm.response.json()` y **no evaluaban ninguna aserción**) y una aserción errónea de la petición 009 (`creado_por` es el username, no `{id}`), que el regex roto había ocultado. |
| 14 | **Cierre técnico de la fase** | **67 pruebas** verdes (`manage.py test`; 14 nuevas de la semana sobre las 53 de la Semana 4), `manage.py check` en 0 issues, `makemigrations --check` sin cambios, `npm run lint` y `npm run build` en 0 problemas, y `docs/comparacion_semana5.md` con **37/37 columnas, 28/28 restricciones y 44/44 datos** frente al diseño SQL. |

## 3. Proceso y calidad

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 15 | **Commits por semana** | Continúa la decisión 15 de la Semana 4: **un único commit al final de la semana**, hecho por el responsable. El agente entrega solo el **nombre del commit** al cierre (F8). No hay commits por fase. |
| 16 | **Responsive siempre** | Continúa la decisión 14 de la Semana 4: requisito transversal en toda pantalla (pestañas, tablas en tarjetas ≤860 px, modales a ancho completo, áreas táctiles ≥ 44 px, sin scroll horizontal en móvil, revisado en 1366/768/390 px). Checklist en `docs/verificacion_ui_semana5.md`. |
| 17 | **Verificación de pantallas** | Continúa la decisión 16 de la Semana 4: checklist manual sin dependencias nuevas; el agente ejecuta `lint` + `build` y prepara el documento, el responsable lo ejecuta en navegador y anota. |

## 4. Preguntas abiertas

| # | Pregunta | Estado / para cuándo |
|---|----------|----------------------|
| A | ¿Entregó el responsable la lista real de ubicaciones? | Pendiente desde la Semana 3; al recibirla: `cargar_ubicacion` y retirar `ejemplo_ubicaciones.csv` |
| B | Confirmar la regla de **enmascarado de DNI/teléfono** (decisión 4 de la Semana 3) | ⚠️ Sigue pendiente; rige la propuesta (Administrador y Técnico ven completo, Coordinador enmascarado) |
| D | Botón «usar mi ubicación actual» (item *estirada*) | Solo funciona en `https://` o `localhost`; decidir en la demo |
| E | Esqueleto de campañas (`campanias`, ciclo por parcela) | Siguiente tema de la lista (bloqueado hasta ahora por los catálogos) |

## 5. Notas de contexto

- **Qué ve cada rol en la API**: Administrador los 4 permisos `catalogos.*`; **Técnico y Coordinador solo `catalogos.ver`** (semilla `usuarios/0002`: el Técnico no tiene `catalogos.crear/editar` y el Coordinador solo recibe `*.ver`), así que `POST`/`PATCH` → 403 (colección 093). Como el menú y la ruta exigen `catalogos.editar`, **solo el Administrador ve y entra en la pantalla**.
- **Filtros**: `?activo=` admite `1/true/yes/si/sí/verdadero` y `0/false/no/falso` (otro valor → `400 Use true o false.`); `?busqueda=` busca por `nombre` (y por `codigo` además en tipos de actividad); filtrar por una **opción inválida de lista cerrada** (`?categoria=NOPE`) devuelve **lista vacía (200)**, no error.
- **Re-ejecución de la colección**: como en la Semana 4 (precedente `SEMANA4R2`), al repetir la validación sobre una BD con datos ya creados se cambian las variables `sufijo` y `dni_productor` (hooks del validador); en una BD limpia funciona con los valores por defecto (`SEMANA5`).
- Los mensajes `Ya existe…` de cada recurso están tabulados en `api_catalogos.md`; los 404 responden `{"detail": "No encontrado."}` (manejador propio de la Semana 4) y los mensajes de permiso/405 son los de la Semana 2/3.
- La validación de la colección (93/93) se ejecutó con el servidor `runserver 127.0.0.1:8000` en marcha y las credenciales de `.credenciales` (fuera de Git); el script del validador vive en el temporal del agente, igual que el de la Semana 4.
