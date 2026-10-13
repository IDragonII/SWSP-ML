# Verificación UI — Semana 8 (checklist manual)

> Decisiones 18 y 19 (`decisiones_semana8.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas)
> y el responsable lo ejecuta en navegador y anota el resultado.
> Pantallas de la semana: **`/parametros`** (nueva: 4 claves + edición en modal),
> la **ficha de campaña** con el nuevo bloque **«Producción»** y los botones
> «Registrar producción» y «Cerrar campaña», los modales **`ProduccionFormulario`**
> (alta/edición) y **`ProduccionFicha`** (revisar/deshacer), y la columna
> **«Producción»** en la sección Campañas de la ficha del productor (HU-62).
> La entrada «Producción» del menú sigue mostrando el placeholder de módulo
> (aún sin pantalla propia, decisión 14).

## Preparación

```bash
# Terminal 1 — backend (puerto 8000)
cd backend && venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload

# Terminal 2 — frontend (puerto 5173)
cd frontend && npm run dev
```

- Abrir `http://localhost:5173` en **Chrome** y en **Edge** (los mismos pasos en ambos).
- Usuarios (de `.credenciales`): `admin` / `SigpaGA2026!`, `coordinador` / `Coordinador2026!`,
  `tecnico` / `Tecnico2026!`.
- Para registrar producción hace falta una campaña **`EN_PRODUCCION` con siembra
  registrada y sin cosecha**: créala desde la UI («Nueva campaña» → «Iniciar campaña»
  → «Registrar actividad» con tipo **Siembra**), **no** usar datos reales (decisión 17
  de la Semana 4). Ojo con las reglas heredadas: una parcela solo admite **una campaña
  activa** y la fecha de cosecha no puede ser **anterior a la siembra ni al inicio**
  de la campaña.
- El desplegable **Unidad** del formulario trae las unidades de masa activas
  (Kilogramo, Quintal, Tonelada); si faltara el Quintal se crea en
  **«Catálogos → Unidades»** (tipo MASA, factor a la base 46).
- Para probar la **revisión por umbrales** hace falta un rendimiento fuera de
  `[100, 5000]` kg/ha (p. ej. 1 kg sobre 2,00 ha → 0,50 kg/ha) o mover los umbrales
  desde `/parametros` antes de registrar la cosecha.

## 1. Chrome — escritorio 1366×768

### Parámetros (`/parametros`)

- [ ] Con **admin**, la opción **«Parámetros»** aparece en el menú, **después de
      «Catálogos» y antes de «Campañas»**; al entrar, la URL es `/parametros` y el
      título es **«Parámetros del sistema»** con el conteo **«4 en total»**.
- [ ] Bajo el título se lee la nota: **«Los umbrales se aplican al registrar o editar
      producciones: no reevalúan las producciones ya guardadas.»**
- [ ] La tabla (componente `Tabla`, ancho completo, sin scroll interno) muestra las
      4 claves con nombre legible — **Días sin actividad** (30), **Umbral de
      rendimiento bajo** (800), **Rendimiento mínimo plausible** (100) y
      **Rendimiento máximo plausible** (5000) — con las columnas **Parámetro, Valor,
      Descripción, Última actualización y Acciones**.
- [ ] **«Editar»** abre el modal (`formulario`) con el **nombre del parámetro** como
      título, un solo campo **«Valor»** con su ayuda; **Cancelar** o ✕ cierra sin
      guardar.
- [ ] Validación de cliente **junto al campo** (sin toast): vacío → «El valor es
      obligatorio.»; no numérico o ≤ 0 → «El valor debe ser un número mayor que 0.»;
      mínimo ≥ máximo → «El rendimiento mínimo debe ser menor que el máximo.»
- [ ] Guardar con rueda **«Guardando…»** dentro del botón (deshabilitado); toast
      **«Parámetro guardado.»**; la tabla se recarga con el valor nuevo y la
      «Última actualización» de hoy.
- [ ] La entrada **«Producción»** del menú (tras «Actividades») muestra el
      **placeholder de módulo** (sin pantalla propia esta semana; decisión 14).

### Ficha de campaña: bloque «Producción» y botones (HU-61, HU-62)

- [ ] En **`/campanias`**, «Ver ficha» abre la ficha de campaña: chip de estado +
      «N actividad(es) activa(s)» y los botones **«Registrar actividad»**,
      **«Registrar producción»**, **«Cerrar campaña»** y **«Editar campaña»**
      según corresponda (la ficha gana una sección **«Producción»** al final).
- [ ] **«Registrar producción»** solo aparece si la campaña está en
      **`EN_PRODUCCION`**, tiene **fecha de siembra** y **aún no tiene cosecha**
      (y con `produccion.crear`).
- [ ] **«Cerrar campaña»** (botón en peligro) solo aparece en **`COSECHADA`** y con
      `campanias.desactivar` (admin). **«Registrar actividad»** desaparece en
      `CERRADA` y `CANCELADA`.
- [ ] Sin cosecha, el bloque «Producción» muestra la nota según el estado:
      planificada → «La campaña está planificada: registra la siembra para poder
      capturar la cosecha.»; `EN_PRODUCCION` sin siembra → «La campaña aún no tiene
      siembra registrada: registra la actividad de siembra antes de la producción.»;
      `EN_PRODUCCION` → «Esta campaña todavía no tiene cosecha registrada.»;
      cancelada → «La campaña está cancelada y no admite producción.».
- [ ] Con cosecha, el bloque muestra **Fecha de cosecha**, **Producción** (kg),
      **Rendimiento** (kg/ha), **Revisión** (chip **REQUIERE REVISIÓN** o
      «Sin revisión») y las acciones **«Ver ficha de producción»** y
      (con `produccion.editar` y campaña no cerrada) **«Editar producción»**.

### Alta y edición de producción (modal `formulario`)

- [ ] «Registrar producción» abre el modal **«Registrar producción»** con la
      **campaña preseleccionada**; la URL **no cambia** y la ficha queda de fondo.
      Dos secciones: **«Datos de la cosecha»** y **«Rendimiento y calidad»**.
- [ ] El desplegable **Campaña** solo ofrece las campañas `EN_PRODUCCION` con siembra
      y sin cosecha (formato «productor — parcela — cultivo (período)»); su ayuda al
      elegir muestra «Cultivo: {cultivo}. Superficie sembrada: {n} ha.» y sin elegir
      «Solo aparecen las campañas en producción con siembra registrada y sin
      cosecha.»
- [ ] **Unidad** solo lista unidades de **masa activas** (Kilogramo (kg), Quintal
      (qq), Tonelada (t)); **Hectárea no aparece**.
- [ ] Ayudas visibles: fecha «No puede ser anterior a la fecha de siembra ni al
      inicio de la campaña.»; superficie «Como máximo la superficie sembrada
      ({n} ha).»; cantidad «La cantidad en kg y el rendimiento kg/ha los calcula el
      sistema.»; pérdida «Pérdida registrada durante la cosecha, si la hubo.»;
      calidad con «Sin calificar» + Primera/Segunda/Tercera.
- [ ] Errores de cliente **junto al campo**: fecha vacía o anterior a la siembra
      («…no puede ser anterior a la fecha de siembra (…).»), superficie ≤ 0
      («La superficie cosechada debe ser mayor que 0.») o mayor que la sembrada
      («…no puede superar la sembrada (X ha).»), cantidad negativa, unidad vacía y
      pérdida negativa.
- [ ] Guardar con rueda **«Guardando…»**; al crear con rendimiento normal → toast
      **«Producción registrada: {kg} kg ({kg/ha} kg/ha). La campaña pasó a
      COSECHADA.»**; si el rendimiento es atípico → **«Producción registrada:
      rendimiento atípico ({kg/ha} kg/ha), requiere revisión.»**; al editar →
      **«Producción guardada.»**
- [ ] Tras guardar, la ficha de campaña se recarga: el chip pasa a **COSECHADA**, el
      bloque «Producción» muestra los datos y aparece **«Cerrar campaña»**.
- [ ] **«Editar producción»** abre **«Editar producción»** con el formulario
      hidratado y **sin campo campaña** (no se puede cambiar); «Guardar cambios» con
      rueda → «Producción guardada.».
- [ ] Los errores de campo del servidor salen junto al campo; los de
      `non_field_errors` (duplicada, campaña cerrada) salen como **toast de error**.

### Ficha de producción: revisar y deshacer (HU-59, HU-60)

- [ ] «Ver ficha de producción» abre el modal **ficha** «Producción del {fecha}»:
      cabecera con el **chip del estado de la campaña** y «{kg} kg · {kg/ha} kg/ha».
- [ ] Sección **«Revisión pendiente»** (solo si la hay): Motivo con el texto
      «Rendimiento atípico: {valor} kg/ha» y «En entrenamiento» (Sí/No). Sección
      **«Datos de la cosecha»**: fecha, campaña, parcela, productor, cantidad con
      símbolo, producción, superficie, rendimiento, pérdida, calidad, requiere
      revisión, observaciones y «Registrado por» cuando aplica.
- [ ] Con `produccion.desactivar` (admin) y revisión pendiente: botón
      **«Revisar producción»** (enfoca el campo de nota) y panel
      **«Registrar revisión»** con «Nota de revisión» (ayuda **«Obligatorio: se
      añade al motivo original para trazabilidad.»**) e «Incluir en el entrenamiento»
      (Sí/No); con nota vacía el botón está **deshabilitado**; con nota → rueda
      **«Procesando…»** → toast **«Revisión registrada.»**; la ficha recarga: la
      sección pasa a **«Revisión»** con el motivo **concatenado** («{original} —
      Revisión: {nota}»), «Requiere revisión: No» y desaparecen el botón y el panel.
- [ ] Panel **«Deshacer cosecha»** (oculto si la campaña está `CERRADA`): motivo
      obligatorio (botón **deshabilitado** mientras esté vacío); con motivo →
      confirmación en peligro **«Deshacer cosecha»** que **cita el motivo** y avisa
      «…La producción se eliminará y la campaña volverá a EN_PRODUCCION…» → rueda
      **«Procesando…»** → toast **«Cosecha deshecha. La campaña volvió a
      EN_PRODUCCION.»** y se cierra la ficha; la ficha de campaña vuelve a
      `EN_PRODUCCION` y reaparece **«Registrar producción»**.
- [ ] En campaña `CERRADA`: **sin** botón «Editar», **sin** panel «Deshacer cosecha»
      (y por API, editar → 400 «La campaña cerrada no admite cambios en la
      producción.»).

### Cerrar campaña (HU-61)

- [ ] En campaña `COSECHADA` con producción **sin revisión pendiente**, «Cerrar
      campaña» → confirmación en peligro **«Cerrar campaña»** con el texto
      **«¿Cerrar la campaña {período}? Una vez cerrada no admite actividades ni
      cambios en la producción. Esta acción es irreversible.»** → rueda
      **«Procesando…»** → toast **«Campaña cerrada.»** y el chip pasa a
      **`CERRADA`**.
- [ ] Con revisión pendiente el cierre falla: toast de error **«No se puede cerrar la
      campaña: la producción requiere revisión pendiente. Revísala antes de
      cerrar.»** (la ficha no se rompe).
- [ ] Cerrada: desaparecen **«Registrar actividad»** y «Editar producción» en el
      bloque; «Editar campaña» sigue según permiso.

### Ficha del productor: columna «Producción» (HU-62)

- [ ] En la ficha del productor, la sección **Campañas** muestra la columna
      **«Producción»** (entre **Estado** y **Acciones**): con cosecha,
      **«{kg} kg · {kg/ha} kg/ha»** (más el chip **REQUIERE REVISIÓN** si aplica);
      sin cosecha, **«—»**.

## 2. Edge — igual que Chrome (1366×768)

- [ ] Repetir al menos: `/parametros` con edición, ficha de campaña con bloque
      «Producción» + alta, ficha de producción con revisar/deshacer y cierre.
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome.

## 3. Móvil — 390×844 (Chrome devtools) y tablet 768×1024

- [ ] Las tablas (parámetros y campañas del productor) se muestran como **tarjetas**
      (≤860 px) con etiqueta a la izquierda y valor a la derecha.
- [ ] **Sin scroll horizontal de la página** en 390 ni en 768 (listados, fichas,
      modales y formularios).
- [ ] Los modales (`formulario` y `ficha`) a **ancho completo ≤ 860 px**, ✕ ≥ 44 px,
      cuerpo con scroll interno y botones (Registrar producción, Guardar cambios,
      Cancelar) apilados a ancho completo; se puede escribir en todos los campos
      (fecha con el selector nativo, cantidad/superficie con teclado numérico).
- [ ] **Pila de modales**: ficha de campaña → registrar producción → ficha de
      producción → editar: Escape/✕ cierran solo el de arriba y el de abajo retoma
      el scroll.
- [ ] Botones de acción (Registrar producción, Cerrar campaña, Deshacer cosecha,
      Editar, Ver ficha) ≥ 44 px en táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Admin** (`admin`): ve «Parámetros» en el menú y edita; usa todas las
      acciones de producción (alta, edición, revisar, deshacer y cerrar).
- [ ] **Coordinador** (`coordinador`): **no ve «Parámetros»** (sin
      `parametros.gestionar`; la ruta directa → Acceso denegado y la API responde
      403, colección 166-167). En producción solo lectura: en la ficha de campaña
      **sin «Registrar producción» ni «Cerrar campaña»**, en la ficha de producción
      **sin «Editar», sin «Revisar producción» ni panel «Deshacer cosecha»** (solo
      `produccion.ver`; crear por API → 403, colección 205).
- [ ] **Técnico** (`tecnico`): **no ve «Parámetros»**; ve las campañas de **sus
      productores asignados** (las ajenas no aparecen). Puede **«Registrar
      producción»** y **«Editar producción»** en las suyas (la respuesta no incluye
      «Registrado por»), pero **no ve** «Revisar producción» ni «Deshacer cosecha»
      (sin `produccion.desactivar`; por API → 403, colecciones 200-201) ni
      **«Cerrar campaña»** (sin `campanias.desactivar`).
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** dentro del botón (`AGENTS.md`): «Guardando…» en parámetros,
      producción y parámetros; **«Procesando…»** en las confirmaciones que pasan por
      `Modal` (revisar, deshacer cosecha, cerrar campaña).
- [ ] Cargando inicial: `/parametros` con `Cargando…` a pantalla completa sin
      parpadear datos viejos; los modales de ficha/edición hidratan con `Cargando…`.
- [ ] Error de red/servidor al listar parámetros: aviso rojo (`Aviso`) en la página y
      el resto sigue operativo; con el backend caído, los modales muestran el
      aviso/toast de error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Parámetro guardado.», «Producción
      registrada…», «Producción guardada.», «Revisión registrada.», «Cosecha
      deshecha…» y «Campaña cerrada.» — éxito verde **auto-cierra a los 4 s**, error
      rojo **se queda hasta la ✕**; los errores de validación **de campo** salen
      **junto al campo**, no como toast.
- [ ] Escape cierra el modal de arriba (pila de modales) y ningún
      `window.confirm`/`alert` en toda la pantalla.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/producciones/{id}/`
      → `405` y `POST http://localhost:8000/api/parametros/` → `405`; la UI nunca
      ofrece borrar.

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 390 | Observaciones |
|---|---|---|---|---|
| 1. Parámetros | ☐ | ☐ | ☐ | |
| 2. Ficha de campaña y bloque Producción | ☐ | ☐ | ☐ | |
| 3. Alta y edición de producción | ☐ | ☐ | ☐ | |
| 4. Revisar y deshacer | ☐ | ☐ | ☐ | |
| 5. Cerrar campaña | ☐ | ☐ | ☐ | |
| 6. Ficha del productor | ☐ | ☐ | ☐ | |
| 7. Permisos por rol | ☐ | ☐ | ☐ | |
| 8. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
