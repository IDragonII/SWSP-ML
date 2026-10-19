# Decisiones — Semana 20: importación histórica y dataset

> Sprint 11 (en curso), semana del **15 al 21 de febrero** (calendario
> referencial; sin feriados). Alcance aprobado en el plan de la semana:
> terminar la importación de datos históricos (RF-49/RF-50) y la vista
> del dataset (RF-51) con pruebas **326–345**, docs y `.tex` v1.4.
> Numeración de decisiones continua desde la Semana 19 (terminó en la
> **116**); esta semana ocupa la **117–163**. Commits por fase (tres en
> total), decisión que sustituye al «commit único por semana» solo para
> esta semana (plan aprobado por el responsable).

---

## 1. Planificación, alcance y proceso

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **117** | Sprint 11 (Semana 20) = importación histórica + dataset + pruebas 326–345 + docs + `.tex` v1.4; **cero UI**. | Solo|RF-49/50/51 estaban abiertos; la semana se cierra con ellos. |
| **118** | Numeración de pruebas: **326–345** (20 pruebas → total **345**). | Continúa la numeración real de la Semana 19 (325). |
| **119** | Commits **por fase**: (1) Fases 1–3 app+servicio+comando (`cc14728`), (2) Fase 4 pruebas+recuentos (`43ee84d`), (3) Fase 5 docs (final). | Cada fase deja la suite en verde; trazabilidad fina. |
| **120** | Las pruebas de la Semana 19 que cuentan tablas/recursos se actualizan a los números nuevos (29 tablas, 30 recursos) en la misma Fase 4. | La app `importaciones` y `catalogos.0003` cambian recuentos reales del esquema; ocultarlos sería mentir. |
| **121** | `DB_sql/01–03` (ignorados por `.gitignore`) se mantienen como referencia local a igual de las migraciones. | Fuente del diseño; lo versionado es el código Django. |

---

## 2. Modelo de datos y migraciones

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **122** | Tabla `importaciones` tal cual el diseño (archivo, tipo, fecha, usuario, filas_totales/ok/error, `detalle_errores` JSONB, estado EN_PROCESO/COMPLETADA/CON_ERRORES). | Registro único por ejecución; el detalle de errores vive en JSONB (ya consultable). |
| **123** | `campanias.origen` ∈ {SISTEMA, DEFAULT} / {IMPORTADA} con `ck_campania_origen` (migración `campanias.0004`). | Distingue lo introducido por la API de lo importado, sin tocar las filas existentes. |
| **124** | Cuatro recursos genéricos «… (total histórico)» (SEMILLA/FERTILIZANTE/MANO_OBRA/AGUA) en `catalogos.0003`; **nunca los crea el importador**. | Los totales del archivo mapean a un recurso estable; los catálogos son responsabilidad del admin. |
| **125** | Vista `vw_dataset_entrenamiento` creada por migración (`importaciones.0002`): antes solo vivía en `DB_sql/02` y los tests ejecutaban su texto. | La BD de Django tiene su propia copia versionada; revertir la migración la elimina. |
| **126** | **Bug latente corregido**: `fn_codigo_productor`/`fn_codigo_parcela` usaban `lpad(nextval::text, N, '0')` y `lpad` **trunca** en PostgreSQL: con la secuencia ≥1000 el código salía `P-100` repetido y el INSERT moría con `duplicate key`. Arreglo en `productores.0005` con `lpad(s, GREATEST(N, length(s)), '0')` (CREATE OR REPLACE conserva el OID: los triggers no cambian) + reflejo en `02_reglas_y_vista.sql`. | Detectado por la importación (quema secuencias con intentos fallidos; los `nextval` no se revierten). Rompería en producción al llegar a 1000 parcelas. |

---

## 3. Formato de archivo y plantillas

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **127** | Plantilla `.xlsx` con fila 1 = encabezados (`marca` + columnas de datos) y fila 2 = **EJEMPLO** con `marca="EJEMPLO"`; el importador ignora cualquier fila con esa marca. | Quien copia la plantilla no puede importar el ejemplo sin borrarlo; las columnas quedan alineadas. |
| **128** | Columna `marca` **opcional**: archivos sin ella se admiten igual (los CSV de ejemplo de `docs/ejemplos_importacion/` no la llevan). | La marca es comodín, no requisito; no penaliza a archivos hechos a mano. |
| **129** | CSV: delimitador `,` o `;` detectado contando en la cabecera; codificación UTF-8 con o sin BOM (`utf-8-sig`); **sin chardet**. | Cubre el Excel en español (UTF-8 con BOM) y el notepad (`,`), sin dependencia nueva. |
| **130** | `.xlsx` con **openpyxl** en modo `read_only`, sin pandas. | openpyxl ya está en `requirements.txt`; pandas añadiría ~30 MB y un ecosistema entero para leer una hoja. |
| **131** | Límites duros: **5 MB** y **5000 filas** de datos (comprobados antes de parsear), extensión `.csv`/`.xlsx`. | Presupuesto de memoria y de tiempo de una operación síncrona por consola. |

---

## 4. Reglas de negocio de la importación

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **132** | Cada fila se valida con los **mismos serializers** que la API (productor, parcela, campaña, producción); una transacción por fila: si falla, no queda nada a medias. | Una sola fuente de verdad de las reglas; «mismo comportamiento, otro canal». |
| **133** | **Idempotencia por claves naturales**: DNI (productores), productor+`referencia_ubicacion` (parcelas), parcela+período excl. CANCELADA (campañas). La fila existente se **omite sin actualizarla**. | Re-ejecutar un archivo no duplica ni pisa ediciones hechas por la API. |
| **134** | Los catálogos (comunidad, cultivo, variedad) **nunca se crean**: error por fila con sugerencia `difflib` («¿Quizá quiso decir…?») o lista de disponibles. | El importador carga datos, no administra catálogos; sugerir evita teletransportar nombres. |
| **135** | Fechas: `dd/mm/aaaa` o `aaaa-mm-dd` **exactamente** (10 caracteres); cualquier otra forma (incluidas las ambiguas `1/2/2020`) → error. | Un archivo de 5000 filas no admite interpretación: dos sistemas leen la misma celda igual. |
| **136** | DNI: 7 dígitos → se antepone `0` (Excel a veces lo pierde); 8 exactos; en mensajes e informes **enmascarado** (`******` + 2 últimos). | Normaliza el dato sin exponerlo en consola ni en archivos. |
| **137** | Campaña importada: `fecha_siembra ∈ [fecha_inicio, fecha_fin_prevista]` (espejo de `fn_validar_fecha_campania`) y `fecha_cosecha ≥ fecha_siembra`; estado inicial EN_PRODUCCION y luego COSECHADA por la producción. | Las mismas transiciones que el flujo normal, sin pisar los triggers. |
| **138** | La atípica (rendimiento fuera de umbrales) queda **COSECHADA con `requiere_revision`**, no se cierra; solo se cierran las que no requieren revisión → CERRADA. | Un dato importado dudoso entra al dataset solo cuando un humano lo confirma. |
| **139** | `superficie_cosechada_ha` vacía → la sembrada validada; `fecha_incorporacion` vacía → hoy; `fecha_incorporacion` no se rellena solo si está vacía en el archivo. | Completitud sin inventar: lo vacío toma el valor documentado, lo presente manda. |
| **140** | Los 4 totales de recursos van en el archivo de campañas (`semilla_kg`, `fertilizante_kg`, `jornales`, `agua_m3`); vacío/0 = sin uso; negativo = error; se graban con `fecha = fecha_siembra` y la unidad base de cada tipo. | Un archivo por campaña (la unidad de trabajo real); `fn_uso_recurso` llena `cantidad_base`. |

---

## 5. Comando `importar_historico`

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **141** | `--tipo {productores,parcelas,campanias} --archivo RUTA --usuario NOMBRE` obligatorios; **un tipo por ejecución**. | Un registro de importación = un archivo = un tipo; el informe es legible. |
| **142** | El usuario debe existir, estar activo y su rol tener el permiso **`importacion.ejecutar`** (sembrado en `usuarios.0002`). | Punto único de control: sin botón/permiso no hay comando. |
| **143** | **`--dry-run`** valida todo con transacción + `set_rollback(True)`: no crea registro, no escribe informe, no audita, no evalúa alertas. | Probar un archivo real sin efectos secundarios. |
| **144** | Solo una importación **EN_PROCESO** a la vez; una interrumpida queda CON_ERRORES (el comando captura `KeyboardInterrupt`/excepciones); **`--forzar`** marca como CON_ERRORES la huérfana y continúa. | Evita dos consolas escribiendo a la vez y destraba sin tocar a mano la BD. |
| **145** | Orden **productores → parcelas → campañas**; el comando no lo fuerza (un tipo por ejecución) pero la guía lo documenta. | Las claves naturales de cada tipo dependen del anterior. |
| **146** | Informe CSV `fila,columna,mensaje` (UTF-8 con BOM) en `IMPORTACION_DIR` (.env, **fuera del repo**, con guarda de existencia); si la variable no está, aviso y sigue. | El informe viaja por correo/pantalla sin datos personales ni código en el repo. |
| **147** | Por ejecución real: **1 registro** en `importaciones` + **1 evento** de auditoría (`modulo="importaciones"` en minúsculas, `accion=CREAR`, `tabla="importaciones"`) + `evaluar_todo()` **una sola vez** al final (con try/except: un fallo de alertas no tumba la importación ya hecha). | Trazabilidad exacta sin inundar la bitácora ni acoplar el cierre al resultado de las alertas. |

---

## 6. Dataset de entrenamiento (RF-51)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **148** | `vw_dataset_entrenamiento` es **vista regular** (no materializada): refleja las importaciones al instante, sin REFRESH. | Un volcado histórico completo tarda minutos: no puede esperar a un refresco. |
| **149** | Filas con `origen='IMPORTADA'`: `n_incidencias`, `severidad_max`, `n_aplicaciones` y `n_heladas` (sin clima) quedan **NULL, no 0**; las SISTEMA conservan el COALESCE a 0. | NULL = «desconocido», 0 = «ninguno»: 0 en una variable desconocida corrompe el entrenamiento. |
| **150** | `dias_ventana_clima = (fecha_cosecha − COALESCE(fecha_siembra, fecha_inicio)) + 1`, la misma fórmula que `dias_ventana` de `resumen_clima`. | Misma ventana que los reportes: una sola definición. |
| **151** | El WHERE **no cambia** (`estado='CERRADA'` + `incluir_en_entrenamiento`): las atípicas importadas no entran hasta que alguien las revisa y cierra. | El dataset sigue siendo «solo datos confirmados». |

---

## 7. Pruebas 326–345

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **152** | Bloque `backend/importaciones/tests.py` con base `ImportacionBase` (admin con permiso, coordinador sin él, ubicación, cultivo+variedad, recursos genéricos de la migración). | Aislamiento por prueba; usa `call_command` con `StringIO` como el resto del repo. |
| **153** | Los informes de error de las pruebas se redirigen con `patch.dict(os.environ, {"IMPORTACION_DIR": …})` a un tempdir. | Las pruebas no ensucian `D:\ImportacionesSigpa` real. |
| **154** | Prueba 345 end-to-end con los CSV reales de `docs/ejemplos_importacion/` (carga `cargar_ubicacion`, crea Quinua/Blanca y ejecuta los 3 archivos en orden). | Los ejemplos de la documentación quedan cubiertos por la suite: no se pudieron desactualizar. |
| **155** | `evaluar_todo` se parchea (`patch` sobre el símbolo del módulo comando) para contar llamadas: 1 real, 0 en dry-run. | Verificar el «una sola vez» sin ejecutar el barrido completo de alertas. |

---

## 8. Documentación y cierre

| Nº | Archivo | Descripción |
|----|---------|-------------|
| **156** | `docs/importacion_historica.md` | Guía de uso: permisos, plantilla, columnas por tipo, límites, idempotencia, informe, ejemplo completo. |
| **157** | `docs/dataset.md` | `vw_dataset_entrenamiento`: fuentes, columnas, NULLs de importadas, ventana de clima. |
| **158** | `docs/decisiones_semana20.md` | Este archivo (117–163). |
| **159** | `docs/ejemplos_importacion/*.csv` | 3 archivos de ejemplo reales (productores, parcelas, campañas) sin columna `marca`. |
| **160** | `requerimientos.tex` v1.4 | Versión 1.4 (Semana 20); RF-50/RF-51 ajustados al alcance final (informe sin datos personales; origen y NULLs del dataset). |
| **161** | `CONTEXTO.md` | Semana actual → 20; sección «Semana 20» con archivos, pruebas y comandos. |
| **162** | Suite completa **345/345** en verde antes de cada commit. | Puerta de calidad por fase. |
| **163** | Cierre: tres commits de fase + revisión final. | Historial de la semana legible por fases. |
