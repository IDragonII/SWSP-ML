# Verificación UI — Semana 7 (checklist manual)

> Decisiones 15 y 16 (`decisiones_semana7.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas)
> y el responsable lo ejecuta en navegador y anota el resultado.
> Pantalla nueva de la semana: **`/actividades`** (listado con filtros, alta/edición en
> modal y la ficha de actividad), más el nuevo bloque de actividades dentro de la
> **ficha de campaña** (`CampaniaFicha`) y la entrada de menú «Actividades».

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
- Para registrar actividades hace falta **una campaña activa**: créala desde la UI
  («Nueva campaña»), **no** usar datos reales (decisión 17 de la Semana 4). Ojo con las
  reglas heredadas: una parcela solo admite **una campaña activa** y la fecha de la
  actividad debe caer **dentro del período de la campaña y no ser futura** (pregunta H).

## 1. Chrome — escritorio 1366×768

### Entrada y filtros (`/actividades`)

- [ ] Con **admin**: la opción **«Actividades»** aparece en el menú, **después de
      «Campañas»** y antes de «Producción».
- [ ] Al entrar, la URL es `/actividades` y bajo el título se muestra el conteo
      («N en total»); arriba a la derecha, el botón **«Nueva actividad»**.
- [ ] Filtros: **Buscar** (placeholder «Parcela, productor, método u observaciones»),
      **Campaña** (Todas + desplegable «productor — parcela — cultivo (período)»),
      **Tipo** (Todos + tipos activos), **Productor**, **Fecha desde**, **Fecha hasta**
      y **Estado** (Todas / Activas / Anuladas); al enviar, la URL cambia
      (`?busqueda=&campania=&tipo=&productor=&fecha_desde=&fecha_hasta=&estado=`)
      y la tabla se recarga.
- [ ] Con filtros activos aparece **Limpiar** y restaura la lista completa.
- [ ] Sin coincidencias → «No hay actividades que coincidan con la búsqueda.» + nota
      «Prueba a limpiar los filtros o registra una actividad nueva.».
- [ ] Cambiar de página (Paginación, 20 por página) resalta la tabla brevemente
      (clase `refrescando`); atrás/adelante del navegador restaura filtros y página.

### Tabla y ficha de actividad (HU-47, HU-49)

- [ ] La tabla usa `components/Tabla.jsx`, ocupa **todo el ancho**, sin scroll interno;
      columnas: **Fecha, Tipo, Campaña (período · cultivo), Parcela (chip), Productor,
      Método, Estado (chip ACTIVA/ANULADA) y Acciones**.
- [ ] En Acciones, con permiso `actividades.editar` y la fila activa aparece
      **«Editar»**; si no (o está anulada) aparece **«Ver ficha»**; ambos abren modales
      sin cambiar la URL.
- [ ] Ficha de actividad: cabecera con el tipo y el chip de estado; secciones
      **«Datos de la actividad»** (fecha, tipo, campaña, parcela, productor, método,
      densidad, horas, costo «S/», observaciones y «Registrado por» cuando aplica) y,
      si está anulada, **«Anulación»** con el motivo.

### Alta y edición (modal `formulario`)

- [ ] «Nueva actividad» abre el modal **«Nueva actividad»**; la URL **no cambia** y la
      lista queda de fondo. Dos secciones: **«Datos de la actividad»** y
      **«Esfuerzo y observaciones»**.
- [ ] **Campaña**: la ayuda muestra «Período de la campaña: {inicio} a {fin}.» según la
      elegida; **Tipo**: al elegir **Siembra** aparece la ayuda «Al elegir SIEMBRA, la
      campaña pasa a EN_PRODUCCION y queda fijada su fecha de siembra.».
- [ ] **Fecha**: `max` = hoy (no deja elegir días futuros en el calendario); el cliente
      rechaza vacía, futura («La fecha no puede ser futura.») y fuera del período
      («La fecha debe estar dentro del período de la campaña (…).»).
- [ ] **Densidad de siembra** (valor + unidad `kg/ha` o `plantas/m²`) solo aparece si
      el tipo es **Siembra**; valor sin unidad (o al revés) → «La densidad de siembra
      y su unidad deben ir juntas (o dejar ambas vacías).».
- [ ] **Horas** y **Costo (S/)** aceptan solo números (teclado numérico en móvil) y
      rechazan negativos bajo el campo.
- [ ] Errores del servidor (fecha fuera del período, campaña no admite registros,
      densidad… ) salen **junto al campo**; toast solo para errores no de campo.
- [ ] Guardar con rueda **«Guardando…»** dentro del botón (deshabilitado); al crear →
      toast **«Actividad creada.»**; si además es una siembra que puso la campaña en
      producción → toast **«Actividad registrada. La campaña pasó a EN_PRODUCCION
      (fecha de siembra: …).»**.
- [ ] **Editar** abre **«Editar actividad»** con `Cargando…` y el formulario hidratado;
      **campaña y tipo aparecen deshabilitados** (inmodificables); guardar →
      **«Actividad guardada.»**.

### Anular y reactivar (HU-50, HU-51)

- [ ] En la ficha, con `actividades.desactivar` (admin), el panel **«Anular actividad»**
      pide un motivo (ayuda «Obligatorio: el registro se conserva y queda como
      anulado.»); con el motivo vacío el botón está **deshabilitado**.
- [ ] Con motivo → confirmación **«Anular actividad»** que **cita el motivo** y avisa:
      «…Al ser una siembra, la fecha de siembra de la campaña se recalculará.» →
      rueda **«Procesando…»** → toast **«Actividad anulada.»**; la ficha recarga con el
      chip **ANULADA** y la sección de anulación.
- [ ] Con la actividad anulada, el botón **«Reactivar»** → confirmación («…La campaña
      debe seguir abierta y la fecha dentro de su período…») → toast
      **«Actividad reactivada.»** y vuelve el chip **ACTIVA** (desaparece la sección
      de anulación).
- [ ] Si la campaña ya no admite registros (cancelada) o la fecha salió del período,
      la reactivación falla con el aviso/toast del error de la API (la ficha no se
      rompe).

### Ficha de campaña y bloque de actividades

- [ ] En **`/campanias`**, el botón **«Ver ficha»** de la tabla abre la **ficha de
      campaña** (`CampaniaFicha`) —antes abría la parcela—; con `campanias.editar` la
      fila muestra **«Editar»** y **«Ver ficha»**.
- [ ] La ficha muestra: chip de estado + «N actividad(es) activa(s)», botones
      **«Registrar actividad»** (con `actividades.crear`) y **«Editar campaña»** (con
      `campanias.editar`), la sección **«Datos de la campaña»** (productor, parcela,
      cultivo, variedad, ciclo, fecha de siembra, superficie, última actividad,
      observaciones, creado por) y la sección **«Actividades»** (Fecha, Tipo, Método,
      Estado y Acciones).
- [ ] Sin actividades → nota «Esta campaña todavía no tiene actividades registradas.».
- [ ] **«Registrar actividad»** abre el formulario con la **campaña preseleccionada**;
      al guardar, la ficha se recarga (conteo, última actividad y tabla).
- [ ] En la tabla de actividades de la ficha: **«Editar»** (fila activa) o
      **«Ver ficha»**; la ficha de actividad anidada también refresca el bloque.

## 2. Edge — igual que Chrome (1366×768)

- [ ] Repetir al menos: entrada con filtros, alta de siembra con densidad, ficha con
      anular/reactivar y la ficha de campaña con su bloque.
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome.

## 3. Móvil — 390×844 (Chrome devtools) y tablet 768×1024

- [ ] Las tablas (listado de actividades y actividades de la ficha de campaña) se
      muestran como **tarjetas** (≤860 px) con etiqueta a la izquierda y valor a la
      derecha.
- [ ] **Sin scroll horizontal de la página** en 390 ni en 768 (listado, filtros, modales
      y fichas).
- [ ] Filtros apilados y Buscar/Limpiar a ancho completo; el modal de actividad en
      **una sola columna** y se puede escribir en todos los campos (fecha, horas y
      costo con teclado numérico).
- [ ] El **modal** se adapta: ancho completo ≤ 860 px, ✕ ≥ 44 px, cuerpo con scroll
      interno y botones (Crear/Guardar cambios/Cancelar) apilados a ancho completo.
- [ ] Botones de acción (Editar, Anular actividad, Reactivar, Registrar actividad,
      fichas) ≥ 44 px en táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Admin** (`admin`): ve «Actividades» en el menú y usa todas las acciones (alta,
      edición, anular, reactivar y las fichas).
- [ ] **Coordinador** (`coordinador`): **sí ve** «Actividades» (tiene
      `actividades.ver`) y la pantalla en solo lectura: **sin botón «Nueva
      actividad»**, en la tabla solo **«Ver ficha»** (nunca «Editar»), en la ficha
      **sin** Editar/Anular/Reactivar, y en la ficha de campaña **sin** «Registrar
      actividad» ni «Editar campaña». En la API, crear → 403 (colección 159).
- [ ] **Técnico** (`tecnico`): ve «Actividades» y **solo las actividades de sus
      productores asignados** (las ajenas no aparecen; por API, 404). Puede crear
      («Nueva actividad») y editar, pero **no ve el panel «Anular actividad» ni el
      botón «Reactivar»** (no tiene `actividades.desactivar`; por API anular → 403,
      colección 155).
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** (`components/RuedaCarga.jsx`, ver `AGENTS.md`): «Crear
      actividad»/«Guardar cambios» muestran la rueda **dentro del botón** con
      «Guardando…»; anular y reactivar pasan por el `Modal` con «Procesando…».
- [ ] Cargando inicial: pantalla completa (`Cargando…`) sin parpadear datos viejos; la
      ficha de actividad y la de campaña hidratan con `Cargando…` en su modal.
- [ ] Error de red/servidor al listar: aviso rojo (`Aviso`) en la página y el resto
      sigue operativo.
- [ ] Con el backend caído (parar el runserver): los modales muestran el aviso/toast de
      error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Actividad creada.», «Actividad
      guardada.», «Actividad anulada.», «Actividad reactivada.» y el aviso de campaña
      EN_PRODUCCION arriba a la derecha, éxito verde **auto-cierra a los 4 s**, error
      rojo **se queda hasta la ✕**; los errores de validación **de campo** salen
      **junto al campo**, no como toast.
- [ ] Escape cierra el modal de arriba (pila de modales) y ningún
      `window.confirm`/`alert` en toda la pantalla.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/actividades/1/` →
      `405`, y la UI nunca ofrece borrar.

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 390 | Observaciones |
|---|---|---|---|---|
| 1. Entrada y filtros | ☐ | ☐ | ☐ | |
| 2. Tabla y ficha de actividad | ☐ | ☐ | ☐ | |
| 3. Alta y edición | ☐ | ☐ | ☐ | |
| 4. Anular y reactivar | ☐ | ☐ | ☐ | |
| 5. Ficha de campaña | ☐ | ☐ | ☐ | |
| 6. Permisos por rol | ☐ | ☐ | ☐ | |
| 7. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
