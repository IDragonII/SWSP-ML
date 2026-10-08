# Verificación UI — Semana 4 (checklist manual)

> Decisión 16 (`decisiones_semana4.md`): sin Playwright. El agente deja este checklist
> (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas) y el
> responsable lo ejecuta en navegador y anota el resultado.

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
- El listado inicial de productores y parcelas debe mostrar datos de demo (o los creados
  durante la prueba); crear datos nuevos está permitido, **no** usar DNI/teléfono/coordenadas
  reales (decisión 17).

## 1. Chrome — escritorio 1366×768

- [ ] Listados y ficha: la tabla (con su cabecera y filtros) ocupa **todo el ancho**
      disponible, sin dejar hueco a la derecha y sin scroll interno (el texto largo se
      parte en varias líneas). Las tablas usan el componente único `components/Tabla.jsx`.

### Productores (`/productores`)

- [ ] La tabla muestra Código, Productor, DNI, Comunidad, Estado y «Ver ficha».
- [ ] «Nuevo productor» visible para admin; oculto para coordinador.
- [ ] Filtrar por estado (Activos/Inactivos) actualiza la tabla y la URL (`?estado=`).
- [ ] Filtrar por comunidad actualiza la tabla y la URL (`?comunidad=`).
- [ ] Buscar por apellidos/DNI/código → «Buscar» cambia la URL (`?busqueda=`) y la tabla.
- [ ] «Limpiar» (solo aparece con filtros activos) restaura la lista completa.
- [ ] Sin coincidencias → mensaje «No hay productores que coincidan con la búsqueda.».
- [ ] Cambiar de página (Paginación) resalta la tabla brevemente (clase `refrescando`).
- [ ] Navegador atrás/adelante: los filtros del formulario vuelven a coincidir con la URL.

### Ficha del productor (modal, desde «Ver ficha»)

- [ ] Al pulsar «Ver ficha» (fila del listado o nombre del productor) se abre una
      **ventana flotante**; la URL **no cambia** y el listado queda de fondo.
- [ ] Título con el nombre; dentro: código (chip), estado y acciones: Editar,
      Nueva parcela, Desactivar; el ✕ de la cabecera cierra.
- [ ] Cuerpo con **scroll interno** (el listado de detrás no se mueve ni baja).
- [ ] Panel «Datos» con DNI/teléfono/fechas; panel «Ubicación» con
      `comunidad · distrito · provincia` (se carga vía `GET /ubicaciones/comunidades/{id}/`).
- [ ] Panel «Parcelas» con resumen (activas/total y ha) y tabla de parcelas con «Editar».
- [ ] Panel «Técnicos asignados» **visible** para admin y coordinador.
- [ ] Admin: el formulario «Asignar un técnico» lista solo técnicos activos y funciona
      (aparece en la tabla de asignaciones con fecha).
- [ ] Admin: «Desactivar» en una asignación abre el **modal de confirmación** (no el
      diálogo del navegador) y la marca INACTIVA; «Reactivar» la vuelve ACTIVA
      (el registro nunca se borra).
- [ ] Admin: «Desactivar» el productor abre el **modal de confirmación**; al confirmar
      recarga y el chip pasa a INACTIVO; «Reactivar» lo devuelve a ACTIVO.
- [ ] Coordinador: ve la ficha y las asignaciones, pero **no** ve Editar/Nueva parcela/Desactivar.

### Alta y edición de productor (modales «Nuevo productor» / «Editar»)

- [ ] «Nuevo productor» (listado) y «Editar» (ficha) abren el formulario en **modal**,
      sin cambiar la URL; formularios en **una sola columna**.
- [ ] Cancelar o ✕ cierra el modal sin guardar (el listado o la ficha siguen intactos).
- [ ] Alta: cascada provincia → distrito → comunidad (cada paso habilita el siguiente).
- [ ] DNI con más o menos de 8 dígitos → error del servidor bajo el campo (en español).
- [ ] DNI duplicado → error de campo en español.
- [ ] Campos vacíos obligatorios → «El productor…» / mensajes 400 por campo.
- [ ] Alta exitosa → cierra el modal, refresca el listado y se abre la **ficha** del
      productor nuevo (con su código PRO-000N ya generado).
- [ ] Edición: la comunidad aparece pre-cargada (cascada completa hidratada) y al guardar
      se cierra el modal y la ficha muestra los cambios.

### Parcelas (`/parcelas`)

- [ ] Tabla con Código, Productor, Comunidad, Superficie, Estado y acción
      (Editar para admin/coordinador-con-permiso, «Ver ficha» para el técnico).
- [ ] Filtros por estado (Activas/Inactivas), comunidad y búsqueda funcionan como en productores.
- [ ] «Nueva parcela» visible para quien tiene `parcelas.crear`.
- [ ] Botón «Ver ficha»/«Editar» de cada fila abre el modal correspondiente
      (ficha o edición) sin cambiar la URL.

### Alta y edición de parcela (modales «Nueva parcela» / «Editar»)

- [ ] Desde la ficha de un productor, «Nueva parcela» abre el modal con el productor
      **preseleccionado** y la comunidad ya elegida.
- [ ] Alta manual: productor, comunidad y superficie/altitud obligatorios → errores 400
      en español bajo cada campo si faltan.
- [ ] Coordenadas: escribir solo latitud → aviso «Las coordenadas deben ir las dos o ninguna.»
      (no llega a llamar al servidor); las dos o ninguna pasa la validación.
- [ ] Listas cerradas (tipo de suelo, pendiente, agua, riego) coinciden con el backend.
- [ ] Edición: el productor aparece en solo lectura y no se puede cambiar.
- [ ] Edición: cabecera con chip de estado + botón Desactivar/Reactivar (admin) que abre
      el **modal de confirmación**; el estado cambia y la lista lo refleja.
- [ ] Alta exitosa → cierra el modal y refresca el listado (o la ficha, si se abrió
      desde ella) con la parcela nueva.

## 2. Edge — igual que Chrome (1366×768)

- [ ] Repetir al menos: listado de productores, ficha, alta de parcela y filtros.
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome.

## 3. Móvil — 390×844 (Chrome devtools) y tablet 768×1024

- [ ] Las tablas se muestran como **tarjetas** (una fila por tarjeta con
      etiqueta a la izquierda y valor a la derecha): listados, parcelas de la ficha y
      asignaciones.
- [ ] **Sin scroll horizontal de la página** en 390 ni en 768 (listados, fichas y formularios).
- [ ] Los formularios siguen en **una sola columna** (decisión 14) y se puede escribir
      en todos los campos.
- [ ] Los **modales** se adaptan: ancho completo ≤ 860 px, ✕ ≥ 44 px, cuerpo con scroll
      interno y botones del pie (Cancelar/Guardar) apilados a ancho completo.
- [ ] Botones y enlaces de acción ≥ 44 px (filtros, acciones de cabecera, paginación).
- [ ] Filtros apilados y botones Buscar/Limpiar a ancho completo.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Técnico** (`tecnico`): solo ve sus productores/parcelas (si un admin le acaba de
      quitar la asignación, `/productores` y `/parcelas` quedan vacíos).
- [ ] **Técnico**: al crear un productor/parcela se auto-asigna (aparece como técnico de
      ese productor).
- [ ] **Técnico**: **no** recibe el bloque «Técnicos asignados» en la ficha (decisión 7)
      ni el formulario de asignación.
- [ ] **Técnico**: no ve «Desactivar» (no tiene `*.desactivar`); sí ve «Nuevo productor»
      y «Editar» en sus propios recursos (al crear, se auto-asigna).
- [ ] **Coordinador** (`coordinador`): ve listados y fichas completas (incluye técnicos
      asignados), pero los botones Crear/Editar/Desactivar **no aparecen** (el permiso se
      ve en el botón). Las rutas antiguas de formulario ya no existen:
      `/productores/nuevo` y `/parcelas/1/editar` caen en «Página no encontrada».
- [ ] **Admin** (`admin`): ve y usa todas las acciones, incluida la gestión de asignaciones.
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) cualquier pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] Cargando inicial: muestra el spinner (`Cargando…`) y no parpadean datos viejos.
- [ ] Error de red/servidor: aviso rojo con mensaje legible y la lista conserva lo último.
- [ ] Con el backend caído (parar el runserver), abrir la ficha desde el listado: el
      modal muestra el aviso de error y el ✕ sigue cerrando.
- [ ] 404 en español vía consola:
      `fetch('http://localhost:8000/api/productores/999999/', { credentials: 'include' }).then(r => r.json())`
      → `{"detail": "No encontrado."}`.
- [ ] Aviso verde de éxito tras activar/desactivar y tras asignar técnico.
- [ ] **Modales** (`components/Modal.jsx`): ningún diálogo nativo del navegador
      (`window.confirm`/`alert`). Confirmación: se abre desde Desactivar/Reactivar
      (ficha, asignaciones, edición de parcela); Escape o clic en el fondo lo cierra;
      mientras muestra «Procesando…» los botones están deshabilitados y no se cierra;
      al terminar aparece el aviso verde en la página de fondo.
- [ ] **Modales apilados**: listado → «Ver ficha» → «Editar» → «Desactivar»
      (confirmación encima). Escape o ✕ cierran **solo el de arriba**; al cerrarlos
      todos, la página de fondo conserva el scroll y el listado se refrescó.
- [ ] PUT/DELETE sobre un recurso (probar con consola: `fetch(...,{method:'DELETE'})`)
      → 405, y la UI nunca ofrece borrar.

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 390 | Observaciones |
|---|---|---|---|---|
| 1. Productores | ☐ | ☐ | ☐ | |
| 2. Ficha | ☐ | ☐ | ☐ | |
| 3. Alta/edición productor | ☐ | ☐ | ☐ | |
| 4. Parcelas | ☐ | ☐ | ☐ | |
| 5. Alta/edición parcela | ☐ | ☐ | ☐ | |
| 6. Permisos por rol | ☐ | ☐ | ☐ | |
| 7. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
