# Verificación UI — Semana 18 (checklist manual)

> Este checklist cumple el papel de `verificacion_ui_semana18.md` (plan
> F5/F7). El agente deja este checklist — además de `npm run lint` (0),
> `npm run build` y la suite de backend **317/317 en verde** (`manage.py
> check` 0 issues, `makemigrations --check` sin cambios) — y el
> responsable lo ejecuta en navegador y anota el resultado.
> Pantallas de la semana: **`/reportes`** con los tipos nuevos
> (**Reporte de actividades**, RF-68, y **Reporte de auditoría**,
> HU-155/HU-156, con su Chip «Datos sensibles») y **`/auditoría`** con
> sus dos botones de exportación.
> Ver también: `decisiones_semana18.md` y `api_reportes.md`.

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
- **Datos de prueba** (sin datos reales, decisión 68): ejecuta
  `manage.py datos_demostracion` (bloques V1 + V2 + **V3**: 6
  actividades inventadas de ago–oct 2026 con la marca «Datos de
  demostración inventados (Semana 18)» y **8 eventos de bitácora** —
  incluido un LOGIN **sin usuario** con IP `190.42.55.99`). Si ya
  existen informa «Los datos de demostración ya existen; nada que
  crear».
- El backend necesita la BD del `docker-compose` levantada
  (`docker compose up -d db` en la raíz).
- No usar datos reales (decisión 68); `.credenciales` solo en local.

## 1. Chrome — escritorio 1366×768

### Catálogo y tipos nuevos (HU-149, HU-150)

- [ ] Con `admin`, el desplegable **«Reporte»** de `/reportes` ofrece
      **4 opciones**: Reporte de productores, Reporte productivo,
      **Reporte de actividades** y **Reporte de auditoría**; al
      cambiarlo cambian `h2`, descripción y filtros.
- [ ] **Reporte de actividades**: descripción «Actividades registradas
      por fecha, con su campaña, cultivo, tipo y responsable.» y **10
      filtros** — los 6 comunes más **Tipo de actividad** (desplegable),
      **Actividad desde**, **Actividad hasta** y **Estado de la
      actividad** (ACTIVAS/ANULADAS/TODAS, por defecto «solo
      activas»).
- [ ] **Reporte de auditoría**: junto al título aparece el
      **`<Chip>Datos sensibles</Chip>`**; **8 filtros**: Fecha desde,
      Fecha hasta (fecha), Usuario, Acción (desplegable), Módulo
      (desplegable), Tabla, Registro e IP.
- [ ] Con `coordinador` el desplegable tiene **3 opciones** (sin
      «Reporte de auditoría»); con `tecnico` también **3** (sin
      auditoría). Un usuario sin `reportes.ver` no llega a la pantalla.

### Vista previa de actividades (RF-68, HU-150..HU-154)

- [ ] Tarjetas del resumen: **Actividades**, **Campañas distintas**,
      **Productores distintos** y **Horas totales** (coma decimal), más
      la tabla «Por tipo» (Tipo de actividad | Actividades) cuando hay
      filas.
- [ ] Tabla de detalle con las **13 columnas**: Fecha, Productor,
      Parcela, Distrito, Campaña, Cultivo, Estado de la campaña, Tipo
      de actividad, Método, Densidad de siembra, Horas, Estado de la
      actividad y Responsable; «—» en celdas vacías.
- [ ] Con los datos V3, filtrando **Actividad desde 2026-08-01** y
      **hasta 2026-10-31** se ven las **6 actividades inventadas**: una
      con Estado «Anulada», una sin Horas («—») y una sin Responsable
      («—»).
- [ ] Invariante: con «**todas**» el total es la suma de «solo
      activas» + «solo anuladas» (recarga con cada cambio); una
      campaña **cancelada** aparece con su estado «Cancelada» en la
      fila (no se filtra).
- [ ] 400 en la previa (aviso en pantalla): `tipo_actividad=99999` →
      «El tipo de actividad indicado no existe.»; `estado_actividad=BOGUS`
      → «Use ACTIVAS, ANULADAS o TODAS.»;
      `fecha_actividad_desde=31/12/2026` → «La fecha no es válida: usa
      el formato AAAA-MM-DD.».
- [ ] Con `tecnico`: la previa sale con **12 columnas** (sin
      «Responsable») y con **totales ≤ a los de `admin`** (alcance
      propio).

### Vista previa de auditoría (HU-155/HU-156)

- [ ] Con **Fecha desde y Fecha hasta vacías**: aparece el aviso
      **«El rango de fechas es obligatorio.»** (no se pinta ninguna
      tabla).
- [ ] Invertido (`desde` posterior a `hasta`) → «La fecha inicial no
      puede ser posterior a la final.»; `hasta` = 2099-12-31 → «La
      fecha final no puede ser futura.»; `desde` = 2020-01-01 → «El
      rango admite como máximo 366 días.».
- [ ] Con un rango válido (p. ej. hoy y hoy − 30 días): tarjetas
      **Eventos**, **Sin usuario** y **Rango de fechas**; tablas
      **Acción | Eventos** y **Módulo | Eventos**; detalle de **8
      columnas** — Fecha y hora (hora de **Lima**), Usuario, Acción,
      Módulo, Tabla, Registro, IP y Detalle — con el evento más
      reciente **arriba**, las acciones con etiqueta («Iniciar
      sesión»…) y el evento sin usuario como **«(sin usuario)»**.
- [ ] En **Detalle** se ven las claves seguras con su valor y los
      textos libres reducidos a **«Campos: …»** (el resumen libre del
      evento nunca aparece).
- [ ] Filtros: con **IP `190.42.55.99`** sale 1 fila (el LOGIN sin
      usuario de V3); `registro=abc` → «Debe ser un id numérico.».
- [ ] Tras exportar, la fila 0 de la previa es el evento **EXPORTAR**
      más reciente con detalle `tipo=auditoria`.

### Exportación desde `/auditoría` (dos botones)

- [ ] Con `admin` se ven **«Exportar Excel»** y **«Exportar PDF»**.
      Con **Desde/Hasta vacíos**, al pulsarlos aparece el aviso
      **«Selecciona un rango de fechas (máximo 366 días) para
      exportar.»** y **no** se abre el modal.
- [ ] Con rango, se abre el **Modal «Exportar estos resultados»** con
      el texto de confidencialidad («Contiene información sensible de
      auditoría: solo para uso interno y de verificación. No es
      evidencia oficial. ¿Exportar de todos modos?») y la opción
      **«Exportar»**; mientras espera, la rueda **«Exportando…»** está
      **dentro** del botón con el botón deshabilitado.
- [ ] El archivo se descarga (`reporte_auditoria_<fecha>…`): el Excel
      tiene la hoja **Resumen con el aviso de confidencialidad** y la
      de Detalle con la hora de Lima; el PDF lleva el aviso en el
      **relato y el pie**.
- [ ] En la bitácora aparece el evento **EXPORTAR** (módulo
      `reportes`) con detalle tipo/formato/filtros/filas.
- [ ] `/auditoría` es de **Administrador**: con `coordinador` o
      `tecnico` no está en el menú y la ruta responde 403.

### Descarga desde `/reportes` de los tipos nuevos

- [ ] **Reporte de actividades**: «Descargar Excel»/«Descargar PDF»
      bajan directo (no es sensible) con la rueda dentro del botón; el
      Excel abre con hoja Resumen (total, por tipo, horas) y Detalle de
      13 columnas.
- [ ] **Reporte de auditoría**: al pulsar se abre el **Modal
      «Descargar reporte de auditoría»** con su aviso y «¿Descargar de
      todos modos?» (confirmación **«Descargar»** con rueda
      «Descargando…»); el archivo lleva las 8 columnas y el aviso de
      confidencialidad.
- [ ] Los filtros viajan en la **URL** (`?reporte=actividades&…`,
      `?reporte=auditoria&fecha_desde=…&fecha_hasta=…`) y al
      recargar se restauran; «Filtros: … · Este reporte no incluye DNI
      ni teléfono» refleja los valores.

### Sin sesión

- [ ] Sin sesión, abrir `/reportes` o `/auditoría` redirige al login y
      `GET /api/reportes/` responde **401**.

## 2. Edge — 1024×768

- [ ] Repetir la pasada de Chrome: filtros en 2 columnas, tarjetas del
      resumen en 2–4 columnas, tablas legibles sin scroll horizontal y
      los botones de exportación visibles.

## 3. Móvil — 360×780

- [ ] Menú hamburguesa → Reportes y → Auditoría.
- [ ] Filtros apilados (1 columna) con controles de 44 px; el Chip
      «Datos sensibles» no desborda.
- [ ] Las tablas de resumen y detalle pasan a **tarjetas** con rótulo
      por celda (estilo `data-rotulo`) sin desbordes horizontales.
- [ ] Los botones de descarga/exportación ocupan el ancho y muestran
      la rueda mientras esperan.

## 4. Consola y red

- [ ] Sin errores rojos en la consola al cargar `/reportes`, al
      cambiar de reporte, al mover filtros y al usar los botones de
      `/auditoría`.
- [ ] Peticiones visibles: `GET /api/reportes/`, `GET
      /api/reportes/{tipo}/vista-previa/` (una por cambio) y `POST
      …/exportar/` solo al confirmar — todo **200** salvo los casos
      previstos (401 sin sesión, 400 con los mensajes de rango/filtros,
      403 sin la segunda capa, 405 en método no permitido, 429 por
      frecuencia).

## Anotación del responsable

| Fecha | Navegador | Resultado | Observaciones |
|---|---|---|---|
| | | | |
