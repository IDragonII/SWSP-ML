# Verificación UI — Semana 17 (checklist manual)

> Este checklist cumple el papel de `verificacion_ui_semana17.md` (plan
> F5/F7). El agente deja este checklist — además de `npm run lint` (0),
> `npm run build` y la suite de backend **299/299 en verde** (`manage.py
> check` 0 issues, `makemigrations --check` sin cambios) — y el
> responsable lo ejecuta en navegador y anota el resultado.
> Pantalla de la semana: **`/reportes`** (reportes descargables
> HU-141..HU-149) para los roles con `reportes.ver`.
> Ver también: `decisiones_semana17.md` y `api_reportes.md`.

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
- **Datos de prueba** (sin datos reales, decisión 59): ejecuta
  `manage.py datos_demostracion` (datos inventados de las Semanas 16 y
  17: V1 + V2 con dos períodos, revisiones y «pocos datos»). Con los
  filtros vacíos la previa del reporte productivo debe anunciar las
  advertencias de revisión/provisional/pocos datos.
- El backend necesita la BD del `docker-compose` levantada
  (`docker compose up -d db` en la raíz).
- No usar datos reales (decisión 59); `.credenciales` solo en local.

## 1. Chrome — escritorio 1366×768

### Acceso y catálogo (HU-149)

- [ ] Con `admin`, el menú lleva a **`/reportes`**: título «Reportes»,
      texto «Elige un reporte, afina los filtros, comprueba la vista
      previa y descárgalo en Excel o PDF. Los archivos no incluyen DNI
      ni teléfono.» y, mientras carga, «Cargando reportes…».
- [ ] Hay un desplegable **«Reporte»** con **«Reporte de productores»**
      y «Reporte productivo»; al cambiarlo cambia el encabezado
      (`h2` con el nombre y la descripción) y los filtros.
- [ ] Un usuario **sin** `reportes.ver` no llega a la pantalla
      (`RutaProtegida` → 403). Si el catálogo saliera vacío (rol con
      permiso a medias) se ve «No tienes reportes disponibles con tus
      permisos actuales.».
- [ ] Se muestran **los 6 filtros** del reporte de productores
      (Período, Cultivo, Provincia, Distrito, Comunidad, Estado de
      campaña y Estado del productor) y los mismos **sin
      `estado_productor`** en el productivo; «Limpiar filtros» está
      **deshabilitado** cuando no hay ninguno.

### Vista previa (HU-145)

- [ ] Bajo los filtros aparece «Filtros: ninguno · Este reporte no
      incluye DNI ni teléfono» (con filtros: «Período: 2025-2026 ·
      …»); mientras carga, «Cargando la vista previa…».
- [ ] **Productores**: 4 tarjetas — Productores, Filas, Superficie de
      parcelas (ha) y Superficie sembrada (ha) — y la tabla de detalle
      con las 13 columnas (Código … Superficie sembrada (ha)); los
      números con coma decimal y «—» en las celdas vacías.
- [ ] **Productivo**: tabla del **resumen por cultivo** (Cultivo,
      Campañas, Ha cosechadas, Producción kg/ton, Rendimiento,
      Provisionales, Excluidas por revisión, Pocos datos) + tarjetas
      Campañas / Ha cosechadas / Producción (kg) / Rendimiento (kg/ha)
      + el detalle de 13 columnas con «Revisión pendiente».
- [ ] Con los datos de `datos_demostracion` se ven las **advertencias**
      (revisiones pendientes, campañas provisionales y «Cultivos con
      menos de 3 campañas en el resumen: Cañihua…») y la fila de
      cultivo con la marca de **pocos datos**.
- [ ] La nota inferior indica «N filas · Excel admite hasta 20.000 ·
      PDF hasta 1.000»; con un filtro sin resultados sale «No hay filas
      con estos filtros.».
- [ ] Al cambiar un filtro la tabla se refresca (estado de carga
      visual) y la **URL guarda el reporte y los filtros**
      (`?reporte=productores&periodo=…`); recargar la URL restaura la
      misma vista. Los desplegables de ubicación van **en cascada**.

### Descargas (HU-143, HU-144, HU-146)

- [ ] **«Descargar Excel»**: la rueda aparece **dentro** del botón
      («Descargando…») con el botón deshabilitado; se descarga
      `reporte_<tipo>_<fecha>.xlsx`, se abre con dos hojas (Resumen y
      Detalle) y **ninguna celda sale como fórmula** (probar con un
      productor cuyo nombre lleve `=` o `+`).
- [ ] **«Descargar PDF»**: igual, archivo `reporte_<tipo>_<fecha>.pdf`
      con encabezado, resumen y tabla; el texto seleccionable y con
      caracteres (ñ, tildes) correctos.
- [ ] En la red: `POST /api/reportes/{tipo}/exportar/` → **200** con
      `Content-Disposition: attachment` y `Cache-Control: no-store`; el
      evento aparece en **`/auditoría`** con acción **EXPORTAR** y
      módulo `reportes` (usuario, IP, detalle con tipo/formato/filtros/
      filas). Un `GET` a esa misma ruta devuelve **405**.
- [ ] (Opcional, más rápido por API) La 21.ª exportación en una hora
      devuelve **429** con `retry_after` y cabecera `Retry-After`; un
      PDF con más de 1000 filas devuelve **400** con el número de
      filas (la vista previa sigue respondiendo 200).

### Alcance (HU-148)

- [ ] Con `tecnico`, la vista previa y las descargas solo incluyen
      **sus** productores asignados: compara los totales con los de
      `admin` y con `/productores` (deben diferir si hay productores
      sin asignar).

### Sin sesión

- [ ] Sin sesión, abrir `/reportes` redirige al login y
      `GET /api/reportes/` responde **401**.

## 2. Edge — 1024×768

- [ ] Repetir la pasada de Chrome: filtros en 2 columnas, tarjetas del
      resumen en 2–4 columnas, tablas legibles sin scroll horizontal y
      los dos botones de descarga visibles.

## 3. Móvil — 360×780

- [ ] Menú hamburguesa → Reportes.
- [ ] Filtros apilados (1 columna) con controles de 44 px.
- [ ] Las tablas de resumen y detalle pasan a **tarjetas** con rótulo
      por celda (estilo `data-rotulo`) sin desbordes horizontales.
- [ ] Los botones de descarga ocupan el ancho y muestran la rueda
      «Descargando…» mientras esperan.

## 4. Consola y red

- [ ] Sin errores rojos en la consola al cargar `/reportes`, al
      cambiar de reporte y al mover filtros.
- [ ] Peticiones visibles: `GET /api/reportes/`, `GET /api/dashboard/
      filtros/` (opciones), `GET /api/reportes/{tipo}/vista-previa/`
      (una por cambio) y `POST …/exportar/` solo al pulsar un botón —
      todo **200** salvo los casos previstos (401 sin sesión, 405 en
      método no permitido, 400 por límite, 429 por frecuencia).

## Anotación del responsable

| Fecha | Navegador | Resultado | Observaciones |
|---|---|---|---|
| | | | |
