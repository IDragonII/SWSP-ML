# Verificación UI — Semana 11 (checklist manual)

> Decisiones 17 y 18 (`decisiones_semana10.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0
> problemas, y la suite de backend **172/172 en verde**; `manage.py check` 0
> issues y `makemigrations --check` sin cambios) y el responsable lo ejecuta
> en navegador y anota el resultado.
> Pantallas de la semana: la entrada **«Incidencias»** del menú, la pantalla
> **`/incidencias`** (listado con filtros), los modales **`IncidenciaFormulario`**
> (alta/edición) e **`IncidenciaFicha`** (con anulación/reactivación), la sección
> **«Incidencias»** de la ficha de campaña (HU-89, resumen), el **historial** por
> campaña en la ficha de parcela (HU-89) y los contadores de la ficha de
> productor (HU-89).

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
- Se necesita al menos una **campaña que admita registros** (`PLANIFICADA`,
  `EN_PRODUCCION` o `COSECHADA`): créala desde la UI («Nueva campaña»), **no**
  usar datos reales (decisión 17 de la Semana 4).
- Los catálogos **«Tipos de incidencia»** y **«Agentes»** se gestionan en
  **Catálogos** (solo admin): para probar el agente, crea un tipo con categoría
  **Biológica** y un agente activo; para el bloque sin agente usa un tipo
  **Climática** o **Otra**.
- La anulación de campañas ya existente sirve para comprobar que una campaña
  **CERRADA/CANCELADA** no admite registros (error junto al campo).
- Alternativa: la colección `docs/coleccion_api_semana11.json` (se cierra en F7)
  levanta, con la siembra previa de F7, todo el guion de datos de la semana.

## 1. Chrome — escritorio 1366×768

### Menú y listado `/incidencias` (HU-85)

- [ ] Con **admin**, la opción **«Incidencias»** aparece en el menú (con
      `incidencias.ver`); al entrar, la URL es `/incidencias` y el título es
      **«Incidencias»** con el conteo **«N en total»**.
- [ ] El botón **«Registrar incidencia»** (primario, esquina superior derecha)
      solo aparece con `incidencias.crear`.
- [ ] Los filtros son: **Buscar** (placeholder «Código de parcela, productor,
      agente o descripción»), **Estado** (Todos/Activa/Anulada), **Severidad**
      (Todas/Baja/Media/Alta), **Categoría** (Todas/Climática/Biológica/Otra),
      **Tipo** (solo activos), **Productor**, **Parcela**, **Fecha desde** y
      **Fecha hasta**; «Buscar» aplica la búsqueda y «Limpiar» (solo visible
      con filtros) resetea todo y la paginación.
- [ ] La tabla (componente `Tabla`) muestra las columnas **Fecha, Tipo**
      (nombre + chip de categoría), **Severidad** (chip), **Agente** (nombre o
      «—»), **Superficie (ha)**, **Campaña** («período · cultivo»), **Parcela**,
      **Estado** (chip **ACTIVA**/**ANULADA**) **y Acciones**.
- [ ] Acciones: **«Editar»** solo con `incidencias.editar` **y** si la fila
      está activa; **«Ver ficha»** siempre. La paginación (20 por página) cambia
      la URL con `?page=` y muestra el estado `refrescando`.
- [ ] Sin coincidencias: panel **«No hay incidencias que coincidan con la
      búsqueda.»** + nota «Prueba a limpiar los filtros o registra una
      incidencia desde el botón superior.»

### Alta y edición de incidencia (modal `formulario`, HU-85/86)

- [ ] «Registrar incidencia» abre el modal **«Registrar incidencia»**; la URL
      **no cambia**. Dos secciones: **«Datos de la incidencia»** y
      **«Agente y tratamiento»**.
- [ ] **Campaña** (formato «productor — parcela — cultivo (período)»): solo
      campañas que admiten registros; ayuda con el período de la elegida; en
      edición aparece **deshabilitada** (la campaña no se puede cambiar).
- [ ] **Tipo de incidencia** (solo activos): ayuda «La categoría define si
      puedes indicar un agente (solo biológicos).»; al cambiar el tipo, el
      agente se limpia.
- [ ] **Fecha** con `max` = hoy (selector nativo); validación de cliente si
      queda **fuera del período de la campaña** («La fecha debe estar dentro
      del período de la campaña (desde a hasta).»).
- [ ] **Severidad** obligatoria (Baja/Media/Alta); **Descripción** obligatoria
      (textarea); **Superficie afectada (ha, opcional)** con ayuda «No puede
      superar la superficie sembrada de la campaña.» y error de cliente si es
      negativa.
- [ ] **Agente**: con tipo **Biológica**, desplegable de agentes activos (o
      «Sin agente asignado»); con otro tipo, el campo sale **deshabilitado**
      con «No aplica para este tipo» y la ayuda «El agente solo puede
      indicarse en tipos biológicos (plaga o enfermedad).»
- [ ] **Producto aplicado (informativo)**: máx. 100 caracteres (el input corta
      en 100; el servidor también), ayuda «solo informativo… no controla
      existencias.»
- [ ] Errores del servidor **junto al campo** (sin toast): superficie > sembrada
      con los dos números («La superficie afectada (8 ha) supera la sembrada
      (5 ha).»), fecha fuera de período con el período, campaña cerrada
      («La campaña está CERRADA y no admite nuevos registros.»), agente en tipo
      no biológico, producto > 100.
- [ ] Guardar con rueda **«Guardando…»** dentro del botón (deshabilitado);
      toast **«Incidencia creada.»**; el listado se recarga con la fila nueva.
- [ ] «Editar» abre **«Editar incidencia»** con el formulario hidratado
      (campaña bloqueada) y «Guardar cambios» → toast **«Incidencia
      guardada.»**

### Ficha de la incidencia (modal `ficha`, con anulación HU-88)

- [ ] «Ver ficha» abre el modal **«Incidencia del {fecha}»**: cabecera con el
      tipo + chips de **categoría**, **severidad** y **ACTIVA/ANULADA**, y
      botones **«Editar»** (con `incidencias.editar` y activa), **«Anular
      incidencia»** (peligro, con `incidencias.desactivar` y activa; al
      pulsarlo se enfoca el campo de motivo) o **«Reactivar»** (solo si está
      anulada).
- [ ] Si está anulada: panel **«Anulación»** con el **Motivo**.
- [ ] Sección **«Datos de la incidencia»**: Fecha, Tipo, Categoría, Severidad,
      Campaña («período · cultivo»), Parcela, Productor, Superficie afectada
      («0.50 ha» o «—»), Agente («nombre (tipo)» o «—»), Producto aplicado y
      Descripción.
- [ ] Sección **«Trazabilidad»**: **Registrado por** (visible con admin;
      **ausente** con `tecnico`), Creado y Última edición.
- [ ] Panel **«Anular incidencia»** (solo con `incidencias.desactivar` y
      activa): campo **«Motivo de la anulación»** obligatorio; el botón está
      deshabilitado sin motivo; al pulsarlo, confirmación en `Modal` («Procesando…»)
      y luego toast **«Incidencia anulada.»** con la ficha recargada (chip
      **ANULADA** + motivo). El texto de la confirmación avisa de que las
      anuladas **no cuentan** en el dataset ni en los resúmenes.
- [ ] **«Reactivar»**: confirmación en `Modal` → toast **«Incidencia
      reactivada.»**; con la campaña ya cerrada, error en toast («La campaña
      está CERRADA y no admite nuevos registros.»).
- [ ] Desde la ficha, **«Editar»** apila el modal de edición encima y al
      guardar la ficha se recarga.

### Ficha de campaña: sección «Incidencias» (HU-89)

- [ ] La ficha de campaña tiene, al final, la sección **«Incidencias»** con
      botones de texto **«Registrar incidencia»** (solo con `incidencias.crear`
      y campaña abierta; abre el formulario con la campaña preseleccionada) y
      **«Ver todas»** (navega a `/incidencias?campania={id}` y cierra la ficha).
- [ ] Con incidencias activas: rejilla con **Activas** (nº), **Por severidad**
      («Baja 1 · Media 0 · Alta 2»), **Severidad máxima**, **Última
      incidencia** (fecha) y **Mayor superficie** («1.20 ha» o «—»), más la
      nota **«Solo cuentan las incidencias activas; las anuladas no se
      incluyen en el resumen ni en el dataset.»**
- [ ] Sin incidencias: **«Esta campaña todavía no tiene incidencias
      activas.»** (bloque con ceros, **no** un error).

### Ficha de parcela: historial de incidencias (HU-89)

- [ ] Entre las secciones «Clima» y «Campañas» aparece **«Incidencias»**:
      agrupadas **por campaña** (línea «período · cultivo» + chip de estado),
      cada grupo con su tabla **Fecha, Tipo** (con chip de categoría)**,
      Severidad, Superficie (ha), Estado** (chip ACTIVA/ANULADA) **y Acciones
      («Ver ficha»)**, más el botón de texto **«Ver todas»**
      (`/incidencias?parcela={id}`, cierra la ficha).
- [ ] Las **anuladas no aparecen** en el historial por defecto (se ocultan).
- [ ] Sin incidencias: **«Esta parcela todavía no tiene incidencias
      registradas.»** + «Ver todas».

### Ficha de productor: contadores (HU-89)

- [ ] En la sección «Parcelas», el resumen añade **«N incidencia(s)
      activa(s)»** y **«Última incidencia: {fecha}»** («—» si no hay).

## 2. Edge — 1024×768 (resolución del responsable)

- [ ] Repetir al menos: `/incidencias` con filtros y alta, edición de una
      incidencia, ficha con anulación (motivo obligatorio) y reactivación,
      ficha de campaña con resumen, ficha de parcela con historial y ficha de
      productor con contadores.
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome; las tablas
      siguen en formato tarjeta a 1024 (umbral ≤ 860 px).

## 3. Móvil — 360×780 (Chrome devtools) y tablet 768×1024

- [ ] La tabla de `/incidencias` y las tablas del historial se muestran como
      **tarjetas** (≤860 px) con etiqueta a la izquierda y valor a la derecha.
- [ ] **Sin scroll horizontal de la página** en 360 ni en 768 (listados, fichas,
      modales y formularios).
- [ ] Los modales (`IncidenciaFormulario`, `IncidenciaFicha`) a **ancho completo
      ≤ 860 px**, ✕ ≥ 44 px, cuerpo con scroll interno y botones (Registrar
      incidencia, Guardar cambios, Anular incidencia, Cerrar/Cancelar) apilados
      a ancho completo; se puede escribir en todos los campos (fechas con el
      selector nativo, superficie con teclado numérico).
- [ ] **Pila de modales**: listado → ficha → edición, ficha de campaña →
      registrar incidencia y ficha de parcela → ficha de incidencia: Escape/✕
      cierran solo el de arriba y el de abajo retoma el scroll.
- [ ] Botones de acción (Registrar incidencia, Editar, Ver ficha, Anular,
      Reactivar, Ver todas) ≥ 44 px en táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Admin** (`admin`): ve «Incidencias» en el menú y usa todas las acciones
      (alta, edición, anulación con motivo, reactivación) y «Registrar
      incidencia» desde la ficha de campaña; ve `registrado_por` en la ficha.
- [ ] **Coordinador** (`coordinador`): ve «Incidencias» (solo `incidencias.ver`)
      pero la pantalla **sin botón «Registrar incidencia»** y las acciones son
      solo **«Ver ficha»**; la ficha **sin «Editar» ni «Anular incidencia»**
      (por API: crear/edición → 403; anular/reactivar → 403).
- [ ] **Técnico** (`tecnico`): el listado solo muestra incidencias de **sus
      productores asignados**; puede **«Editar»** y **«Registrar incidencia»**
      (campaña ajena → «La campaña indicada no existe.» 400); **no** tiene
      «Anular incidencia» (sin `incidencias.desactivar`; por API → 403, no
      404); en la ficha **no ve «Registrado por»**.
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al
      login tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** dentro del botón (`AGENTS.md`): «Guardando…» en el
      formulario; **«Procesando…»** en la anulación/reactivación (el `Modal` de
      confirmación también muestra «Procesando…» con `ocupado`).
- [ ] Cargando inicial: `/incidencias` con `Cargando…` a pantalla completa sin
      parpadear datos viejos; los modales de ficha/edición hidratan con
      `Cargando…`.
- [ ] Error de red/servidor al listar: aviso rojo (`Aviso`) en la página y el
      resto sigue operativo; con el backend caído, los modales muestran el
      aviso/toast de error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Incidencia creada.», «Incidencia
      guardada.», «Incidencia anulada.», «Incidencia reactivada.» — éxito verde
      **auto-cierra a los 4 s**, error rojo **se queda hasta la ✕**; los
      errores de validación **de campo** salen **junto al campo**, no como
      toast.
- [ ] Escape cierra el modal de arriba (pila de modales) y ningún
      `window.confirm`/`alert` en toda la pantalla.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/incidencias/{id}/`
      → `405`; la UI nunca ofrece borrar (solo edición y anulación).
- [ ] Una incidencia **anulada** desaparece del resumen de su campaña, del
      historial de la parcela y del contador del productor (y del listado con
      filtro «Activa»), pero sigue siendo visible con el filtro «Anulada».

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 360 | Observaciones |
|---|---|---|---|---|
| 1. Menú y listado `/incidencias` | ☐ | ☐ | ☐ | |
| 2. Alta y edición de incidencia | ☐ | ☐ | ☐ | |
| 3. Ficha con anulación y reactivación | ☐ | ☐ | ☐ | |
| 4. Ficha de campaña (resumen) | ☐ | ☐ | ☐ | |
| 5. Ficha de parcela (historial) y productor | ☐ | ☐ | ☐ | |
| 6. Permisos por rol | ☐ | ☐ | ☐ | |
| 7. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
