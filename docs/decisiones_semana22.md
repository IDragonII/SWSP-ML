# Decisiones — Semana 22: Machine Learning, integración y entrega final

> Sprint 12 (Sprints 13–16 comprimidos), semana del **1 al 7 de marzo**
> (calendario referencial). Alcance aprobado: **variante de 1 semana
> (36 h)**, 4 bloques con puntos de control y recortes en orden.
> Entrenar/evaluar/guardar, 3 tablas + función de producción, comando
> `registrar_modelo`, API de predicción, pantallas React, pruebas
> **366–392** (total **392**), colección final **598**, manuales y
> `.tex` **v1.5**. Numeración de decisiones continua desde la Semana 21
> (terminó en la **201**); esta semana ocupa la **202 en adelante**.
> Commits diarios en piezas lógicas. El video, la reunión final y los
> informes de entrega los hace el responsable del proyecto.

---

## 1. Planificación, alcance y proceso

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **202** | Semana 22 = **los 4 sprints restantes en una semana** (36 h): Bloque 1 criterio+entrenamiento (8 h), Bloque 2 BD+registro+servicio+API (14 h), Bloque 3 React (6 h), Bloque 4 cierre (8 h). Se eligió la variante de **1 semana** sobre la de 2. | Decisión explícita del responsable del proyecto al plan; los puntos de control diarios y el orden de recortes mitigan el riesgo. |
| **203** | Numeración de pruebas: **366–392** (27 pruebas → total **392**). El plan decía 370–396 sobre una base de 369; la base real al cerrar la Semana 21 fue **365** → renumeración −4. | Confirmado con `manage.py test` (suite baseline 365/365, 748 s) el primer día. |
| **204** | Historias **HU-169..HU-179** (continuas tras HU-166 y los HU-167/168 de los docstrings de `carga.py`). El plan decía HU-175..185, lo que dejaba un hueco 169–174 sin explicar. | Numeración sin huecos en la memoria y el tablero. |
| **205** | Colección final de API = **598** peticiones (**574** de la Semana 18 + **24** nuevas: 8 Modelos, 2 Modelo activo, 12 Predicciones, 2 Campañas predecibles). | El plan hablaba de «la Entrega 1»; la colección viva del repositorio es la de la Semana 18. |
| **206** | `.tex` pasa a **v1.5** (v1.4 se usó en la Semana 20); incluye control de cambios (S20→S22), la corrección del momento de predicción y los RF de ML; grupo ML = **RF-52..RF-61** (auto-numerados, confirmados en el PDF). | Un documento con cambios sustantivos no puede reutilizar la versión intermedia. |
| **207** | **Go/No-Go de datos (primer día):** la vista tiene **13 campañas aptas = 11 de demostración + 2 importadas** (2 en 2024-25, 10 en 2025-26, 1 en 2026-27). Tramo **«menos de 30 reales»**: el sistema se afirma **funcionando**; **ninguna métrica se presenta como resultado de la tesis**. El responsable confirmó que **no hay más datos históricos**. | Conteo real con `SELECT count(*) FROM vw_dataset_entrenamiento` cruzado con los DNI demo (990000xx). |
| **208** | **Inamovibles** (no entran en ningún recorte): marca de demostración, criterio de selección escrito antes, verificación de huella del modelo, filtro por asignación del Técnico, auditoría, comparación con lo real y las pruebas de la predicción. **Orden de recorte** si falta tiempo: estirado → pantalla «Modelos» → filtros del historial → manuales a una hoja → aviso de valor fuera de rango. | Acordado en el plan; protege la honestidad y las pruebas mínimas. |
| **209** | El **entrenamiento y el registro se hacen fuera de la interfaz** (comandos); la semana no implementa reentrenar desde UI. | Plan: la UI de entrenamiento es mejora futura; el sistema solo carga y activa. |

---

## 2. Criterio de selección y estrategia por tramo

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **210** | `docs/criterio_seleccion.md` **escrito y commiteado antes del primer entrenamiento**: gana el **menor RMSE** en la validación agrupada; si la diferencia con un candidato más simple es menor que **1 desvío estándar entre particiones**, gana el más simple (lineal → Random Forest → Gradient Boosting); además debe **mejorar a la línea base** o no se activa ninguno. | La elección tiene que ser defendible aunque se vean los resultados: la prueba 367 verifica que se aplica como está escrito. |
| **211** | Estrategia por tramo de datos (escrita de antemano): ≥100 reales → CV agrupada + holdout final 20 %; 30–99 → CV repetida 5×5; **<30 (tramo actual) → solo CV agrupada con datos de demostración y métricas solo como verificación técnica**. | Ningún resultado de las 13 campañas de demostración se declara hallazgo de la tesis. |

---

## 3. Entrenamiento y modelo guardado (Bloque 1)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **212** | `ml/entrenamiento.py` + comando `manage.py entrenar_modelos`: los tres algoritmos con los **hiperparámetros fijos** del criterio, el **mismo GroupKFold (semilla 42)** para todos y la línea base; sin búsqueda de hiperparámetros (con 13 campañas, buscar sobreajusta). | Reproducible (prueba 366) y honesto con el tamaño de los datos. |
| **213** | Métricas: MAE, RMSE y R² (MAPE solo sin ceros), **siempre contra la línea base por pliegue** y desglosadas **por cultivo** si hay más de un cultivo. | Un promedio general puede esconder un cultivo mal predicho; la línea base evita métricas «bonitas» sin valor. |
| **214** | El modelo elegido se guarda con **su pipeline completo** (preparación incluida) en `backend/ml_models/` (**versionado en Git**) con **manifiesto de huellas SHA-256**; el servidor verifica la huella antes de cargar. | El disco de las plataformas es temporal: el archivo viaja con el código; joblib usa pickle, solo se cargan archivos del equipo (prueba 368). |
| **215** | `notebooks/03_resultados.ipynb` (sin salidas) con la tabla comparativa, el criterio aplicado y el modelo elegido; el informe de resultados vive en `docs/informe_resultados_ml.md`. | Reproducible sin versionar salidas; la evidencia del Capítulo IV sale de aquí. |

---

## 4. Base de datos: 3 tablas y función de producción (Bloque 2)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **216** | `backend/ml/` **pasa de paquete plano a app de Django** (nombre real: **`ml`**, el mismo de los códigos de permiso `ml.*`), con `apps.py`, `models.py` (`EntrenamientoML`, `ModeloML`, `Prediccion`), `admin.py` y migración **`0001`** reversible. | Los nombres de tabla coinciden con `01_tablas.sql` **sin cambios de diseño**. |
| **217** | Índices y restricciones del diseño presentes: CHECK de algoritmo (los 3), MAE/RMSE ≥ 0, `uq_modelo_entrenamiento`, `uq_modelo_version`, **índice único parcial de modelo activo**, CHECK de intervalo, índices de campaña y modelo en `predicciones`. Diferencias normales: nombres de restricciones de Django, índices extra de `db_index` y `ON DELETE` hecho por Django. | Contrastado con `01_tablas.sql`; la prueba 388 cuenta **32 tablas propias y 25 triggers**. |
| **218** | Migración 2 (`produccion`): `fn_produccion_post` **completa** (reemplaza la parcial); al revertir restaura la parcial **sin eliminar `fn_set_actualizado_en`**. Los triggers siguen en **25** (solo cambia el cuerpo de la función). | Es la comparación predicho/real de la referencia (`02_reglas_y_vista.sql:349-367`), que hasta ahora no estaba en Django. |
| **219** | `predicciones` **no se puede borrar** si el modelo tiene predicciones (`ON DELETE RESTRICT`); en Django se logra con la relación normal (sin `cascade` de borrado de modelo). Las campañas no se borran. | Evita perder histórico; el borrado en cascada de diseño lo maneja el propio Django. |

---

## 5. Registro y activación de modelos

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **220** | Comando **`registrar_modelo`** (no pantalla): `--usuario`, `--metricas`, `--archivo`, `--version`, `--activar`, `--dry-run`. Exige usuario activo con **`ml.entrenar`**; crea 1 entrenamiento y **3 modelos** con sus métricas, copia el archivo a `ml_models/` y actualiza el manifiesto. | Los modelos se entrenan fuera; el sistema solo los da de alta con trazabilidad (HU-171). |
| **221** | Protecciones del registro: rechaza **menos de 30 campañas**, rechaza **modelos de demostración fuera del modo desarrollo** (salvo bandera explícita de desarrollo) y **no repite una versión** (única por algoritmo). | Un modelo de juguete no puede quedar activo en un entorno real (pruebas 369–370). |
| **222** | Activación: **un solo modelo activo**; activar uno desactiva el anterior **en la misma transacción**; exige que el archivo exista, la **huella coincida** y una **predicción de prueba** funcione; permiso **`ml.activar_modelo`**. Eventos `ACTIVAR`/`DESACTIVAR` (acciones ya existentes en el CHECK de auditoría). | Sin migración de acciones y con la red de seguridad completa (prueba 371). |
| **223** | `entrenamientos_ml.variables_usadas` es un **objeto JSON**: lista de variables, conjunto, `origen_datos` (real/demostración), huella del dataset, semilla y estrategia. `modelos_ml.hiperparametros` incluye los hiperparámetros, **la línea base y las métricas de validación**. **Sin columnas nuevas** respecto del diseño. | Trazabilidad completa sin tocar el modelo físico. |
| **224** | La **línea base no es una fila** de `modelos_ml` (la tabla solo admite los tres algoritmos del CHECK); sus métricas viven en `hiperparametros` de cada modelo. | Respeta el diseño sin migraciones de alcance. |

---

## 6. Servicio de predicción y API

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **225** | `ml/servicio.py`: **una sola función arma las variables de una campaña** con la misma definición que la fila de la vista (categorías de recursos, por hectárea, unidades base); la prueba 372 compara la fila del servicio con la de la vista. | El riesgo «variables de predicción ≠ variables de entrenamiento» se elimina con una definición compartida y testeada. |
| **226** | Carga del modelo: consulta el **modelo activo en cada petición**, verifica la **huella** contra el manifiesto al cargar, guarda el modelo en memoria y **lo recarga si cambió**. | Huella siempre verificada y coste bajo por predicción. |
| **227** | Elegibilidad: solo campañas **PLANIFICADA o EN_PRODUCCION**; cosechada/cerrada/cancelada → rechazo; campaña ajena o inexistente → **mismo 404**; sin modelo activo → **409** con mensaje claro. | Nada de 404/409 distinguibles que filtren información; el 409 evita un 500 en el camino feliz. |
| **228** | **Valores planificados** de semilla, fertilizante, mano de obra y agua: opcionales, prioridad sobre los registrados, validados (≥ 0) y guardados **junto con su origen** dentro de `variables_entrada`. | Una predicción al planificar no tiene insumos registrados; el origen permite auditar qué fue medido y qué supuesto (prueba 375). |
| **229** | **Avisos**: variables faltantes (imputadas con la **mediana del entrenamiento**), categoría nunca vista (se ignora y se avisa) y valor fuera del rango de entrenado (si se alcanzó). **Confiabilidad BAJA** con 2 de las 4 variables de manejo ausentes. | La predicción declara sus agujeros; la confiabilidad es visible, no implícita (pruebas 376, 379). |
| **230** | **Resultado**: rendimiento en kg/ha + producción estimada = rendimiento × **superficie sembrada**; valor negativo → se ajusta a **0 con marca**; **sin intervalo** (las columnas quedan NULL: el intervalo de estos modelos no es válido). | Regla «solo se muestra intervalo si el método lo permite bien»; nada de números inventados (prueba 377). |
| **231** | **Marca de demostración**: si el modelo activo fue entrenado con datos demostración, **cada respuesta y cada pantalla** lo lleva. Textos fijos: «Es una estimación basada en datos históricos, no una medición» + el **MAE del modelo** junto al resultado. | Honestidad visible (prueba 380). |
| **232** | Las predicciones son **ineditables e inborrables** (405 en PUT/PATCH/DELETE), varias por campaña, límite de **30 por hora y usuario**; campos protegidos (modelo, resultados, errores, creador) nunca llegan del cliente. | Registro histórico; el límite evita abuso y la validación en servidor evita manipulación (prueba 385). |
| **233** | **Privacidad y alcance**: sin DNI/teléfono; el Técnico solo ve predicciones y campañas predecibles de **sus productores asignados** (404 en lo ajeno) y **no recibe quién predijo**. Coordinador: consulta sin predecir ni ver detalles de modelos; Administrador: todo. | Reparto ya sembrado en `usuarios.0002` (5 permisos `ml.*`, **sin permisos nuevos**) (pruebas 383–384). |
| **234** | **Auditoría**: registrar modelo y predecir → `CREAR`; activar/desactivar → `ACTIVAR`/`DESACTIVAR`; módulo «Machine Learning», **sin variables de entrada** en el detalle. Acciones existentes: **sin migración del CHECK**. | Trazabilidad completa con las 16 acciones vigentes (prueba 385). |
| **235** | API: 4 recursos — `GET/POST /api/ml/predicciones/`, `GET /api/ml/predicciones/{id}/`, `GET /api/ml/modelos/` + `POST {id}/activar/`, `GET /api/ml/modelo-activo/`, `GET /api/ml/campanas-predecibles/` — con 405 en escrituras no permitidas y errores por campo en español. | Contrato nuevo documentado en `docs/api_ml.md`. |

---

## 7. Comparación con lo real (HU-176)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **236** | Al registrar o editar una producción, `fn_produccion_post` (completa) rellena `rendimiento_real`, `error_abs` y `error_pct` de las predicciones de esa campaña: **1580 predicho vs 1620 real → 40 kg/ha y 2.47 %**. Al deshacer la cosecha, el servicio limpia esos valores **en la misma transacción**. | Lo prometido en el RF; el ejemplo es la evidencia del Capítulo IV. |
| **237** | Si alguien borra la producción **por SQL directo**, la comparación no se limpia (el trigger no corre): queda anotado como **limitación conocida**. | Transparencia sobre los límites del mecanismo. |
| **238** | `dias_ciclo` se guarda como días desde la **siembra** (o vacío si no hay siembra), en la propia predicción. | Un dato derivado al momento de predecir; con la fecha de siembra ya registrada en la campaña. |

---

## 8. Frontend (Bloque 3)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **239** | Tres pantallas: **Predicción** (selector + valores planificados + resultado), **Historial** (Tabla con filtros en URL y pendientes primero) y **Modelos** (Admin, con «Activar» en Modal); menú «Predicción» sin «próximamente» bajo `ml.predecir` o `ml.ver_predicciones`. | AGENTS.md: todo en Modal, todo con `Tabla`, rueda en el botón; estados de vacío/error/carga en cada vista. |
| **240** | Banner **«DATOS DE DEMOSTRACIÓN»** en las tres pantallas cuando el modelo activo es de demostración; junto al resultado, el texto de estimación y el MAE. | La marca no depende de quién pregunte: está en la pantalla. |
| **241** | Responsivo (≤860 px → tarjetas), teclado numérico en los 4 campos de valores planificados, resultado grande; filtros y pestaña en la URL. | Uso en campo, prioridad celular (decisión 14). |

---

## 9. Cierre y entrega (Bloque 4)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **242** | Pruebas **366–392** (27); suite final 392/392; `migrate` desde cero y reversible, `makemigrations --check`, lint/build en 0, colección **598** en verde, `matriz_rutas_por_rol.md` regenerada. | Criterio «mínimo / bien hecha» del plan. |
| **243** | `docs/manual_usuario.md` (por rol) y `docs/manual_tecnico.md` (instalación, `.env`, respaldo, alertas, entrenar/registrar/activar); `docs/limitaciones_conocidas.md` ampliado (momento de predicción, clima fuera del modelo, sin intervalo, tamaño de datos, origen, despliegue pendiente, mejoras futuras). | HU-179; la entrega se sostiene con instrucciones y límites declarados. |
| **244** | Fuera de alcance (mejoras futuras, en las limitaciones): búsqueda de hiperparámetros, logaritmo del rendimiento, Conjunto 2 con clima integrado (salvo notebook estirado), intervalo, reportes de ML en Excel/PDF, alerta de rendimiento bajo, tarjeta del dashboard, reentrenar desde UI, despliegue en la nube, escenarios sin campaña, mapa de parcelas. | Corte acordado en el plan; lo que queda se lista para quien continúe. |
| **245** | Video de 5 min, reunión final, capturas y etiqueta `entrega-final`: **los hace el responsable del proyecto**; el desarrollo entrega el sistema, pruebas y documentación. | Acordado al empezar la semana. |

---

## 10. Preguntas sin respuesta del responsable → decisiones del desarrollador

> El responsable no respondió antes de la semana. Las propuestas pasan
> a ser **decisiones del desarrollador**, anotadas aquí y en el informe.

| Letra | Pregunta | Decisión del desarrollador (propuesta) |
|-------|----------|----------------------------------------|
| **U** | ¿Cuándo se hace la predicción? | **Al planificar el ciclo (plan de manejo)**: solo datos registrados hasta ese momento; el clima del ciclo **no entra** (monitoreo = objetivo 1, pero no alimenta el modelo; limitación declarada). Corregido en `.tex` v1.5 (líneas 447/309). |
| **V** | ¿Qué error útil es aceptable? | **Propuesta ±200 kg/ha**; mientras tanto, el criterio manda: solo se activa un modelo que **mejora a la línea base** y el MAE se muestra junto al resultado. |
| **I** | ¿El productor que registra un técnico se asigna automáticamente? | Sigue sin responder (Semana 4); se mantiene la asignación explícita. |
| **J** | ¿Cuántas campañas históricas existen? | **13 aptas (11 demo + 2 importadas)** — tramo «<30» (decisión 207). |
| **K** | ¿Valor del quintal y umbrales? | Se mantienen los del diseño (46 kg); sin cambio. |
| **L** | ¿Etapas fenológicas aprobadas? | Las 12 del diseño (Quinua/Cañihua), sin cambiar. |
| **M** | ¿Open-Meteo como fuente del clima? | Sigue implementado con `archive-api`; sustituible en un archivo. |
| **T** | ¿Regla de alertas limitadas a asignados? | Se mantiene `limita_a_asignados` del diseño. |
| **Nueva V** (colisión anotada) | Error útil | Ver V arriba. Siguiente letra libre: **W**. |

---

## 11. Notas de contexto

- **Decisión 246:** la bandera `--version` choca con el `--version`
  propio de Django (`BaseCommand`); los comandos usan
  **`--version-modelo`** (`entrenar_modelos` y `registrar_modelo`).
- **Decisión 247:** con las 13 filas reales de la BD de desarrollo el
  criterio no elige ningún modelo (ninguno gana a la línea base). Para
  poder demostrar el flujo completo en la entrega existe el comando
  **`datos_ml_demostracion`**, que genera en `ML_EXPORT_DIR` un CSV de
  **demostración** (48 filas con patrón lineal inventado, semilla 42,
  marcado como origen «demostracion» en ficha y en el informe). Nunca se
  presenta como resultado de tesis.
- **Decisión 248:** `fn_produccion_post` completa vive en una
  migración **nueva `produccion/0003_fn_produccion_post_completa`**
  (nunca se edita una migración ya aplicada, regla de la casa; el
  precedente es `campanias/0003`). Al revertir restaura la versión
  parcial de `0002` sin tocar `fn_set_actualizado_en`. `ml.0001` no
  depende de ella: es al revés (`0003` depende de `ml.0001`), así el
  revertido de las tablas ML va antes que la restauración de la función.
- **Mapeo HU (11):** HU-169 entrenar y comparar · HU-170 criterio ·
  HU-171 registrar · HU-172 activar · HU-173 predecir · HU-174
  confiabilidad · HU-175 historial · HU-176 comparar con lo real ·
  HU-177 ver resultados · HU-178 alcance del Técnico · HU-179 entregar.
- **Pruebas:** base 365 (baseline 748 s, verde el primer día); nuevas
  366–392.
- **Go/No-Go**: `SELECT count(*) FROM vw_dataset_entrenamiento` = 13;
  cruzado con `DEMO_DNIS` de `datos_demostracion.py`.
- **Docker**: contenedor `sigpa_db`; si la BD no responde, arrancar
  Docker Desktop antes de tocar código (lección de la Semana 21).
- **Versión de sklearn**: misma en entrenamiento y servidor (1.9.1,
  requirements.txt); el manifiesto de huellas protege la carga.
