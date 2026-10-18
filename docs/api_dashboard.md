# API del panel — `/api/dashboard/` (RF-62, HU-133..HU-140)

> Documentación de la Semana 16. Ver `decisiones_semana16.md` para las
> decisiones de diseño y `verificacion_ui_semana16.md` para el checklist
> de navegador. **La API es de solo lectura**: las cuatro lecturas están
> bajo el permiso `dashboard.ver` (sembrado en la Semana 2) y no hay
> escritura —POST/PUT/PATCH/DELETE responden 405—. Todas las cifras
> respetan el **alcance del usuario**: para el Técnico solo cuenta sus
> productores asignados (mismo `filtrar_asignados` que desde la Semana 4).

## 1. Endpoints

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/dashboard/resumen/` | `dashboard.ver` | 200 tarjetas del panel (§2) |
| GET | `/api/dashboard/campanias-estado/` | `dashboard.ver` | 200 campañas por estado (§3) |
| GET | `/api/dashboard/produccion/` | `dashboard.ver` | 200 producción agrupada (§4) |
| GET | `/api/dashboard/filtros/` | `dashboard.ver` | 200 opciones de los filtros (§5) |
| POST/PUT/PATCH/DELETE | cualquiera de las anteriores | — | **405** `{"detail": "Método \"POST\" no permitido."}` |
| GET | `/api/alertas/resumen/` (franja) | `alertas.ver` | 200 `{"pendientes": n, "por_tipo": {…}}` (§6) |

- Sin sesión → **401** `{"detail": "Las credenciales de autenticación no se proveyeron."}`.
- Con sesión pero sin `dashboard.ver` → **403**
  `{"detail": "No tienes permiso para realizar esta acción."}`.
- Sin sesión, cualquier método (incluido POST) → **401** (DRF comprueba
  la autenticación antes que el método; con sesión, POST → 405).
- El portón de cambio obligatorio de contraseña (S13) va por delante:
  una sesión con la marca recibe **403** en todas las rutas.

## 2. `GET /api/dashboard/resumen/` — tarjetas (HU-133, HU-134, HU-140)

```json
{
  "generado_en": "2026-01-20T09:15:32-05:00",
  "productores": { "activos": 2, "inactivos": 1, "con_campania_activa": 1 },
  "superficie_sembrada_ha": "10.50",
  "campanias_por_estado": {
    "PLANIFICADA": 1, "EN_PRODUCCION": 0, "COSECHADA": 5,
    "CERRADA": 2, "CANCELADA": 1
  },
  "aptas_entrenar": 1,
  "revisiones_pendientes": 1,
  "alertas": { "total": 4, "pendientes": 3 }
}
```

| Campo | Notas |
|---|---|
| `generado_en` | Hora de **America/Lima** con huso, segundos exactos |
| `productores.*` | Del alcance; `con_campania_activa` = con al menos una campaña en estado activo (PLANIFICADA/EN_PRODUCCION/COSECHADA) |
| `superficie_sembrada_ha` | `Sum(superficie_sembrada_ha)` de las campañas **activas** del alcance; texto con 2 decimales, `null` si no hay |
| `campanias_por_estado` | Los **5 estados siempre** (con ceros) |
| `aptas_entrenar` | Campañas CERRADA con `produccion.incluir_en_entrenamiento = true` — el mismo WHERE de `vw_dataset_entrenamiento` |
| `revisiones_pendientes` | Producciones del alcance con `requiere_revision = true` |
| `alertas.*` | Total y pendientes del alcance (la insignia) |

## 3. `GET /api/dashboard/campanias-estado/` — serie (HU-135)

`?periodo=` (texto, opcional): filtra por ese período; un período sin
campañas devuelve la serie **a cero** (mismo criterio que los listados).

```json
{ "periodo": "2025-2026", "estados": { "PLANIFICADA": 1, "EN_PRODUCCION": 0, "COSECHADA": 5, "CERRADA": 2, "CANCELADA": 1 } }
```

## 4. `GET /api/dashboard/produccion/` — agrupado (HU-136, HU-139)

| Parámetro | Tipo | Notas |
|---|---|---|
| `?agrupar=` | `cultivo` (defecto) · `distrito` | Otro valor → **400** «Use cultivo o distrito.» |
| `?periodo=` | texto | `campania.periodo` |
| `?cultivo=` | id numérico | No numérico → **400** «Debe ser un id numérico.» |
| `?provincia=` | id numérico | Ídem |
| `?distrito=` | id numérico | Ídem |
| `?comunidad=` | id numérico | Ídem |

```json
{
  "agrupar": "cultivo",
  "filtros": { "periodo": null, "cultivo": null, "provincia": null, "distrito": null, "comunidad": null },
  "totales": { "campanias": 6, "superficie_ha": "9.50", "produccion_kg": "2400.00", "rendimiento_kg_ha": "252.63" },
  "filas": [
    {
      "clave": 1, "etiqueta": "Quinua", "campanias": 3,
      "superficie_ha": "6.00", "produccion_kg": "1300.00",
      "rendimiento_kg_ha": "216.67", "rendimiento_promedio_kg_ha": "200.00",
      "provisional": false, "pocos_datos": false
    }
  ]
}
```

- **Excluye** producciones con `requiere_revision` (dato aún no validado).
- `rendimiento_kg_ha` es el **ponderado** (kg ÷ superficie cosechada,
  el que manda en el cierre); `rendimiento_promedio_kg_ha` es la media
  simple, solo comparación.
- `provisional`: queda alguna campaña sin cerrar; `pocos_datos`: menos
  de 3 campañas en la fila.
- Orden: más kilogramos arriba, luego por nombre.
- `totales` sin filas → `campanias: 0` y los decimales en **`null`**
  (nunca cero falso).

## 5. `GET /api/dashboard/filtros/` — opciones (HU-137)

`?provincia=`/`?distrito=` (ids numéricos) estrechan los niveles
inferiores; id no numérico → **400** «Debe ser un id numérico.»; id
inexistente → **400** «La provincia indicada no existe.» / «El distrito
indicado no existe.».

```json
{
  "periodos": ["2024-2025", "2025-2026"],
  "cultivos": [{ "id": 1, "nombre": "Quinua" }],
  "provincias": [{ "id": 1, "nombre": "Avaroa" }],
  "distritos": [{ "id": 1, "nombre": "Sopa", "provincia": 1 }],
  "comunidades": [{ "id": 1, "nombre": "Alto Sopa", "distrito": 1 }]
}
```

- Períodos y cultivos: los que tengan campañas **del alcance**.
- Ubicación: catálogo activo para los roles sin límite; para el Técnico,
  solo las comunidades/distritos/provincias de **sus** productores.

## 6. `GET /api/alertas/resumen/` — franja de alertas (HU-138)

Mantiene `pendientes` (insignia del menú) y añade `por_tipo` con
**ceros** para los tipos sin pendientes:

```json
{ "pendientes": 3, "por_tipo": { "INCIDENCIA_SEVERA": 0, "SIN_ACTIVIDAD": 2, "RENDIMIENTO_BAJO": 1 } }
```

`RENDIMIENTO_BAJO` hoy se crea solo desde el modelo de regresión
(Semana 15, decisión 2); el panel lo muestra a 0 hasta entonces.

## 7. Colección y pruebas

`docs/coleccion_api_semana16.json` — **F7 cerrada: 506/506 en verde
(504 obligatorias + 2 opcionales), 939/939 aserciones**. Validada con
el pipeline habitual (BD temporal `sigpa_ga_coleccion16` con siembra
previa, servidor 8001 con `LOGIN_RATE_IP=120/min`, borrada al
terminar). Pruebas **263–279** en `backend/dashboard/tests.py`;
`manage.py test` → **279/279 OK**.
