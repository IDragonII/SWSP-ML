# Verificación UI — Entrega 1 (única pasada total de la etapa)

> **Esta es la única pasada completa de la Semana 19** (plan F1): el
> recorrido manual de **todos los menús** en **Chrome, Edge y 360 px**.
> Se ejecuta una vez, con los tres roles, sobre los datos inventados de
> demostración (V1 + V2 + V3 de `manage.py datos_demostracion`). El
> detalle fino de los reportes y de `/auditoría` sigue disponible en
> `verificacion_ui_semana18.md`; aquí lo que no se pierde es el
> recorrido por menú. El backend deja además: suite **325/325**,
> `check` 0, `makemigrations --check` sin cambios, `npm run lint` 0 y
> `npm run build` 0.

## Preparación

```bash
# Terminal 1 — backend (puerto 8000)
cd backend && venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload

# Terminal 2 — frontend (puerto 5173)
cd frontend && npm run dev

# Datos inventados (marcados como tales); si ya existen no hace nada
cd backend && venv\Scripts\python.exe manage.py datos_demostracion
```

- Abrir `http://localhost:5173` en **Chrome** y en **Edge**.
- Usuarios (de `.credenciales`, solo local): `admin` / `SigpaGA2026!`,
  `coordinador` / `Coordinador2026!`, `tecnico` / `Tecnico2026!`.
- La BD del `docker-compose` levantada (`docker compose up -d db`).
- **Sin datos reales**: todo lo que se ve es inventado y está marcado
  como «Datos de demostración inventados».

## Visibilidad esperada por rol (menú)

| Pantalla (ruta) | admin | coordinador | tecnico |
|---|---|---|---|
| Inicio `/` (dashboard) | ✓ | ✓ | ✓ |
| Productores, Parcelas | ✓ | ✓ | ✓ |
| Catálogos (`catalogos.editar`) | ✓ | — | — |
| Parámetros (`parametros.gestionar`) | ✓ | — | — |
| Campañas, Actividades, Producción | ✓ | ✓ | ✓ |
| Recursos, Clima, Incidencias | ✓ | ✓ | ✓ |
| Alertas, Productores en riesgo | ✓ | ✓ | ✓ |
| Predicción (`ml.ver_predicciones`) | ✓ | ✓ | ✓ |
| Reportes (`reportes.ver`) | ✓ (4 tipos) | ✓ (3 tipos) | ✓ (3 tipos) |
| Usuarios (`usuarios.ver`) | ✓ | — | — |
| Roles y permisos (`roles.gestionar`) | ✓ | — | — |
| Auditoría (`auditoria.ver`) | ✓ | — | — |
| `/cambiar-clave` | en los 3 roles al entrar con clave temporal | | |

## 1. Chrome — escritorio 1366×768

### Sesión y accesos

- [ ] Con cada uno de los **3 usuarios**: el login muestra la rueda
      «Entrando…» dentro del botón, entra al dashboard y el menú lateral
      solo ofrece las pantallas de la tabla anterior (las demás ni
      aparecen; abrirlas a mano da `/acceso-denegado`).
- [ ] Sin sesión, cualquier pantalla redirige a `/login` y la API
      responde **401**.
- [ ] Con `admin`, entrar con la clave temporal obliga a
      `/cambiar-clave` (el menú no se ve mientras dure la marca) y
      después vuelve a entrar con la clave nueva.

### Inicio (dashboard)

- [ ] Carga con las tarjetas de resumen y las gráficas, con la rueda de
      carga mientras llegan los datos; filtros superiores funcionando.
- [ ] Con `tecnico` los totales solo suman sus productores asignados
      (alcance propio), con `coordinador` y `admin` ven todo.

### Productores y Parcelas (CRUD completo, decisión 19)

- [ ] Listado con filtros, buscador y paginación; las fichas se abren
      en **modal** (no hay páginas de detalle aparte).
- [ ] **Alta** desde el botón: modal con rueda «Guardando…», validaciones
      visibles (DNI de 8 dígitos, superficie > 0, coordenadas las dos o
      ninguna) y el registro nuevo en la lista.
- [ ] **Edición** en modal (misma validación) y alta/edición de parcelas
      dentro de la ficha del productor; cambiar estado (activo/inactivo)
      pide confirmación con rueda.
- [ ] En Parcelas: el código de parcela aparece rellenado (lo genera el
      trigger), la superficie valida contra la campaña y los filtros por
      comunidad/distrito/provincia responden.

### Catálogos y Parámetros (solo admin)

- [ ] Catálogos: crear/editar tipos de actividad, recursos, unidades,
      etapas por cultivo y cultivos/variedades; activar/desactivar con
      confirmación; una **unidad nueva** aparece sola en los
      desplegables correspondientes.
- [ ] Parámetros: umbrales de rendimiento y helada editables con
      validación y guardado con rueda.

### Campañas (ciclo completo)

- [ ] Listado con estados por color; alta en modal (parcela, cultivo,
      variedad del cultivo, período y fechas) → nace **Planificada**.
- [ ] Ficha de campaña: pestañas de detalle (etapas con línea de
      tiempo, actividades, recursos, clima, incidencias, producción) y
      acciones de estado: **Iniciar** (planificada → producción) y
      **Cancelar** (con motivo obligatorio).
- [ ] Con `admin` se ve **Cerrar** (exige producción revisada: sin ella
      el aviso explica el motivo) y el paso de revisión de producción
      con nota + «incluir en entrenamiento».
- [ ] Con `tecnico`: solo sus campañas asignadas (el listado no muestra
      las ajenas) y **no** aparece Cerrar; con `coordinador` todo es de
      solo lectura (los botones de alta/edición no están: sin botón,
      sin modal).

### Actividades, Recursos, Clima, Incidencias, Producción

- [ ] Alta de actividad en modal: tipo (desplegable), fecha dentro del
      período, método/horas y densidad solo en siembras; **anular**
      exige motivo; el registro nuevo se refleja en la ficha de campaña.
- [ ] Uso de recurso: recurso + unidad compatibles (la unidad inválida
      se rechaza con mensaje); clima: se calcula la temperatura
      promedio y «helada» valida la mínima; incidencia: superficie
      afectada ≤ superficie sembrada.
- [ ] Producción: el alta muestra `produccion_kg` y
      `rendimiento_kg_ha` calculados por el servidor (no se escriben);
      un rendimiento atípico sale con la marca de revisión y solo
      `admin` la levanta.

### Alertas y Productores en riesgo

- [ ] Insignia del menú con el contador de pendientes; atender (con
      nota) y reabrir pasan por modal con rueda; la pantalla de
      evaluación muestra la hora de Lima de la última corrida.

### Reportes

- [ ] Con `admin`, 4 tipos en el desplegable; con `coordinador` y
      `tecnico`, 3 (sin auditoría); Chip «Datos sensibles» junto al
      reporte de auditoría; filtros en URL; previa con tarjetas y
      tablas; descarga con rueda (modal de confirmación en auditoría).
      El detalle fino: `verificacion_ui_semana18.md`.

### Usuarios, Roles y Auditoría (solo admin)

- [ ] Usuarios: alta en modal, desactivar/reactivar, restablecer clave,
      desbloquear y «cambiar clave obligatoria» con confirmaciones y
      ruedas.
- [ ] Roles: los 3 roles del sistema con su matriz de permisos
      (55/32/14) editable; guardar reemplaza el conjunto con rueda.
- [ ] Auditoría: listado paginado con filtros, detalle con claves
      seguras y «Campos: …», exportación Excel/PDF con el modal de
      confidencialidad (los dos botones). El detalle fino:
      `verificacion_ui_semana18.md`.

### Datos inventados

- [ ] Los datos de demostración se ven **marcados como inventados** en
      los listados/detalles donde aplica (V1+V2+V3, incluidas las 6
      actividades de ago–oct 2026 y los eventos de bitácora V3).

## 2. Edge — 1024×768

- [ ] Misma pasada completa de Chrome: filtros en 2 columnas, tarjetas
      en 2–4 columnas, tablas legibles sin scroll horizontal, modales
      centrados y botones con rueda visibles.

## 3. Móvil — 360×780

- [ ] Menú hamburguesa despliega **todas** las opciones visibles del
      rol; `/cambiar-clave` y `/acceso-denegado` se leen completos.
- [ ] En las pantallas de listado, las tablas pasan a **tarjetas** con
      rótulo por celda (`data-rotulo`) sin desbordes; los modales de
      alta/edición caben con sus botones (Guardar con rueda incluida).
- [ ] Reportes y Auditoría: filtros apilados (1 columna), Chip «Datos
      sensibles» sin desborde, botones de descarga a ancho completo.

## 4. Consola y red

- [ ] Sin errores rojos en la consola en toda la pasada de Chrome; en
      Edge solo se revisan las pantallas nuevas de la semana si Chrome
      ya salió limpio (orden de recorte del brief).
- [ ] Las peticiones de listado salen con **número fijo de consultas**
      (medido en la prueba 324) y responden **200** salvo los casos
      previstos (401 sin sesión, 403 sin permiso, 400 con mensajes de
      validación, 405 en método no permitido, 429 por frecuencia de
      exportación).

## Anotación del responsable

| Fecha | Navegador | Resultado | Observaciones |
|---|---|---|---|
| | Chrome | | |
| | Edge | | |
| | Móvil 360 px | | |
