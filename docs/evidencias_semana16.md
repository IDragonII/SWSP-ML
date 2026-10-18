# Evidencias — Semana 16: panel de indicadores (dashboard)

> Salidas reales de los comandos de cierre de la Semana 16 (fases F1–F7).
> Ver `decisiones_semana16.md` (decisiones), `api_dashboard.md`
> (contrato) y `verificacion_ui_semana16.md` (checklist de navegador
> que ejecuta el responsable). Fecha de las ejecuciones: **2026-10-17**.

## 1. Suite de backend — 279/279

```bash
cd backend && venv\Scripts\python.exe manage.py test
```

```
System check identified no issues (0 silenced).
Ran 279 tests
OK
```

- **279 pruebas en verde** (corte mínimo acordado: 279; las 17 de la
  semana son la 263–279 de `backend/dashboard/tests.py`).
- `manage.py check` → `System check identified no issues (0 silenced).`
- `manage.py makemigrations --check` → `No changes detected`
  (la app `dashboard/` no tiene modelos ni migraciones).
- **Hallazgo corregido en el cierre:** la prueba 270 comparaba dos
  respuestas completas de `/api/dashboard/resumen/` y el campo
  `generado_en` podía cambiar de segundo entre una llamada y otra
  (carrera de reloj). Se excluye de esa comparación —la hora de Lima
  la cubre la prueba 274— y el test queda estable.

## 2. Frontend — lint y build

```bash
cd frontend && npm run lint   # exit 0
cd frontend && npm run build  # exit 0
```

- `eslint .` sin ningún error (exit 0).
- Build correcto (`✓ built`); el aviso de Vite de chunks > 500 kB es
  el aceptado en la decisión 38 (Recharts 3.10.1).

## 3. Colección de la API (F7) — 506/506, 939/939

Pipeline completo (el habitual de F7, `f7_correr16.ps1`):

1. BD temporal `sigpa_ga_coleccion16` creada de cero + `manage.py migrate`.
2. Usuarios de `.credenciales` (`admin`, `coordinador`, `tecnico`).
3. **Siembra previa de F7** (`siembra_coleccion10.py`): parcela sin
   coordenadas + registro de clima de fuente `API` (2026-02-01), que la
   colección necesita desde la Semana 10.
4. Servidor temporal en el puerto **8001** con `LOGIN_RATE_IP=120/min`
   (la colección supera los 30 logins por IP del valor por defecto).
5. Ejecución con `validador/validar.js` sobre
   `docs/coleccion_api_semana16.json` (el fichero tal cual se entrega).

```
Peticiones en verde: 506/506
Obligatorias: 504/504 · Opcionales: 2/2
Aserciones: 939/939 en verde
exit=0
```

- **506/506 peticiones** (504 obligatorias + 2 opcionales: la 270 de
  Open-Meteo y la 486) y **939/939 aserciones**, exit 0.
- Las 18 nuevas de la semana (489–506) son obligatorias: panel de
  indicadores (`resumen`, `campanias-estado`, `produccion`, `filtros`),
  `por_tipo` en `/alertas/resumen/`, permisos por rol, 405 en
  escritura y 401 sin sesión.
- Al terminar se borró la BD temporal `sigpa_ga_coleccion16` y el
  servidor del 8001 quedó detenido (decisión 44).
- Nota de método: la colección se valida con el **pipeline propio** de
  las semanas anteriores, no con newman: el validador resuelve
  `{{variables}}` también dentro de los guiones de prueba, añade
  `Content-Type: application/json` a los cuerpos y entiende la
  cabecera `sin-sesion`; newman no hace nada de eso y generaba
  fallos espurios (415, 401/405 y `{{sufijo}}` literal).

## 4. Comando `datos_demostracion` (F7)

```bash
cd backend && venv\Scripts\python.exe manage.py datos_demostracion
```

Primera ejecución:

```
Datos de demostración creados: 5 productores, 5 parcelas, 5 campañas
(una por estado), 3 producciones (1 para revisión) y 4 actividades.
Todos los registros llevan la marca «Datos de demostración inventados
(Semana 16)».
```

Segunda ejecución (idempotencia):

```
Los datos de demostración ya existen; nada que crear.
```

Comprobación del panel sobre esos datos (`/api/dashboard/resumen/` con
`admin`):

```json
{
  "productores": {"activos": 29, "inactivos": 4, "con_campania_activa": 3},
  "superficie_sembrada_ha": "4.00",
  "campanias_por_estado": {"PLANIFICADA": 1, "EN_PRODUCCION": 1,
                            "COSECHADA": 1, "CERRADA": 1, "CANCELADA": 1},
  "aptas_entrenar": 1,
  "revisiones_pendientes": 1,
  "alertas": {"total": 0, "pendientes": 0}
}
```

- Los 5 estados con campaña propia; producción agrupada con fila
  **PROVISIONAL** (campaña sin cerrar) y **POCOS DATOS** (< 3
  campañas); `revisiones_pendientes` = 1 (la producción atípica queda
  fuera del agregado, como manda la decisión 30).
- El recuento de productores es el total de la BD de desarrollo; los
  registros demo son los 5 de la marca.

## 5. Estado final de la Semana 16

| Comprobación | Resultado |
|---|---|
| `manage.py test` | **279/279 OK** |
| `manage.py check` | 0 issues |
| `manage.py makemigrations --check` | sin cambios |
| `npm run lint` | exit 0 |
| `npm run build` | exit 0 |
| Colección (F7, pipeline propio) | **506/506 · 939/939 · exit 0** |
| BD temporal / servidor 8001 | borrada / detenido |
| `manage.py datos_demostracion` | creado, probado e idempotente |
| HU-123 (pruebas 280–284) | no aplicado (corte mínimo 279/506) |
| Commits | ninguno: la semana se entrega sin commitear (decisión 41) |
