# API de auditoría — `/api/auditoria/` (RF-71/RF-72, HU-105..HU-111)

> Documentación de la Semana 13. Ver `decisiones_semana13.md` para las
> decisiones de diseño y `verificacion_ui_semana13.md` para el checklist
> de navegador. **Solo lectura**: la tabla se escribe desde el backend
> (punto único `registrar_evento`) y el trigger 25 impide toda
> modificación.

## 1. Endpoints

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/auditoria/` | `auditoria.ver` | 200 paginado (20/página; `count`, `results`) |
| GET | `/api/auditoria/{id}/` | `auditoria.ver` | 200 (detalle) / 404 |
| POST | `/api/auditoria/` | — | **405** (sin escritura) |
| PATCH | `/api/auditoria/{id}/` | — | **405** |
| PUT | `/api/auditoria/{id}/` | — | **405** |
| DELETE | `/api/auditoria/{id}/` | — | **405** |

- `usuario` que no tiene el permiso (Técnico, Coordinador en el catálogo
  actual) → **403** «No tienes permiso para realizar esta acción.».
- Sesión expirada o sin permiso en el catálogo → **401**.
- El listado es **descendente por fecha** (`-fecha, -id`); `?page=`
  pagina (20 por página).

## 2. Filtros del listado

| Parámetro | Tipo | Notas |
|---|---|---|
| `?usuario=` | id numérico | Si no es numérico → **400** «Debe ser un id numérico.» |
| `?modulo=` | texto | Módulo exacto (`productores`, `parcelas`, `usuarios`, …) |
| `?accion=` | texto | Una de las 15 acciones (`LOGIN`, `MODIFICAR`, …) |
| `?tabla=` | texto | Tabla exacta del registro (`productor`, `usuarios`, …) |
| `?registro=` | id numérico | Combinable con `?tabla=` para ver el historial de una ficha. Si no es numérico → **400** «Debe ser un id numérico.» |
| `?fecha_desde=` / `?fecha_hasta=` | día (`AAAA-MM-DD`) | Sobre el campo `fecha` (hora de Lima) |
| `?busqueda=` | texto | Busca en módulo, acción, tabla y detalle |

## 3. Fila y detalle

**Fila** (`results` en la lista):

```json
{
  "id": 42,
  "fecha": "2026-01-03T10:45:12-05:00",
  "usuario": {"id": 1, "username": "admin"},
  "accion": "CREAR",
  "modulo": "productores",
  "tabla": "productores",
  "registro_id": 17,
  "detalle": {},
  "ip": "127.0.0.1"
}
```

- `usuario` puede ser **`null`** (evento sin cuenta: login fallido con
  username inexistente, por ejemplo).
- `detalle` es JSON libre: `{}` en la mayoría de eventos y, por ejemplo,
  `{"motivo": "…"}` en ANULAR/REACTIVAR, `{"username": "…"}` en
  BLOQUEAR o `{"cultivo": …, "orden": …}` en el reordenar de etapas.
- `ip` es **solo `REMOTE_ADDR`** (no se lee `X-Forwarded-For`, decisión 3
  de la semana).

## 4. Acciones auditadas (resumen por módulo)

| Módulo | Acciones registradas |
|---|---|
| productores / parcelas / ubicacion / asignaciones | CREAR, MODIFICAR, ACTIVAR, DESACTIVAR, ASIGNAR, DESASIGNAR |
| catalogos (incluye etapas fenológicas) | CREAR, MODIFICAR (p. ej. reordenar etapas con `tabla="cultivos"`) |
| campanias | CREAR, MODIFICAR, ACTIVAR/DESACTIVAR según estado |
| seguimiento (actividades, incidencias, uso) | CREAR, MODIFICAR, ANULAR (con motivo), REACTIVAR |
| produccion | CREAR, MODIFICAR (revisión/deshacer) |
| sistema | CREAR, MODIFICAR (parámetros) |
| usuarios | CREAR, MODIFICAR, DESACTIVAR/ACTIVAR, RESTABLECER_CLAVE, DESBLOQUEAR, LOGIN, LOGOUT, BLOQUEAR (5.º fallo), **CAMBIAR_CLAVE** |

Las **lecturas no generan eventos** (decisión 5).

## 5. Inmutabilidad (HU-108)

- `UPDATE`/`DELETE` directos sobre la tabla responden la excepción del
  trigger: **«Los registros de auditoría no se pueden modificar ni
  eliminar.»** (`DatabaseError`).
- El modelo **no está registrado** en el admin de Django.
- No existe endpoint de escritura; un `POST` manual a la API responde
  **405**.

## Coleccion de pruebas (Postman)

docs/coleccion_api_semana13.json — validada en la fase F7: **430/430 peticiones
con codigo y aserciones en verde (793/793 aserciones)**; los items nuevos de
auditoria son los **393-410** (listado paginado, filtros por accion, modulo,
usuario, registro/tabla, fechas y busqueda, historial de ficha desde las tres
fichas, detalle, 404, 405 solo-lectura, 403 para Coordinador y Tecnico, y 400
con id no numerico).

