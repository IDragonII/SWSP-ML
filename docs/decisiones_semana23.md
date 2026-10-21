# Decisiones — Semana 23: entrenamiento desde el sistema

> Semana del **8 al 14 de marzo** (calendario referencial). Alcance: que el
> Administrador entrena, siga el avance, compare resultados y active un
> modelo desde pantallas React, sin tocar `.py`; trabajador de segundo
> proceso con cancelación; **27 pruebas nuevas → 419**, colección de API
> de la semana, manuales y control de cambios del `.tex`.
> Numeración de decisiones continua desde la Semana 22 (terminó en la
> **248**); esta semana ocupa la **249 en adelante**.
> Commits diarios en piezas lógicas (F0-F6).

---

## 1. Planificación, alcance y proceso

| N.º | Decisión | Justificación |
|-----|----------|---------------|
| **249** | Numeración de pruebas: **393–419** (27 pruebas → total **419**). El plan asumía 396 como base y numeraba 397–423; la base real al cerrar la Semana 22 fue **392** → renumeración −4. | Confirmado con `manage.py test` (suite 392/392) el primer día. |
| **250** | Historias **HU-180..HU-187** (continuas tras HU-179). El plan decía HU-186..193, lo que dejaba un hueco 180–185 sin explicar. | Numeración sin huecos en la memoria y el tablero (precedente: decisión 204). |
| **251** | **Inamovibles** (no entran en ningún recorte): 1 modelo activo, entrenar no activa, versión única, huella verificada, atomicidad, los 55 permisos sin cambios, auditoría sin contenido de entrada y honestidad de métricas. **Orden de recorte** si falta tiempo: detalle de etapas del trabajador → cancelación de tarea en proceso → aviso de datos nuevos. | Acordado en el plan; protege lo ya validado en la S22. |
| **252** | El trabajador es un comando **portátil** (Windows, Linux o contenedor). El manual técnico documenta los tres casos para mantenerlo vivo: **Task Scheduler** (Windows), **systemd** (Linux) y **docker compose** (contenedor); el comando es el mismo en los tres. | Plataforma de producción aún sin cerrar; el código no se ata a un SO (decisión 258). |

---

## 2. Base de datos: 4.ª tabla de ML y modelo en BD

| N.º | Decisión | Justificación |
|-----|----------|---------------|
| **253** | Cuarta tabla de `ml`: **`tareas_entrenamiento`** → **33 tablas propias** (32 + 1) y **25 triggers** sin cambios (la tabla no necesita triggers: los cambios de estado se hacen en transacciones de Python). Convención `db_table` = plural snake_case igual al `CREATE TABLE`. | El trabajador necesita persistir el pedido, el progreso y el resultado. |
| **254** | `modelos_ml` gana **3 columnas**: `contenido` (bytea, el `.joblib` en la BD), `huella` (varchar 64, SHA-256 de esos bytes) y `versiones_librerias` (jsonb: pandas/numpy/scikit-learn/joblib fijados en `requirements.txt`). El **trabajador guarda el modelo en la BD**; el registro manual por comando sigue usando archivo + `manifiesto.json` como **fallback** (compatibilidad total con la S22). CHECK `ck_modelo_tamano` (vía SQL crudo en la migración): `contenido IS NULL OR octet_length(contenido) <= 20971520` (20 MiB). | El disco de las plataformas es temporal; el modelo viaja con la BD. El límite evita payloads desmedidos y el CHECK vive en la BD, no solo en Python. |
| **255** | **Una sola tarea activa a la vez en todo el sistema**: índice único parcial `uq_tarea_activa` sobre la constante `(1)` con predicado `estado IN ('PENDIENTE','PROCESANDO')`. Un segundo pedido con tarea activa → **409** en la API. | El índice parcial sobre constante garantiza "cero o una" fila activa global (no una por estado ni por usuario). |
| **256** | La reversión de la migración 2 (`modelos_ml` → sin columnas de BD) está **anotada**: si existe algún modelo con `contenido` y sin `archivo`, la reversión lanza un error claro antes de tocar nada (esos modelos quedarían sin artefacto en ninguna parte); la salida es **restaurar el respaldo previo**. | Dato que se pierde una vez revertido; mejor frenar que destruir en silencio (precedente: decisión 248). |
| **257** | `DB_sql/01_tablas.sql` y `02_reglas_y_vista.sql` se **actualizan en F0** junto a las migraciones (el plan de la semana decía «ya actualizado»; el working tree real no lo tenía). | Un solo esquema de verdad: Django y el SQL del diseño se mueven juntos (regla de la casa). |

---

## 3. Trabajador y entrenamiento desde el sistema

| N.º | Decisión | Justificación |
|-----|----------|---------------|
| **258** | Trabajador = comando `sistema/management/commands/procesar_entrenamientos` (patrón de `evaluar_alertas`: pensado para proceso programado, con `--dry-run`). **Bucle de 5 s** o `--una-vez`; reclama la tarea con `select_for_update(skip_locked=True)`; ejecuta el entrenamiento en un **subproceso** (`n_jobs=1`, tope **15 min**) con **latido cada 30 s** → si el latido envejece 5 min, la tarea pasa a FALLIDA. **Cancelación portátil**: `taskkill /T /F` en Windows, `os.killpg` en POSIX (mata el árbol de procesos; sin precedente en el repo, patrón nuevo). | Dos trabajadores no pisan la tarea (SKIP LOCKED); el tope y el latido impiden tareas zombis; el kill portátil no ata el sistema a Windows. |
| **259** | Los datos del entrenamiento salen **siempre del sistema**: el trabajador lee `vw_dataset_entrenamiento` con `columnas.consulta_exportacion()` + cursor (patrón de `exportar_dataset`) y arma el DataFrame en memoria; **sin CSV y sin `ML_EXPORT_DIR`** en esta ruta. `variables_usadas["origen_datos"] = "sistema"`. | Es el objetivo de la semana: el Administrador entrena sin salir de la interfaz ni mover archivos. |
| **260** | `registro.registrar` se **extiende con `contenido: bytes`** (opcional): calcula la huella desde los bytes, guarda `contenido`/`huella`/`versiones_librerias` en los 3 modelos y **no exige archivo**. La ruta con `archivo` + manifiesto sigue intacta para el comando manual. | Reutiliza la alta de 1 entrenamiento + 3 modelos, la validación del criterio y la auditoría ya probadas (369-371). |
| **261** | Nuevo throttle **`ml_entrenamiento` = 5 por día y por usuario** (`ML_ENTRENAMIENTO_RATE=5/day` en `.env.example`), 429 en español. | Frecuencia confirmada con el responsable; un entrenamiento por hora ya es abuso razonable. |
| **262** | El origen **real o demostración** no cambia la fuente de datos (sigue siendo la vista): `ML_ORIGEN_DATOS` (default `real`) solo **sella la honestidad** en `variables_usadas` y alimenta el banner cuando la BD corre con datos de demostración sembrados por `datos_ml_demostracion`. | El brief pedía decidirlo; la respuesta del responsable fue tajante: «la cosa es que el entrenamiento tome los datos del sistema, no de archivos». |

---

## 4. API y frontend

| N.º | Decisión | Justificación |
|-----|----------|---------------|
| **263** | Cuatro recursos nuevos (`estado-datos`, `entrenamientos` lista/alta, `cancelar`, `resultados`) y dos ampliados (`modelos` con las columnas de BD, `predicciones` sin cambio funcional). El frontend consulta el progreso **cada 5 s solo mientras hay tarea activa** (patrón de polling de alertas); sin tarea activa no hay sondeo. | Sin tarea no hay nada que observar; el sondeo continuo quemaría la ventana del throttle y la batería del navegador. |
| **264** | La pantalla de resultados muestra la tabla comparativa de los 3 candidatos, marca el **recomendado** por el criterio (menor RMSE con la regla del desvío) y ofrece **«Activar este modelo»** con la misma red de seguridad que el comando (verificación de huella y un solo activo). | La activación desde UI debe ser tan segura como la del comando (220-222). |

---

## 5. Notas de ejecución

- **Pruebas clave**: 399 dos trabajadores no pisan la tarea · 401
  interrupción por tope/latido · 407 el sistema y el script `ml` dan
  idénticos resultados (semilla 42) · 419 recorrido completo de punta a
  punta.
- **Migraciones**: `ml/0002_tareas_entrenamiento` y
  `ml/0003_modelos_en_bd` (anotada, decisión 256). Orden de reversión de
  la app completa: primero `produccion 0002`, luego `ml zero` (decisión
  248, sigue vigente).
- **Respaldos**: `docker exec sigpa_db pg_dump -U postgres sigpa_ga`
  antes de aplicar `0003` en cualquier BD con datos (decisión 256).
- **Docker**: si la BD no responde, arrancar Docker Desktop antes de
  tocar código (lección de la Semana 21).
