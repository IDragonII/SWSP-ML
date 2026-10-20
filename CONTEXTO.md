# Contexto del proyecto SIGPA-GA

## Visión general
SIGPA-GA (Sistema de Información y Gestión de la Producción Agropecuaria — Granos Andinos) es una aplicación web para el seguimiento de productores de granos andinos (quinua, cañihua, tarwi) en Puno, Perú, con módulo de Machine Learning para predicción de rendimiento.

**Stack**: React (frontend) + Django REST Framework (backend) + PostgreSQL 17 (Docker).
**Metodología**: Scrum, sprints de 2 semanas. Semana actual: **21**.

---

## Estado por semana

### Semana 1–3 (Fase 1 base)
- Autenticación JWT (access/refresh en cookies httpOnly), 3 roles (Administrador, Coordinador, Técnico de campo).
- Catálogos: cultivos, variedades, provincias/distritos/comunidades, tipos de actividad, recursos, unidades, incidencias, etapas fenológicas.
- CRUD productores/parcelas (modales, código auto, DNI único 8 dígitos).
- API paginada (`API_PAGE_SIZE=20`), componente `Tabla` responsive (≤860 px → tarjetas).

### Semana 4–6 (Campañas y actividades)
- Campañas: estados (PLANIFICADA → EN_PRODUCCION → COSECHADA → CERRADA / CANCELADA), una activa por parcela (`uq_campania_activa_por_parcela`), una por parcela+período excluyendo CANCELADA (`uq_campania_parcela_periodo`).
- Actividades: 7 tipos (PREPARACION, SIEMBRA, FERTILIZACION, CONTROL_FITOSANITARIO, RIEGO, DESHIERBO, COSECHA); densidad solo en siembra; anulación lógica.
- Recursos/insumos con conversión a unidad base; costos informativos.
- Validaciones de fecha dentro del período de la campaña (trigger `fn_validar_fecha_campania`).

### Semana 7–9 (Clima, incidencias, producción)
- Clima: registro manual por parcela+día (único), rangos, temp_min ≤ temp_max, promedio coherente, helada derivada.
- Incidencias: tipos, severidad, superficie afectada ≤ sembrada, anulación lógica.
- Producción: fecha cosecha ≥ siembra, rendimiento = kg/ha (trigger `fn_validar_produccion` recalcula siempre), atípicos con marca de revisión + decisión admin.
- Alertas (Semana 9): generación por incidencia severa, campaña sin actividades (30 días), rendimiento predicho bajo umbral; gracia + barrido diario; **sin triggers en BD** (decisión Semana 15 §1.1).

### Semana 10–12 (Seguimiento, dashboard, reportes)
- Etapas fenológicas: una por campaña, cronología, validación por cultivo.
- Dashboard: indicadores (productores, superficie, campañas por estado, producción/rendimiento por cultivo/distrito), alertas, productores en riesgo.
- Reportes: productores, productivo, predicciones, actividades, modelos ML, auditoría; exportación PDF/Excel.
- Importación histórica desde Excel/CSV con plantilla y reporte de errores.

### Semana 13–14 (Machine Learning y calidad)
- Dataset: vista `vw_dataset_entrenamiento` (campañas CERRADA con producción e `incluir_en_entrenamiento=TRUE`).
- Modelos: regresión lineal, Random Forest, Gradient Boosting; métricas MAE, RMSE, R²; versión + fecha + n_registros.
- Predicción vs realidad: comparación tras cierre de campaña.
- Matriz de reglas de calidad (RN-01…RN-16) con cruce API/BD/pruebas (M236–M241). 262/262 OK.

### Semana 15–16 (Alertas, auditoría, demo)
- Alertas: 13 ganchos `on_commit` + comando `evaluar_alertas`; endpoint evaluación con aviso 36 h.
- Auditoría: registro inmutable (usuario, acción, módulo, tabla, registro_id, IP, detalle, fecha).
- Datos de demostración V1 (5 prod, 5 parc, 5 camp) + V2 (5 prod con ñ/tildes/canario, 10 parc, 20 camp en 2 períodos, 10 prod, 4 act).

### Semana 17–18 (Reportes nuevos, auditoría UI, colección API)
- V3 demo: 6 actividades para reporte RF-68 (PREPARACION/SIEMBRA, horas, método, densidad, una anulada, una sin horas, una campaña creada+actividad+cancelada) + 8 eventos auditoría (LOGIN×2, CREAR, MODIFICAR, ANULAR, CAMBIAR_CLAVE, EXPORTAR×2).
- Colección Postman `coleccion_api_semana18.json` (tests `test` + `pm.environment.set`).
- Verificación UI navegador (`docs/verificacion_ui_semana4.md`).

### **Semana 19 — Entrega 1**
**Objetivo**: pruebas E2E, seguridad, respaldo/restauración, rendimiento, docs, cierre.

#### Pruebas nuevas (318–325)
| Nº | Prueba | Archivo/Clase |
|----|--------|---------------|
| 318 | Recorrido E2E 3 roles | `RecorridoCompletoTests.test_318_recorrido_completo_tres_roles` |
| 319 | Matriz rutas por rol | `MatrizRutasTests.test_319_matriz_rutas_por_rol` |
| 320 | Anónimo sin acceso | `SeguridadTests.test_320_anonimo_sin_acceso` |
| 321 | `check --deploy` limpio | `SeguridadTests.test_321_check_deploy_cero_avisos` |
| 322 | Error 500 sin trazas | `SeguridadTests.test_322_error_500_sin_trazas` |
| 323 | Logs limpios | `SeguridadTests.test_323_registros_limpios` |
| 324 | Rendimiento volumen | `RendimientoTests.test_324_rendimiento_con_volumen_reducido` |
| 325 | Respaldo/restauración | `RespaldoTests.test_325_migraciones_desde_cero_respaldo_y_restauracion` |

#### Comandos nuevos
- `matriz_rutas` → genera `docs/matriz_rutas_por_rol.md` (107 rutas × 5 métodos × 3 roles).
- `respaldo_bd` → vuelca BD a `RESPALDO_DIR` (fuera del repo) con `--clean --if-exists`, poda `RESPALDO_KEEP`.
- `datos_volumen` → siembra 500 prod / 1 000 parc / 1 200 camp / 20 000 act / 100 000 clima (idempotente).

#### Módulos nuevos
- `sistema/matriz_rutas.py` — introspección `actions ∩ http_method_names` + permisos por rol.
- `sistema/respaldo.py` — `volcar_bytes()`, `restaurar()`, `crear_bd()`, `eliminar_bd()` (Docker `pg_dump`/`psql`).

#### Configuración producción
- Bloque `PRODUCCION` en `settings.py` (env `PRODUCCION=1`): HSTS, cookies secure, SSL redirect, proxy header.
- `ADMIN_URL` configurable (env `ADMIN_URL`, default `admin/`).
- `JWT_COOKIE_SECURE=True` en producción.

#### Seguridad verificada
- `AllowAny` solo en login/refresh/logout.
- Anónimo → 401 en todo lo demás × 5 métodos.
- `check --deploy` 0 avisos con `DEBUG=False`, `PRODUCCION=1`, `SECRET_KEY` ≥50 chars, `ADMIN_URL` no default.
- Excepción interna (`DEBUG=False`) → 500 sin trazas.
- Logger `sigpa.seguridad`: sin contraseñas, sin JWT (`eyJ`), sin `SECRET_KEY`; con `login_correcto`.
- `pip-audit` / `npm audit` / `gitleaks` → 0 vulnerabilidades / 0 secretos (1 FP en fixture de test).

#### Documentos generados/actualizados
- `docs/seguridad_entrega1.md` — informe completo F2.
- `docs/matriz_rutas_por_rol.md` — 552 líneas (viva, test 319 la exige).
- `docs/rendimiento_entrega1.md` — medición test 324 + extrapolación.
- `docs/limitaciones_conocidas.md` — huecos §3 matriz + alertas sin triggers.
- `docs/resumen_pruebas_entrega1.md` — tabla 318–325.
- `docs/decisiones_semana19.md` — 48 decisiones (69–116).
- `requerimientos.tex` v1.3 — versión + §2 agregados + §3 limitaciones.
- `CONTEXTO.md` — este archivo (actualizado Semana 19).

#### Próximos pasos (post-Entrega 1)
1. Ejecutar suite completa (325) + lint/build → commit «semana 19» + tag `entrega-1`.
2. Grabar video 5 min (login 3 roles, ciclo campaña, dashboard/alertas, respaldo, seguridad, rendimiento).
3. Retrospectiva: matriz viva, tests E2E, respaldo canonizado ✅; volumen en BD limpia, alertas con triggers ⏳.

---

### **Semana 20**
**Objetivo**: terminar la importación histórica (RF-49/RF-50) y el dataset (RF-51) con pruebas 326–345, docs y `.tex` v1.4. Cero UI.

#### Pruebas nuevas (326–345 → total 345)
| Nº | Prueba | Archivo/Clase |
|----|--------|---------------|
| 326–327 | Plantillas xlsx (encabezados, fila EJEMPLO) | `importaciones/tests.py` · `PlantillaTests` |
| 328–329 | Lectura CSV/XLSX (delimitador, BOM, límites) | `LecturaTests` |
| 330–331 | Normalización (fechas, DNI 7→8, mascarado) | `NormalizacionTests` |
| 332–333 | Productores (creación, idempotencia, catálogos) | `ProductoresTests` |
| 334 | Parcelas (`;`, coma decimal, trigger de código) | `ParcelasTests` |
| 335–337 | Campañas (producción, atípica, recursos) | `CampaniasTests` |
| 338–343 | Comando (permiso, dry-run, EN_PROCESO/--forzar, informe, auditoría, evaluar_todo) | `ComandoTests` |
| 344–345 | Dataset (NULLs de importadas, ventana, WHERE) + end-to-end con `docs/ejemplos_importacion/` | `DatasetTests` |

#### Comando nuevo
- `importar_historico` → `--tipo/--archivo/--usuario` (+ `--dry-run`, `--forzar`, `--plantilla/--salida`); permiso `importacion.ejecutar`; informe CSV en `IMPORTACION_DIR` sin datos personales.

#### Módulos nuevos
- App `backend/importaciones/`: `plantillas.py`, `servicio.py`, `models.Importacion`, `management/commands/importar_historico.py`.
- `campanias.origen` (SISTEMA/IMPORTADA) + `catalogos.0003` (4 recursos genéricos totales históricos).
- Fix `productores.0005`: `fn_codigo_parcela`/`fn_codigo_productor` sin truncar (`lpad` recortaba códigos ≥1000).

#### Documentos generados/actualizados
- `docs/importacion_historica.md` — guía de uso del comando.
- `docs/dataset.md` — `vw_dataset_entrenamiento` (fuentes, columnas, NULLs).
- `docs/decisiones_semana20.md` — decisiones 117–163.
- `docs/ejemplos_importacion/*.csv` — 3 archivos de ejemplo (los cubre la prueba 345).
- `requerimientos.tex` v1.4 — versión + RF-50/RF-51 ajustados.
- `CONTEXTO.md` — este archivo (actualizado Semana 20).

---

### **Semana 21**
**Objetivo**: preparación de datos para Machine Learning (Sprint 12) — comando `exportar_dataset`, paquete `backend/ml/`, notebooks y docs; pruebas **346–365**. Sin API, UI, tablas nuevas ni entrenamiento.

#### Pruebas nuevas (346–365 → total 365)
| Nº | Prueba | Archivo/Clase |
|----|--------|---------------|
| 346–348 | Comando `exportar_dataset` (permiso `ml.entrenar`, dry-run, ficha con SHA-256) | `ml/tests.py` · `ExportarTests` |
| 349 | Vista con `parcela_id`/`productor_id` reversible | `VistaTests` |
| 350–351 | Columnas fijas sin datos personales; carga (faltantes/desconocidas/tipos) | `ColumnasTests` / `CargaTests` |
| 352–355 | Catálogo de 28 variables, conjuntos sin fuga, supuestos 80 %/40 % | `CatalogoTests` |
| 356–357 | Tabla de exclusiones y resumen del waterfall | `LimpiezaTests` |
| 358–359 | Mediana dentro del pliegue; one-hot ignora desconocidas | `PreparacionTests` |
| 360–361 | GroupKFold por `productor_id`, semilla 42, sin productor compartido | `ValidacionTests` |
| 362 | Línea base = media del entrenamiento (MAE/RMSE kg/ha) | `LineaBaseTests` |
| 363–365 | Higiene: 29 tablas de dominio, 25 triggers, notebooks sin salidas | `HigieneTests` |

#### Comandos y módulos nuevos
- `sistema/management/commands/exportar_dataset.py` → CSV + ficha JSON a `ML_EXPORT_DIR` (fuera del repo), auditoría `EXPORTAR` del módulo «Machine Learning» **antes** de escribir.
- Paquete plano `backend/ml/`: `columnas`, `catalogo`, `carga`, `limpieza`, `preparacion`, `validacion`, `linea_base`, `exportacion` (semilla 42 única).
- `importaciones.0003` → vista `vw_dataset_entrenamiento` con `parcela_id`/`productor_id` (reversible a la de Semana 20).
- `notebooks/01_exploracion.ipynb` y `02_preparacion.ipynb` (sin salidas, marca demostración); `.ipynb_checkpoints/` en `.gitignore`.

#### Documentos generados/actualizados
- `docs/decisiones_semana21.md` — decisiones 164–201 + **preguntas abiertas A..V en un solo mensaje** (U = momento de predicción, V = error útil ±200 kg/ha).
- `docs/ml_preparacion.md`, `docs/diccionario_variables.md` (espejo del catálogo), `docs/dataset.md` §Semana 21, `backend/ml/README.md`.
- `docs/evidencias_capitulo4.md` — actualizadas a Semana 21 (365/365).
- `backend/requirements-ml.txt` — jupyter + matplotlib (fuera del despliegue).

---

### **Semana 22** (actual)
**Objetivo**: cerrar el sistema con Machine Learning (Sprint 12, variante 1 semana / 36 h) — modelos con criterio escrito, servicio + API + pantallas React, pruebas **366–392 (total 392)**, colección **598/598 (1125/1125 aserciones)**, manuales y limitaciones. HU-169..HU-179; decisiones 202–248 (`docs/decisiones_semana22.md`).

#### Pruebas nuevas (366–392 → total 392)
| Nº | Prueba | Archivo/Clase |
|----|--------|---------------|
| 366–368 | Entrenamiento reproducible, criterio escrito, `.joblib` recargable | `ml/tests.py` · `EntrenamientoTests` |
| 369–371 | `registrar_modelo`: 1 entrenamiento + 3 modelos, validaciones, un solo activo | `RegistroTests` |
| 372–380 | Servicio: variables de la vista, huella y recarga, estados válidos, prioridad del plan, avisos, resultado, comparación al cosechar/deshacer, confiabilidad BAJA, marca de demostración | `ServicioTests` |
| 381–387 | API: permisos/escrituras rechazadas, ficha sin DNI, alcance del Técnico, Coordinador, límite 30/hora, contrato de activo/campañas, activar por API | `ApiTests` |
| 388 | Migraciones: 3 tablas ML, **32 tablas de dominio** y 25 triggers | `MigracionesTests` |
| 389 | Recorrido completo punta a punta (registro → predicción → comparación → deshacer) | `RecorridoTests` |
| 390–392 | Entrega sana: migraciones reversibles sin cambios, lint/build del frontend, manifiesto de archivos ML | `EntregaTests` |

#### Comandos y módulos nuevos
- App Django **`backend/ml/`** (antes paquete plano): modelos `entrenamientos_ml`, `modelos_ml`, `predicciones`; servicio `prediccion.py`; API `ModeloViewSet`, `PrediccionViewSet` (con auditoría) y comparación al cosechar.
- Comandos: **`entrenar_modelos`** (3 candidatos + criterio → `ml_models/`), **`registrar_modelo`** (`--version-modelo`, `--desarrollo`, `--activar`; huella SHA-256 y predicción de prueba antes de tocar la BD), **`datos_ml_demostracion`** (CSV inventado con marca; 48 filas, semilla 42).
- `produccion/0003` → `fn_produccion_post` completa: al cosechar guarda rendimiento real y error (absoluto y %) en la predicción pendiente; reversible.
- Pantallas React: **`/predicción`** (`Prediccion.jsx`), **`/predicciones`** (historial con pestañas y comparación) y **`/modelos`** (`ModelosMl.jsx`), con banner de demostración y MAE junto al resultado.

#### Documentos generados/actualizados
- `docs/decisiones_semana22.md` — decisiones 202–248 + preguntas U/V/I/J/K/L/M/T/Nueva V.
- `docs/api_ml.md`, `docs/criterio_seleccion.md` (criterio **antes** de entrenar), `docs/informe_resultados_ml.md` (lo genera `entrenar_modelos`), `docs/coleccion_api_semana22.json` (598).
- `docs/manual_usuario.md` (por rol) y `docs/manual_tecnico.md` (HU-179); `docs/limitaciones_conocidas.md` ampliado (§5 ML); `docs/matriz_rutas_por_rol.md` regenerada; `docs/evidencias_capitulo4.md` — actualizadas a Semana 22 (392/392, 598/598). `requerimientos.tex` **v1.5** (externo, cambios documentados en decisiones).

---

## Archivos clave

| Archivo | Descripción |
|---------|-------------|
| `backend/config/settings.py` | Configuración Django (bloque PRODUCCION, LOGGING, JWT_COOKIE_SECURE). |
| `backend/config/urls.py` | `ADMIN_URL` env + 12 includes bajo `api/`. |
| `backend/sistema/tests_entrega1.py` | Pruebas 318–325 (base `Entrega1Base`). |
| `backend/sistema/matriz_rutas.py` | Generación de matriz de rutas por rol. |
| `backend/sistema/respaldo.py` | Núcleo de respaldo/restauración (Docker). |
| `backend/sistema/management/commands/*.py` | `matriz_rutas`, `respaldo_bd`, `datos_volumen`, `datos_demostracion`, `exportar_dataset`, `entrenar_modelos`, `registrar_modelo`, `datos_ml_demostracion`. |
| `backend/importaciones/` | App importación histórica: `plantillas.py`, `servicio.py`, `importar_historico`, `tests.py` (326–345), migraciones `0001`–`0003` (vista dataset con ids, Semana 21). |
| `backend/ml/` | App ML (Semana 21 paquete plano → Semana 22 app): `catalogo.py`, `columnas.py`, `carga.py`, `limpieza.py`, `preparacion.py`, `validacion.py`, `linea_base.py`, `exportacion.py`, `criterio.py`, `entrenamiento.py`, `guardado.py`, `prediccion.py`, `registro.py`, `models.py`/`views.py`/`serializers.py` (API), `tests.py` (346–392), migración `0001` (3 tablas). |
| `backend/ml_models/` | Artefactos versionados: `<algoritmo>_v<N>.joblib` elegido, `resultados_v<N>.json`, `manifiesto.json` (SHA-256). |
| `frontend/src/pages/` | `Prediccion.jsx`, `PrediccionHistorial.jsx`, `ModelosMl.jsx` (Semana 22). |
| `backend/sistema/management/commands/exportar_dataset.py` | Exporta el dataset a `ML_EXPORT_DIR` (CSV + ficha JSON + auditoría). |
| `notebooks/` | `01_exploracion.ipynb` y `02_preparacion.ipynb` (Semana 21, sin salidas). |
| `docs/decisiones_semana21.md` | Decisiones 164–201 + preguntas abiertas recopiladas. |
| `docs/decisiones_semana22.md` | Decisiones 202–248 (ML end-to-end, HU-169..179). |
| `docs/api_ml.md` · `docs/criterio_seleccion.md` · `docs/informe_resultados_ml.md` | Contrato de la API de ML, criterio escrito antes de entrenar e informe generado. |
| `docs/manual_usuario.md` · `docs/manual_tecnico.md` | Manual por rol y manual de instalación/operación (HU-179). |
| `docs/ml_preparacion.md` · `docs/diccionario_variables.md` | Flujo ML y diccionario de las 28 variables. |
| `docs/coleccion_api_semana22.json` | Colección final: 598 peticiones (574 S18 + 24 ML), validada 598/598. |
| `docs/importacion_historica.md` | Guía de uso de `importar_historico`. |
| `docs/dataset.md` | `vw_dataset_entrenamiento`: fuentes, columnas, NULLs de importadas. |
| `docs/decisiones_semana20.md` | Decisiones 117–163. |
| `D:\ProyectoJoseLuis\Documentos\Requerimeintos\requerimientos.tex` | v1.5 (Semana 22: RF-52..RF-61, momento de predicción, control de cambios). |
| `docs/matriz_reglas_calidad.md` | RN-01…RN-16 + agregados (§2) + huecos (§3) + alertas. |
| `.env` | `SECRET_KEY`, `DB_*`, `RESPALDO_DIR`, `ML_EXPORT_DIR`, `DB_DOCKER_CONTAINER`, `PRODUCCION`, `ADMIN_URL`. |
| `docker exec sigpa_db …` | Vía real a `pg_dump`/`psql`/`createdb`/`dropdb` (contenedor `sigpa_db`, user `sigpa_user`). |

---

## Decisiones transversales (vigentes)

1. **Responsive siempre** (decisión 14, Semana 4): ≤860 px → tarjetas.
2. **Rueda de carga en botón** (AGENTS.md §1): botón `disabled` + `RuedaCarga` con `aria-label`.
3. **Todo formulario en Modal** (AGENTS.md §2): nunca página/ruta nueva; permisos en el botón.
4. **Todo tabla usa `Tabla`** (AGENTS.md §3): nunca `<table>` a mano; `scope="col"`, `data-rotulo`, `celda-acciones`.
5. **Validación colección API** (decisión 40, Semana 16): solo `test` y `pm.environment.set`.
6. **UI**: `Campo` wrapper, `useToast()` → `avisar`, `useSesion()` → `tienePermiso`.
7. **Numeración pruebas**: Semana 18 = 317; Semana 19 = 318–325; Semana 20 = 326–345; Semana 21 = 346–365; Semana 22 = 366–392.
8. **Commit único por semana** + tag al final (decisión 72); **excepción Semana 20**: commit por fase (3 en total, decisión 119); **Semana 21**: commits por fase (6 de código + docs + cierre); **Semana 22**: commits por fase (F0–F6).