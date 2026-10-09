# Verificación UI — Semana 5 (checklist manual)

> Decisiones 16 y 17 (`decisiones_semana5.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas)
> y el responsable lo ejecuta en navegador y anota el resultado.
> Pantalla nueva de la semana: **`/catalogos`** (8 catálogos en pestañas).

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
- Los 8 catálogos ya tienen datos (26 fijos de la migración + los que cree el comando
  `cargar_catalogos`); crear datos nuevos está permitido, **no** usar datos reales
  (decisión 17 de la Semana 4).

## 1. Chrome — escritorio 1366×768

### Entrada y pestañas (`/catalogos`)

- [ ] Con **admin**: la opción **«Catálogos»** aparece en el menú, después de «Parcelas».
- [ ] Al entrar, la URL es `/catalogos` (sin parámetro rige el primer catálogo) y se
      muestran las **8 pestañas**: Cultivos, Variedades, Etapas fenológicas, Unidades,
      Tipos de actividad, Recursos, Tipos de incidencia, Agentes.
- [ ] La pestaña activa queda resaltada y con `aria-pressed="true"`; al pulsar otra,
      la URL cambia (`?catalogo=`), se limpian `busqueda`/`estado`/`page` y cambian
      las columnas de la tabla.
- [ ] Debajo del título «Catálogos» se muestra el **conteo** («12 cultivos», etc.)
      según el catálogo activo.
- [ ] La URL con un catálogo desconocido (`?catalogo=zzz`) abre el primero (Cultivos).
- [ ] Botón de alta arriba a la derecha con el texto del catálogo («Nuevo cultivo»,
      «Nueva variedad»…); **no aparece** en Tipos de actividad.

### Filtros y tabla

- [ ] **Buscar** (placeholder «Nombre del cultivo», etc.) + botón **Buscar** → la tabla
      filtra y la URL cambia (`?busqueda=`); **Estado** (Todos/Activos/Inactivos)
      cambia la URL (`?estado=`) y la tabla **al vuelo**.
- [ ] Con filtros activos aparece **Limpiar** y restaura la lista completa.
- [ ] Sin coincidencias → «No hay cultivos que coincidan con la búsqueda.» + nota
      (con admin: «…usa el botón de arriba para crear uno nuevo.»).
- [ ] La tabla usa `components/Tabla.jsx` y ocupa **todo el ancho**, sin scroll interno.
- [ ] Cambiar de página (Paginación, 20 por página) resalta la tabla brevemente
      (clase `refrescando`).
- [ ] Navegador atrás/adelante: pestaña, filtros y página vuelven a coincidir con la URL.

### Columnas por catálogo

- [ ] **Cultivos:** Nombre, Descripción, Estado (chip ACTIVO/INACTIVO) y Acciones.
- [ ] **Variedades:** Cultivo (nombre del cultivo), Nombre, Estado, Acciones.
- [ ] **Etapas fenológicas:** Cultivo, Orden, Etapa — **sin columna Estado y sin botón
      Desactivar/Reactivar** (las etapas no tienen estado).
- [ ] **Unidades:** Nombre, Símbolo (chip), Tipo (etiqueta en español: «Masa»…),
      Factor a la base, Unidad base («Base» o «—») y Estado.
- [ ] **Tipos de actividad:** Código (chip), Nombre, Estado; **no hay botón de alta**.
- [ ] **Recursos:** Nombre, Categoría («Semilla»…) y Tipo de unidad en español, Estado.
- [ ] **Tipos de incidencia:** Nombre, Categoría («Climática»…), Estado.
- [ ] **Agentes:** Nombre, Tipo («Plaga»/«Enfermedad»), Estado.

### Alta y edición (modal, mismo patrón para los 7 catálogos con alta)

- [ ] «Nuevo cultivo» abre el formulario en **modal** (título «Nuevo cultivo»), la URL
      **no cambia** y la tabla queda de fondo; formulario en **una sola columna**.
- [ ] Cancelar o ✕ cierra sin guardar; mientras se guarda, el botón muestra la **rueda**
      con «Guardando…» y queda deshabilitado (el ✕ también, prop `ocupado`).
- [ ] **Variedades/Etapas:** el select «Cultivo» lista solo cultivos **activos**
      (desplegable); sin elegir opción → error del cliente «Elige una opción.» bajo el campo.
- [ ] **Cultivo** con nombre ya usado → error del servidor bajo el campo:
      «Ya existe un cultivo con ese nombre.» (prueba también con MAYÚSCULAS y espacios:
      la API normaliza, no debe duplicar).
- [ ] **Etapas:** orden `0` → «El orden debe ser un número entre 1 y 1000.» bajo el
      campo; orden repetido en el cultivo → «Ya existe otra etapa con el orden N para
      ese cultivo.»; la ayuda del campo dice «Entre 1 y 1000; no puede repetirse dentro
      del cultivo.»
- [ ] **Unidades:** factor `0` → «El factor debe ser mayor que 0.»; el formulario **no
      ofrece** el campo «es base» (las unidades base vienen sembradas).
- [ ] Alta exitosa → cierra el modal, refresca la tabla y aparece el **toast** verde
      «Registro creado.»
- [ ] **Editar** (botón de la fila) abre el modal «Editar cultivo» **hidratado** con el
      dato (se ve `Cargando…` mientras carga); guardar → «Cambios guardados.» y la tabla
      refleja el cambio.
- [ ] **Tipos de actividad:** solo se puede editar el nombre; guardar no ofrece código.

### Desactivar / reactivar (confirmación en modal)

- [ ] «Desactivar» en una fila abre el **modal de confirmación** (no el diálogo del
      navegador): «¿Desactivar «Quinua»? Dejará de aparecer en los listados y
      desplegables.» con botón rojo «Desactivar».
- [ ] Al confirmar, el botón muestra «Procesando…» (deshabilitado) y al terminar
      aparece el **toast** «Registro desactivado.»; el chip pasa a INACTIVO.
- [ ] «Reactivar» (fila inactiva o filtro Inactivos) → «¿Reactivar «X»? Volverá a
      aparecer…» → «Registro reactivado.» y chip ACTIVO.
- [ ] **Unidad base** (Kilogramo, Hectárea…): «Desactivar» → **toast de error**
      «Las unidades base no se pueden desactivar.» (el registro no cambia).
- [ ] **Siembra/Cosecha** (tipos de actividad): «Desactivar» → toast de error
      «Siembra y Cosecha no se pueden desactivar.»
- [ ] Escape o clic en el fondo cancelan la confirmación sin llamar a la API.

## 2. Edge — igual que Chrome (1366×768)

- [ ] Repetir al menos: pestañas, cultivos (alta + edición), variedades y etapas.
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome.

## 3. Móvil — 390×844 (Chrome devtools) y tablet 768×1024

- [ ] Las pestañas siguen pulsables (áreas ≥ 44 px) y **no producen scroll horizontal
      de la página**.
- [ ] Las tablas se muestran como **tarjetas** (una fila por tarjeta con etiqueta a la
      izquierda y valor a la derecha): los 8 catálogos.
- [ ] **Sin scroll horizontal de la página** en 390 ni en 768 (listados, modales y filtros).
- [ ] Filtros apilados y Buscar/Limpiar a ancho completo; el formulario del modal sigue
      en **una sola columna** y se puede escribir en todos los campos.
- [ ] El **modal** se adapta: ancho completo ≤ 860 px, ✕ ≥ 44 px, cuerpo con scroll
      interno y botones (Guardar/Cancelar) apilados a ancho completo.
- [ ] Botones de acción de fila (Editar/Desactivar) ≥ 44 px en táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Coordinador** (`coordinador`): la opción «Catálogos» **no aparece** en el menú;
      entrar directamente en `/catalogos` **redirige** a `/acceso-denegado`
      («No tienes acceso a esta sección»). En la API, `POST /api/cultivos/` → 403
      (puede comprobarse con la colección 093).
- [ ] **Técnico** (`tecnico`): igual que coordinador (solo tiene `catalogos.ver`;
      ni menú ni pantalla).
- [ ] **Admin** (`admin`): ve y usa todas las acciones de los 8 catálogos.
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** (`components/RuedaCarga.jsx`, ver `AGENTS.md`): «Guardar» del
      formulario muestra la rueda **dentro del botón** con «Guardando…» y el botón
      queda deshabilitado; la confirmación de estado usa el `Modal` con «Procesando…».
- [ ] Cargando inicial: pantalla completa (`Cargando…`) sin parpadear datos viejos;
      al cambiar de pestaña no se muestran columnas viejas con datos nuevos.
- [ ] Error de red/servidor al listar: aviso rojo (`Aviso`) en la página y el resto
      sigue operativo.
- [ ] Con el backend caído (parar el runserver): los modales de alta/edición muestran
      el aviso/toast de error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Registro creado.», «Cambios
      guardados.», «Registro desactivado./reactivado.» arriba a la derecha, éxito
      verde **auto-cierra a los 4 s**, error rojo **se queda hasta la ✕**; los errores
      de validación **de campo** salen **junto al campo**, no como toast (para no
      duplicarlos).
- [ ] **Modales** (`components/Modal.jsx`): ningún `window.confirm`/`alert` en toda
      la pantalla.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/cultivos/1/` →
      `405`, y la UI nunca ofrece borrar.

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 390 | Observaciones |
|---|---|---|---|---|
| 1. Entrada y pestañas | ☐ | ☐ | ☐ | |
| 2. Filtros y tabla | ☐ | ☐ | ☐ | |
| 3. Columnas por catálogo | ☐ | ☐ | ☐ | |
| 4. Alta y edición | ☐ | ☐ | ☐ | |
| 5. Desactivar/reactivar | ☐ | ☐ | ☐ | |
| 6. Permisos por rol | ☐ | ☐ | ☐ | |
| 7. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
