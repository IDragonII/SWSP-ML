# Cierre — Semana 12: línea de tiempo de la campaña y usuarios

> Sprint 7, semana del **21 al 27 de diciembre** (calendario referencial).
> **Documento único de la semana** (Opción A aprobada por el responsable):
> condensa en un solo archivo lo que en semanas anteriores eran
> `decisiones_semanaN.md`, `api_*.md` y `verificacion_ui_semanaN.md`.
> Sustituye a `decisiones_semana12.md`, `api_seguimiento_etapas.md`,
> `api_usuarios.md` y `verificacion_ui_semana12.md` (que no se crean).
> Los textos originales de los HU **no están en el repositorio**: el mapeo
> HU-93..HU-104 es el **propuesto** de la semana, anclado a los RF/RN del
> documento de requerimientos (igual que en semanas anteriores).
> Estado: **7/7 fases ejecutadas, sin commitear** (decisión 16: el commit
> único lo hace el responsable); **F7 cerrada**: colección validada
> **392/392** (391 obligatorias + 1 opcional, **726/726 aserciones**).

## 1. Decisiones

### 1.1 Reglas de negocio

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 1 | **Alcance: etapas fenológicas por campaña (HU-93)** | Tabla **`seguimiento_etapas`** en la app `seguimiento/`: `campania + etapa + fecha_inicio + fecha_fin + observaciones + registrado_por`. **Una etapa por campaña** (`uq_seguimiento_etapa`), **sin `DELETE` (405) y sin anulación** — un error se corrige editando. `fecha_fin NULL` = etapa **en curso**; al registrar (o editar hacia) una etapa en curso, **la anterior en curso se cierra automáticamente** con la fecha de inicio de la nueva: una sola operación en la transacción con la campaña bloqueada (`select_for_update`) — **nunca hay dos etapas en curso** por campaña. |
| 2 | **Validaciones de etapas (HU-95)** | El serializador valida **antes que la base** (400 en español): campaña **que admite registros** (PLANIFICADA/EN_PRODUCCION/COSECHADA) y del **ámbito del Técnico**; etapa **del cultivo de la campaña** (el mensaje lista las etapas válidas del cultivo); **unicidad por campaña nombrando el registro existente** y devolviendo `etapa_existente` (enlazable, patrón de campañas); fechas **dentro del período** de la campaña y **no futuras** (hora de America/Lima, herencia de la pregunta H); `fecha_fin ≥ fecha_inicio`; y **coherencia cronológica por orden del catálogo**: la etapa nueva no empieza antes que una de menor orden ya registrada ni después que una de mayor orden — **los saltos de etapa sí se permiten** (catálogo con Cosecha en orden 5 sin llenar 3-4). Doble red: los triggers **`trg_seguimiento_etapa`** (`fn_validar_etapa`: etapa del cultivo, literal del diseño) y **`trg_seguimiento_fecha`** (`fn_validar_fecha_campania`: fecha en período) protegen el SQL directo. |
| 3 | **Cierre «en curso antes que» (decisión técnica de la semana)** | Si la etapa nueva queda **en curso** (`fecha_fin` NULL) y otra en curso tiene `fecha_inicio` **posterior**, la validación responde un 400 claro («no puede quedar en curso antes que …») en lugar del `IntegrityError` del CHECK `ck_seguimiento_fechas` que se produciría al cerrar la anterior (fue un hallazgo de F2a: el cierre automático escribía un `fecha_fin` anterior a la `fecha_inicio` de la que se cerraba). |
| 4 | **Línea de tiempo de la campaña (HU-94)** | `GET /api/campanias/{id}/linea-tiempo/` devuelve **una sola cronología** con las etapas del catálogo (registradas y **pendientes**), las actividades no anuladas, las incidencias activas y la cosecha (si existe). Orden: **fecha ascendente** (los pendientes, sin fecha, al final por orden del catálogo) y, entre dos hechos del mismo día, **etapa → actividad → incidencia → cosecha**. Estados: `EN_CURSO` (etapa sin fin) / `REGISTRADA` / `PENDIENTE`. Tope de **500 elementos** con `truncado` y `total_elementos`. `etapa_actual` (la en curso; si ninguna, la última registrada; `null` si no hay etapas) se añade también a `GET /api/campanias/` y a `GET /api/campanias/{id}/` para el chip de la tabla. Lectura con `campanias.ver`; campaña ajena del ámbito → 404. |
| 5 | **Permisos de las etapas** | `PermisosEtapaCampania`: `list`/`retrieve` → **`campanias.ver`**, `create`/`update` → **`campanias.editar`** (mismos permisos que la campaña: quien gestiona campañas gestiona su fenología). En UI: «Registrar etapa» y «Editar» solo con `campanias.editar` **y** campaña no cerrada/cancelada; sin permiso, **sin botón** (decisión de UI de la Semana 4). |
| 6 | **Alta y edición de usuarios (HU-100)** | `POST /api/usuarios/` → **201 + ficha completa** (contrato de viewset; sustituye al endpoint de prueba de la Semana 2, `CrearUsuarioView` eliminado). `PATCH /api/usuarios/{id}/` → 200. **`DELETE` → 405**: las cuentas se **desactivan**, nunca se borran (trazabilidad de auditoría y el rol protege las filas). `username` **obligatorio, único y solo en alta** (al editar: «El nombre de usuario no se puede modificar.», el valor enviado se ignora); `first_name`/`last_name` **obligatorios** (la tabla y el menú usan el nombre completo); `email`/`telefono` opcionales; `rol` obligatorio y **activo**; `password` **solo en alta** — en edición: «Para cambiar la contraseña use la acción restablecer-clave.» |
| 7 | **Protecciones de la cuenta propia y del último gestor (HU-101/HU-103/HU-104)** | Nadie puede: **desactivarse a sí mismo** (400 «No puedes desactivar tu propia cuenta.», HU-101), **cambiar su propio rol** (400, validado en el serializador con la sesión, HU-100) ni **restablecer su propia contraseña** (400, HU-104; se deja para el Sprint 7). Además **nunca puede perderse el último usuario activo con `roles.gestionar`**: desactivarlo o quitarle el rol responde 400 «Debe quedar al menos un usuario activo con permiso para gestionar roles.» (HU-103; verificado en la práctica con un rol editor **sin** `roles.gestionar`, que es el único caso alcanzable). |
| 8 | **Desactivar, reactivar y restablecer la contraseña (HU-101/HU-104)** | `desactivar`/`reactivar` exigen **`usuarios.desactivar`**; desactivar también exige cuenta activa («El usuario ya está desactivado.») y reactivar la inversa («El usuario ya está activo.»). **Desactivar y restablecer la contraseña invalidan las sesiones abiertas** del usuario con la **marca de sesión** (`sigpa:sesion-cambiada:{id}`): el `access` anterior queda rechazado por `AutenticacionJWT.get_user` y el `refresh` por `RenovarSesionView` (401). **Restablecer** (`usuarios.editar`) exige contraseña con los validadores de Django y responde «Contraseña restablecida…»; además **limpia el bloqueo** por intentos. `reactivar` y `desbloquear` **no** marcan sesión (cambios benignos). |
| 9 | **Bloqueo y desbloqueo (HU-103)** | El bloqueo por intentos fallidos sigue en caché (`usuarios/ratelimit.py`, 5 intentos / 15 min). `POST /api/usuarios/{id}/desbloquear/` (**`usuarios.editar`**) solo limpia la caché: «Acceso desbloqueado.» si había bloqueo, «El usuario no estaba bloqueado.» si no (200 en ambos casos). La ficha de usuario enseña `bloqueado` y `bloqueado_segundos`. |
| 10 | **Permisos por acción de usuarios (HU-100/HU-102)** | `PermisosUsuario`: `list`/`retrieve` → `usuarios.ver`; `create` → `usuarios.crear`; `update`/`partial_update` → `usuarios.editar`; `desactivar`/`reactivar` → `usuarios.desactivar`; `restablecer_clave`/`desbloquear` → `usuarios.editar`. El permiso se comprueba **antes** que el objeto (sin permiso → 403, no 404). `GET /api/roles/` (desplegable): solo **roles activos**, **sin paginación**, exige `usuarios.ver`. En el catálogo actual solo el **Administrador** tiene los 5 `usuarios.*`; el rol **vacío** (sin permisos) sí es asignable. |

### 1.2 Decisiones técnicas

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 11 | **Dos migraciones reversibles + 24/24 triggers** | `seguimiento/0009_seguimiento_etapas.py` (tabla, `uq_seguimiento_etapa`, `ck_seguimiento_fechas`, índice `ix_seguimiento_campania`, ordering `("-fecha_inicio","id")`; la tabla **no** tiene `creado_en`/`actualizado_en`, no los necesita) y `seguimiento/0010_fn_trg_seguimiento.py` (`fn_validar_etapa` **literal** de `02_reglas_y_vista.sql:172-184` + los 2 triggers; la reversión **no** dropea `fn_validar_fecha_campania`, que comparten otras tablas). El diseño SQL se actualizó en F1 → **24/24 triggers** del diseño (9 de la plantilla `trg_*_actualizado` + 15 nominales). Verificado: `manage.py check` (0 issues), `makemigrations --check` (sin cambios) y las pruebas 120/137/172 (que pasaron de contar 22 a 24). |
| 12 | **Serializadores de etapas** | `EtapaCampaniaListaSerializer` (fila: campaña mini, etapa `{id,nombre,orden}`, fechas), `EtapaCampaniaDetalleSerializer` (ficha con `observaciones` y `registrado_por` **oculto** a roles con `limita_a_asignados`, como en actividades/incidencias) y `EtapaCampaniaEscrituraSerializer` (todas las validaciones de la decisión 2; `__init__` que **elimina** el `UniqueValidator`/`UniqueTogetherValidator` de DRF sobre `{campania, etapa}` para sustituirlo por la validación con enlace). Hereda el contrato de errores: campo → lista `{"campo": ["msg"]}`; una clave «extra» (`etapa_existente`) puede acompañar a la del campo. |
| 13 | **Vista de etapas sin `DELETE`** | `EtapaCampaniaViewSet` (List/Retrieve/Create/Update, **sin `DestroyModelMixin`** → 405) con filtros `?busqueda=` (etapa, observaciones, código de parcela, apellidos/nombres), `?campania=`, `?etapa=`, `?cultivo=`, `?parcela=`, `?productor=`, `?fecha_desde=`/`?fecha_hasta=` y `?en_curso=1`; `?page=` (20/página); ámbito del Técnico antes que los filtros; `create`/`update` con `transaction.atomic()` + `_bloquear_campania` (vuelve a leer el estado de la campaña) + `_cerrar_en_curso`; cualquier `IntegrityError` de carrera → **400** («No se pudo guardar la etapa: …»), nunca 500. |
| 14 | **Contrato de usuarios: lista, ficha y escritura** | `UsuarioListaSerializer` (fila: `username`, `nombre_completo`, `email`, `telefono`, `rol`, `is_active`, `bloqueado`), `UsuarioDetalleSerializer` (ficha: + `first_name`/`last_name`, `bloqueado_segundos`, `date_joined`, `last_login` **(no `ultimo_login`)** y `permisos` del rol — la misma lista que `/me`), `UsuarioEscrituraSerializer` (alta/edición con las reglas de la decisión 6; sin `UniqueValidator` en `username`: la unicidad la cubre `validate()` con `usuario_existente`) y `RestablecerClaveSerializer`. `UsuarioViewSet` con `BusquedaPorNombre` (`?busqueda=` sobre username, nombres, apellidos y email) y **sin destroy**; `RolViewSet` es `ListModelMixin` puro con `pagination_class = None`. |
| 15 | **Marca de sesión en la autenticación** | `usuarios/autenticacion.py` añade `marcar_sesion_cambiada(user_id)` / `sesion_cambiada_despues(user_id, iat)` con clave `sigpa:sesion-cambiada:{id}` (timeout = vida del refresh, 7 días). `AutenticacionJWT.get_user` rechaza los `access` **anteriores** a la marca («Sesión invalidada. Vuelve a iniciar sesión.») y `RenovarSesionView` decodifica el `refresh` (`RefreshToken(bruto)`) y lo rechaza con `SesionInvalida` si es anterior. Se marca en `restablecer-clave` y `desactivar`. |
| 16 | **Pantallas de la semana** | **Etapas/linea de tiempo**: componente `components/LineaTiempo.jsx` (etapa actual + pasos del catálogo + cronología con chips por tipo/estado), sección **«Línea de tiempo»** en `CampaniaFicha` (botón «Registrar etapa», tabla de etapas registradas con «Editar» y enlace de edición), `pages/EtapaFormulario.jsx` (modal con desplegable `etapas-fenologicas/?cultivo=` y validación de período en cliente) y `api/etapasCampania.js`; columna **«Etapa»** (con chip EN CURSO/CERRADA) en la tabla de `Campanias`. **Usuarios**: pantalla **`/usuarios`** (entrada ya existente en el menú con `usuarios.ver`), `pages/Usuarios.jsx` (búsqueda en URL, `Tabla`+`Paginacion`, acciones Editar/Desactivar-Reactivar/Ficha), `UsuarioFormulario.jsx` (alta/edición en modal) y `UsuarioFicha.jsx` (datos, permisos del rol y acciones **Restablecer contraseña**, **Desbloquear acceso**, **Desactivar/Reactivar** en confirmación, con la rueda dentro del botón); `api/usuarios.js`; ruta `/usuarios` en `App.jsx` (ya no cae en el placeholder de módulo). |
| 17 | **Verificación: 197 pruebas verdes + lint/build** | Pruebas **173–185** (13, `EtapaCampaniaApiTests` sobre `Semana12Base` en `seguimiento/tests.py`): alta válida, validaciones (cultivo, unicidad con enlace, fechas, orden), cierre automático de la etapa en curso, edición, `DELETE` → 405, permisos/ámbito. Prueba **197** (1, HU-97): **listado de etapas con paginación y filtros** (`?campania=`, `?etapa=`, `?en_curso=1`, `?busqueda=`, `?fecha_desde=`/`?fecha_hasta=` y el ámbito del Técnico aplicado **antes** que los filtros) — añadida en F6 al detectar que `GET /api/etapas-campania/` no tenía ninguna prueba; mueve el total de 196 a **197**. Pruebas **186–196** (11, `GestionUsuariosApiTests` en `usuarios/tests.py`): lista y permisos, alta y duplicado, altas inválidas, edición (username inmutable, rol propio, contraseña rechazada), desactivar (cuenta propia y ya desactivada), último gestor, reactivar, restablecer (cierra sesiones: `/me` y `refresh` → 401), desbloquear (429 → desbloquear → login), roles del desplegable y fin del CRUD (405/403/404). Total: **197 en verde**. Además `manage.py check` (0 issues), `makemigrations --check` (sin cambios), `npm run lint` (0) y `npm run build` (152 módulos). **Hallazgos de F3**: (a) el error con varias claves levantado desde `validate_<campo>` queda **anidado bajo el campo** → moverlo a `validate()` para que las claves (`usuario_existente`) queden en la raíz; (b) el `UniqueValidator` de DRF en `username` dispara antes que `validate()` → declarar el campo sin validadores; (c) los recuentos de triggers de las pruebas 120/137/172 suben de 22 a **24**. |

### 1.3 Proceso y calidad

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 18 | **Sin commitear: el commit único lo hace el responsable** | Continúa la decisión 16 de la Semana 11: la Semana 12 se entrega **entera sin commitear** («sin commitear» — indicación explícita del responsable para esta semana). |
| 19 | **Opción A: un solo documento de cierre** | Aprobada por el responsable: calidad completa (pruebas, triggers, colección validada) pero documentación de la semana **condensada en este archivo**, en lugar de los cuatro documentos habituales (decisions/api×2/checklist). |
| 20 | **Responsive siempre** | Continúa la decisión 14 de la Semana 4: tablas en tarjetas ≤ 860 px, modales a ancho completo, áreas táctiles ≥ 44 px, sin scroll horizontal en móvil. Checklist con columnas **Chrome 1366×768**, **Edge 1024×768** y **Móvil 360×780**. |
| 21 | **Verificación de pantallas** | Continúa la decisión 16 de la Sección 4: sin Playwright; el agente deja el checklist de la §3 (además de `lint` + `build` en 0 y la suite en verde) y el responsable lo ejecuta en navegador y anota los resultados. |
| 22 | **Sin datos reales y con ensayo limpio** | Continúa la decisión 17 de la Semana 4: ni en pruebas ni en la colección se usan datos reales; `.credenciales` nunca en la colección; las BD temporales (pruebas, smoke y colección) y el servidor del 8001 se borran/detenen al terminar cada fase. |
| 23 | **Colección Postman (F7)** | `docs/coleccion_api_semana12.json`: copia de la de la Semana 11 más los ítems de etapas/línea de tiempo y usuarios (**81 nuevos** → **392** en total: 311 + 312–392). **Cerrada en F7: 392/392 peticiones (726/726 aserciones)** contra un servidor temporal en **8001** con BD temporal `sigpa_ga_coleccion12`, borrada al terminar; el servidor usa `LOGIN_RATE_IP=120/min` (la colección supera los 30 logins por IP del valor por defecto). Hallazgos de F7 ajustados en el generador antes del cierre: la línea de tiempo de CAM7 tiene **10** elementos (la actividad del 7 de octubre fue anulada), la producción se compara con el decimal `'3220.00 kg'`, las validaciones de etapa usan una etapa no registrada (el chequeo de unicidad va antes que el de cronología) y el rechazo de restablecer la propia contraseña se comprueba por texto (el detalle llega como cadena). |

### 1.4 Preguntas abiertas

| # | Pregunta | Estado / para cuándo |
|---|----------|----------------------|
| A | ¿Entregó el responsable la lista real de ubicaciones? | Pendiente desde la Semana 3; al recibirla: `cargar_ubicacion` y retirar `ejemplo_ubicaciones.csv` |
| B | Confirmar la regla de **enmascarado de DNI/teléfono** | ⚠️ Pendiente; rige la propuesta (Administrador y Técnico completos, Coordinador enmascarado) |
| D | Botón «usar mi ubicación actual» | Solo funciona en `https://` o `localhost`; decidir en la demo |
| F | ¿Las fechas de campaña deben caer dentro del período? | Pendiente; rige la validación en la API (en etapas también: fechas de la etapa dentro del período) |
| G | ¿Bloquear la desactivación de productor/parcela con campañas activas? | Pendiente; implementado con mensaje de error |
| H | ¿Rechazar fechas futuras? | Pendiente; rige `fecha ≤ hoy` (hora de Lima) en actividades, incidencias, clima **y etapas** (`max = hoy` en los formularios) |
| I | ¿Unidad de densidad de siembra? | Pendiente; siguen las dos (`KG_HA`, `PLANTAS_M2`) |
| J | ¿Producción bruta o neta? | Pendiente; rige bruta |
| K | ¿Umbrales de revisión, factor del quintal y umbral de helada? | Pendiente; rigen los del diseño (`100`, `5000`, `800`, `30`, `46 kg`, `0 °C`) |
| L | ¿Costo de recursos: registro o cálculo? | Pendiente; rige registro por uso sin agregar |
| M | ¿Open-Meteo como fuente del clima? | Pendiente; rige Open-Meteo (adaptador en `servicio_meteorologico.py`) |
| N | ¿Criterio de severidad de la incidencia? | Pendiente; rige la elección libre de quien registra |
| O | **¿La coherencia cronológica de etapas debe relajarse?** | **Nueva — implementada y CONFIRMAR.** Rige que la regla (por orden del catálogo, con saltos permitidos) se valida **solo en la API** (decisión explícita de la semana: para poder relajarla sin migraciones); si el responsable quiere registrar etapas «fuera de orden» completo, se quita la validación de `validate()` sin tocar la base. |
| P | **¿Restablecer la propia contraseña desde la UI?** | **Nueva — NO implementado a propósito** (queda para el **Sprint 7** con verificación de contraseña actual); hoy la API lo rechaza con «No puedes restablecer tu propia contraseña desde aquí.» |

### 1.5 Notas de contexto

- **Qué ve cada rol**: Administrador todo; Técnico `campanias.ver/editar` y etapas **solo de sus productores asignados** (campaña ajena → «La campaña indicada no existe.»), `usuarios.ver` no (no gestiona cuentas); Coordinador `campanias.ver` (ver la ficha y la línea de tiempo, sin «Registrar etapa») y `usuarios.ver` si el catálogo se lo concede (en el sembrado actual, solo Administrador tiene `usuarios.*`). En UI «sin botón, sin modal».
- **Ciclo de vida de una etapa**: se registra (la anterior en curso se cierra sola) → se edita (fechas/observaciones; la campaña es inmutable) → **nunca se borra ni se anula** (`DELETE` → 405). La campaña CERRADA/CANCELADA no admite cambios (400).
- **Ciclo de vida de una cuenta**: se crea activa → se edita → se **desactiva** (nunca se borra; cierra sus sesiones) → se **reactiva** → puede quedar **bloqueada** por intentos (caché) y **desbloquearse**. Las acciones de mantenimiento son `restablecer-clave` y `desbloquear`.
- **Pruebas**: 197 en total (`manage.py test`); las de la semana son la 173 a la 197 (173–185 y 197 de etapas; 186–196 de usuarios). El smoke de navegador (F5) es la §3 de este documento.
- **Mapeo HU de la semana (12, en dos rangos como en semanas anteriores)**: etapas **HU-93..HU-99** — HU-93 (CRUD de etapas), HU-94 (línea de tiempo), HU-95 (validaciones de etapas), HU-96 (permisos y ámbito de las etapas), HU-97 (filtros del listado), HU-98 (pantallas de etapas) y HU-99 (`etapa_actual` en la tabla y la ficha de campaña); usuarios **HU-100..HU-104** — HU-100 (alta y edición), HU-101 (desactivar/reactivar), HU-102 (pantalla `/usuarios` con ficha), HU-103 (bloqueo/desbloqueo, cuenta propia y último gestor) y HU-104 (restablecer contraseña). El mismo rango usan los docstrings de `seguimiento/views.py`, `campanias/serializers.py` y `usuarios/views.py`.
- **Herencia**: sigue anotado que `docs/api_recursos.md` (citado por `evidencias_capitulo4.md` y el tablero) **no existe**; repararlo en un cierre pendiente.

## 2. API de la semana

### 2.1 Etapas de campaña — `/api/etapas-campania/`

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/etapas-campania/` | `campanias.ver` | 200 paginado (`count`, `results`, 20/página) |
| GET | `/api/etapas-campania/{id}/` | `campanias.ver` | 200 / 404 |
| POST | `/api/etapas-campania/` | `campanias.editar` | **201** (ficha) |
| PATCH | `/api/etapas-campania/{id}/` | `campanias.editar` | 200 (ficha) |
| DELETE | `/api/etapas-campania/{id}/` | — | **405** (sin borrado) |

**Filtros del listado**: `?busqueda=` (etapa, observaciones, código de parcela, apellidos/nombres), `?campania=`, `?etapa=`, `?cultivo=`, `?parcela=`, `?productor=`, `?fecha_desde=`/`?fecha_hasta=` (sobre `fecha_inicio`), `?en_curso=1`, `?page=`.

**Fila (lista)**: `{id, campania: {id, periodo, estado, cultivo, parcela…}, etapa: {id, nombre, orden}, fecha_inicio, fecha_fin}`. **Ficha** (detalle): + `observaciones`, `registrado_por` (oculto para roles con `limita_a_asignados`).

**Escritura**: `{campania, etapa, fecha_inicio, fecha_fin?, observaciones?}` — en edición la `campania` **no se envía/cambia**.

**Errores 400** (campo → lista; principales, en español):

| Clave | Mensaje (resumen) |
|---|---|
| `campania` | «La campaña es obligatoria.» / «La campaña indicada no existe.» (incluye el ámbito del Técnico) / «La campaña está {estado} y no admite nuevos registros.» / «La campaña de una etapa no se puede cambiar…» |
| `etapa` | «La etapa es obligatoria.» / «La etapa indicada no existe.» / «La etapa «X» no corresponde al cultivo de la campaña (Y). Etapas válidas: …» / «Ya se registró la etapa «X» en esta campaña (id N): edítala en su lugar.» (+ clave `etapa_existente: "N"`) |
| `fecha_inicio` | «La fecha de inicio es obligatoria.» / «…no es válida: usa el formato AAAA-MM-DD.» / «…no puede ser futura.» / «… {fecha} está fuera del período de la campaña (A a B).» / «… no puede empezar antes/después que «X» (fecha).» / «… no puede quedar en curso antes que «X» (fecha): cierra primero esa etapa…» |
| `fecha_fin` | «…no es válida…» / «…no puede ser futura.» / «… no puede ser anterior a la de inicio (X).» / «… {fecha} está fuera del período…» |
| `estado` (acción) | IntegrityError de carrera traducido: «No se pudo guardar la etapa: …» (400, nunca 500) |

### 2.2 Línea de tiempo — `GET /api/campanias/{id}/linea-tiempo/`

Permiso `campanias.ver` (campaña ajena al ámbito → 404). Respuesta:

```json
{
  "campania": {"id", "periodo", "estado", "cultivo", "parcela", "fecha_inicio", "fecha_fin_prevista"},
  "etapa_actual": {"id", "nombre", "fecha_inicio", "fecha_fin", "en_curso"} | null,
  "etapas_definidas": [{"id", "nombre", "orden", "registrada", "fecha_inicio", "fecha_fin"}],
  "elementos": [{"tipo": "ETAPA|ACTIVIDAD|INCIDENCIA|PRODUCCION",
                 "fecha": "AAAA-MM-DD" | null, "fecha_fin": "…|null",
                 "titulo", "detalle": "…|null",
                 "estado": "EN_CURSO|REGISTRADA|PENDIENTE",
                 "severidad": "BAJA|MEDIA|ALTA"   // solo incidencias
                }],
  "total_elementos": 12,
  "truncado": false
}
```

Orden: `fecha` asc (null → «9999-12-31»), desempate por tipo (etapa → actividad → incidencia → cosecha) y pendientes al final por `orden` del catálogo. Tope: 500 (`truncado: true` si hay más). `etapa_actual` se añade también a `GET /api/campanias/` y `GET /api/campanias/{id}/`.

### 2.3 Usuarios — `/api/usuarios/`

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/usuarios/` | `usuarios.ver` | 200 paginado (20/página); `?busqueda=` (username, nombres, apellidos, email), `?page=` |
| GET | `/api/usuarios/{id}/` | `usuarios.ver` | 200 (ficha) / 404 |
| POST | `/api/usuarios/` | `usuarios.crear` | **201 + ficha** |
| PATCH | `/api/usuarios/{id}/` | `usuarios.editar` | 200 (ficha) |
| DELETE | `/api/usuarios/{id}/` | — | **405** (desactivar, no borrar) |
| POST | `/api/usuarios/{id}/desactivar/` | `usuarios.desactivar` | 200 (ficha) — cierra sesiones |
| POST | `/api/usuarios/{id}/reactivar/` | `usuarios.desactivar` | 200 (ficha) |
| POST | `/api/usuarios/{id}/restablecer-clave/` | `usuarios.editar` | 200 `{"detail": "Contraseña restablecida…"}` — cierra sesiones y limpiea bloqueo |
| POST | `/api/usuarios/{id}/desbloquear/` | `usuarios.editar` | 200 `{"detail": "Acceso desbloqueado." | "El usuario no estaba bloqueado.", "usuario": ficha}` |
| GET | `/api/roles/` | `usuarios.ver` | 200 **lista sin paginación** (solo roles activos: `[{id, nombre}]`) |

**Fila (lista)**: `{id, username, nombre_completo, email, telefono, rol: {id, nombre}, is_active, bloqueado}`.
**Ficha**: + `first_name`, `last_name`, `bloqueado_segundos`, `date_joined`, `last_login`, `permisos: ["codigo", …]`.
**Escritura**: `{username, first_name, last_name, email?, telefono?, rol, password}` — `username` y `password` **solo en alta**; nombres, apellidos y rol obligatorios.

**Errores 400** (principales):

| Clave | Mensaje (resumen) |
|---|---|
| `username` | «El nombre de usuario es obligatorio.» / «El nombre de usuario no se puede modificar.» / «Ya existe un usuario con el nombre de usuario «X» (id N).» (+ `usuario_existente: "N"`) |
| `first_name` / `last_name` | «Los nombres son obligatorios.» / «Los apellidos son obligatorios.» |
| `password` | «La contraseña es obligatoria.» / validadores de Django (longitud, numérica, común, similar al usuario) / «Para cambiar la contraseña use la acción restablecer-clave.» / «No puedes restablecer tu propia contraseña desde aquí.» (acción) |
| `rol` | «El rol es obligatorio.» / «El rol indicado no existe.» / «El rol indicado está inactivo.» / «No puedes cambiar tu propio rol.» |
| `estado` (acciones) | «No puedes desactivar tu propia cuenta.» / «El usuario ya está desactivado.» / «El usuario ya está activo.» / «Debe quedar al menos un usuario activo con permiso para gestionar roles.» |

**Sesiones**: `restablecer-clave` y `desactivar` colocan la **marca de sesión**; el `access` y el `refresh` anteriores a ella responden **401** en `/api/auth/me/` y `/api/auth/refresh/`.

## 3. Verificación UI (checklist manual)

> La §3 cumple el papel de `verificacion_ui_semana12.md` (Opción A). El agente
> deja este checklist — además de `npm run lint` (0), `npm run build` (152
> módulos) y la suite de backend **197/197 en verde** (`manage.py check` 0
> issues, `makemigrations --check` sin cambios) — y el responsable lo ejecuta
> en navegador y anota el resultado.
> Pantallas de la semana: la sección **«Línea de tiempo»** de la ficha de
> campaña (HU-93/94), el modal **`EtapaFormulario`** (HU-95), la columna
> **«Etapa»** de `/campanias` (HU-99), la pantalla **`/usuarios`** con
> `UsuarioFormulario` y `UsuarioFicha` (HU-100..HU-104).

### Preparación

```bash
# Terminal 1 — backend (puerto 8000)
cd backend && venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload

# Terminal 2 — frontend (puerto 5173)
cd frontend && npm run dev
```

- Abrir `http://localhost:5173` en **Chrome** y en **Edge** (los mismos pasos en ambos).
- Usuarios (de `.credenciales`): `admin` / `SigpaGA2026!`, `coordinador` / `Coordinador2026!`,
  `tecnico` / `Tecnico2026!`.
- Se necesita una **campaña que admita registros** (PLANIFICADA, EN_PRODUCCION
  o COSECHADA) con **al menos una etapa registrada** (créala desde la ficha:
  «Registrar etapa») y, si procede, una campaña CERRADA/CANCELADA para ver el
  modo solo lectura. No usar datos reales (decisión 22).
- El catálogo **«Etapas fenológicas»** se gestiona en **Catálogos** (solo
  admin): para la prueba, el cultivo de la campaña debe tener 2-3 etapas
  activas (p. ej. Siembra, Emergencia, Floración).
- Para usuarios: con `admin` crea un usuario de prueba (rol Cualquiera o
  Coordinador) y bloquéalo con 5 logins fallidos (para «Desbloquear acceso»).

### 1. Chrome — escritorio 1366×768

#### Línea de tiempo en `CampaniaFicha` (HU-93/HU-94/HU-95)

- [ ] En `/campanias`, «Ver ficha» de una campaña → la sección **«Línea de
      tiempo»** aparece **después de «Datos de la campaña»** y antes de
      «Actividades».
- [ ] El bloque muestra la **«Etapa actual»** (chip EN CURSO o REGISTRADA +
      nombre + «desde fecha») o el aviso «La campaña todavía no tiene etapas
      registradas.».
- [ ] Los **pasos del catálogo** (`etapas_definidas`) se ven en orden con su
      fecha (o «Pendiente»); las completadas con fondo, la activa con borde
      marigold.
- [ ] La **cronología** mezcla etapas, actividades, incidencias y cosecha con
      su fecha, tipo, título, chip de estado (y chip de severidad en
      incidencias) y detalle; las etapas pendientes cierran la lista.
- [ ] El botón **«Registrar etapa»** (cabecera de la sección) solo aparece con
      `campanias.editar` **y** campaña no cerrada/cancelada.
- [ ] La **tabla de etapas registradas** (Etapa con orden, Inicio, Fin con chip
      EN CURSO si `fecha_fin` es null, Observaciones y Acciones) solo muestra
      «Editar» con `campanias.editar` y campaña abierta; sin permiso, la celda
      dice «Solo lectura».
- [ ] `EtapaFormulario` (modal): desplegable **solo con las etapas del
      cultivo**, fechas con `max = hoy`, ayuda con el período de la campaña;
      «Registrar etapa» con rueda «Guardando…».
- [ ] Validaciones en cliente: etapa vacía, fecha de inicio vacía/futura/fuera
      del período; fecha de fin anterior a la de inicio. Errores del servidor
      (etapa repetida → «Ya se registró la etapa…», etapa de otro cultivo, etapa
      fuera de orden) junto al campo correspondiente.
- [ ] Al registrar una etapa con otra **en curso**, la anterior se cierra sola
      (chip pasa a REGISTRADA con su fecha de fin = fecha de inicio de la nueva)
      sin recargar la página manualmente (recarga interna).
- [ ] Editar una etapa desde la tabla funciona y la campaña **cerrada** no
      muestra los botones (solo lectura).
- [ ] En `/campanias`, la columna **«Etapa»** muestra el nombre con chip
      **EN CURSO**/**CERRADA** (o «Sin etapas») en cada fila.

#### Pantalla `/usuarios` (HU-100..HU-104)

- [ ] Con `admin`, la opción **«Usuarios»** del menú abre `/usuarios` (título
      «Usuarios» + «N en total»); con un usuario **sin `usuarios.ver`** (p. ej.
      Técnico) la ruta muestra **Acceso denegado** y la opción no está en el
      menú.
- [ ] El botón **«Nuevo usuario»** solo aparece con `usuarios.crear`.
- [ ] Filtros: **Buscar** (placeholder «Usuario, nombre o correo») con «Buscar»
      y «Limpiar»; la búsqueda vive en la URL (`?busqueda=`) y la paginación
      respeta la página (20 por página).
- [ ] La tabla (`Tabla`): **Nombre** (botón a la ficha), **Usuario** (código),
      **Correo**, **Rol**, **Estado** (chip ACTIVO/INACTIVO + BLOQUEADO) y
      **Acciones**.
- [ ] Acciones por fila: **Editar** (`usuarios.editar`), **Desactivar/
      Reactivar** (`usuarios.desactivar` y **no en la propia fila** — con
      «Procesando…» mientras dura) y **Ficha**.
- [ ] `UsuarioFormulario` (alta): username, nombres, apellidos, correo,
      teléfono, rol (desplegable solo roles activos) y contraseña; rueda
      «Guardando…»; validaciones en cliente (nombres/apellidos/rol/contraseña
      ≥ 8, no solo numérica, sin el username) y del servidor (duplicado con
      enlace, rol inactivo/inexistente).
- [ ] `UsuarioFormulario` (edición): el **username sale deshabilitado** y la
      **contraseña no aparece** (se avisa de que es con «Restablecer
      contraseña»); cambiar el **propio rol** responde «No puedes cambiar tu
      propio rol.».
- [ ] `UsuarioFicha`: chips de estado (ACTIVO/INACTIVO, BLOQUEADO), «Rol:
      …», bloque de «Datos de la cuenta» (incluye **Bloqueo** con segundos y
      «Último acceso») y el resumen de permisos del rol.
- [ ] Acciones de la ficha (con sesión admin y sobre **otra** cuenta):
      **«Restablecer contraseña»** (modal con rueda; cierra las sesiones
      abiertas del usuario), **«Desbloquear acceso»** (solo si está bloqueado;
      aviso «Acceso desbloqueado.» / «El usuario no estaba bloqueado.»),
      **«Desactivar»** (peligro, con confirmación) y **«Reactivar»**.
- [ ] **Cuenta propia**: la ficha del usuario de la sesión **no** ofrece
      «Restablecer contraseña» ni «Desactivar» (ni siquiera con los permisos).
- [ ] **Último gestor**: con un editor sin `roles.gestionar`, intentar
      desactivar o quitar el rol al único Administrador responde el aviso
      «Debe quedar al menos un usuario activo con permiso para gestionar
      roles.» (si no se dispone del editor, basta comprobar que la propia
      sesión no puede desactivarse).
- [ ] Tras «Desactivar» con la UI: el login de esa cuenta falla y sus sesiones
      abiertas quedan invalidadas (si tenía una pestaña abierta, la siguiente
      llamada expira).

### 2. Edge — escritorio 1024×768

- [ ] Repetir los apartados principales de §1 (ficha de campaña con línea de
      tiempo, formulario de etapas y pantalla de usuarios con sus tres
      modales); sin scroll horizontal y sin solapes.

### 3. Móvil — 360×780 (y 768 px de ancho)

- [ ] Las tablas de etapas, campañas y usuarios se convierten en **tarjetas**
      (`data-rotulo`), con las acciones visibles y pulsables.
- [ ] Los modales (`EtapaFormulario`, `UsuarioFormulario`, `UsuarioFicha`,
      confirmaciones) ocupan el ancho completo, sin cortar el botón de envío.
- [ ] La línea de tiempo se lee en columna (fecha encima del contenido) sin
      desbordes; los pasos del catálogo envuelven en varias filas.
- [ ] El menú de la entrada **«Usuarios»** y la navegación a `/usuarios`
      funcionan con táctil (áreas ≥ 44 px).

### 4. Comprobaciones transversales

- [ ] `npm run lint` y `npm run build` en 0 problemas; backend **197/197**.
- [ ] Ninguna acción asíncrona queda sin rueda dentro de su botón
      (guardar, desactivar, reactivar, restablecer, desbloquear).
- [ ] Sin datos reales en las pruebas manuales (decisión 22); `.credenciales`
      fuera de la colección de Postman.
