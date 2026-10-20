# Decisiones — Semana 21: preparación de datos para Machine Learning

> Sprint 12 (en curso), semana del **22 al 28 de febrero** (calendario
> referencial; sin feriados). Alcance aprobado en el plan de la semana:
> exportar el dataset de entrenamiento (HU-166), el paquete `backend/ml/`
> (catálogo, carga, limpieza, pipeline, validación agrupada y línea base),
> dos notebooks sin salidas, docs y pruebas **346–365**. **Sin API,
> sin pantallas, sin tablas nuevas y sin entrenar modelos.**
> Numeración de decisiones continua desde la Semana 20 (terminó en la
> **163**); esta semana ocupa la **164–196**. Commits por fase, como en
> la Semana 20.

---

## 1. Planificación, alcance y proceso

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **164** | Sprint 12 (Semana 21) = preparación de datos para ML: `exportar_dataset`, paquete `ml/`, 2 notebooks, docs y pruebas 346–365; **cero UI y cero API**. | El ML se apoya en lo ya construido (RF-51, auditoría, permisos); lo nuevo esta semana es el material de entrada al modelo, no el modelo. |
| **165** | Numeración de pruebas: **346–365** (20 pruebas → total **365**). | Continúa la numeración real de la Semana 20 (345). |
| **166** | Todo dato que se use para explorar o enseñar es **de demostración**, con marca visible en los notebooks y en la ficha (`origen_datos: demostración`); ninguna cifra se presenta como resultado de la tesis. | Regla 3 de `CONTEXTO_PROYECTO.md` («no presentar datos de ejemplo como reales») y honestidad en el ML (regla 13). |
| **167** | Commits **por fase** (8 fases: 6 de código+pruebas ya hechas, 1 de docs y 1 de cierre). | Cada fase deja la suite `ml` en verde; trazabilidad fina, como en la Semana 20. |
| **168** | **Correcciones al plan**: (a) `Auditoria.modulo` es `CharField(40)` → la exportación no necesita migración condición de módulos; (b) la «lista de 19 módulos» son los de permisos y **ya incluye Machine Learning** (siguen 55 permisos y 19 módulos; no pasa a 20); (c) la suite anterior cerró en 345, no 349 → toda la numeración se renumeró −4. | Confirmado en el código al empezar la semana; anotado para no repetir el error en la defensa. |

---

## 2. Exportación del dataset (`exportar_dataset`, HU-166)

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **169** | Comando `manage.py exportar_dataset --usuario N --origen-datos {real,demostracion} [--dry-run]` en `sistema/management/commands/`; la lógica reutilizable vive en `backend/ml/exportacion.py`. | Mismo patrón que `respaldo_bd`/`importar_historico`: consola en `sistema/`, lógica testeable aparte. |
| **170** | El usuario debe **existir, estar activo y su rol tener `ml.entrenar`** (sembrado en `usuarios.0002`; hoy solo Administrador). Sin permiso → `CommandError`. | Punto único de control, igual que el resto de comandos sensibles. |
| **171** | Carpeta de destino: **`ML_EXPORT_DIR` en el `.env`** (patrón de `RESPALDO_DIR`/`IMPORTACION_DIR`), con guarda que **rechaza la raíz del repositorio y cualquier subcarpeta suya**. | El archivo es dato sensible: fuera de Git, fuera de la nube, fuera de capturas. |
| **172** | **Orden con seguridad**: el CSV se arma en memoria → se calcula la huella SHA-256 → se registra el evento `EXPORTAR` del módulo «Machine Learning» (`detalle = {filas, origen_datos, sha256}`, **sin contenido**) → **si la auditoría falla, no se escribe el archivo**. | Espejo de la exportación de reportes («sin rastro no hay descarga», `reportes/views.py:195`). |
| **173** | **Ficha técnica** `ficha_dataset_*.json` junto al CSV: fecha de Lima (ISO 8601), filas, columnas, `sha256` de los bytes exactos, `origen_datos` y `semilla` (42). | Reproducibilidad: cualquiera comprueba que el archivo es el mismo y de qué semana es la semilla. |
| **174** | CSV en **UTF-8 con BOM** y punto decimal «.»; encabezado = `COLUMNAS_EXPORTADAS` en orden; NULL de la vista → celda vacía. | Se abre bien en Excel con tildes y ñ; el punto decimal no depende de la configuración regional. |
| **175** | `--dry-run` informa de filas, columnas, carpeta y origen **sin escribir nada y sin evento**. | Probar la consulta y la ruta sin efectos secundarios. |

---

## 3. Vista del dataset con identificadores

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **176** | Migración `importaciones.0003_vista_dataset_ids`: la vista suma `parcela_id` y `productor_id` (tras `campania_id`) para poder **agrupar la validación por productor** y trazar cada fila sin abrir la campaña. | Sin el productor no hay `GroupKFold` anti-fuga; con sus ids internos (nunca DNI ni nombres). |
| **177** | La migración es **reversible a la vista de la Semana 20** (`VISTA_S20` construida quitando las dos columnas; el WHERE no cambia); lo comprueba la prueba 349 subiendo y bajando de versión. | El diseño de Semana 20 queda a un `migrate` de distancia; nadie se queda sin plan B. |
| **178** | `DB_sql/02_reglas_y_vista.sql` (ignorado) se actualiza al mismo tiempo, con la nota de que **la predicción es de plan, no del ciclo**: al predecir de verdad, el clima del ciclo no existe (decisión 194 y `.tex`). | El SQL de referencia no puede contradecir a las migraciones ni al documento. |

---

## 4. Paquete `backend/ml/`

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **179** | `backend/ml/` es un **paquete plano, no una app de Django**: sin `models.py` ni migraciones; `manage.py test` lo descubre igual (verificado con la prueba 349). | La semana prohíbe tablas nuevas; la lógica de datos no necesita ORM. |
| **180** | `columnas.py`: **lista fija** `COLUMNAS_EXPORTADAS` (28) + `COLUMNAS_PROHIBIDAS`; la consulta se construye desde la lista, **nunca `SELECT *`**. | Si mañana la vista suma una columna, no sale del archivo hasta que alguien la declare aquí y en el catálogo (pruebas 350 y 352). |
| **181** | `catalogo.py`: **28 entradas** con `rol` (identificador, objetivo, predictor, metadato, cobertura, seguimiento, fuga), `conjuntos` (`plan` = Conjunto 1; `plan_clima` = Conjunto 2 con la advertencia de su clima inexistente), `cuando` y `observacion`. Lo que no está clasificado no se usa; `dias_ciclo` es **fuga** y jamás predice (pruebas 352–353). | El contrato anti-fuga más importante del ML: una sola tabla en código que el diccionario replica (decisión 192). |
| **182** | Supuestos del desarrollador marcados como tales: **cobertura de clima mínima 80 %** y **faltantes máximos 40 %**; el clima bajo cobertura se vacía (no se promedia a medias) y las columnas que superan el umbral salen del conjunto informando (pruebas 354–355). | Pendiente de confirmar con el responsable; se cambia en una constante. |
| **183** | `carga.py`: puerta de entrada de **cualquier consumidor** (notebooks, Sprint 13): valida columnas, tipos numéricos, identificadores enteros y texto; aplica la política de cobertura del catálogo (prueba 351). | Un CSV raro muere aquí, con su lista de columnas y filas, no en medio de un entrenamiento. |
| **184** | `limpieza.py`: **tabla de exclusiones declarativa** (`EXCLUSIONES`: motivo, condición, columnas, máscara). Solo se excluyen filas imposibles o sin objetivo (ids vacíos, superficie ≤ 0, altitud fuera de 0–6000 m, rendimiento vacío o ≤ 0); si una fila incumple dos, gana la primera; el resumen trae **solo conteos** (pruebas 356–357). | «Lo inusual no se excluye»: un rendimiento alto es un dato, no un error. La tabla es también la fuente de `docs/ml_preparacion.md`. |
| **185** | `preparacion.py`: `ColumnTransformer` **sin ajustar**: mediana y escalado de los numéricos se aprenden con `fit` **dentro del pliegue** (sin fuga); one-hot con `handle_unknown="ignore"` (una categoría nueva se ignora, no se inventa); categoría vacía = nivel propio; el **objetivo nunca se imputa ni se transforma**; falta un predictor del conjunto → error con su lista (pruebas 358–359). | La lección clásica de prep. de datos: ni la mediana ni la media de prueba tocan el entrenamiento. |
| **186** | `validacion.py`: **`GroupKFold` con grupos = `productor_id`**, `shuffle=True` y `random_state=42` (misma semilla de la ficha); cada productor cae entero en un lado; menos productores que pliegues → error claro (pruebas 360–361). | Un productor no puede estar en entrenamiento y prueba a la vez: sus parcelas se parecen y el modelo las memorizaría. |
| **187** | `linea_base.py`: predecir **la media del entrenamiento** (solo del entrenamiento) y evaluar con MAE y RMSE en kg/ha; la barra que cualquier modelo del Sprint 13 debe ganar en **cada** pliegue (prueba 362). | «La línea base es el modelo más tonto y por eso manda»: sin ella, cualquier métrica es ininterpretable. |

---

## 5. Notebooks e higiene

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **188** | Dos notebooks en `notebooks/`, versionados **sin salidas** (`outputs: []`, `execution_count: null`) y con `.ipynb_checkpoints/` en `.gitignore` (prueba 365). | El repositorio guarda el código, no los resultados; los resultados se regeneran. |
| **189** | Los notebooks **leen los datos de `ML_EXPORT_DIR`** (vía `.env` o el entorno) y usan la puerta `ml.carga.cargar`; **no llevan CSV dentro del repo** y no llaman `read_csv` a pelo (lo comprueba la prueba 365). | Un dataset no se versiona; el archivo vivo sale de `exportar_dataset`. |
| **190** | `01_exploracion.ipynb`: carga, faltantes, cobertura de clima, catálogo y distribución del objetivo (incluye un histograma). `02_preparacion.ipynb`: limpieza, Conjunto 1, pipeline, pliegues agrupados y línea base. **Ninguno entrena modelos.** | Explorar y preparar son las dos mitades del trabajo de datos; entrenar es Sprint 13. |
| **191** | Dependencias de notebooks en `backend/requirements-ml.txt` (`jupyter`, `matplotlib`), **fuera del `requirements.txt` de despliegue**. | El servidor de la app no necesita un kernel de Jupyter. |

---

## 6. Pruebas 346-365

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **192** | Bloque `backend/ml/tests.py` (20 pruebas) con `MLBase` (admin con `ml.entrenar`, coordinador sin él, geografía propia y helpers de API/BD/vista copiados del patrón de `dashboard/tests.py`). | Mismo aislamiento y mismo estilo que el resto del repositorio. |
| **193** | Reparto: 346–348 exportación (permisos, ruta, ficha, auditoría, dry-run), 349 vista+reversibilidad, 350–351 columnas y carga, 352–355 catálogo y fuga, 356–357 limpieza, 358–359 pipeline sin fuga, 360–361 validación agrupada, 362 línea base, 363–364 esquema intacto (**29 tablas de dominio y 25 triggers**, mismas consultas que `sistema/tests_entrega1.py`), 365 notebooks limpios. | Cubre cada decisión de este documento con una prueba que la pueda contradecir. |
| **194** | Las pruebas de exportación redirigen `ML_EXPORT_DIR` con `patch.dict(os.environ, …)` a un `tempdir`; la carpeta real (`D:\MLDatasetSigpa`) no se toca. | Igual que `IMPORTACION_DIR` en la Semana 20 (prueba 153). |

---

## 7. Documentación, `.tex` y cierre

| Nº | Archivo | Descripción |
|----|---------|-------------|
| **195** | `docs/ml_preparacion.md` | Guía del flujo completo: exportar → cargar → limpiar → conjuntos → pipeline → validar → línea base, con la tabla de exclusiones y los comandos. |
| **196** | `docs/diccionario_variables.md` | Las 28 columnas con rol, conjuntos, cuándo se conoce y observación (espejo del catálogo; cualquier cambio toca los dos). |
| **197** | `docs/dataset.md` (sección «Semana 21») | Identificadores de la vista y el momento de predicción (hecha en la Fase 1). |
| **198** | `backend/ml/README.md` | Mapa del paquete y orden de llamadas para quien llegue al código. |
| **199** | `docs/evidencias_capitulo4.md` y `CONTEXTO_PROYECTO.md` | Sección de ML del capítulo 4; contexto actualizado (vista, paquete, 29 tablas, pendientes). |
| **200** | `requerimientos.tex` (v1.4, **sin subir versión**) | Corrección del **momento de predicción**: la predicción es **al planificar el cultivo** («plan de manejo»), no «durante la campaña»; se ajusta el párrafo general y el ejemplo del Random Forest. |
| **201** | Suite completa **365/365** + `migrate` desde cero + `makemigrations --check` + lint/build del frontend + newman de la colección, al cierre de la fase final. | Puertas de calidad del cierre de semana. |

---

## 8. Preguntas abiertas para el responsable (recopiladas en un solo mensaje)

> El tablero venía pidiendo «enviar en un solo mensaje con fecha límite»;
> esta tabla es ese mensaje. Las nuevas de esta semana llevan la letra
> que les asignó el plan de la Semana 21 (**U** y **V**), con su nota de
> colisión, al estilo de la **R** de la Semana 18.

| Letra | Pregunta | Estado / propuesta |
|-------|----------|--------------------|
| **A** | ¿Entregó la lista real de provincias, distritos y comunidades? | Pendiente desde la Semana 3; rige `datos/ejemplo_ubicaciones.csv` (marcado como inventado). |
| **B** | Confirmar la regla de **enmascarado de DNI/teléfono** por rol. | Rige la propuesta: Administrador y Técnico completos, Coordinador enmascarado. |
| **D** | Botón «usar mi ubicación actual». | Solo funciona en `https://` o `localhost`; decidir en la demo. |
| **F** | ¿Las fechas de campaña deben caer dentro de su período? | Rige el rango 1 ene año₁–31 dic año₂ validado en la API (y en etapas). |
| **G** | ¿Bloquear la desactivación de productor/parcela con campañas activas? | Implementado con mensaje de error (HU-45/46). |
| **H** | ¿Rechazar fechas futuras en actividades? | Implementado (`fecha ≤ hoy`, hora de Lima); afecta a la colección de Postman. |
| **I** | ¿Unidad de densidad de siembra (kg/ha, plantas/m² o ambas)? | Implementadas **las dos** del diseño; la API exige valor+unidad. |
| **J** | ¿La producción registrada es bruta o neta de la pérdida? | Rige **bruta**; `perdida_kg` se guarda aparte y no descuenta. |
| **K** | ¿Umbrales de revisión, factor del quintal y umbral de helada? | Rigen los del diseño (100 / 5000 / 800 / 30 días / 46 kg / 0 °C); configurables en `/parametros`. |
| **L** | ¿Costo de recursos: registro o cálculo? | Rige registro por uso, sin agregar en resúmenes. |
| **M** | ¿Open-Meteo como fuente del clima? | Implementado con `archive-api` (sin clave); el adaptador es un solo archivo (`servicio_meteorologico.py`). |
| **N** | ¿Criterio para la severidad de la incidencia (BAJA/MEDIA/ALTA)? | Rige que **quien registra elige**. |
| **O** | ¿Relajar la coherencia cronológica de etapas? | La regla (orden del catálogo, con saltos) se valida **solo en la API** para poder relajarla sin migraciones. |
| **P** | ¿Restablecer la propia contraseña desde la UI? | ~~Cerrada en la Semana 13~~ (`cambiar-clave/`, RF-73/HU-112). |
| **Q** | ¿Auditar también las lecturas? | Sin implementar a propósito (la traza es de acciones, RF-71). |
| **R** (histórica) | ¿Expiración/purgado de la auditoría? | Sin implementar; recomendar por lotes o partición por fecha cuando el volumen lo pida. |
| **S** | ¿Aceptar X-Forwarded-For en la auditoría tras desplegar con proxy? | Hoy solo `REMOTE_ADDR`; con proxy de confianza, decidir si se acepta XFF **solo para auditoría**. |
| **T** | ¿Cambiar «limita a asignados» de un rol que ya tiene usuarios? | Rige **NO** (reescribiría qué ve cada usuario autenticado; prueba 227). |
| **R** (nueva, S18) | ¿Membrete (logo) en el PDF? | Sin cambios; si se pide, se añade en `reportes/pdf.py`. Colisiona con la R histórica: las dos siguen anotadas. |
| **V** (S17) | ¿Los reportes descargables pueden incluir DNI? | Implementado **sin** DNI/teléfono/`registrado_por`; si se pide, se añade como columna fija. |
| **U** (**nueva, S21**) | **¿En qué momento se predice el rendimiento?** | Propuesta de esta semana: **al planificar el cultivo** («plan de manejo»: superficie, variedad, densidad, insumos y clima estimado). El Conjunto 2 usa el clima del ciclo completo solo como comparación — al predecir de verdad ese clima **no existe**. Colisiona con la U de la Semana 16 (reglas de la semana, resuelta); aquí queda como U de ML. |
| **V** (**nueva, S21**) | **¿Qué error es útil para el productor?** | Propuesta: enseñar el rango **±200 kg/ha** (y nunca un único número suelto). Sin esta cifra no se puede discutir si un modelo sirve. Colisiona con la V de la Semana 17 (DNI en reportes); las dos quedan anotadas. |
| — | ¿Las 12 etapas fenológicas de Quinua y Cañihua cargadas en la Semana 5? | **CONFIRMAR** (catálogo sembrado con `cargar_catalogos`). |
| — | Veto posible a los **dos botones** de exportación de `/auditoría`. | En el radar del tablero; ningún cambio previsto. |
| — | ¿Cuándo se necesita el sistema funcionando y cuál es la fecha límite de sustentación? | Abierta desde semanas tempranas; define el ritmo del Sprint 13. |

### Nota de letras

Las letras **A..V** están usadas (A..S en `cierre_semana12.md` §1.4 y
`decisiones_semana13.md` §1.4; **T** en `decisiones_semana15.md`; **U**
en `decisiones_semana16.md`; **V** en `decisiones_semana17.md`; **R**
nueva en `decisiones_semana18.md`). Esta semana el plan asignó **U** y
**V** a las dos preguntas nuevas de ML, sabiendo la colisión (mismo
criterio que la R de la Semana 18): las cuatro quedan anotadas en sus
documentos. **Siguiente letra libre: W.**

---

## 9. Notas de contexto

- **Mapeo HU de la semana**: el plan la ancló a **HU-166** (exportación
  del dataset con ficha y auditoría) y al trabajo de datos previo al
  modelo; los HU-167/168 aparecen en los docstrings de `carga.py` como
  la puerta de validación del archivo. El modelo en sí **no** se toca.
- **Lo que NO se hizo a propósito**: API de predicción, pantalla de
  «Predicción», entrenamiento de modelos (Random Forest u otros),
  tabla de predicciones y métricas contra datos reales. Todo eso es
  Sprint 13, y se apoya sobre esta semana.
- **Pruebas**: 365 en total al cierre (`manage.py test`); las de la
  semana son las 346–365 (`backend/ml/tests.py`).
- **Semilla**: `SEMILLA = 42` vive en `ml/exportacion.py`; la ficha la
  registra y `ml/validacion.py` la usa para el corte de pliegues. Un
  solo número para toda la semana.
- **Cómo se genera un dataset real de demostración**:
  `manage.py exportar_dataset --usuario admin --origen-datos demostracion`
  (previo: campañas CERRADA con `incluir_en_entrenamiento`). Los notebooks
  leen ese archivo de `ML_EXPORT_DIR`.
- **Docker**: la semana se desarrolló con el contenedor `sigpa_db` en
  marcha; una sesión larga puede apagar Docker Desktop — si la BD no
  responde, se arranca de nuevo antes de tocar código (lección de esta
  semana).
