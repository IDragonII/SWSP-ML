# Verificación UI — Semana 15 (checklist manual)

> Este checklist cumple el papel de `verificacion_ui_semana15.md` (plan
> F6). El agente deja este checklist — además de `npm run lint` (0),
> `npm run build` y la suite de backend **262/262 en verde** (`manage.py
> check` 0 issues, `makemigrations --check` sin cambios) — y el
> responsable lo ejecuta en navegador y anota el resultado.
> Pantallas de la semana: **`/alertas`** (HU-125, HU-127), **`/productores-riesgo`**
> (HU-126), la **insignia** del menú (HU-127), la sección **«Alertas»**
> de las fichas de campaña y productor (HU-127) y el panel **«Evaluación
> de alertas»** + parámetro de **`/parametros`** (HU-129, HU-132).
> Ver también: `decisiones_semana15.md`, `api_alertas.md`,
> `evaluacion_alertas.md`.

## Preparación

```bash
# Terminal 1 — backend (puerto 8000)
cd backend && venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload

# Terminal 2 — frontend (puerto 5173)
cd frontend && npm run dev
```

- Abrir `http://localhost:5173` en **Chrome** y en **Edge** (los mismos
  pasos en ambos).
- Usuarios (de `.credenciales`): `admin` / `SigpaGA2026!`,
  `coordinador` / `Coordinador2026!`, `tecnico` / `Tecnico2026!`.
- **Datos de prueba** (sin datos reales, decisión 27): con `admin`,
  registra una campaña con `fecha_inicio` pasada y **sin actividades**, o
  una **incidencia de severidad ALTA**, y pulsa **«Evaluar ahora»** en
  `/alertas` (o espera a que el gancho de la API cree la alerta al
  registrar la incidencia). Con eso hay pendientes para todo el
  checklist; atiende alguna para ver la pestaña «Atendidas».
- El backend necesita la BD del `docker-compose` levantada
  (`docker compose up -d db` en la raíz).
- No usar datos reales (decisión 27); `.credenciales` solo en local.

## 1. Chrome — escritorio 1366×768

### Menú e insignia (HU-127)

- [ ] Con cualquiera de los tres usuarios, el menú tiene **«Alertas»** y
      **«Productores en riesgo»** (los tres roles tienen `alertas.ver`) y
      ambas rutas abren su pantalla (no hay «Acceso denegado»).
- [ ] Con alertas pendientes, la opción **«Alertas»** del menú muestra la
      **insignia** con el número de pendientes y `aria-label` «N alertas
      pendientes»; con todas atendidas, la insignia **desaparece**.
- [ ] El contador de la insignia respeta el ámbito: con `tecnico` solo
      cuenta las de sus productores (mira `/alertas/resumen/` o compara
      con el listado).

### Pantalla `/alertas` (HU-125, HU-127)

- [ ] Cabecera: título **«Alertas»** y conteo «N en total».
- [ ] **Aviso de atraso** (bloque `Aviso` amarillo) mientras no haya
      evaluación reciente: «La evaluación automática de alertas está
      atrasada (aún no se ha ejecutado). El proceso diario debe correr al
      menos cada 36 horas.» — tras «Evaluar ahora» (o un barrido), el
      aviso **se va** (chip `AL DÍA` en `/parametros`).
- [ ] **«Evaluar ahora»** aparece **solo con `admin`** (Técnico y
      Coordinador no lo ven: sin botón, sin modal). Al pulsarlo: rueda
      «Evaluando…» + botón deshabilitado y toast «Evaluación completada:
      N creada(s), M cerrada(s).».
- [ ] **Pestañas** `Pendientes` (activa por defecto) · `Atendidas` ·
      `Todas` (`role="tab"`, `aria-selected`); cambiar de pestaña filtra
      y guarda el estado en la URL.
- [ ] **Filtros**: Buscar (placeholder «Mensaje, código o nombre del
      productor»), Tipo («Todos» + Incidencia severa / Sin actividad /
      Rendimiento bajo), Campaña («Todas» + entradas «productor -
      parcela - cultivo (periodo)»), Productor («Todos» + nombres);
      botones **«Buscar»** y **«Limpiar»** (este solo si hay filtros);
      los filtros viven en la URL y la paginación respeta la página
      (20 por página).
- [ ] **Tabla**: columnas **Creada** (fecha+hora es-PE), **Tipo** (chip),
      **Productor** (`nombre (código)`), **Campaña** (periodo),
      **Mensaje**, **Estado** (chip `PENDIENTE`/`ATENDIDA`) y
      **Acciones**.
- [ ] Acciones de fila: **«Atender»** solo en pendientes y con
      `alertas.atender`; **«Reabrir»** solo en atendidas y con el
      permiso; **«Ver ficha»** siempre.
- [ ] **Ficha** (`Ver ficha`, modal tamano `ficha`): chips de estado y
      tipo, y la rejilla **Mensaje · Productor · Campaña · Creada ·
      Atendida · Atendida por · Nota de atención**; si el cierre fue
      automático, el pie «Se cerró automáticamente: volverá a abrirse si
      la condición vuelve a cumplirse.» y **«Atendida por» = —**.
- [ ] **Atender**: el modal «Atender alerta» muestra el mensaje, la
      textarea «Nota de atención (opcional)» (ayuda «Máximo 250
      caracteres…», `maxLength` 250) y los botones **«Atender»**
      (rueda «Atendiendo…») / «Cancelar»; al guardar, toast «Alerta
      atendida.» y la fila sale de la pestaña Pendientes.
- [ ] **Reabrir**: confirmación «¿Reabrir esta alerta? Volverá a la
      pestaña de pendientes y quedará registrada en la auditoría. Solo se
      pueden reabrir las atendidas a mano.» con «Reabrir»/«Cancelar» y
      toast «Alerta reabierta.».
- [ ] **Estado vacío** de una pestaña: panel «No hay alertas en esta
      pestaña.» con la nota «Las alertas se crean solas con la
      evaluación diaria…».
- [ ] **Con `coordinador`**: todo el listado, la ficha y los filtros
      funcionan, pero **no existen** los botones «Atender», «Reabrir» ni
      «Evaluar ahora» (y la ruta `/alertas/evaluar/` responde 403 si se
      llama a mano).
- [ ] **Con `tecnico`**: solo ve alertas de sus productores; en la ficha
      de una alerta atendida, **«Atendida por»** aparece «—» (privacidad
      HU-128) mientras que con `admin` muestra el nombre o username.

### Pantalla `/productores-riesgo` (HU-126)

- [ ] Título **«Productores en riesgo»** + «N con alertas pendientes» y
      la nota «Cada productor agrupa sus alertas pendientes…».
- [ ] Tabla: **Código**, **Productor**, **Ubicación** (`distrito ·
      provincia`), **Alertas pendientes**, **Tipos** (lista), **Última
      alerta** (`mensaje (fecha)`) y **Acciones**.
- [ ] **«Ver alertas»** lleva a `/alertas?productor={id}` con el filtro
      ya puesto.
- [ ] Estado vacío: «No hay productores en riesgo: ninguna alerta está
      pendiente.».
- [ ] Con `tecnico` solo aparecen sus productores.

### Fichas de campaña y productor (HU-127)

- [ ] En la ficha de una **campaña**, la sección **«Alertas»** (con
      `alertas.ver`) muestra la tabla Creada · Tipo · Mensaje · Estado y
      el botón **«Ver todas»** → `/alertas?campania={id}`; sin alertas,
      «Esta campaña no tiene alertas registradas.».
- [ ] En la ficha de un **productor**, la misma sección con las columnas
      Creada · Tipo · **Campaña** · Mensaje · Estado y **«Ver todas»** →
      `/alertas?productor={id}`; sin alertas, «Este productor no tiene
      alertas registradas.».
- [ ] Ambas secciones muestran la nota «Solo se muestran las 20 alertas
      más recientes…; usa «Ver todas» para atenderlas.» cuando hay datos.

### Pantalla `/parametros` (HU-129, HU-132)

- [ ] El panel **«Evaluación de alertas»** muestra el chip **`AL DÍA`**
      (o `ATRASADA` si no se evalúa en 36 h), «Última evaluación: <fecha
      larga en es-PE>» (o «La evaluación automática aún no se ha
      ejecutado.») y la nota «El proceso diario debe correr al menos cada
      36 horas. Puedes lanzarla a mano desde la pantalla de Alertas
      (requiere el permiso de gestión de parámetros).».
- [ ] El parámetro **«Días sin actividad»** existe con su ayuda «Días sin
      actividad registrada antes de generar una alerta de seguimiento a
      la campaña (entero de 1 a 365).»; al editarlo:
      - [ ] validación del cliente: «Los días sin actividad deben ser un
            entero de 1 a 365.» (p. ej. `400` o `12.5`);
      - [ ] validación del servidor (400 del backend) si se salta el
            cliente;
      - [ ] al guardar con un valor nuevo, la respuesta avisa: «El nuevo
            valor se aplica en la siguiente evaluación de alertas; las ya
            generadas no cambian.» (el toast/estado lo refleja) y el
            cambio queda en la tabla.

## 2. Edge — escritorio 1024×768

- [ ] Repetir los apartados principales de §1 (`/alertas` con pestañas,
      filtros, ficha, atender/reabrir/evaluar, `/productores-riesgo`,
      fichas y `/parametros`); sin scroll horizontal y sin solapes.

## 3. Móvil — 360×780 (y 768 px de ancho)

- [ ] La tabla de `/alertas` y la de `/productores-riesgo` se convierten
      en **tarjetas** (`data-rotulo`) con las etiquetas legibles y la
      paginación pulsable (áreas ≥ 44 px).
- [ ] Las pestañas y los filtros se apilan sin desbordes; «Buscar»/
      «Limpiar» y «Evaluar ahora» quedan visibles y pulsables.
- [ ] Los modales (ficha, atender, reabrir) ocupan el ancho completo y
      los botones «Atender»/«Reabrir» no quedan cortados (rueda
      incluida).
- [ ] Las secciones «Alertas» de las fichas pasan a tarjetas y «Ver
      todas» funciona con táctil.
- [ ] La insignia del menú se ve sin desbordar la opción «Alertas».

## 4. Comprobaciones transversales

- [ ] `npm run lint` y `npm run build` en 0 problemas; backend
      **262/262** (`manage.py test`, `check`, `makemigrations --check`).
- [ ] Ninguna acción asíncrona queda sin rueda dentro de su botón
      (Evaluar ahora, Atender, Reabrir, Guardar parámetro, Buscar).
- [ ] Sin datos reales en las pruebas manuales (decisión 27);
      `.credenciales` no se pega en la colección ni en los tickets.
- [ ] La API **no permite crear ni editar alertas**: un `POST`/`PATCH`/
      `DELETE` manual a `/api/alertas/` responde **405** (solo el sistema
      las genera y solo atender/reabrir escriben).
- [ ] El cierre automático **no deja atendiente**: en la auditoría,
      atender deja `operacion: "atender"` con `registro_id`, mientras el
      evento resumen de la evaluación es único por evaluación con
      `detalle.resumen: true`.
