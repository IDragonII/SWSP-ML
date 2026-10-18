# Evidencias — Semana 17: reportes descargables en Excel y PDF

> Salidas reales de los comandos de cierre de la Semana 17 (fases F1–F7).
> Ver `decisiones_semana17.md` (decisiones), `api_reportes.md`
> (contrato) y `verificacion_ui_semana17.md` (checklist de navegador
> que ejecuta el responsable). Fecha de las ejecuciones: **2026-10-17**.

## 1. Suite de backend — 299/299

```bash
cd backend && venv\Scripts\python.exe manage.py test --noinput
```

```
Found 299 test(s).
System check identified no issues (0 silenced).
Ran 299 tests in 595.746s

OK
```

- **299 pruebas en verde** (corte de la semana: 299; las 20 de la
  semana son la 280–299 de `backend/reportes/tests.py`).
- `manage.py check` → `System check identified no issues (0 silenced).`
- `manage.py makemigrations --check` → `No changes detected`
  (la app `reportes/` no tiene modelos; la única migración de la semana
  es `auditoria/0003_accion_exportar.py`).
- **Hallazgos de cierre**: (a) la suite tarda ~595 s: la primera
  ejecución se cortó por timeout y dejó `test_sigpa_ga` huérfana →
  Django pedía borrarla con confirmación interactiva (`EOFError`);
  relanzada con `--noinput` y saliendo a fichero, todo en verde;
  (b) el bloque V2 de `datos_demostracion` chocaba con el índice
  `uq_campania_activa_por_parcela` → rediseñado (10 parcelas y cierre
  inmediato a CERRADA antes de crear la campaña activa de 2026-2027);
  (c) la BD de desarrollo tenía un solo cultivo con variedad activa (la
  variedad de Quinua no existía) → creada «Quinua Amarilla» y el
  comando ahora avisa si hay menos de 2 cultivos con variedad.

## 2. Frontend — lint y build

```bash
cd frontend && npm run lint   # exit 0
cd frontend && npm run build  # exit 0
```

- `eslint .` sin ningún error (exit 0).
- Build correcto (`✓ built in 3.77s`); el aviso de Vite de chunks >
  500 kB es el aceptado en la decisión 38 de la Semana 16 (Recharts).

## 3. Colección de la API (F7) — 540/540, 1005/1005

Pipeline completo (el habitual de F7, `f7_correr17.ps1`):

1. BD temporal `sigpa_ga_coleccion17` creada de cero + `manage.py migrate`.
2. Usuarios de `.credenciales` (`admin`, `coordinador`, `tecnico`).
3. **Siembra previa de F7** (parcela sin coordenadas + clima de fuente
   `API`, necesaria desde la Semana 10).
4. Servidor temporal en el puerto **8001** con `LOGIN_RATE_IP=120/min`
   (la colección supera los 30 logins por IP del valor por defecto).
5. Ejecución con `validador/validar.js` sobre
   `docs/coleccion_api_semana17.json` (el fichero tal cual se entrega).

```
Peticiones en verde: 540/540
Obligatorias: 538/538 · Opcionales: 2/2
Aserciones: 1005/1005 en verde
exit=0
```

- **540/540 peticiones** (538 obligatorias + 2 opcionales: la 270 de
  Open-Meteo y la 486) y **1005/1005 aserciones**, exit 0.
- Las 34 nuevas de la semana (507–540) son **todas obligatorias**:
  catálogo, vista previa de ambos reportes (con aserciones de filas y
  resumen), 404/405/401, filtros y sus 400 (`formato`, `estado`,
  `estado_productor`, ids no numéricos), descargas **xlsx** (firma
  `PK` de Excel leída del blob) y **pdf** (firma `%PDF`), frecuencia
  20/hora con `retry_after`, alcance del Técnico (≤ total de admin) y
  que la vista previa **no** registra eventos (comparación de eventos
  de auditoría por variables `exportar_evento_id`/`exportar_eventos`).
- Al terminar se borró la BD temporal `sigpa_ga_coleccion17` y el
  servidor del 8001 quedó detenido (decisión 59).
- Nota de método: la colección se valida con el **pipeline propio** de
  las semanas anteriores, no con newman (el validador resuelve
  `{{variables}}` en URLs, cuerpos y guiones, añade `Content-Type` y
  entiende la cabecera `sin-sesion`).

## 4. Comando `datos_demostracion` (F7)

```bash
cd backend && venv\Scripts\python.exe manage.py datos_demostracion
```

Tras el rediseño del bloque V2 (y una limpieza de las filas marcadas
para resembrar con los dos cultivos), primera ejecución:

```
Datos de demostración creados: 10 productores, 15 parcelas, 25 campañas,
13 producciones y 8 actividades. Todos los registros llevan la marca
«Datos de demostración inventados (Semana 16)» y «Datos de demostración
inventados (Semana 17)».
```

Segunda ejecución (idempotencia de los dos bloques por separado):

```
Los datos de demostración ya existen; nada que crear.
```

Comprobación de las reglas de la base y del resumen sobre esos datos
(consulta directa + `preparar()` de los dos reportes con `admin`):

```
estados {'CERRADA': 11, 'PLANIFICADA': 6, 'EN_PRODUCCION': 6,
         'COSECHADA': 1, 'CANCELADA': 1}
campañas activas/parcela max 1
PRODUCTORES filas: 45 | filtros: ninguno | advertencias: []
  resumen: productores 33, filas 45, superficie parcelas 78.95 ha,
           superficie sembrada 35.40 ha
PRODUCTIVO filas: 13 | filtros: ninguno
  advertencias: ['2 producciones esperan revisión y no cuentan en el
                 rendimiento',
                 '1 campaña sin cerrar aparece como provisional',
                 'Cultivos con menos de 3 campañas en el resumen:
                 Cañihua. Su rendimiento puede no ser representativo']
  totales: 11 campañas, 18.95 ha, 26855.00 kg, ~1417.15 kg/ha
  por_cultivo: [('Quinua', pocos_datos=False), ('Cañihua', True)]
  provisionales: 1 · excluidas por revisión: 2
```

- **V2** = 5 productores (ñ, tildes y «=1+1»), 10 parcelas, **20
  campañas** en **2 períodos** (10 de 2025-2026 cerradas con producción
  + 10 de 2026-2027 activas: 5 EN_PRODUCCION y 5 PLANIFICADA), 10
  producciones (1 atípica de 50 kg/ha → revisión) y 4 actividades.
- Máximo **1 campaña activa por parcela** respetado en los 25
  registros (índice `uq_campania_activa_por_parcela`).
- Con dos cultivos, el resumen por cultivo queda **Quinua 9 / Cañihua
  2** → fila **POCOS DATOS** en Cañihua y 2 revisiones pendientes (una
  del bloque V1 y una del V2).

## 5. Estado final de la Semana 17

| Comprobación | Resultado |
|---|---|
| `manage.py test` | **299/299 OK** (595.746 s) |
| `manage.py check` | 0 issues |
| `manage.py makemigrations --check` | sin cambios |
| `npm run lint` | exit 0 |
| `npm run build` | exit 0 (`✓ built in 3.77s`) |
| Colección (F7, pipeline propio) | **540/540 · 1005/1005 · exit 0** |
| BD temporal / servidor 8001 | borrada / detenido |
| `manage.py datos_demostracion` | V1+V2 sembrados, probados e idempotentes |
| Vista previa real (admin) | 45 filas (productores) y 13 (productivo) con 3 advertencias |
| Commits | ninguno: la semana se entrega sin commitear (decisión 59) |
