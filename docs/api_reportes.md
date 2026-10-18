# API de reportes — `/api/reportes/` (RF-62, HU-141..HU-149)

> Documentación de la Semana 17. Ver `decisiones_semana17.md` para las
> decisiones de diseño y `verificacion_ui_semana17.md` para el checklist
> de navegador. **Tres lecturas y una exportación** bajo **doble
> permiso**: `reportes.ver` (catálogo y vista previa) o
> `reportes.exportar` (descarga) **más** el `ver` del módulo de donde
> salen los datos (`productores.ver` para el reporte de productores y
> `produccion.ver` para el productivo). Los permisos `reportes.*` están
> sembrados desde la Semana 2 y los tres roles los tienen → **el
> catálogo ofrece siempre los 2 reportes**. Todas las cifras respetan el
> **alcance del usuario** (el Técnico solo lo suyo, con
> `filtrar_asignados`) y el **cliente no puede elegir columnas ni
> orden**: todo está fijado en el servidor (`reportes/catalogo.py`).

## 1. Endpoints

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/reportes/` | `reportes.ver` | 200 catálogo de reportes (§2) |
| GET | `/api/reportes/{tipo}/vista-previa/` | `reportes.ver` + ver del módulo | 200 previa (§3) |
| POST | `/api/reportes/{tipo}/exportar/` | `reportes.exportar` + ver del módulo | 200 archivo (§4) |
| POST/PUT/PATCH/DELETE | `/api/reportes/` o la vista previa | — | **405** `{"detail": "Método \"POST\" no permitido."}` |
| GET | `/api/reportes/{tipo}/exportar/` | — | **405** (solo POST) |

- Sin sesión → **401** `{"detail": "Las credenciales de autenticación no se proveyeron."}` (cualquier método).
- Sin el permiso de la primera capa → **403** `{"detail": "No tienes permiso para realizar esta acción."}`.
- `tipo` que no existe en el catálogo → **404** `{"detail": "No encontrado."}` (el manejador global de 404 de `usuarios/excepciones.py` pisa el mensaje de DRF).
- Con el permiso de `reportes.*` pero sin el `ver` del módulo (segunda capa) → **403** con el mismo detalle (pruebas 280, 281).
- El portón de cambio obligatorio de contraseña (S13) va por delante: una sesión con la marca recibe **403** en todas las rutas.

## 2. `GET /api/reportes/` — catálogo (HU-149)

Solo aparece cada reporte si el usuario tiene **ambos** permisos
(`reportes.ver` ya está exigido en la vista; aquí se filtra por el
`ver` del módulo):

```json
{
  "reportes": [
    {
      "tipo": "productores",
      "nombre": "Reporte de productores",
      "descripcion": "Productores con su ubicación, parcelas, superficie, cultivo y campaña.",
      "filtros": ["periodo", "cultivo", "provincia", "distrito", "comunidad", "estado", "estado_productor"],
      "formatos": ["xlsx", "pdf"],
      "limites": { "xlsx": 20000, "pdf": 1000 },
      "aviso_privacidad": "Este reporte no incluye DNI ni teléfono"
    },
    {
      "tipo": "productivo",
      "nombre": "Reporte productivo",
      "descripcion": "Producción y rendimiento por cultivo, con el detalle por campaña.",
      "filtros": ["periodo", "cultivo", "provincia", "distrito", "comunidad", "estado"],
      "formatos": ["xlsx", "pdf"],
      "limites": { "xlsx": 20000, "pdf": 1000 },
      "aviso_privacidad": "Este reporte no incluye DNI ni teléfono"
    }
  ]
}
```

`limites` y `aviso_privacidad` se leen en cada llamada (constantes del
código, no migración).

## 3. `GET /api/reportes/{tipo}/vista-previa/` — previa (HU-145)

Mismos filtros que la descarga, **en la query string**. De solo lectura
y **sin eventos de auditoría**: contar filas no es exportar (pruebas
293, 299).

```json
{
  "tipo": "productivo",
  "nombre": "Reporte productivo",
  "total_filas": 13,
  "limites": { "xlsx": 20000, "pdf": 1000 },
  "columnas": [
    { "clave": "periodo", "etiqueta": "Período" },
    { "clave": "cultivo", "etiqueta": "Cultivo" }
  ],
  "filas": [ { "periodo": "2025-2026", "cultivo": "Quinua", "…": "…" } ],
  "resumen": { "por_cultivo": [ … ], "totales": { … }, "campanias_provisionales": 1, "excluidas_revision": 2 },
  "advertencias": [
    "2 producciones esperan revisión y no cuentan en el rendimiento",
    "1 campaña sin cerrar aparece como provisional",
    "Cultivos con menos de 3 campañas en el resumen: Cañihua. Su rendimiento puede no ser representativo"
  ],
  "filtros": { "periodo": "2025-2026" },
  "filtros_texto": "Período: 2025-2026",
  "aviso_privacidad": "Este reporte no incluye DNI ni teléfono"
}
```

- `filas`: **las primeras 20**, ya formateadas a **texto** (fechas en
  largo, números con la coma decimal, «Sí/No» en los booleanos); `filas`
  vacías con `total_filas` > 0 solo si el reporte tiene más de 20.
- `resumen`: del reporte elegido (§5 y §6). `advertencias` salen solo
  en el productivo (revisiones, provisionales y «pocos datos»).
- `filtros` solo incluye los filtros con valor y `filtros_texto` es el
  texto que también llevan los archivos: `ninguno` si no hay; partes
  unidas con ` · ` (p. ej. `Período: 2025-2026 · Cultivo: Quinua`).

## 4. `POST /api/reportes/{tipo}/exportar/` — descarga (HU-143, HU-144, HU-146)

Cuerpo: `{"formato": "xlsx" | "pdf"}`. Los filtros van en la **query
string** (los mismos de la previa). Orden de la operación:

1. Validaciones: `formato`, filtros y **límite de filas** (§7).
2. Límite de frecuencia: **20 exportaciones por hora y usuario**.
3. Generación **en memoria** (sin disco).
4. Evento de auditoría **`EXPORTAR`** (módulo `reportes`) con detalle
   `{tipo, formato, filtros, filas}` — **antes** de entregar el archivo.
5. Entrega con cabeceras anti-caché.

| Condición | Respuesta |
|---|---|
| `formato` distinto de `xlsx`/`pdf` | **400** `{"formato": "Use xlsx o pdf."}` |
| Más filas que el límite | **400** `{"detail": "El reporte tiene N filas y el máximo para XLSX es 20000. Afina los filtros para reducir el número de filas."}` (con PDF: «…el máximo para PDF es 1000. Descarga en Excel (admite más filas) o afina los filtros.») — **nunca se trunca en silencio** |
| 21.ª exportación en la hora | **429** `{"detail": "Has alcanzado el límite de exportaciones por hora. Intenta de nuevo en N segundos.", "retry_after": N}` + cabecera `Retry-After` |
| La auditoría falla | **503** `{"detail": "No se pudo registrar la auditoría de la exportación; no se entregó el archivo. Vuelve a intentarlo."}` — **sin rastro no hay descarga** |
| OK | **200** con el archivo |

Cabeceras de la descarga:

```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet  (o application/pdf)
Content-Disposition: attachment; filename="reporte_productivo_20260120-0915.xlsx"
Cache-Control: no-store
X-Content-Type-Options: nosniff
```

- El nombre lleva la fecha de **America/Lima** en `AAAAMMDD-HHMM`.
- La vista previa **no** consume el límite de 20 por hora ni registra
  eventos (pruebas 293, 294, 299).
- Un `GET` a la ruta de exportación → **405**; sin sesión → **401**.

## 5. Filtros (HU-147) y sus errores 400

Los mismos del panel con la misma lectura y mensajes, combinables, en
la query string:

| Filtro | Válido | Error 400 |
|---|---|---|
| `periodo` | texto (p. ej. `2025-2026`) | — (valor libre; vacío = sin filtro) |
| `cultivo`, `provincia`, `distrito`, `comunidad` | id numérico | `{"<campo>": "Debe ser un id numérico."}` |
| `estado` | `PLANIFICADA`, `EN_PRODUCCION`, `COSECHADA`, `CERRADA`, `CANCELADA` | `{"estado": "Use PLANIFICADA, EN_PRODUCCION, COSECHADA, CERRADA o CANCELADA."}` |
| `estado_productor` | `ACTIVO`, `INACTIVO`, `TODOS` (solo el reporte de productores) | `{"estado_productor": "Use ACTIVO, INACTIVO o TODOS."}` |

- **Sin `estado_productor` el servidor usa `ACTIVO`** («solo activos»);
  `TODOS` incluye activos e inactivos. El texto del filtro solo aparece
  en `filtros`/`filtros_texto` si venía en la query.
- Un id inexistente **no es error**: devuelve 200 con 0 filas (los
  catálogos de los filtros vienen de `/api/dashboard/filtros/`).
- Las etiquetas del texto: `Período`, `Cultivo`, `Provincia`,
  `Distrito`, `Comunidad`, `Estado de campaña` (nombre completo del
  estado) y `Estado del productor` (`solo activos` / `solo inactivos` /
  `todos`).

## 6. Columnas y resúmenes

### 6.1 Reporte de productores (HU-141) — 13 columnas

`Código · Productor · Estado · Provincia · Distrito · Comunidad ·
Parcelas activas · Superficie de parcelas (ha) · Campaña · Cultivo ·
Variedad · Estado de la campaña · Superficie sembrada (ha)`

- Una fila por **productor y campaña** (campañas canceladas excluidas);
  un productor sin campañas aparece con la campaña vacía («—»), salvo
  que se pida un filtro de campaña, en cuyo caso no aparece.
- La ubicación es la **del productor** (a diferencia del panel, que usa
  la de la parcela); `Superficie de parcelas` suma las parcelas
  **activas** del productor (contadas una sola vez en el resumen).
- Orden fijado por el servidor: **período descendente** y, sobre eso,
  apellidos.

Resumen: `{productores, filas, superficie_parcelas_ha, superficie_sembrada_ha}`
(con decimales como texto).

### 6.2 Reporte productivo (HU-142) — 13 columnas

`Período · Cultivo · Variedad · Código del productor · Nombre del
productor · Cód de parcela · Distrito · Fecha de cosecha · Superficie
cosechada (ha) · Producción (kg) · Rendimiento (kg/ha) · Estado de la
campaña · Revisión pendiente`

- Detalle: producciones de campañas **COSECHADA/CERRADA** más las que
  están **en revisión** (se muestran marcadas aunque su campaña esté en
  otro estado); con `?estado=` se limita a ese estado.
- Resumen: `{por_cultivo, totales, campanias_provisionales,
  excluidas_revision}` — **exactamente el mismo cálculo que el panel**
  (`dashboard.consultas`): rendimiento **ponderado**, exclusiones de
  `requiere_revision`, señales `provisional` y `pocos_datos` (< 3
  campañas). Con los mismos filtros, el reporte y `/api/dashboard/
  produccion/` dan las mismas cifras (prueba 287).
- `por_cultivo` añade `toneladas`, `provisionales` y
  `excluidas_revision`; los archivos suman una fila **Totales**.

## 7. Límites, frecuencia y alcance (HU-146, HU-148)

| Regla | Valor | Comportamiento |
|---|---|---|
| Filas máximas en **Excel** | **20 000** | Se supera → 400 con el número y la sugerencia; **nunca** truncado |
| Filas máximas en **PDF** | **1 000** | Ídem, sugiriendo Excel |
| Frecuencia | **20 exportaciones/hora y usuario** | 429 con `retry_after` + `Retry-After`; la vista previa no cuenta |
| Alcance | `filtrar_asignados` | El Técnico solo exporta de **sus** productores (pruebas 282, 299); el catálogo y la previa usan el mismo alcance |

## 8. Privacidad (pregunta V)

Los dos reportes **no llevan DNI, teléfono ni `registrado_por`**: ni en
las columnas, ni en el resumen, ni en los textos de filtro, ni en el
evento de auditoría. El catálogo y la vista previa acompañan siempre el
aviso `Este reporte no incluye DNI ni teléfono`. Es la pregunta **V**
(`decisiones_semana17.md` §1.4), pendiente de confirmación: si el
responsable pide añadir el DNI, se toca `reportes/catalogo.py` (columnas
fijas) sin mover la base.

## 9. Colección y pruebas

`docs/coleccion_api_semana17.json` — **F7 cerrada: 540/540 en verde
(538 obligatorias + 2 opcionales), 1005/1005 aserciones**. Validada con
el pipeline habitual (BD temporal `sigpa_ga_coleccion17` con siembra
previa, servidor 8001 con `LOGIN_RATE_IP=120/min`, borrada al terminar).
Pruebas **280–299** en `backend/reportes/tests.py`; `manage.py test` →
**299/299 OK**.
