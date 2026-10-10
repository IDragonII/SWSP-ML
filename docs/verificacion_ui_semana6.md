# Verificación UI — Semana 6 (checklist manual)

> Decisiones 17 y 18 (`decisiones_semana6.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas)
> y el responsable lo ejecuta en navegador y anota el resultado.
> Pantalla nueva de la semana: **`/campanias`** (listado con filtros, alta/edición en
> modal y las fichas de productor/parcela con su sección de campañas).

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
- La BD de desarrollo **no tiene campañas** al empezar: crearlas desde la UI está
  permitido, **no** usar datos reales (decisión 17 de la Semana 4). Ojo: una parcela
  solo admite **una campaña activa por período** (y un cultivo por parcela/periodo):
  si un alta devuelve duplicado, es la regla de la decisión 4, no un fallo.

## 1. Chrome — escritorio 1366×768

### Entrada y filtros (`/campanias`)

- [ ] Con **admin**: la opción **«Campañas»** aparece en el menú, después de «Catálogos».
- [ ] Al entrar, la URL es `/campanias` y bajo el título se muestra el conteo
      («N en total»); arriba a la derecha, el botón **«Nueva campaña»**.
- [ ] Filtros: **Buscar** (placeholder «Productor, parcela, cultivo o variedad»),
      **Estado** (Todos + los 5 estados), **Cultivo** (solo activos) y **Período**
      (placeholder `2025-2026`); al enviar, la URL cambia
      (`?busqueda=&estado=&cultivo=&periodo=`) y la tabla se recarga.
- [ ] Con filtros activos aparece **Limpiar** y restaura la lista completa.
- [ ] Sin coincidencias → «No hay campañas que coincidan con la búsqueda.» + nota
      «Prueba a limpiar los filtros o registra una campaña nueva.».
- [ ] Cambiar de página (Paginación, 20 por página) resalta la tabla brevemente
      (clase `refrescando`); atrás/adelante del navegador restaura filtros y página.

### Tabla y fichas (HU-42, HU-44)

- [ ] La tabla usa `components/Tabla.jsx`, ocupa **todo el ancho**, sin scroll interno;
      columnas: **Productor, Parcela, Cultivo, Variedad, Período, Estado (chip) y Acciones**.
- [ ] El nombre del **productor** es un botón de texto → abre la **ficha del productor**
      en modal; el **código de la parcela** (chip) → abre la **ficha de la parcela**.
- [ ] Ficha del productor (HU-44): sección **«Campañas»** con el resumen
      («N activas de N»), tabla (Período, Parcela, Cultivo, Variedad, Estado, Acciones)
      y botón **«Nueva campaña»** (con `campanias.crear`); si no tiene, nota
      «Este productor todavía no tiene campañas.».
- [ ] Ficha de la parcela (HU-44): sección **«Campañas»** con columnas adicionales de
      fechas (`inicio → fin prevista`) y superficie (`N ha`).
- [ ] En ambas fichas, la columna Acciones ofrece **«Editar»** (con `campanias.editar`)
      que abre el mismo modal de edición.

### Alta y edición (modal `formulario`)

- [ ] «Nueva campaña» abre el modal **«Nueva campaña»**; la URL **no cambia** y la
      lista queda de fondo. Dos secciones: **«Identidad de la campaña»** y
      **«Ciclo y superficie»**, en una sola columna.
- [ ] **Variedad**: hasta elegir cultivo dice «Primero el cultivo»; al elegir cultivo
      se recarga solo con sus variedades (ayuda «Solo las variedades del cultivo elegido.»).
- [ ] Validaciones de cliente bajo el campo: período vacío/mal formado («…formato
      AAAA-AAAA…»), obligatorios (parcela/cultivo/variedad/fechas), «La fecha de fin
      prevista no puede ser anterior a la de inicio.» y «La superficie sembrada debe
      ser mayor que 0.».
- [ ] La ayuda de **superficie** muestra «En blanco se usa la de la parcela (X ha).»
      según la parcela elegida; en blanco → la API usa la superficie de la parcela.
- [ ] Errores del servidor (duplicado, fecha fuera del período, superficie > parcela…)
      salen **junto al campo** (formato lista); toast solo para errores no de campo.
- [ ] Guardar con rueda **«Guardando…»** dentro del botón (deshabilitado, ✕ también
      con `ocupado`); al crear → toast **«Campaña creada.»** y la fila aparece
      refrescando la tabla.
- [ ] **Editar** abre **«Editar campaña»** con `Cargando…` y el formulario hidratado;
      guardar → **«Campaña guardada.»**.

### Iniciar y cancelar (HU-39, HU-40)

- [ ] En edición de una campaña **PLANIFICADA** aparece, junto al chip de estado, el
      botón **«Iniciar campaña»** → abre confirmación: «¿Iniciar esta campaña? Pasará
      a EN_PRODUCCION y sus campos de identidad (parcela, cultivo, variedad, período y
      fecha de inicio) quedarán bloqueados.» → al confirmar, rueda **«Procesando…»** y
      toast **«Campaña iniciada.»**; el chip pasa a EN_PRODUCCION.
- [ ] Con la campaña **EN_PRODUCCION**, los campos **parcela, cultivo, variedad,
      período y fecha de inicio** quedan **deshabilitados**; fecha de fin, superficie
      y observaciones siguen editables.
- [ ] La sección **«Cancelar campaña»** pide un motivo (ayuda «Obligatorio: quedará en
      las observaciones de la campaña.»); con el motivo vacío el botón está
      deshabilitado; con motivo → confirmación roja que **cita el motivo** («…El motivo
      quedará en las observaciones: «…»…») → toast **«Campaña cancelada.»**.
- [ ] Una campaña **CANCELADA** muestra la nota «Esta campaña está cancelada: es de
      solo lectura y no admite cambios.»: todos los campos deshabilitados y **sin
      botones** de guardar/iniciar/cancelar.
- [ ] Escape o clic en el fondo cierran sin llamar a la API; ningún
      `window.confirm`/`alert` en toda la pantalla.

## 2. Edge — igual que Chrome (1366×768)

- [ ] Repetir al menos: entrada con filtros, alta, edición con iniciar/cancelar y las
      fichas de productor/parcela.
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome.

## 3. Móvil — 390×844 (Chrome devtools) y tablet 768×1024

- [ ] Las tablas (listado de campañas y secciones de las fichas) se muestran como
      **tarjetas** (≤860 px) con etiqueta a la izquierda y valor a la derecha.
- [ ] **Sin scroll horizontal de la página** en 390 ni en 768 (listado, filtros, modales
      y fichas).
- [ ] Filtros apilados y Buscar/Limpiar a ancho completo; el modal de campaña sigue en
      **una sola columna** y se puede escribir en todos los campos.
- [ ] El **modal** se adapta: ancho completo ≤ 860 px, ✕ ≥ 44 px, cuerpo con scroll
      interno y botones (Crear/Guardar cambios/Cancelar) apilados a ancho completo.
- [ ] Botones de acción (Editar, Iniciar campaña, Cancelar campaña, fichas) ≥ 44 px en
      táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Admin** (`admin`): ve «Campañas» en el menú y usa todas las acciones (alta,
      edición, iniciar, cancelar y las fichas).
- [ ] **Coordinador** (`coordinador`): **sí ve** «Campañas» (tiene `campanias.ver`) y
      la pantalla en solo lectura: **sin botón «Nueva campaña»**, en la tabla solo
      **«Ver ficha»** (nunca «Editar»), y la ficha de productor/parcela **sin**
      «Nueva campaña» ni «Editar». En la API, crear → 403 (colección 127).
- [ ] **Técnico** (`tecnico`): ve «Campañas» y **solo las campañas de sus productores
      asignados** (las ajenas no aparecen; por API, 404 — colección 119). Puede crear
      («Nueva campaña»), editar e iniciar, pero **no ve el botón «Cancelar campaña»**
      (no tiene `campanias.desactivar`; por API cancelar → 403, colección 123).
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** (`components/RuedaCarga.jsx`, ver `AGENTS.md`): «Crear
      campaña»/«Guardar cambios» muestran la rueda **dentro del botón** con
      «Guardando…»; iniciar y cancelar pasan por el `Modal` con «Procesando…».
- [ ] Cargando inicial: pantalla completa (`Cargando…`) sin parpadear datos viejos; la
      ficha hidrata con `Cargando…` en su modal.
- [ ] Error de red/servidor al listar: aviso rojo (`Aviso`) en la página y el resto
      sigue operativo.
- [ ] Con el backend caído (parar el runserver): los modales muestran el aviso/toast de
      error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Campaña creada.», «Campaña guardada.»,
      «Campaña iniciada.», «Campaña cancelada.» arriba a la derecha, éxito verde
      **auto-cierra a los 4 s**, error rojo **se queda hasta la ✕**; los errores de
      validación **de campo** salen **junto al campo**, no como toast.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/campanias/1/` →
      `405`, y la UI nunca ofrece borrar.

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 390 | Observaciones |
|---|---|---|---|---|
| 1. Entrada y filtros | ☐ | ☐ | ☐ | |
| 2. Tabla y fichas | ☐ | ☐ | ☐ | |
| 3. Alta y edición | ☐ | ☐ | ☐ | |
| 4. Iniciar y cancelar | ☐ | ☐ | ☐ | |
| 5. Permisos por rol | ☐ | ☐ | ☐ | |
| 6. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
