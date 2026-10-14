# Decisiones — Semana 9: recursos e insumos

> Sprint 4, semana del 30 de noviembre al 6 de diciembre. Documento análogo a
> `decisiones_semana8.md`: recoge lo acordado con el responsable y las reglas
> que guían la implementación de esta semana (HU-67 a HU-75, mapeo propuesto).
> Estado: **aprobadas en el plan de la semana** (el responsable dio el «ok»
> al plan por fases F1–F7, que incluía estas decisiones).

## 1. Reglas de negocio (recursos e insumos)

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 1 | **Alcance: la tabla `uso_recursos` de la campaña** | La tabla (13 columnas del diseño, en la app `seguimiento/`) guarda cada recurso consumido por una campaña o por una actividad concreta (siembra, fertilización…): semilla, fertilizante, mano de obra, combustible. Alimenta las variables del ML por hectárea (semilla, fertilizante, jornales). HU-67 (listado y filtros), HU-68 (ficha y uso vinculado a actividad), HU-69 (alta y edición), HU-70 (unidad por categoría), HU-71 (permisos y ámbito), HU-72 (anular), HU-73 (reactivar), HU-74 (resumen en campaña) y HU-75 (protección de unidades). **Completa HU-48**: la anulación de una actividad arrastra en cascada sus usos de recursos. |
| 2 | **La categoría del recurso fija el tipo de unidad** | Cada recurso pertenece a una de las 8 categorías (`SEMILLA`, `FERTILIZANTE`, `COMBUSTIBLE`, `MANO_OBRA`, `FITOSANITARIO`, `MAQUINARIA`, `RIEGO`, `OTRO`) y su `tipo_unidad` determina qué unidades admite al registrarlo: `MASA` (kg, qq, t…), `VOLUMEN` (L, m³), `LABOR` (jornal) o `TIEMPO` (hora). El formulario solo lista las unidades activas de ese tipo; una unidad de otro tipo se rechaza en la API con el error «La unidad no es válida para el tipo de recurso.» |
| 3 | **La conversión a la unidad base la hace la base** | El cliente envía `cantidad` + `unidad_id`; `fn_uso_recurso` reescribe `cantidad_base` (= cantidad × factor de conversión de la unidad a su base: kg, L, jornal, hora). Los campos calculados (`cantidad_base`) y protegidos son de solo lectura por API. |
| 4 | **Cascada atómica al anular una actividad** | Cuando se anula una actividad con usos de recursos **activos**, esos usos se anulan en la **misma transacción** y con el **mismo motivo** (`recursos_anulados` en el resumen). No se puede anular la actividad «a medias»: o se propagan todos los usos o no se anula nada. |
| 5 | **Anulación lógica, sin `DELETE`** | No hay `DELETE` en `/api/usos-recursos/` → **405** (continuidad del «nada se borra» de las semanas previas). La anulación es con motivo obligatorio y deja el registro con `ANULADA` + `motivo_anulacion`; la reactivación limpia el motivo y devuelve el estado a activo. |
| 6 | **Ámbito y permisos por acción** | `PermisosUsoRecurso`: `list`/`retrieve` → `recursos.ver`, `create` → `crear`, `update`/`partial_update` → `editar`, `anular`/`reactivar` → `desactivar`. Sembrados en `usuarios/0002`: Administrador los 4, **Técnico** `ver/crear/editar` (anular → 403), **Coordinador** solo `ver` (crear → 403). El ámbito del Técnico se limita a los usos de **sus productores asignados** (usos ajenos → 404); el chequeo de permiso va **antes** de `get_object`. |
| 7 | **Resumen de recursos en la ficha de campaña** | `GET /api/campanias/{id}/` incluye `resumen_recursos`: suma de `cantidad_base` agrupada por categoría (con su unidad base), **excluyendo** los usos anulados (incluidos los de la cascada), más el recuento de registros. La ficha de campaña en React lo muestra en la sección «Resumen de recursos». |

## 2. Decisiones técnicas

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 8 | **Dos migraciones reversibles** | `seguimiento.0003_uso_recursos.py` (la tabla, con las 13 columnas, `anulada`+`motivo_anulacion` y los checks) y `seguimiento.0004_funciones_y_triggers_uso_recursos.py` (`fn_uso_recurso`, `fn_validar_fecha_uso` y 3 triggers: `trg_uso_recursos_base`, `trg_uso_recursos_fecha`, `trg_uso_recursos_actualizado`); reversible: dropea los 3 triggers y 2 funciones. Verificado: migrate adelante/atrás y desde cero; quedan **18 triggers**. Sin `comparacion_semana9.md`: la semana no genera documento de comparación aparte (la comparación se tabula aquí y en el tablero). |
| 9 | **Tres serializadores** | `UsoRecursoListaSerializer` (fila HU-67: recurso, unidad, campaña, actividad y `cantidad_base`), `UsoRecursoDetalleSerializer` (ficha HU-68, con campaña y actividad anidadas, `registrado_por` y motivo) y `UsoRecursoEscrituraSerializer` (alta/edición: sin `cantidad_base` ni `registrado_por`; la campaña no se puede cambiar al editar). |
| 10 | **Contrato de errores (herencia de las Semanas 6-8)** | Campo de serializador → **lista** `{"campo": ["msg"]}`; vista/acción/filtro → **string** `{"clave": "msg"}` (anular, reactivar, filtros, unidad incompatible, actividad con fecha distinta). 404 `{"detail": "No encontrado."}`; 403 con el `detail` del manejador; 405 en `DELETE`. Todo tabulado en `api_recursos.md`. |
| 11 | **Filtros y desplegables** | `/api/usos-recursos/`: `?campania=`, `?actividad=`, `?recurso=`, `?categoria=`, `?estado=ACTIVA\|ANULADA`, `?fecha_desde=`/`?fecha_hasta=` y `?busqueda=` (nombre de recurso, observaciones y código de parcela/productor de la campaña). Orden por **fecha descendente**; 20 por página. El desplegable de recursos (`?desplegable=1`) trae id, nombre, categoría y `tipo_unidad`; el de unidades se filtra por `?tipo=` desde el formulario. |
| 12 | **Pantalla `/recursos` y secciones en las fichas** | Nueva entrada en el menú (tras «Producción», con `recursos.ver`): listado con filtros en URL (búsqueda, campaña, categoría, recurso, fechas y estado), `Tabla`+`Paginacion`, alta/edición en modal (`RecursoFormulario`) y ficha en modal (`RecursoFicha` con «Anular uso»/«Reactivar»). **`ActividadFicha`** gana la sección «Recursos usados» y el botón «Registrar recurso» (HU-68, con aviso de cascada en la confirmación de anulación); **`CampaniaFicha`** gana la sección «Resumen de recursos» y su propio «Registrar recurso» (HU-74). Checklist en `docs/verificacion_ui_semana9.md`. |
| 13 | **Validaciones de cliente junto al campo** | En el formulario: campaña/recurso/cantidad/unidad obligatorios; cantidad > 0; costo ≥ 0; fecha no futura (hora de Lima, heredada de la Semana 7) y dentro del período de la campaña; si la actividad está vinculada, la fecha del uso debe coincidir con la de la actividad. Los errores del servidor (unidad incompatible, campaña cerrada/cancelada) salen junto al campo; los `non_field_errors` como toast. |
| 14 | **Colección de Postman: 235 peticiones** | `docs/coleccion_api_semana9.json` = las **205 de la Semana 8 + 30 nuevas** (206–235): 403 del Coordinador al crear, login de Administrador, 4 recursos (Semilla MASA, Urea MASA, Jornal LABOR, Diésel VOLUMEN), regla de categoría contra tipo de unidad (400), desplegable de unidades con `factor_a_base`/`es_base`, 4 altas (16 kg semilla, 2 qq urea → 92 kg, 40 jornales, 10 L diésel → 0.010 m³), unidad incompatible (400), campos protegidos ignorados, edición de cantidad (base recalculada), anular sin motivo (400)/con motivo/reactivar, 4 tipos de actividad + actividad FERT con uso y anulación con cascada (`recursos_anulados`), campaña de la semana (parcela 2, período 2028-2029) con edición inmutable, cancelación, alta rechazada, factor del Litro protegido (400), ficha de campaña con `resumen_recursos` y permisos del Técnico (403 al anular). **Validada 235/235 (431/431 aserciones)** contra el servidor en la BD temporal `sigpa_ga_coleccion9`, que se borró al terminar. Sufijo `SEMANA9`; pensada para **una ejecución por base de datos**. |
| 15 | **Cierre técnico de la fase** | **137 pruebas** verdes (`manage.py test`; 17 nuevas de la semana sobre las 120 de la Semana 8, en `seguimiento/tests.py`), `manage.py check` en 0 issues, `makemigrations --check` sin cambios, `npm run lint` y `npm run build` en 0 problemas. Sin documento de comparación aparte (ver decisión 8). |

## 3. Proceso y calidad

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 16 | **Commits por semana** | Continúa la decisión 15 de la Semana 4: **un único commit al final de la semana**, hecho por el responsable. El agente entrega solo el **nombre del commit** al cierre (F7). No hay commits por fase. |
| 17 | **Responsive siempre** | Continúa la decisión 14 de la Semana 4: requisito transversal (tablas en tarjetas ≤860 px, modales a ancho completo, áreas táctiles ≥ 44 px, sin scroll horizontal en móvil). Checklist en `docs/verificacion_ui_semana9.md` con columnas Chrome, **Edge (1024×768)** y **Móvil (360×780)** — el ancho móvil baja de 390 a 360 px esta semana. |
| 18 | **Verificación de pantallas** | Continúa la decisión 16 de la Semana 4: checklist manual sin dependencias nuevas; el agente ejecuta `lint` + `build` y prepara el documento, el responsable lo ejecuta en navegador y anota los resultados. |
| 19 | **Costo como registro, no como cálculo** | `costo` (S/) es el dato que registra el usuario por cada uso; el sistema **no lo agrega ni lo divide** automáticamente (por hectárea o por producción). Si más adelante se necesita un costo total de campaña o por hectárea, se calcula en el resumen (pregunta L). |
| 20 | **Sin borrado físico y con motivo en todo** | Como en actividades, campañas y producciones: la anulación siempre lleva **motivo obligatorio** y el registro se conserva (`ANULADA` + `motivo_anulacion`); `DELETE` → 405. La única vía de «deshacer» es la **reactivar**, que limpia el motivo. |

## 4. Preguntas abiertas

| # | Pregunta | Estado / para cuándo |
|---|----------|----------------------|
| A | ¿Entregó el responsable la lista real de ubicaciones? | Pendiente desde la Semana 3; al recibirla: `cargar_ubicacion` y retirar `ejemplo_ubicaciones.csv` |
| B | Confirmar la regla de **enmascarado de DNI/teléfono** (decisión 4 de la Semana 3) | ⚠️ Sigue pendiente; rige la propuesta (Administrador y Técnico ven completo, Coordinador enmascarado) |
| D | Botón «usar mi ubicación actual» (item *estirada*) | Solo funciona en `https://` o `localhost`; decidir en la demo |
| F | ¿Las fechas de campaña deben caer dentro del período? | **Pendiente de confirmar** (decisión 3 de la Semana 6): rige la validación solo en la API |
| G | ¿Bloquear la desactivación de productor/parcela con campañas activas (HU-45/46)? | **Pendiente de confirmar** (decisión 5 de la Semana 6): implementado con mensaje de error |
| H | ¿Rechazar fechas futuras en actividades? | **Pendiente de confirmar** (decisión 3 de la Semana 7). En recursos se aplica el mismo criterio (fecha ≤ hoy en hora de Lima, `max = hoy` en el formulario) |
| I | ¿Cuál es la unidad de densidad de siembra? | **Pendiente de decisión** (Semana 7): siguen implementadas las dos (`KG_HA`, `PLANTAS_M2`) |
| J | ¿La producción registrada es **bruta o neta** de la pérdida? | **Pendiente de confirmar** (decisión 20 de la Semana 8): rige **bruta** |
| K | **¿Umbrales de revisión y factor del quintal?** | **Pendiente de confirmar** (decisión 16 de la Semana 8): rigen `rendimiento_min_plausible = 100`, `rendimiento_max_plausible = 5000` kg/ha, `umbral_rendimiento_bajo = 800` kg/ha, `dias_sin_actividad = 30` y **quintal = 46 kg** |
| L | **¿Costo de los recursos: registro o cálculo?** | **Nueva — implementado según el plan y CONFIRMAR.** Rige: `costo` se guarda por cada uso y **no se agrega** en ningún resumen (decisión 19); si el responsable quiere un costo total de campaña o por hectárea se añade al `resumen_recursos` |

## 5. Notas de contexto

- **Qué ve cada rol en la API**: Administrador todo (`recursos.*`); Técnico `recursos.ver/crear/editar` solo dentro de sus productores asignados (sin `desactivar`: anular/reactivar → 403, colección 235); Coordinador `recursos.ver` (sin `recursos.crear`: 403, colección 206). El menú y la ruta `/recursos` exigen `recursos.ver`.
- **Ciclo de vida de un uso de recurso**: se crea activo; `anular/` lo deja `ANULADA` con motivo (y en cascada, si viene de anular la actividad); `reactivar/` lo devuelve a activo y limpia el motivo. La campaña de un uso **no se puede cambiar** al editar; la actividad vinculada tampoco (son inmutables como en producciones).
- **Re-ejecución de la colección**: los nombres llevan el sufijo `SEMANA9`; los recursos de referencia son fijos (Semilla, Urea, Jornal, Diésel) y la campaña de la semana usa la parcela del segundo productor con período `2028-2029`; sobre una BD ya recorrida las altas se declaran duplicadas. Para repetir, restablece la base de ensayo.
- Los mensajes de error de la API están tabulados en `api_recursos.md`; los de campañas siguen en `api_campanias.md` (ahora con `resumen_recursos`).
- La validación de la colección (235/235) se ejecutó con un `runserver 127.0.0.1:8001` en marcha y las credenciales de `.credenciales` (fuera de Git); la BD temporal `sigpa_ga_coleccion9` se creó, migró y **se borró al terminar**; la BD de desarrollo solo recibió las migraciones de la semana.
- **Nota de HU**: el mapeo HU-67..HU-75 es el **mapeo propuesto** de la semana (igual que en el tablero); los textos originales de los HU no están en el repositorio.
