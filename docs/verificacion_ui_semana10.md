# Verificación UI — Semana 10 (checklist manual)

> Decisiones 17 y 18 (`decisiones_semana10.md`): sin Playwright. El agente deja este
> checklist (además de `npm run lint` y `npm run build`, ya ejecutados con 0 problemas)
> y el responsable lo ejecuta en navegador y anota el resultado.
> Pantallas de la semana: la entrada **«Clima»** del menú, la pantalla
> **`/clima`** (listado de registros con filtros), los modales
> **`ClimaFormulario`** (alta/edición), **`ClimaFicha`** y **`ClimaConsulta`**
> (HU-84, consulta a la API meteorológica), la sección **«Clima»** de la ficha
> de parcela (HU-83), la sección **«Resumen de clima»** de la ficha de campaña
> (HU-82) y la fila **`umbral_helada_c`** en `/parametros`.

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
- Hacen falta **parcelas con coordenadas** para la HU-84 (el alta de parcela
  tiene `latitud`/`longitud` opcionales pero **ambas juntas o ninguna**): si
  las parcelas actuales no tienen, añádelas editándolas desde **Parcelas**.
  Para probar el bloque de parcela, registra al menos un día de clima.
- Para la sección «Resumen de clima» hace falta una **campaña abierta**
  (`PLANIFICADA`, `EN_PRODUCCION` o `COSECHADA`): créala desde la UI
  («Nueva campaña»), **no** usar datos reales (decisión 17 de la Semana 4).
- Las consultas a la API solo aceptan **fechas pasadas** (≤ hoy en hora de
  Lima) y rangos de **92 días** como máximo; para ver el informe completo usa
  un rango corto (p. ej. una semana).
- `umbral_helada_c` se ve y se edita en **Parámetros** (solo admin, `PATCH`
  por clave); cambiarlo **no** recalcula lo ya guardado.
- Alternativa: la colección `docs/coleccion_api_semana10.json` (validada en
  F7: **270/270**) levanta, con la siembra previa de F7, todo el guion de
  datos de la semana.

## 1. Chrome — escritorio 1366×768

### Menú y listado `/clima` (HU-76)

- [ ] Con **admin**, la opción **«Clima»** aparece en el menú (con
      `clima.ver`); al entrar, la URL es `/clima` y el título es
      **«Registro de clima»** con el conteo **«N en total»**.
- [ ] Los botones **«Consultar API»** (secundario) y **«Registrar clima»**
      (primario, esquina superior derecha) solo aparecen con `clima.crear`.
- [ ] Los filtros son: **Buscar** (placeholder «Código de parcela, productor
      o comunidad»), **Parcela** («código — productor»), **Productor**,
      **Provincia**, **Distrito** (deshabilitado sin provincia), **Comunidad**
      (deshabilitada sin distrito), **Fecha desde**, **Fecha hasta**,
      **Fuente** (Todas/Manual/API) y **Heladas** (Todos/Con helada/Sin
      helada); «Buscar» aplica la búsqueda y «Limpiar» (solo visible con
      filtros) resetea todo y la paginación. Los tres desplegables de
      ubicación se cargan **en cascada** (provincia → distrito → comunidad).
- [ ] La tabla (componente `Tabla`, ancho completo, sin scroll interno) muestra
      las columnas **Fecha, Parcela, Productor, Mín / prom / máx (°C)** («5.0 /
      10.0 / 15.0», con «—» en los vacíos)**, Precipitación** («3.5 mm» o
      «—»)**, Helada** (chip **SÍ** / «No»)**, Fuente** (chip **API** /
      **MANUAL**) **y Acciones**.
- [ ] Acciones: **«Editar»** (solo con `clima.editar`) abre el formulario; en
      otro caso solo **«Ver ficha»**. La paginación (20 por página) cambia la
      URL con `?page=` y muestra el estado `refrescando`.
- [ ] Sin coincidencias: panel **«No hay registros de clima que coincidan con
      la búsqueda.»** + nota «Prueba a limpiar los filtros, registra un día a
      mano o consulta la API meteorológica.»

### Alta y edición de clima (modal `formulario`, HU-78/79)

- [ ] «Registrar clima» abre el modal **«Registrar clima»**; la URL **no
      cambia**. Tres secciones: **«Datos del registro»**, **«Temperaturas
      (°C)»** y **«Otras medidas»**.
- [ ] **Parcela** (formato «código — productor»): ayuda «Una sola fila por
      parcela y día.»; en edición aparece **deshabilitada** (no se puede
      cambiar de parcela desde la UI).
- [ ] **Fecha** con `max` = hoy (selector nativo): ayuda «No puede ser futura
      (hora de Lima).»
- [ ] **Mínima**: ayuda «Entre -30 y 45 °C. Si hay mínima, la helada la
      deriva el servidor del umbral del sistema.»; **Máxima**: «Entre -30 y
      45 °C y no menor que la mínima.»; **Promedio (opcional)**: «Déjalo
      vacío y el servidor guardará el punto medio de mínima y máxima.»
- [ ] **Otras medidas**: Precipitación (mm), Humedad (%), Viento máximo (m/s)
      y Radiación (MJ/m²), cada uno con su ayuda; **Helada**: con mínima
      escrita, la casilla queda **deshabilitada** y la ayuda dice «Con
      temperatura mínima, el servidor marca la helada según el umbral del
      sistema.»; sin mínima, «Márcala si hubo helada y no registras la
      temperatura mínima.» con la casilla **«Hubo helada este día»**.
- [ ] Errores de cliente **junto al campo** (sin toast): parcela/fecha vacías;
      fecha futura; fecha anterior a 2000; temperaturas fuera de [−30, 45];
      mínima > máxima; precipitación/viento/radiación negativos; humedad
      fuera de [0, 100]; y «Indica al menos una medida meteorológica o marca
      la helada.»
- [ ] Guardar con rueda **«Guardando…»** dentro del botón (deshabilitado);
      toast **«Registro de clima creado.»**; el listado se recarga con la fila
      nueva. Comprobar que al crear con mínima y máxima **sin promedio**, la
      fila muestra el punto medio.
- [ ] «Editar» abre **«Editar registro de clima»** con el formulario
      hidratado y «Guardar cambios» → toast **«Registro de clima guardado.»**
- [ ] Los errores del servidor (duplicado «Ya existe un registro de clima…»,
      parcela inactiva/ajena, promedio fuera de rango) salen **junto al campo**
      correspondiente; los `non_field_errors` como **toast de error**.

### Editar un registro que viene de la API (HU-80)

- [ ] Al editar un registro con chip **API**, el formulario muestra el campo
      **«Reemplazar registro de la API»** con la ayuda «Este registro proviene
      de la API meteorológica: al guardarlo quedará como MANUAL.» y la casilla
      **«Entiendo que este registro pasará a MANUAL»**.
- [ ] Guardar **sin marcar** la casilla → error junto al campo: «Este registro
      proviene de la API meteorológica: envía confirmar_reemplazo=true para
      reemplazarlo con valores manuales.»
- [ ] **Marcada** → toast «Registro de clima guardado.» y la ficha/listado
      muestran ahora el chip **MANUAL**.

### Ficha del registro (modal `ficha`, HU-77)

- [ ] «Ver ficha» abre el modal **«Clima del {fecha}»**: cabecera con el
      código de la parcela + chip **MANUAL**/**API** + chip **HELADA** si
      aplica, y botón **«Editar»** solo con `clima.editar`.
- [ ] Sección **«Días del registro»**: Fecha, Parcela, Productor y Comunidad.
- [ ] Sección **«Medidas del día»**: mínima/máxima/promedio en °C (con
      **«(punto medio calculado)»** cuando el promedio lo calculó el
      servidor), Precipitación, Humedad, Viento máximo, Radiación y **Helada**
      («Sí (derivada del umbral)» cuando hay mínima, «Sí»/«No» en el resto).
- [ ] Sección **«Trazabilidad»**: Fuente («API meteorológica» o «Manual»),
      **Registrado por** (visible con admin; **ausente** con `tecnico`),
      Creado y Última edición.
- [ ] Desde la ficha, **«Editar»** apila el modal de edición encima y al
      guardar la ficha se recarga.

### Consulta a la API meteorológica (modal `ClimaConsulta`, HU-84)

- [ ] «Consultar API» abre el modal **«Consultar API meteorológica»** con la
      sección **«Qué consultar»**: **Parcela** (ayuda «La parcela debe tener
      coordenadas registradas; solo se consultan días pasados (máx. 92).»),
      **Fecha inicial** y **Fecha final** (ambas con `max` = hoy; ayuda de la
      final: «Los registros manuales nunca se pisan; los de la API se
      refrescan.»).
- [ ] Errores de cliente junto al campo: parcela/fechas vacías, inicial >
      final, rango > 92 días («La consulta admite como máximo 92 días.») y
      fecha final futura.
- [ ] «Consultar» con rueda **«Consultando…»** dentro del botón
      (deshabilitado) y «Cerrar» activo; al terminar, toast **«Consulta a la
      API meteorológica finalizada.»** y panel **«Informe de la consulta»**
      con los 6 contadores: **Registros creados, Registros actualizados,
      Omitidos (eran manuales), Omitidos (sin dato nuevo), Días sin datos y
      Días descartados por medidas inválidas**, más la nota «Consulta del
      {desde} al {hasta} en la parcela {id} ({latitud}, {longitud}).»
- [ ] Parcela **sin coordenadas** → error 400 junto al campo «La parcela no
      tiene coordenadas registradas.»; rango > 92 → junto al campo; el
      servidor **caído/sin red** → toast de error con «El servicio
      meteorológico no está disponible en este momento.» (502) y el modal
      sigue operativo.
- [ ] Tras la consulta, el listado `/clima` se recarga con los días nuevos
      (chip **API**); un día que ya era **manual** aparece **sin cambios**
      (contador «Omitidos (eran manuales)»).

### Ficha de parcela: sección «Clima» (HU-83)

- [ ] En la ficha de parcela hay una sección **«Clima»**: con registros muestra
      **Registros** (nº) y **Último día** (fecha), más los botones de texto
      **«Ver registros»** (navega a `/clima?parcela={id}` y cierra la ficha) y
      **«Registrar clima»** (solo con `clima.crear`; abre el formulario con la
      parcela preseleccionada).
- [ ] Sin registros: «Esta parcela todavía no tiene registros de clima.» y el
      botón **«Registrar clima»**.

### Ficha de campaña: sección «Resumen de clima» (HU-82)

- [ ] La ficha de campaña tiene la sección **«Resumen de clima»**: rejilla con
      **Precipitación acumulada** («4.4 mm»), **Temperatura promedio**
      («14.2 °C»), **Humedad promedio** («53.3 %»), **Heladas**, **Cobertura**
      («2.0 %») y **Días con clima** («8 de 409»).
- [ ] Nota: **«Ventana provisional (la campaña aún no tiene fecha de
      cosecha): de {desde} hasta hoy.»** si la campaña aún no cosecha; si ya
      cosechó, «Ventana de la campaña: de {desde} a {hasta}.»
- [ ] Sin registros en la ventana: «Esta campaña todavía no tiene registros de
      clima en su ventana.»

### Parámetros: `umbral_helada_c` (HU-83)

- [ ] En **Parámetros** (solo admin) aparece la quinta fila **umbral de
      helada** con valor `0`; al editarla, un valor fuera de **−10 a 5** se
      rechaza junto al campo («El umbral de helada debe estar entre -10 y
      5 °C.»).

## 2. Edge — 1024×768 (resolución del responsable)

- [ ] Repetir al menos: `/clima` con filtros y alta, edición de un registro
      API con la casilla de reemplazo, ficha del registro, consulta HU-84 con
      informe, ficha de parcela con «Clima» y ficha de campaña con «Resumen de
      clima».
- [ ] Sin diferencias visuales ni de comportamiento respecto a Chrome; las tablas
      siguen en formato tarjeta a 1024 (umbral ≤ 860 px).

## 3. Móvil — 360×780 (Chrome devtools) y tablet 768×1024

- [ ] La tabla de `/clima` se muestra como **tarjetas** (≤860 px) con etiqueta a
      la izquierda y valor a la derecha.
- [ ] **Sin scroll horizontal de la página** en 360 ni en 768 (listados, fichas,
      modales y formularios).
- [ ] Los modales (`ClimaFormulario`, `ClimaFicha`, `ClimaConsulta`) a **ancho
      completo ≤ 860 px**, ✕ ≥ 44 px, cuerpo con scroll interno y botones
      (Registrar clima, Guardar cambios, Consultar, Cerrar/Cancelar) apilados a
      ancho completo; se puede escribir en todos los campos (fechas con el
      selector nativo, temperaturas con teclado numérico).
- [ ] **Pila de modales**: listado → ficha → edición, y ficha de parcela →
      registrar clima: Escape/✕ cierran solo el de arriba y el de abajo
      retoma el scroll.
- [ ] Botones de acción (Registrar clima, Consultar API, Editar, Ver ficha,
      Ver registros) ≥ 44 px en táctil.

## 4. Permisos por rol (probar en Chrome, cerrando sesión entre roles)

- [ ] **Admin** (`admin`): ve «Clima» en el menú y usa todas las acciones
      (alta, edición, edición de registros API con confirmación, consulta a la
      API) y «Registrar clima» desde la ficha de parcela; ve `registrado_por`
      en la ficha.
- [ ] **Coordinador** (`coordinador`): ve «Clima» (solo `clima.ver`) pero la
      pantalla **sin botones «Consultar API» ni «Registrar clima»** y las
      acciones son solo «Ver ficha»; la ficha **sin «Editar»**; en la ficha de
      parcela **sin «Registrar clima»** (por API: crear/consulta → 403).
- [ ] **Técnico** (`tecnico`): el listado solo muestra registros de **sus
      productores asignados**; puede **«Editar»** y **«Registrar clima»** y
      consultar la API de **sus parcelas**; parcela ajena → «La parcela
      indicada no existe.» (400); en la ficha **no ve «Registrado por»**.
- [ ] Con sesión caducada (borrar cookies `sigpa_access`) la pantalla vuelve al login
      tras renovar fallida.

## 5. Estados de UI (Chrome, con admin)

- [ ] **Rueda de carga** dentro del botón (`AGENTS.md`): «Guardando…» en el
      formulario de clima; **«Consultando…»** en la consulta HU-84; las
      confirmaciones que pasan por `Modal` muestran «Procesando…».
- [ ] Cargando inicial: `/clima` con `Cargando…` a pantalla completa sin parpadear
      datos viejos; los modales de ficha/edición hidratan con `Cargando…`.
- [ ] Error de red/servidor al listar registros: aviso rojo (`Aviso`) en la página y el
      resto sigue operativo; con el backend caído, los modales muestran el aviso/toast
      de error y el ✕ sigue cerrando.
- [ ] **Toasts** (`context/ToastProvider.jsx`): «Registro de clima creado.»,
      «Registro de clima guardado.», «Consulta a la API meteorológica
      finalizada.» — éxito verde **auto-cierra a los 4 s**, error rojo **se
      queda hasta la ✕**; los errores de validación **de campo** salen
      **junto al campo**, no como toast.
- [ ] Escape cierra el modal de arriba (pila de modales) y ningún
      `window.confirm`/`alert` en toda la pantalla.
- [ ] Comprobación por consola: `DELETE http://localhost:8000/api/clima/{id}/`
      → `405`; la UI nunca ofrece borrar (solo edición).

## 6. Resultados (rellenar el responsable)

| Sección | Chrome | Edge | Móvil 360 | Observaciones |
|---|---|---|---|---|
| 1. Menú y listado `/clima` | ☐ | ☐ | ☐ | |
| 2. Alta y edición de clima | ☐ | ☐ | ☐ | |
| 3. Editar registro API (confirmación) | ☐ | ☐ | ☐ | |
| 4. Ficha del registro | ☐ | ☐ | ☐ | |
| 5. Consulta API meteorológica (HU-84) | ☐ | ☐ | ☐ | |
| 6. Ficha de parcela y de campaña | ☐ | ☐ | ☐ | |
| 7. Parámetros: umbral de helada | ☐ | ☐ | ☐ | |
| 8. Permisos por rol | ☐ | ☐ | ☐ | |
| 9. Estados de UI | ☐ | ☐ | ☐ | |

Fecha: __________   Responsable: __________   Resultado global: __________
