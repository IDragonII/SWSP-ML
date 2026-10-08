# Decisiones — Semana 4: parcelas y asignación de técnicos

> Sprint 2, semana del 26 de octubre al 1 de noviembre. Documento análogo a
> `decisiones_semana3.md`: recoge lo acordado con el responsable y las reglas
> que guían la implementación de esta semana.
> Estado: **aprobadas en el plan de la semana** (el responsable dio el «ok»
> al plan completo, incluidas las cinco decisiones que se le sometieron).

## 1. Reglas de negocio (parcelas y asignaciones)

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 1 | **Alta de parcela** | El código `P-001` lo genera la base de datos (`trg_parcelas_codigo`) y es **solo lectura** por la API (igual que `creado_por`: se relee el registro tras guardar). Productor y comunidad son **obligatorios** (FK `RESTRICT`: no se puede borrar un productor que tenga parcelas). El productor debe estar **ACTIVO** para recibir parcelas nuevas. La comunidad de la parcela **se propone** la del productor pero es **editable y obligatoria**. |
| 2 | **Validaciones de parcela** | `superficie_ha > 0` (2 decimales), `altitud_msnm` obligatoria entre 0 y 6500, coordenadas **las dos o ninguna** (`ck_parcela_coordenadas`), listas cerradas con los valores del diseño (`tipo_suelo`, `pendiente`, `disponibilidad_agua`, `sistema_riego`) y estado `ACTIVA`/`INACTIVA`. |
| 3 | **Vida de la parcela** | **Nada se borra**: la API **no ofrece DELETE** (405); solo se desactiva/reactiva con `PATCH /api/parcelas/{id}/estado/`. Un productor **inactivo conserva** sus parcelas visibles (historial), pero no admite parcelas nuevas. |
| 4 | **Auto-asignación** (cierra la pregunta C de la Semana 3) | **Sí.** Si un **Técnico** crea un productor, su asignación se crea **en la misma operación, de forma atómica**: si falla una parte, no se guarda nada. Si el productor lo crea el **Administrador**, **no** se asigna a nadie (queda pendiente de asignar desde la ficha). |
| 5 | **Vida de la asignación** | **Desactivar** (`activo=false`) conserva el registro **sin efecto**: el técnico deja de ver al productor. **Reasignar = desactivar + crear otra** (no se cambia el técnico de una asignación activa). **Cambiar de rol no borra** sus asignaciones (siguen ahí, sin efecto según la regla de visibilidad). Unicidad `uq_asignacion(tecnico, productor)`: no se duplica. |
| 6 | **El filtro da 404, no 403** | Ver, editar o desactivar un productor/parcela **ajeno** devuelve **404 «no encontrado»** (evita adivinar existencia); el listado del técnico solo muestra los suyos. Los recursos anidados (detalle de parcela de otro productor) también responden 404. **El permiso manda antes que el ámbito:** el Técnico no tiene `*.desactivar`, así que en esa acción recibe **403** —igual con id existente que con id inexistente, tampoco se filtra existencia—; el 404 rige en las acciones que sí puede hacer (ver/editar). |
| 7 | **Quién ve los técnicos asignados** | `tecnicos_asignados` en la ficha **solo para Administrador y Coordinador**; el **Técnico no recibe el campo** en su respuesta. |
| 8 | **Rechazos: API primero, trigger como red** | `fn_validar_asignacion` exige que el técnico tenga un rol con `limita_a_asignados` (mensaje literal del diseño). La API **valida antes** (rol y usuario activo) y responde **400 en español**; el trigger se comprueba además en SQL crudo como red de seguridad. |

## 2. Decisiones técnicas

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 9 | **Dónde viven las 2 tablas** | En la app **`productores`** (misma app que `productores` y ubicación): migración **`0003`** (estructura de `parcelas` + `asignaciones_tecnico`) y **`0004`** (funciones y triggers, reversible). Se cumplen las «2 migraciones propias» de la semana. |
| 10 | **Numeración de las pruebas nuevas** | El repositorio cerró la Semana 3 con **37** pruebas, no con 32: las 16 nuevas se numeran **38 a 53** (**53 en total ≥ 48**). Mapeo spec → repositorio: 33→38, 34→39, 35→40, 36→41, 37→42, 38→43, 39→44, 40→45, 41→46, 42→47, 43→48, 44→49, 45→50, 46→51, 47→52, 48→53. |
| 11 | **404 en español** | `EXCEPTION_HANDLER` propio en `config/settings.py`: todos los 404 de la API responden `{"detail": "No encontrado."}` (los 404 de la Semana 3 en inglés —`No Productor matches…`— pasan también a español; se actualiza `api_ubicacion_productores.md` en F5). |
| 12 | **Colección de Postman** | Archivo **nuevo** `docs/coleccion_api_semana4.json` (parcelas, asignaciones y filtro por asignación), validado con script al cerrar. La colección de la Semana 3 **queda intacta**. |
| 13 | **Datos de ejemplo** | Hoja `datos/ejemplo_demo.md` con productores/parcelas **inventados** para la demostración; **sin comando de carga**: se dan de alta por la interfaz siguiendo el guion de demo. Los tests crean sus propios datos. |

## 3. Proceso y calidad

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 14 | **Responsive siempre** | Requisito **transversal e innegociable en todas las pantallas**: listados en tabla en escritorio → **tarjetas en móvil**, formularios en 1 columna, ficha/detalle en bloques apilados, filtros y paginación adaptados, áreas táctiles ≥ 44 px, **sin scroll horizontal en móvil**, revisado en **1366 / 768 / 390 px**. Checklist por pantalla en `docs/verificacion_ui_semana4.md`. El diseño se hace con la guía `frontend-design` del repositorio, **sobre la identidad existente** (Fraunces + Public Sans de `App.css`), sin inventar una marca nueva. |
| 15 | **Commits por semana** | **Un único commit al final de la semana**, hecho por el responsable. El agente entrega solo el **nombre del commit** al cierre (F8). No hay commits por fase. |
| 16 | **Verificación de pantallas** | **Checklist manual**: el agente ejecuta `lint` + `build` y prepara `docs/verificacion_ui_semana4.md` (Chrome, Edge, móvil, permisos, estados); el responsable lo ejecuta y anota. Sin dependencias nuevas (no Playwright). |
| 17 | **Sin datos reales** | Ni DNI/teléfono reales ni coordenadas reales en el repositorio; todo dato de demo va inventado y marcado como tal. |
| 18 | **Modales, no diálogos del navegador** | Las confirmaciones de edición (activar/desactivar productor y parcela, quitar/reactivar técnico) usan el componente reutilizable **`components/Modal.jsx`** en lugar de `window.confirm`: mismo aspecto en Chrome/Edge/móvil, botones ≥ 44 px, Escape o clic en el fondo para cancelar y botones deshabilitados con «Procesando…» mientras se llama a la API. **No se confunde con las notificaciones**: los avisos de éxito/error siguen siendo mensajes en la página (`Aviso`), no modales. |
| 19 | **CRUD completo en ventanas flotantes** | A petición del responsable, **toda la operativa de productores y parcelas vive en modales**: ver ficha, alta y edición se abren como ventana flotante y **la única navegación son los dos listados** (`/productores` y `/parcelas`). Se **eliminan las rutas** `/productores/nuevo`, `/productores/{id}`, `/productores/{id}/editar`, `/parcelas/nueva` y `/parcelas/{id}/editar` (ahora caen en «Página no encontrada»). `Modal.jsx` gana tres tamaños (`confirmacion`, `formulario`, `ficha`), cuerpo con scroll y **pila de modales** (Escape/✕ cierran solo el de arriba; el de abajo retoma el scroll). Al cerrar, el listado o la ficha de fondo se refresca (`recarga`); alta de productor desde el listado abre además la ficha del nuevo. Los permisos siguen verse **en el botón**: sin botón, sin modal. |
| 20 | **Avisos de acción → toast** | A petición del responsable, el **feedback de acción** (éxito/error tras guardar, activar/desactivar, asignar/quitar técnico) se muestra con el componente nuevo **`context/ToastProvider.jsx`** (`useToast().avisar(texto, nivel)`): notificación flotante arriba a la derecha, **por encima de los modales** (`z-index` 70 > 60), ✕ ≥ 44 px, `role="alert"` (error) y `role="status"` (éxito), máximo 3 visibles; **el éxito se cierra solo a los 4 s y el error se queda hasta pulsar la ✕**. Así el mensaje se ve **sin mover el scroll del modal** (el caso que motivó la decisión: error de asignación duplicada que solo aparecía arriba en una ficha larga). `Aviso` en página **se reserva** para errores de carga inicial y validaciones junto al campo; Login conserva su mensaje inline. |

## 4. Preguntas abiertas

| # | Pregunta | Estado / para cuándo |
|---|----------|----------------------|
| A | ¿Entregó el responsable la lista real de ubicaciones? | Pendiente desde la Semana 3; al recibirla: `cargar_ubicacion` y retirar `ejemplo_ubicaciones.csv` |
| B | Confirmar la regla de **enmascarado de DNI/teléfono** (decisión 4 de la Semana 3) | ⚠️ Sigue pendiente; rige la propuesta (Administrador y Técnico ven completo, Coordinador enmascarado) |
| C | ¿Auto-asignación al crear un productor? | **Cerrada: sí** (decisión 4 de este documento) |
| D | Botón «usar mi ubicación actual» (item *estirada*) | Solo funciona en `https://` o `localhost`; verificar en la demo si se implementa en F7 |

## 5. Notas de contexto

- Los permisos `parcelas.ver/crear/editar/desactivar` y `asignaciones.gestionar` **ya existen** (sembrados en `usuarios/0002`, dentro de los 55 permisos): no toca migrar permisos nuevos.
- `trg_parcelas_actualizado` **reutiliza** `fn_set_actualizado_en` (creada en la migración `productores.0002`): la migración `0004` **no debe dropearla** al revertir (dependencia de reversibilidad).
- Como con `PROD-000N`, la secuencia `seq_parcela_codigo` **no se reinicia** entre pruebas: saltos de `P-00N` tras un fallo son normales y no se corrigen.
- El filtro «solo mis productores» se **activó en F5** (productores y parcelas del técnico limitados a sus asignaciones activas). Se prueba el efecto «desactivada → pierde acceso» con la prueba 51.
- **Sin rutas en los mensajes de usuario** (seguridad): el rechazo por duplicado ya no
  menciona `PATCH /api/asignaciones/{id}/estado/`, sino «Esa asignación ya existe
  (activa o desactivada): ve a la ficha del productor y reactiva la existente.» La
  prueba 46 comprueba además que el mensaje no contiene `/api/` ni `PATCH`.
