# Verificación UI — Semana 9 (checklist manual)

> Decisiones 18 y 19 (`decisiones_semana8.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas)
> y el responsable lo ejecuta en navegador y anota el resultado.
> Pantallas de la semana: la entrada **«Recursos»** del menú (tras «Producción»),
> la pantalla **`/recursos`** (listado de usos con filtros), los modales
> **`RecursoFormulario`** (alta/edición) y **`RecursoFicha`** (anular/reactivar),
> la sección **«Recursos usados»** de la ficha de actividad (HU-68, con aviso de
> cascada) y la sección **«Resumen de recursos»** de la ficha de campaña (HU-74).

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
- Los **recursos** (Semilla, Urea, Jornal, Diésel…) se crean desde **«Catálogos →
  Recursos»** (categoría + tipo de unidad); el **Quintal** (46 kg) desde
  **«Catálogos → Unidades»** si faltara. La regla de la Semana 9 rechaza en el
  servidor una categoría contra un tipo de unidad no admitido (p. ej. SEMILLA en
  VOLUMEN): el error sale **junto al campo** del formulario de catálogo.
- Para registrar usos hace falta una campaña **abierta** (`PLANIFICADA` o
  `EN_PRODUCCION`): créala desde la UI («Nueva campaña»; y para la cascada,
  además «Iniciar campaña» → «Registrar actividad» con tipo **Siembra** o
  **Fertilización**), **no** usar datos reales (decisión 17 de la Semana 4).
  Ojo con las reglas heredadas: una parcela solo admite **una campaña activa** y
  la fecha del uso no puede ser **futura** ni salir del **período** de la campaña.
- Alternativa: la colección `docs/coleccion_api_semana9.json` (235 peticiones)
  levanta en una BD de ensayo todo el guion de datos de la semana.

## 1. Chrome — escritorio 1366×768

### Menú y listado `/recursos` (HU-67)

- [ ] Con **admin**, la opción **«Recursos»** aparece en el menú, **después de
      «Producción» y antes de «Predicción»**; al entrar, la URL es `/recursos` y el
      título es **«Recursos e insumos»** con el conteo **«N en total»**.
- [ ] El botón **«Nuevo uso de recurso»** (primario, esquina superior derecha) solo
      aparece con `recursos.crear`.
- [ ] Los filtros son: **Buscar** (placeholder «Parcela, productor, recurso u
      observaciones»), **Campaña**, **Categoría** (8 categorías), **Recurso**
      (desplegable con «nombre (categoría)»), **Fecha desde**, **Fecha hasta** y
      **Estado** (Todos/Activos/Anulados); «Buscar» aplica la búsqueda y «Limpiar»
      (solo visible con filtros) resetea todo y la paginación.
- [ ] La tabla (componente `Tabla`, ancho completo, sin scroll interno) muestra las
      columnas **Fecha, Recurso** (nombre + chip de categoría)**, Cantidad**
      («16 kg»)**, En unidad base, Campaña** («período · cultivo»)**, Costo**
      («S/ 120.50» o «—»)**, Estado** (chip ACTIVA/ANULADA) **y Acciones**.
- [ ] Acciones: **«Editar»** (solo con `recursos.editar` y uso activo) abre el
      formulario; en otro caso **«Ver ficha»** abre la ficha. La paginación (20 por
      página) cambia la URL con `?page=` y muestra el estado `refrescando`.
- [ ] Sin coincidencias: panel **«No hay usos de recursos que coincidan con la
      búsqueda.»** + nota «Prueba a limpiar los filtros o registra un uso de
      recurso nuevo.»

### Alta y edición de usos (modal `formulario`, HU-69)

- [ ] «Nuevo uso de recurso» abre el modal **«Nuevo uso de recurso»**; la URL **no
      cambia**. Dos secciones: **«Datos del uso»** y **«Costo y observaciones»**.
- [ ] **Campaña** (formato «productor — parcela — cultivo (período)»): su ayuda al
      elegir muestra «Período de la campaña: {inicio} a {fin}.»; sin elegir, «Elige
      la campaña donde se registra el uso.»
- [ ] **Recurso** (formato «nombre (CATEGORÍA)»): al elegirlo, su ayuda muestra
      «Categoría {categoría}: se mide en unidades de tipo {masa|volumen|labor|tiempo}.»
      y el campo **Unidad** se recarga solo con las unidades activas de ese tipo
      (p. ej. para Urea: Kilogramo, Quintal, Tonelada, Gramo; para Jornal: Jornal).
- [ ] **Actividad (opcional)**: solo se puebla tras elegir campaña, con las
      actividades **activas** de esa campaña («fecha — tipo»); su ayuda avisa «Si la
      vinculas, la fecha del uso debe coincir con la de la actividad.»
- [ ] **Fecha** con `max` = hoy (selector nativo): ayuda «No puede ser futura y debe
      caer dentro del período de la campaña.»; **Cantidad** con ayuda «La base de
      datos convierte la cantidad a la unidad base.»; **Costo (S/)** y
      **Observaciones**.
- [ ] Errores de cliente **junto al campo** (sin toast): campaña/recurso/cantidad/
      unidad vacíos; cantidad ≤ 0; costo negativo; fecha futura; fecha fuera del
      período («La fecha debe estar dentro del período de la campaña (…).»); fecha
      distinta a la de la actividad vinculada.
- [ ] Guardar con rueda **«Guardando…»** dentro del botón (deshabilitado); toast
      **«Uso de recurso creado.»**; el listado se recarga con la fila nueva.
- [ ] «Editar» abre **«Editar uso de recurso»** con el formulario hidratado, la
      **campaña deshabilitada** (no se puede cambiar) y «Guardar cambios» → toast
      **«Uso de recurso guardado.»**
- [ ] Los errores del servidor (unidad incompatible, campaña cerrada, fecha fuera…)
      salen **junto al campo** correspondiente; los `non_field_errors` como **toast
      de error**; la campaña cancelada rechaza el alta con «La campaña está CANCELADA
      y no admite nuevos registros.»

### Ficha del uso (modal `ficha`, HU-68/72/73)

- [ ] «Ver ficha» abre el modal **«Uso de recurso del {fecha}»**: cabecera con
      nombre del recurso + chip de **categoría** + chip **ACTIVA/ANULADA** y botones
      **«Editar»**, **«Anular uso»** (peligro) o **«Reactivar»** según permiso y
      estado.
- [ ] Sección **«Datos del uso»**: Fecha, Recurso, Categoría, Tipo de unidad,
      Cantidad (con símbolo), En unidad base, Campaña («período · cultivo»),
      Actividad («fecha — tipo» o «—»), Costo, Observaciones y «Registrado por».
- [ ] **Anular uso** enfoca el campo **«Motivo de la anulación»** (ayuda
      «Obligatorio: el registro se conserva y queda como anulado.»); con motivo
      vacío el botón está **deshabilitado**; con motivo → confirmación en peligro
      **«Anular uso de recurso»** que **cita el motivo** → rueda **«Procesando…»**
      → toast **«Uso de recurso anulado.»**; la ficha recarga: chip **ANULADA** y
      sección **«Anulación»** con el motivo.
- [ ] Uso anulado: desaparecen «Editar» y el panel de anulación; **«Reactivar»**
      → confirmación **«Reactivar uso de recurso»** → rueda → toast **«Uso de
      recurso reactivado.»** y el chip vuelve a **ACTIVA**.
- [ ] Sin `recursos.desactivar` (técnico) la ficha **no muestra** «Anular uso» ni
      «Reactivar»; sin `recursos.editar` (coordinador) tampoco «Editar».

### Ficha de actividad: sección «Recursos usados» (HU-68)

- [ ] En la ficha de actividad (desde `/actividades` o desde la ficha de campaña)
      hay una sección **«Recursos usados»** con tabla **Fecha, Recurso** (+chip)**,
      Cantidad y Estado**; sin vínculos muestra «Esta actividad todavía no tiene usos
      de recursos vinculados.»
- [ ] Con `recursos.crear` y actividad activa aparece **«Registrar recurso»**: abre
      el formulario con la **campaña y la actividad preseleccionadas**.
- [ ] Debajo de la tabla se lee la nota fija: **«Al anular la actividad, sus usos de
      recursos activos se anulan en cascada, en la misma transacción y con el mismo
      motivo.»**
- [ ] Al anular la actividad con usos activos, la confirmación **añade** «Sus usos de
      recursos activos se anularán en cascada, en la misma transacción y con el
      mismo motivo.»; tras anular, la tabla de la ficha muestra esos usos con chip
      **ANULADA**.

### Ficha de campaña: sección «Resumen de recursos» (HU-74)

- [ ] La ficha de campaña gana la sección **«Resumen de recursos»** después de
      «Producción»: tabla **Categoría** (chip)**, Total** («184 kg», «10 L»)**, Por
      hectárea** («{n} {unidad}/ha» o «—» si la superficie es 0) **y Registros**.
- [ ] Con la nota: «Suma de los usos activos en la unidad base de cada categoría; el
      combustible se muestra en litros. Los usos anulados (incluidos los de la
      cascada) no cuentan.» — comprobar que un uso anulado **no** suma.
- [ ] Sin usos: «Esta campaña todavía no tiene usos de recursos registrados.»; en
      campaña **CANCELADA**: «La campaña está cancelada y no admite usos de
      recursos.»
- [ ] Con `recursos.crear` y campaña no `CERRADA`/`CANCELADA`, la cabecera de la
      ficha muestra también **«Registrar recurso»** (con la campaña preseleccionada).

## 2. Edge — 1024×768 (resolución del responsable)

- [ ] Repetir al menos: `/recursos` con filtros y alta, ficha del uso con
      anular/reactivar, ficha de actividad con «Recursos usados» y cascada, ficha de
      campaña con «Resumen de recursos».
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome; las tablas
      siguen en formato tarjeta a 1024 (umbral ≤ 860 px).

## 3. Móvil — 360×780 (Chrome devtools) y tablet 768×1024

- [ ] La tabla de `/recursos` se muestra como **tarjetas** (≤860 px) con etiqueta a
      la izquierda y valor a la derecha.
- [ ] **Sin scroll horizontal de la página** en 360 ni en 768 (listados, fichas,
      modales y formularios).
- [ ] Los modales (`formulario` y `ficha`) a **ancho completo ≤ 860 px**, ✕ ≥ 44 px,
      cuerpo con scroll interno y botones (Nuevo uso de recurso, Guardar cambios,
      Anular uso, Cancelar) apilados a ancho completo; se puede escribir en todos los
      campos (fecha con el selector nativo, cantidad/costo con teclado numérico).
- [ ] **Pila de modales**: ficha de campaña → registrar recurso → ficha de actividad
      → recursos usados: Escape/✕ cierran solo el de arriba y el de abajo retoma el
      scroll.
- [ ] Botones de acción (Nuevo uso de recurso, Editar, Anular uso, Reactivar, Ver
      ficha, Registrar recurso) ≥ 44 px en táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Admin** (`admin`): ve «Recursos» en el menú y usa todas las acciones (alta,
      edición, anular, reactivar) y «Registrar recurso» desde actividad y campaña.
- [ ] **Coordinador** (`coordinador`): ve «Recursos» (solo `recursos.ver`) pero la
      pantalla **sin botón «Nuevo uso de recurso»** y las acciones son solo «Ver
      ficha»; la ficha del uso **sin «Editar», sin «Anular uso» ni «Reactivar»**; en
      la ficha de actividad y en la de campaña **sin «Registrar recurso»** (crear por
      API → 403, colección 206).
- [ ] **Técnico** (`tecnico`): ve las campañas de **sus productores asignados**; en
      sus usos puede **«Editar»** pero **no** «Anular uso» ni «Reactivar» (sin
      `recursos.desactivar`; por API → 403, colección 235); «Registrar recurso» solo
      en campañas de sus productores.
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** dentro del botón (`AGENTS.md`): «Guardando…» en el
      formulario de usos; **«Procesando…»** en las confirmaciones que pasan por
      `Modal` (anular uso, reactivar, anular actividad con cascada).
- [ ] Cargando inicial: `/recursos` con `Cargando…` a pantalla completa sin parpadear
      datos viejos; los modales de ficha/edición hidratan con `Cargando…`.
- [ ] Error de red/servidor al listar usos: aviso rojo (`Aviso`) en la página y el
      resto sigue operativo; con el backend caído, los modales muestran el aviso/toast
      de error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Uso de recurso creado.», «Uso de
      recurso guardado.», «Uso de recurso anulado.», «Uso de recurso reactivado.» —
      éxito verde **auto-cierra a los 4 s**, error rojo **se queda hasta la ✕**; los
      errores de validación **de campo** salen **junto al campo**, no como toast.
- [ ] Escape cierra el modal de arriba (pila de modales) y ningún
      `window.confirm`/`alert` en toda la pantalla.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/usos-recursos/{id}/`
      → `405`; la UI nunca ofrece borrar (anulación lógica con motivo).

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 360 | Observaciones |
|---|---|---|---|---|
| 1. Menú y listado `/recursos` | ☐ | ☐ | ☐ | |
| 2. Alta y edición de usos | ☐ | ☐ | ☐ | |
| 3. Ficha del uso (anular/reactivar) | ☐ | ☐ | ☐ | |
| 4. Ficha de actividad y cascada | ☐ | ☐ | ☐ | |
| 5. Ficha de campaña y resumen | ☐ | ☐ | ☐ | |
| 6. Permisos por rol | ☐ | ☐ | ☐ | |
| 7. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
