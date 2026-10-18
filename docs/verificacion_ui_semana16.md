# Verificación UI — Semana 16 (checklist manual)

> Este checklist cumple el papel de `verificacion_ui_semana16.md` (plan
> F5/F7). El agente deja este checklist — además de `npm run lint` (0),
> `npm run build` y la suite de backend **279/279 en verde** (`manage.py
> check` 0 issues, `makemigrations --check` sin cambios) — y el
> responsable lo ejecuta en navegador y anota el resultado.
> Pantalla de la semana: **`/` (Inicio)** con el **panel de
> indicadores** (HU-133..HU-140) para los roles con `dashboard.ver`.
> Ver también: `decisiones_semana16.md` y `api_dashboard.md`.

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
- **Datos de prueba** (sin datos reales, decisión 44): con `admin`,
  registra una campaña con producción y otra planificada sin
  actividades, o ejecuta `manage.py datos_demostracion` (datos
  inventados, F7). El panel se pinta con lo que haya: vacío también es
  una comprobación («—» donde no hay cifras).
- El backend necesita la BD del `docker-compose` levantada
  (`docker compose up -d db` en la raíz).
- No usar datos reales (decisión 44); `.credenciales` solo en local.

## 1. Chrome — escritorio 1366×768

### Inicio sin panel (roles sin `dashboard.ver`)

- [ ] Con un usuario sin `dashboard.ver` (p. ej. crear uno con un rol
      personal sin ese permiso), `/` muestra **solo** el saludo y «Tus
      módulos»: **no aparece** ningún bloque del panel y la consola
      **no** muestra errores 403.

### Tarjetas y franja (HU-133, HU-134, HU-138, HU-140)

- [ ] Con `admin`, `/` muestra el **panel de indicadores**: 8 tarjetas
      (productores activos/inactivos/con campaña activa, superficie
      sembrada, aptas para entrenar, revisiones pendientes, alertas
      pendientes y totales) y la nota «actualizado el …» con fecha y
      hora de Lima.
- [ ] Los valores sin datos salen como **«—»** (no como 0); los
      decimales tienen 2 cifras (p. ej. superficie «10.50 ha»).
- [ ] Franja **«Alertas pendientes por tipo»**: pendientes + los 3
      tipos (incidencia severa / sin actividad / rendimiento bajo) y
      enlace **«Ver el listado de alertas»** → `/alertas`.

### Campañas por estado (HU-135)

- [ ] Gráfico de barras con **los 5 estados** (Planificadas, En
      producción, Cosechadas, Cerradas, Canceladas); al pasar el cursor
      se ve el conteo; el gráfico tiene etiqueta accesible (`role="img"`
      con resumen narrado).
- [ ] Con el filtro **Período** en un período existente, la serie se
      recalcula; con un período sin campañas, sale el mensaje «No hay
      campañas en tu alcance…» (no un gráfico en cero).

### Producción agrupada (HU-136, HU-139)

- [ ] Pestañas **«Por cultivo»** / **«Por distrito»**: cambian el
      gráfico y la primera columna de la tabla; la URL guarda la
      agrupación (`?agrupar=distrito`).
- [ ] La tabla usa el componente `Tabla`: columnas Cultivo/Distrito,
      Campañas, Superficie cosechada (ha), Producción (kg), Rendimiento
      ponderado (kg/ha), Promedio simple (kg/ha) y Señales; los chips
      **PROVISIONAL** y **POCOS DATOS** aparecen según corresponda.
- [ ] Filtros de arriba (Período, Cultivo, Provincia, Distrito,
      Comunidad) recalculan la tabla y el gráfico; **«Limpiar filtros»**
      los borra todos (y se deshabilita cuando no hay ninguno).
- [ ] Al cambiar **Provincia**, distrito y comunidad se limpian solos
      (cascada); al cambiar **Distrito**, se limpia comunidad. Las
      opciones vienen de `/api/dashboard/filtros/`.
- [ ] Al final, el resumen «Total: N campañas · X ha · Y kg · Z kg/ha
      (ponderado)»; sin filas, «No hay producciones registradas con
      estos filtros.».

### Alcance del Técnico (HU-133..HU-137)

- [ ] Con `tecnico`, el panel solo cuenta **sus** productores: compara
      las tarjetas con las de `admin` (deben diferir si hay productores
      sin asignar) y con el contenido de `/productores`.
- [ ] Los filtros de ubicación del Técnico solo ofrecen **sus**
      provincias/distritos/comunidades (HU-137).

### Sin sesión / sin permiso

- [ ] Sin sesión, `/api/dashboard/resumen/` → 401; en el navegador,
      abrir `/` sin sesión redirige al login.
- [ ] Un rol con `dashboard.ver` pero sin `alertas.ver` ve el panel
      **sin** la franja de alertas (y sin 403 en consola).

## 2. Edge — 1024×768

- [ ] Repetir la pasada de Chrome: tarjetas en 2–3 columnas, filtros
      en 2 columnas, gráficos con ancho completo y tabla legible sin
      scroll horizontal.
- [ ] La ruta `/` sigue mostrando «Tus módulos» debajo del panel.

## 3. Móvil — 360×780

- [ ] Menú hamburguesa → Inicio.
- [ ] Tarjetas apiladas (1 columna) y filtros en 1 columna con
      controles de 44 px.
- [ ] La tabla de producción pasa a **tarjetas** con rótulo por celda
      (estilo `data-rotulo`) y los gráficos bajan a ~200 px de alto.
- [ ] Sin desbordes horizontales en ningún bloque.

## 4. Consola y red

- [ ] Sin errores rojos en la consola al cargar `/` y al cambiar
      filtros/agrupación.
- [ ] Las peticiones del panel se ven en la red: `/api/dashboard/
      resumen/`, `/api/alertas/resumen/` (franja),
      `/api/dashboard/campanias-estado/`, `/api/dashboard/filtros/` y
      `/api/dashboard/produccion/` — todas **GET** y **200**; un POST a
      cualquiera devuelve **405** (o 401 sin sesión).

## Anotación del responsable

| Fecha | Navegador | Resultado | Observaciones |
|---|---|---|---|
| | | | |
