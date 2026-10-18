# Evaluación de alertas — cómo se generan y se cierran (Semana 15, HU-124..HU-132)

> Documentación de la Semana 15. Ver `decisiones_semana15.md` para las
> decisiones (filas 2–6, 12, 13, 17–20) y `api_alertas.md` para la API.
> La lógica vive en **`backend/alertas/servicio.py`** (no en triggers): se
> ejecuta al confirmar cada escritura relevante y en el barrido diario.
> **Nunca bloquea el negocio**: un fallo se loguea y pasa; el barrido
> diario es la red de seguridad.

## 1. Qué se genera hoy (y qué no)

| Tipo | Condición | Unicidad |
|---|---|---|
| `INCIDENCIA_SEVERA` | Incidencia con severidad **`ALTA`** y **sin anular** | **Una sola por incidencia** (`uq_alerta_incidencia`) — atendida o no |
| `SIN_ACTIVIDAD` | Campaña `PLANIFICADA` o `EN_PRODUCCION` **ya iniciada** (`fecha_inicio ≤ hoy`) cuya última referencia pasó hace **más de `dias_sin_actividad` días** (por defecto 30) | **Una pendiente por campaña** (`uq_alerta_pendiente_campania_tipo`) |
| `RENDIMIENTO_BAJO` | — | **No se genera** (prueba 261): el RF-63 pide rendimiento **predicho** y la predicción llega con el modelo de regresión (Sprint 14 de ML); el tipo existe en la tabla y en los filtros |

- **Referencia de actividad**: última `Actividad` **no anulada** de la
  campaña (`Max(fecha)`) → si no hay, `fecha_siembra` → si no, `fecha_inicio`.
- Estados **no evaluables**: `COSECHADA`, `CERRADA`, `CANCELADA` (una
  campaña que sale de la ventana **cierra** su pendiente, §5).
- Mensajes de ejemplo (siempre **sin datos personales**):
  - `Incidencia severa de Helada el 2026-01-05 en la campaña 2025-2026.`
  - `La campaña 2025-2026 (Quinua) no registra actividades desde el 2025-11-30.`

## 2. Cuándo se ejecuta

1. **Tras el COMMIT de escrituras relevantes** — `tras_confirmar(tipo, obj)`
   agenda `transaction.on_commit` con **13 puntos de llamada**:
   - `campanias`: `iniciar`, `cancelar`, `cerrar`;
   - `seguimiento`: crear/editar y anular/reactivar **actividades**
     (evaluación de campaña) e **incidencias** (evaluación de la incidencia);
   - `produccion`: registrar producción (la campaña pasa a `COSECHADA` → se
     reevalúa) y anular producción (vuelve a `EN_PRODUCCION`).
   El callback **relee** el registro (algún trigger pudo cambiar el estado
   en memoria) y, si algo falla, `logger.exception` y pasa — la escritura
   de negocio **no se revierte**.
2. **Barrido diario** — `evaluar_todo()` desde el comando `evaluar_alertas`
   (§6) o desde la evaluación manual de la API (§2.3). Es la red de
   seguridad de todo lo anterior.
3. **Evaluación manual** — `POST /api/alertas/evaluar/`
   (`parametros.gestionar`, una cada 5 minutos, `dry_run` opcional): llama
   al **mismo** `evaluar_todo()`. Ver `api_alertas.md` §4.

## 3. El barrido `evaluar_todo()` paso a paso

Todo ocurre dentro de **una** transacción (`transaction.atomic`):

1. Para cada campaña **evaluable** (estado en `PLANIFICADA`/`EN_PRODUCCION`
   y `fecha_inicio ≤ hoy`): `evaluar_campania()` — crea la pendiente
   `SIN_ACTIVIDAD` si corresponde, o cierra la existente si la condición
   desapareció.
2. **Red de seguridad**: cada pendiente `SIN_ACTIVIDAD` cuya campaña ya no
   sea evaluable → cierre automático.
3. Para cada incidencia `ALTA` **sin anular**: `evaluar_incidencia()` —
   crea, reabre (si el cierre fue automático) o cierra.
4. **Red de seguridad**: cada pendiente `INCIDENCIA_SEVERA` cuya
   incidencia ya no cumple (anulada, severidad rebajada o campaña fuera de
   la ventana) → cierre automático.
5. `dry_run=True` → **rollback** de la transacción (nada escrito) y **sin**
   evento de auditoría; si no, evento resumen (§8).

**Idempotente**: correrlo muchas veces no duplica nada (prueba 248) — la
creación es `get_or_create`/«ya existe una por incidencia» y el cierre solo
actúa sobre pendientes.

## 4. Cierre automático, reapertura y gracia (ciclo de vida)

- **Cierre automático** (`_cerrar_automaticamente`): `atendida=True`,
  `atendida_por=NULL`, `atendida_en=now`, `nota_atencion=NULL`. Así se
  distingue de la atención manual (prueba 243).
- **Reapertura automática**: si la condición vuelve y la alerta estaba
  cerrada **sin usuario**, se reabre (`atendida=False`, `atendida_en=NULL`).
- **Lo cerrado a mano no lo toca el sistema**: una incidencia severa
  atendida manualmente se queda atendida aunque la condición siga (una
  sola por incidencia); una `SIN_ACTIVIDAD` atendida a mano entra en
  **periodo de gracia**.
- **Gracia** (`_en_periodo_de_gracia`, HU-131): desde la última atención
  **manual** de esa campaña+tipo hasta pasados los mismos
  `dias_sin_actividad` días, el sistema **no crea** una nueva pendiente
  (sin gracia, cada barrido reabriría la lluvia que el técnico acaba de
  resolver — prueba 245). La gracia **no** protege de los cierres
  automáticos.
- **Reapertura manual**: solo por `POST /api/alertas/{id}/reabrir/` sobre
  alertas atendidas a mano; una automática responde 400 (prueba 252).

## 5. Cambios de estado de la campaña (HU-130)

`cancelar`, `cerrar` y la cosecha (producción) sacan la campaña de los
estados evaluables → sus pendientes `SIN_ACTIVIDAD` se cierran en el
mismo evento (ganchos) y el barrido lo repite como red de seguridad
(prueba 247: cancelar cierra; la 246: una actividad nueva hace lo
inverso — cierra porque la condición desaparece).

## 6. Comando `evaluar_alertas` (HU-131)

```
manage.py evaluar_alertas [--dry-run] [--hoy AAAA-MM-DD]
```

- Salida: `Alertas creadas: N · cerradas: M` (con «(dry-run, sin
  cambios)» al final en seco).
- `--dry-run`: evalúa y **revierte** la transacción; no escribe y **no**
  registra evento de auditoría (prueba 248).
- `--hoy`: fija la fecha de evaluación para pruebas; **solo con `DEBUG`**
  (si no → `CommandError`, prueba 249) y formato `AAAA-MM-DD`.
- **Pendiente**: programarlo en la instalación (cron/systemd/Task
  Scheduler) — aún **sin programar**; queda para el despliegue y el `.tex`.

## 7. Fecha de Lima

El backend guarda en UTC pero el sistema es de Perú: `fecha_hoy()` devuelve
la fecha civil de **America/Lima** y con ella se comparan los días de
inactividad, se redacta la fecha del mensaje y se mide la gracia (prueba
249).

## 8. Auditoría: evento resumen y las 36 horas (HU-132)

- Cada evaluación real (comando o manual; **no** en `dry_run`) deja **un
  evento**: `usuario=null`, `MODIFICAR`, `modulo="alertas"`,
  `tabla="alertas"`, `detalle={"resumen": true, "creadas": N,
  "cerradas": M}` (prueba 250).
- `GET /api/alertas/evaluacion/` toma **el evento más reciente** con ese
  detalle: `ultima_evaluacion` = su `fecha`; `atrasada = true` si no hay
  evento o si han pasado **más de 36 horas** (`umbral_horas: 36`, prueba
  259). El aviso se muestra en `/alertas` y en el panel de `/parametros`
  (chip `ATRASADA`/`AL DÍA`).

## 9. Parámetro `dias_sin_actividad` (RF-15, HU-129)

- Fila del catálogo `parametros_sistema`, por defecto **30**.
- La API de parámetros valida **1–365** («Los días sin actividad deben
  estar entre 1 y 365.») y al cambiarlo responde con `aviso`: «El nuevo
  valor se aplica en la siguiente evaluación de alertas; las ya generadas
  no cambian.» (prueba 260) — el umbral afecta a la **siguiente**
  evaluación, no reevalúa lo ya generado.
- El servicio se defiende además leyendo la BD directamente: valor no
  numérico o `< 1` → 30.

## 10. Privacidad de los mensajes (RF-63/RF-64)

Los mensajes solo llevan periodo/cultivo de la campaña, tipo de
incidencia y fechas: **nunca** nombres, DNI ni teléfono (prueba 261). La
fecha embebida es la de referencia **fija** al crear el mensaje (no se
reescribe cada día).

## 11. Pruebas de la semana (242–262)

| # | Cubre | HU |
|---|---|---|
| 242 | Incidencia severa crea **una sola** alerta por incidencia | HU-124 |
| 243 | Anular cierra; reactivar reabre; lo atendido a mano no se toca | HU-124 |
| 244 | `SIN_ACTIVIDAD` con fecha inyectada (umbral configurable) | HU-129 |
| 245 | Una pendiente por campaña+tipo y gracia tras atender a mano | HU-131 |
| 246 | Actividad nueva cierra la pendiente (ganchos de la API) | HU-129 |
| 247 | Cancelar la campaña cierra sus pendientes | HU-130 |
| 248 | Comando idempotente y `--dry-run` no escribe | HU-131 |
| 249 | Fecha de Lima en el mensaje; `--hoy` solo con `DEBUG` | HU-131 |
| 250 | Evento resumen de la evaluación en auditoría | HU-132 |
| 251 | Atender con permiso, nota y auditoría | HU-125 |
| 252 | Reabrir solo lo atendido a mano; lo automático no | HU-125 |
| 253 | Ámbito del Técnico y privacidad del atendiente | HU-128 |
| 254 | 401 sin sesión y 403 sin permiso | HU-125 |
| 255 | Filtros y búsqueda del listado | HU-127 |
| 256 | Productores en riesgo | HU-126 |
| 257 | Resumen de la insignia | HU-127 |
| 258 | Evaluación manual con límite de una cada 5 minutos (429 con `retry_after`; hallazgo de F6) | HU-131 |
| 259 | Estado de la evaluación y atraso de 36 horas | HU-132 |
| 260 | `dias_sin_actividad` es entero 1–365 y avisa del cambio | HU-129 |
| 261 | Mensajes sin datos personales y `RENDIMIENTO_BAJO` no se genera | HU-124 |
| 262 | Restricciones de la tabla y los 25 triggers intactos | — |

Los ganchos `on_commit` se prueban con `captureOnCommitCallbacks` (el
`TestCase` de Django no confirma transacciones).
