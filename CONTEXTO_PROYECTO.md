# SIGPA-GA · Contexto completo del proyecto

> **Para qué sirve este archivo.** Reúne todo lo decidido y construido hasta ahora: qué es el proyecto, la arquitectura, las 32 tablas (y por qué existe cada una), los triggers, las reglas de negocio y lo que falta. Está pensado para que un agente de IA (o una persona nueva) entienda el proyecto sin tener que leer toda la conversación previa.
>
> **Regla de oro:** si algo no está aquí o está marcado como *por confirmar*, no se inventa: se pregunta.

## Índice

1. [Qué es el proyecto](#1-qué-es-el-proyecto)
2. [Decisiones técnicas tomadas](#2-decisiones-técnicas-tomadas)
3. [Estado actual](#3-estado-actual)
4. [Cómo funciona el sistema (flujo de datos)](#4-cómo-funciona-el-sistema-flujo-de-datos)
5. [Base de datos: las 32 tablas](#5-base-de-datos-las-32-tablas)
6. [Triggers, funciones y restricciones](#6-triggers-funciones-y-restricciones)
7. [La vista del dataset de Machine Learning](#7-la-vista-del-dataset-de-machine-learning)
8. [Roles y permisos](#8-roles-y-permisos)
9. [Datos iniciales (seeds)](#9-datos-iniciales-seeds)
10. [Qué NO hace la base de datos (trabajo de la aplicación)](#10-qué-no-hace-la-base-de-datos-trabajo-de-la-aplicación)
11. [Plan de Machine Learning](#11-plan-de-machine-learning)
12. [Cómo pasar el diseño SQL a Django](#12-cómo-pasar-el-diseño-sql-a-django)
13. [Metodología y hoja de ruta (Scrum)](#13-metodología-y-hoja-de-ruta-scrum)
14. [Pendientes y preguntas abiertas](#14-pendientes-y-preguntas-abiertas)
15. [Instrucciones para agentes de IA](#15-instrucciones-para-agentes-de-ia)
16. [Índice de archivos y glosario](#16-índice-de-archivos-y-glosario)

---

## 1. Qué es el proyecto

**Título:** Sistema web para el seguimiento de productores con algoritmos de Machine Learning en el Proyecto de Mejora Agroproductiva de Granos Andinos en Puno – 2025.

**Nombre corto del sistema:** SIGPA-GA.

**Objetivo general.** Desarrollar e implementar un sistema web de seguimiento y control para los productores de granos andinos en la región Puno, utilizando algoritmos de Machine Learning.

**Objetivos específicos.**
1. Diseñar un sistema web que permita el monitoreo continuo y actualizado de las actividades productivas de los agricultores, integrando datos climáticos, rendimiento de cultivos y recursos utilizados.
2. Desarrollar algoritmos de Machine Learning que permitan predecir los rendimientos de los cultivos de granos andinos.

**Contexto de trabajo.**
- La tesis es de otra persona (el **responsable del proyecto**, que actúa como *Product Owner*). El desarrollador es **Ivan Rony Condori Inquilla**.
- El desarrollo sigue **Scrum**, con sprints de dos semanas y **sin fecha límite definida**; el calendario es referencial.
- El responsable del proyecto tiene que poder entender y defender el sistema ante un jurado, por lo que se documenta todo.

**Enfoque en dos componentes y tres fases.**

| Fase | Contenido |
|---|---|
| 1. Sistema de seguimiento | Se construye primero. Recolecta datos de forma estructurada y validada. |
| 2. Dataset | Importación de datos históricos y vista de entrenamiento (una fila por campaña cerrada). |
| 3. Machine Learning | Preparación, entrenamiento, evaluación, integración y comparación predicción vs. realidad. |

> **Idea central:** el sistema web es la herramienta de recolección y el ML es la capa que aprovecha lo recolectado. La calidad del modelo depende directamente de la calidad de los datos, por eso las validaciones son un requisito central y no un detalle.

---

## 2. Decisiones técnicas tomadas

| Tema | Decisión |
|---|---|
| Backend | **Python 3.13 + Django 5.2 LTS + Django REST Framework** (API REST que devuelve JSON) |
| Autenticación | JWT con `djangorestframework-simplejwt`: access y refresh en **cookies httpOnly** con rotación y blacklist (`docs/decisiones_seguridad.md`) |
| CORS | `django-cors-headers` (React corre en `http://localhost:5173`) |
| Variables de entorno | `python-dotenv`, un único archivo `.env` en la raíz (no se sube a Git) |
| Frontend | **React con Vite** (JavaScript), Axios, React Router |
| Base de datos | **PostgreSQL 17 en Docker** (`docker-compose.yml` en la raíz) |
| ML | Python: pandas, scikit-learn, joblib. Va **dentro del mismo backend Django**, sin servicio aparte |
| Entrenamiento | Primero en notebook (local) y se sube el archivo `.joblib`; reentrenar desde el sistema es opcional y posterior |
| Documentos | LaTeX, compilados con **XeLaTeX** (TeXstudio) |
| Entorno | Windows + PowerShell. Python viene de Laragon; el proyecto usa `venv` propio |
| Ruta del proyecto | `D:\ProyectoJoseLuis\Sistema` (`backend/` y `frontend/` dentro) |
| Despliegue | **Aún no decidido.** Se verá con el responsable del proyecto, con el sistema ya funcionando |
| Seguridad adicional | **Limitación de intentos fallidos de login (*rate limit*) es esencial**, y se implementa en el backend (no en la BD) |
| Primer usuario administrador | `python manage.py crear_superusuario`, que lee `ADMIN_USERNAME` / `ADMIN_PASSWORD` del `.env`. Es idempotente y **nunca** se hardcodean credenciales en el código ni en Git |

**Por qué Django y no Laravel.** El desarrollador conoce Laravel, pero Django deja todo el backend y el ML en un solo lenguaje, evita un servicio extra en Python y simplifica el despliegue. Se eligió Django asumiendo el costo de aprender el framework.

**Decisiones de diseño de datos (vigentes).**
1. La **campaña** es la entidad central: una parcela + un cultivo + un ciclo. Todo lo demás cuelga de ella.
2. Una parcela tiene **una sola campaña activa a la vez** y **un solo cultivo por campaña**.
3. El **clima es diario por parcela**.
4. Las **cantidades se guardan tal como las escribe el técnico y también normalizadas** a una unidad base (kg, ha, m³, jornal, h), para que el ML no interprete texto.
5. **Nada con historial se borra físicamente**: se desactiva.
6. **Permisos por rol guardados en la BD** (el administrador los edita), no escritos en el código.
7. Las **predicciones siempre van ligadas a una campaña** (no hay escenarios sueltos).
8. Nombres de tablas en español, **sin tildes ni eñe** (`campanias`, no `campañas`).
9. El borrado en cascada de algunas tablas hijas **se dejó como está por ahora** (decisión explícita del desarrollador).

---

## 3. Estado actual

### Hecho
- Estructura creada: `backend/` (proyecto Django `config` + app `usuarios`) y `frontend/` (React con Vite).
- Entorno virtual con Django 5.2.17, DRF, simplejwt, django-cors-headers, python-dotenv, y `requirements.txt` generado.
- PostgreSQL en Docker levantado y **conectado a Django**.
- `README.md` con instrucciones completas (Docker, migrate, superusuario, admin, pruebas).
- Documento de requerimientos en LaTeX: **fuera del repositorio**, en `D:\ProyectoJoseLuis\Documentos\Requerimeintos\requerimientos.tex` (compilado con XeLaTeX). No está dentro de `Sistema/`.
- Diseño de base de datos en **tres archivos SQL** (en `DB_sql/`, como diseño de muestra), probados en un PostgreSQL real (ver sección 5 y 6).

### Semana 1 (5–11 oct): roles, permisos y usuarios — COMPLETADA
- **`settings.py` completo:** `INSTALLED_APPS` (usuarios, DRF, CORS), CORS en primer lugar del middleware, `REST_FRAMEWORK` con JWT y `IsAuthenticated` por defecto, `AUTH_USER_MODEL = "usuarios.Usuario"`, `LANGUAGE_CODE = "es-pe"`, `TIME_ZONE = "America/Lima"`.
- **Modelos** (`backend/usuarios/models.py`): `Permiso`, `Rol`, `RolPermiso` (constraint `uq_rol_permiso`), `Usuario(AbstractUser)` con `rol` (FK `PROTECT`), `telefono`, `groups = None` y `user_permissions = None` (no se usan los grupos/permisos de Django).
- **3 migraciones propias** en `backend/usuarios/migrations/`:
  - `0001_initial` — las 4 tablas (`db_table` = nombres del diseño, `db_default` replicando cada `DEFAULT` de `01_tablas.sql`).
  - `0002_datos_iniciales` — 3 roles de sistema, 55 permisos y 101 asignaciones (55/32/14). Idempotente (`get_or_create`) y reversible.
  - `0003_trigger_rol_sistema` — `fn_proteger_rol_sistema` + `trg_roles_proteger` con el texto literal de `02_reglas_y_vista.sql`.
- **Panel de administración** (`admin.py`): los 4 modelos; `permisos` solo lectura; en roles del sistema el campo `nombre` es solo lectura y no se pueden borrar desde el panel; formulario de usuario con `rol` obligatorio también en el alta; `permisos` del rol con autocompletado.
- **Comando `crear_superusuario`** (lee `ADMIN_USERNAME`/`ADMIN_PASSWORD` del `.env`, idempotente). El `createsuperuser` de Django no sirve solo porque `rol_id` es NOT NULL.
- **8 pruebas** (`manage.py test usuarios`) verdes: semilla, asignaciones, trigger (mensaje exacto), rol normal borrable, `ProtectedError`, `IntegrityError` sin rol, `uq_rol_permiso` y panel admin. `manage.py check` en 0 issues.
- **Comparación con el diseño:** `docs/comparacion_sprint1.md` (columna por columna vs `01_tablas.sql`; 5 diferencias documentadas: `BY DEFAULT`, sin `ON DELETE`, `statement_timestamp()`, nombres auto de constraints/índices, sin `COMMENT`).

### Semana 2 (12–18 oct): autenticación, permisos, rate limit y login en React — COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_seguridad.md` (duración de tokens, cookies httpOnly, blacklist de refresh, rate limit comparado con `django-axes` y `django-ratelimit`, superusuario regido por su rol).
- **Endpoints** (`backend/usuarios/`): `POST /api/auth/login/`, `refresh/`, `logout/`, `GET /api/auth/me/` y `POST /api/usuarios/`, todos bajo `/api/` (contrato completo en `docs/api_autenticacion.md`).
- **Cookies httpOnly** (`sigpa_access` 15 min, `sigpa_refresh` 7 días con `Path=/api/auth/`); rotación con `token_blacklist` (2 tablas); se acepta `Authorization: Bearer` como alternativa.
- **Permisos por vista:** clase reutilizable `TienePermiso` lee `permiso_requerido` de la vista y comprueba los códigos de la BD en **1 consulta por petición**; el superusuario no tiene atajos.
- **Rate limit propio con DRF:** `ScopedRateThrottle` por IP (30/min) + bloqueo por cuenta (5 fallos → 15 min, caché), respuesta 429 en español con `Retry-After`, acción **«Desbloquear acceso»** en el panel admin y logger `sigpa.seguridad`.
- **Frontend:** cliente Axios con `withCredentials` y renovación *single-flight* (una sola petición de refresh compartida, reintento único), `SesionProvider`/`useSesion`, pantalla de **Login**, rutas protegidas, **menú filtrado por permiso** (`opcionesMenu.js` genera menú y rutas), páginas 403 y 404, marca propia y tipografías Fraunces + Public Sans.
- **20 pruebas verdes** (`manage.py test usuarios`: 8 de la Semana 1 + 12 de la Semana 2, incluidas 2 extra de tiempo de bloqueo y refresco de permisos), `manage.py check` en 0 issues, `npm run lint` y `npm run build` en 0 problemas.

### Semana 3 (19–25 oct): ubicación y productores — COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_semana3.md` (7 decisiones): lista real de ubicación **pendiente** del responsable (mientras tanto, CSV de datos inventados), comando de carga CSV/Excel idempotente, desactivar sin borrar, enmascarado por rol ⚠️ pendiente de confirmar, filtro «solo mis productores» aplazado a la Semana 4, nada se borra (sin `DELETE`, responde 405) y paginación global de 20 con orden por apellidos y `?busqueda=`.
- **App `backend/productores/`**: modelos `Provincia`, `Distrito`, `Comunidad` y `Productor` con `db_table` y restricciones del diseño (`uq_distrito`, `uq_comunidad`, `ck_productores_dni`, `ck_productores_estado`, índices `ix_distritos_provincia`, `ix_comunidades_distrito`, `ix_productores_comunidad/estado/apellidos`); **2 migraciones propias**: `0001` (tablas) y `0002` (funciones y triggers, reversible); panel admin con filtros, búsqueda y `creado_por` rellenado en el alta.
- **Triggers con el texto literal de `02_reglas_y_vista.sql`:** `fn_set_actualizado_en` + `trg_productores_actualizado`, `fn_codigo_productor` + `seq_productor_codigo` + `trg_productores_codigo` (código `PROD-0001`, automático).
- **Comando `cargar_ubicacion`** (`--archivo`, acepta `.csv` y `.xlsx` con `openpyxl`), **idempotente**, con informe de filas creadas, existentes y fallidas sin detenerse; datos de ejemplo inventados en `datos/ejemplo_ubicaciones.csv` (fuera de las migraciones).
- **API** (`/api/ubicaciones/{provincias,distritos,comunidades}/` y `/api/productores/`): permisos por acción (`catalogos.*` y `productores.*` con la clase `TienePermiso`), paginación global (`API_PAGE_SIZE=20`), `?busqueda=`, filtros por jerarquía y estado, `PATCH …/estado/` para desactivar/reactivar, **sin `DELETE` (405)**, DNI/teléfono enmascarados por rol (`ROLES_CON_DATOS_COMPLETOS`: Administrador y Técnico completos, Coordinador `****5678`). Contrato completo en `docs/api_ubicacion_productores.md`.
- **17 pruebas nuevas (21–37)** → **37 en total**; `manage.py check` en 0 issues; `makemigrations --check` sin cambios; la 33 usa `TransactionTestCase` porque `now()` es el tiempo de la transacción.
- **Documentación:** `docs/comparacion_semana3.md` (diseño SQL vs migraciones: 4 tablas + 2 triggers), `docs/tablero.md` (HU-15..HU-22 con evidencias) y `docs/coleccion_api_semana3.json` (**36 peticiones validadas 36/36** contra el servidor, sin secretos).
- **Migración desde BD vacía verificada:** base nueva `sigpa_ga_migracion` → 27 migraciones OK, 55 permisos / 3 roles / 101 asignaciones, las 4 tablas, 3 triggers, 3 funciones y la secuencia; prueba funcional en SQL crudo (`PROD-0001` generado y `actualizado_en` actualizado en otra transacción). Base de prueba borrada al terminar.

### Semana 4 (26 oct - 1 nov): parcelas y asignaciones - COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_semana4.md` (19 decisiones): desactivar sin borrar, CRUD en modales (decisión 19), responsive siempre (14), toasts (20), auto-asignación del técnico al crear el productor (4, cierra la pregunta C).
- **Tablas:** `parcelas` y `asignaciones_tecnico` en la app `productores` (migraciones `0003` y `0004`, reversibles) con `fn_codigo_parcela` + secuencia (`P-0001`), `trg_parcelas_actualizado`, `trg_parcelas_codigo` y `fn_validar_asignacion` + `trg_asignaciones_validar`.
- **API:** `/api/parcelas/` (filtros jerárquicos, `?desplegable=1`, sin `DELETE`, `./estado/`) y `/api/asignaciones/` (`tecnicos-disponibles`, `./estado/`, reasignar = desactivar + crear); el ámbito del Técnico (`SoloSusProductores`) reutilizado desde entonces en todas las APIs; ficha del productor completa (`parcelas`, `resumen`, `tecnicos_asignados`).
- **Frontend:** pantallas `Productores` y `Parcelas` con ficha y formularios en modales, filtros en URL, checklist `docs/verificacion_ui_semana4.md`.
- **Cierre:** **53 pruebas** (16 nuevas), `check` en 0 issues, colección `coleccion_api_semana4.json` validada **48/48**, `lint`/`build` en 0; comparación `comparacion_semana4.md` (2 tablas, 2 funciones y 3 triggers).

### Semana 5 (2-8 nov): catálogos de campañas - COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_semana5.md` (17 decisiones): los 8 catálogos, datos CONFIRMAR solo por comando, nada se borra, etapas sin estado, unidad base protegida, unicidad normalizada en español.
- **App `catalogos/`** con 2 migraciones (`0001` con las 8 tablas y sus constraints, `0002` con las 26 filas fijas) + comando idempotente **`cargar_catalogos`** (18 datos CONFIRMAR → 44 filas en total).
- **API de los 8 recursos** con `VistaCatalogo`/`VistaCatalogoConEstado`, `?desplegable=1`, reordenado de etapas atómico y mensajes `Ya existe…` por recurso; contrato en `docs/api_catalogos.md`.
- **Frontend:** pantalla `/catalogos` con 8 pestañas en la URL, configuración declarativa `catalogosConfig.js`, alta/edición en modal; checklist `docs/verificacion_ui_semana5.md`.
- **Cierre:** **67 pruebas** (14 nuevas), `check` en 0 issues, colección `coleccion_api_semana5.json` validada **93/93**, `lint`/`build` en 0; comparación `comparacion_semana5.md` (37/37 columnas, 28/28 restricciones, 44/44 datos).

### Semana 6 (9-15 nov): campañas de producción - COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_semana6.md` (18 decisiones, mapeo HU-38..HU-46): 5 estados con máquina de transiciones, período `AAAA-AAAA` con fechas dentro del rango 1 ene año₁ – 31 dic año₂ (solo API, **pregunta F pendiente de confirmar**), una campaña activa por parcela y período, bloqueo de la desactivación de productor/parcela con campañas activas (**pregunta G pendiente de confirmar**), edición por estado y cancelación con motivo.
- **App `campanias/`** con 2 migraciones: `0001_initial.py` (tabla de 14 columnas, FK compuesta `fk_campania_variedad_cultivo`, `ck_campania_periodo`, `ck_campania_fechas`, 6 índices del diseño) y `0002_funciones_y_triggers.py` (`fn_validar_campania` **parcial** + `trg_campanias_validar` + `trg_campanias_actualizado`); las transiciones de estado completas quedan para el Sprint 4 (`campanias.0003`; nunca se edita una migración aplicada).
- **API** `/api/campanias/` (listado con filtros, detalle, alta, edición por estado, `iniciar/` y `cancelar/` con motivo) con permisos `campanias.*` por acción (`PermisosCampania`), ámbito del Técnico (campaña ajena → 404) y, en `productores`, los bloqueos HU-45/HU-46 al desactivar con campañas activas; contrato completo en `docs/api_campanias.md`.
- **Frontend:** pantalla `/campanias` (listado con filtros en URL, `Tabla` + `Paginacion`), alta/edición en modal con las acciones de estado, y sección **Campañas** en las fichas de productor y parcela (HU-44); permisos siempre en el botón (el botón «Cancelar campaña» exige `campanias.desactivar`); checklist `docs/verificacion_ui_semana6.md`.
- **Cierre:** **86 pruebas** (19 nuevas, 68–86), `check` en 0 issues, colección `coleccion_api_semana6.json` validada **127/127 (221/221 aserciones)**, `lint`/`build` en 0; comparación `comparacion_semana6.md` (14/14 columnas, 9/9 restricciones, 6/6 índices + 1 extra documentado, 2/2 triggers).

### Semana 7 (16–22 nov): actividades productivas - COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_semana7.md` (17 decisiones, mapeo HU-47..HU-55): la actividad como registro diario con dos estados (`ACTIVA`/`ANULADA`) y anulación con motivo como borrado lógico (sin `DELETE` → 405), validaciones en el serializador antes que la BD (campaña activa, fecha no futura según la hora de **America/Lima** — **pregunta H pendiente de confirmar**, densidad solo en siembras y con valor+unidad juntos, campaña y tipo inmodificables al editar), efecto siembra en los triggers (`fn_actividad_siembra` v2), ámbito del Técnico sobre las campañas de sus productores y permisos `actividades.*` por acción; fertilización y fitosanitarios aún **sin cantidades de insumos** hasta el Sprint 5 (decisión 17).
- **App `seguimiento/`** con 2 migraciones: `0001_initial.py` (tabla `actividades` de 15 columnas con `anulada`+`motivo_anulacion` y 6 checks) y `0002_funciones_y_triggers.py` (`fn_validar_fecha_campania`, `fn_actividad_siembra` v2 + `trg_actividades_siembra`, `trg_actividades_fecha`, `trg_actividades_actualizado`; reversible). Diseño SQL actualizado (anuladas fuera del dataset); **11 triggers** implementados en total. Migración verificada desde cero en BD temporal (borrada).
- **API** `/api/actividades/` (listado con filtros y búsqueda, detalle, alta, edición, `anular/` y `reactivar/`, sin `DELETE` → 405) con `PermisosActividad`, ámbito del Técnico (404) y `registrado_por` oculto a los roles con `limita_a_asignados`; además `?desplegable=1` en `/api/campanias/` (solo activas) y `/api/productores/` (solo activos); contrato completo en `docs/api_actividades.md`.
- **Frontend:** pantalla `/actividades` (filtros en URL, `Tabla`+`Paginacion`), alta/edición en modal (densidad solo si el tipo es SIEMBRA, `max` = hoy en hora Lima), `ActividadFicha` con panel «Anular actividad»/«Reactivar» y **`CampaniaFicha`** con bloque de actividades (ventana flotante estilo `ParcelaFicha`); entrada en el menú con `actividades.ver`; bug de `listarTodo` corregido (los desplegables devuelven array plano); checklist `docs/verificacion_ui_semana7.md`.
- **Cierre:** **102 pruebas** (16 nuevas, 87–102), `check` en 0 issues, colección `coleccion_api_semana7.json` validada **159/159 (286/286 aserciones)**, `lint`/`build` en 0; comparación `comparacion_semana7.md` (15/15 columnas, 10/10 restricciones, 2/2 índices sin extras, 3/3 triggers y 2 funciones literales).

### Semana 8 (23–29 nov): producción, rendimiento y cierre de campañas - COMPLETADA
- **Decisiones documentadas** en `docs/decisiones_semana8.md` (20 decisiones, mapeo HU-56..HU-62): **una sola producción por campaña** (`OneToOne`), kg y rendimiento **calculados por la base** (pregunta J: rige **bruta**, `perdida_kg` no descuenta — pendiente de confirmar), revisión por umbrales configurables (pregunta K: `100`/`5000`/`800`/`30` y quintal = 46 kg, **CONFIRMAR**), «deshacer cosecha» como única excepción del «nada se borra», `cerrar/` irreversible desde `COSECHADA` con producción sin revisión pendiente, parámetros con claves fijas (solo cambia el valor) y pérdida/calidad como registro, no cálculo (decisión 20).
- **Apps `produccion/` y `sistema/`** con **4 migraciones reversibles**: `produccion.0001` (tabla de 17 columnas + `OneToOne` + 5 checks), `sistema.0001` (5 columnas + los 4 parámetros), `produccion.0002` (`fn_validar_produccion`, `fn_produccion_post` **parcial** y 3 triggers) y `campanias.0003` (`fn_validar_campania` **v3 completa**, con las transiciones `COSECHADA`/`CERRADA`); **15 triggers** en total; migración verificada desde cero en BD temporal (borrada).
- **API:** `/api/producciones/` (listado con filtros, detalle, alta, edición, `revisar/`, `deshacer-cosecha/`, sin `DELETE` → 405), `/api/parametros/` (GET lista/detalle y PATCH por clave; sin `POST`/`DELETE` → 405) y `POST /api/campanias/{id}/cerrar/`, con permisos por acción, ámbito del Técnico (campaña ajena → mismo mensaje que si no existiera; producción ajena → 404), `registrado_por` oculto al ámbito y bloques `produccion` en las fichas de campaña y de productor; contrato completo en `docs/api_produccion.md`.
- **Frontend:** pantalla **`/parametros`** (tabla de las 4 claves + edición en modal), `ProduccionFormulario` (alta/edición en modal) y `ProduccionFicha` (paneles «Registrar revisión» y «Deshacer cosecha»), bloque **«Producción»** con «Registrar producción» y «Cerrar campaña» en `CampaniaFicha`, columna «Producción» en `ProductorFicha` y entrada «Parámetros» en el menú (la de «Producción» sigue siendo placeholder); checklist `docs/verificacion_ui_semana8.md`.
- **Cierre:** **120 pruebas** (18 nuevas, 103–120), `check` en 0 issues, colección `coleccion_api_semana8.json` validada **205/205 (374/374 aserciones)**, `lint`/`build` en 0; comparación `comparacion_semana8.md` (17 + 5 columnas, 11 restricciones, 0 índices extra, 15 triggers).

### No hecho todavía
- Recursos, clima, incidencias, reportes, alertas y el resto de tablas (con sus triggers: `fn_validar_etapa`, `fn_validar_incidencia`, `fn_uso_recurso`) y la vista del dataset. `fn_produccion_post` está **parcial**: solo pasa la campaña a `COSECHADA`; la parte de `predicciones` (rendimiento real y error) entra en los **Sprints 13–14**.
- Pantallas React de los módulos que faltan (listado de **Producción** — la entrada del menú es placeholder —, Predicción, Reportes, Usuarios, Auditoría; hoy: login, 403, 404, productores, parcelas, catálogos, campañas, actividades, **parámetros** y producción dentro de las fichas).
- Administración de usuarios/roles desde React, cambio de contraseña y recuperación de acceso.
- Diagrama entidad-relación y modelo lógico para el Capítulo IV.
- Ejecutar los checklists de UI de las Semanas 4 a 8 en navegador.

### Ojo: cosas que quedaron superadas
- Antes se propuso un modelo `Usuario` con un campo de texto `rol` (ADMIN/TECNICO/COORDINADOR). **Está descartado.** El diseño vigente usa `rol_id` → tabla `roles` con permisos (secciones 5.C y 8).
- El documento de requerimientos (`.tex`) **no refleja aún** varios cambios posteriores (ver sección 14).

---

## 4. Cómo funciona el sistema (flujo de datos)

Ejemplo con un productor real:

1. Juan Mamani es un **productor** (`productores`), de una **comunidad** (`comunidades`).
2. Tiene una **parcela** P-001 de 2 ha a 3850 msnm (`parcelas`).
3. Se crea una **campaña** 2025-2026 de quinua variedad X en esa parcela (`campanias`, estado `PLANIFICADA`).
4. El técnico registra **actividades** (`actividades`): preparación, siembra (con densidad), fertilización, etc. Al registrar la **siembra**, el sistema fija `fecha_siembra` y pasa la campaña a `EN_PRODUCCION`.
5. Registra los **recursos usados** (`uso_recursos`): 16 kg de semilla, 2 quintales de urea (el sistema los convierte a 92 kg), 40 jornales.
6. Registra **incidencias** (`incidencias`), p. ej. una helada de severidad alta con 0.5 ha afectadas, y el **clima** diario (`clima`).
7. Va avanzando la **línea de tiempo** (`seguimiento_etapas`): emergencia, floración, etc.
8. En cualquier momento se puede **predecir** el rendimiento (`predicciones`) con el modelo activo (`modelos_ml`).
9. Al cosechar se registra la **producción** (`producciones`): p. ej. 70.435 quintales en 2 ha. El sistema calcula los kg (3240.01) y el rendimiento (1620.01 kg/ha), pasa la campaña a `COSECHADA` y **rellena automáticamente** el rendimiento real y el error de las predicciones previas de esa campaña.
10. Se **cierra** la campaña (`CERRADA`). Desde ese momento es una fila del dataset de entrenamiento.

### Estados de la campaña

```
PLANIFICADA ──► EN_PRODUCCION ──► COSECHADA ──► CERRADA
     │                │               │
     └─► CANCELADA    └─► CANCELADA   └─► (vuelve a EN_PRODUCCION)
```

- Una campaña **nace** como `PLANIFICADA` o `EN_PRODUCCION` (esta última solo para cargas históricas). Nunca nace `CERRADA`.
- **No se puede cerrar sin producción registrada.**
- `CERRADA` y `CANCELADA` no admiten nuevos registros.
- Se considera **activa** la campaña en `PLANIFICADA`, `EN_PRODUCCION` o `COSECHADA`.

### Ciclo que se retroalimenta

```
Registrar → Cosechar → Calcular rendimiento → Nueva fila de datos
    ↑                                               ↓
Predecir ←── Modelo reentrenado ←── Entrenar ←──────┘
```

---

## 5. Base de datos: las 32 tablas

Archivos: `DB_sql/01_tablas.sql` (solo estructura), `DB_sql/02_reglas_y_vista.sql` (triggers y vista), `DB_sql/03_insert.sql` (datos iniciales). Se ejecutan **en ese orden**, solo en bases de prueba vacías.

> **Estos SQL son el diseño de muestra / modelo físico de referencia (para la tesis).** En el sistema real, **Django crea las tablas desde sus modelos y migraciones**; esos archivos no se ejecutan sobre la base que usa la aplicación (ver sección 12). Por eso la carpeta `DB_sql/` está ignorada en Git: es documentación, no código que se despliega.

Convenciones: `PK` identificador; `FK` enlace a otra tabla; `UQ` único; `NN` obligatorio. Las tablas con `creado_en` y `actualizado_en` los llenan automáticamente.

### A. Ubicación (3 tablas)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `provincias` | Lista de provincias | Evita escribir la ubicación a mano y permite filtrar y agrupar reportes | `nombre` UQ |
| `distritos` | Distritos de cada provincia | Los indicadores del coordinador se piden **por distrito** | `provincia_id`, `nombre` (UQ junto con provincia) |
| `comunidades` | Comunidades de cada distrito | Ubica al productor y a la parcela | `distrito_id`, `nombre` (UQ junto con distrito) |

### B. Catálogos (8 tablas, los administra el Administrador)

Existen para que nadie escriba «Quinua», «quinoa» y «QUINUA» como si fueran cosas distintas. **Un dato limpio es lo que el ML necesita.**

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `cultivos` | Granos andinos (quinua, cañihua, tarwi) | El cultivo es variable del ML y eje de los reportes | `nombre` UQ |
| `variedades` | Variedades de cada cultivo | La variedad influye en el rendimiento | `cultivo_id`; UQ `(id, cultivo_id)` habilita la clave compuesta de `campanias` |
| `etapas_fenologicas` | Etapas del ciclo de cada cultivo (siembra, emergencia, floración…) | Alimenta la **línea de tiempo** del seguimiento | `cultivo_id`, `nombre`, `orden` |
| `unidades` | Unidades de medida con **factor de conversión** a la base | El técnico puede escribir quintales o jornales y el sistema normaliza | `tipo` (MASA, SUPERFICIE, VOLUMEN, LABOR, TIEMPO), `factor_a_base`, `es_base` |
| `tipos_actividad` | Tipos de actividad productiva | Estandariza las actividades; `SIEMBRA` dispara reglas automáticas | `codigo` (PREPARACION, SIEMBRA, FERTILIZACION, FITOSANITARIO, RIEGO, DESHIERBO, COSECHA) |
| `recursos` | Qué se puede consumir en una campaña | Define semilla, fertilizante, mano de obra, agua, etc. | `categoria`, `tipo_unidad` (para no registrar semilla en jornales) |
| `tipos_incidencia` | Helada, sequía, granizada, plaga… | Estandariza incidencias; la categoría distingue climáticas de biológicas | `nombre`, `categoria` (CLIMATICA, BIOLOGICA, OTRA) |
| `agentes` | Catálogo de **plagas y enfermedades** | Evita texto libre («gusano cortador» vs «gusano cortado») | `nombre` UQ, `tipo` (PLAGA, ENFERMEDAD) |

### C. Seguridad (6 tablas)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `permisos` | Catálogo de acciones permitidas (`productores.crear`, `ml.entrenar`…) | Los permisos son fijos y los define el desarrollador; 55 en total | `codigo` UQ, `modulo`, `accion` |
| `roles` | Conjuntos de permisos (Administrador, Técnico de campo, Coordinador) | Permite crear roles nuevos sin tocar código | `es_sistema` (no se borra), `limita_a_asignados`, `activo` |
| `roles_permisos` | Qué permisos tiene cada rol | Es lo que el administrador marca o desmarca en pantalla | `rol_id`, `permiso_id` (UQ juntos) |
| `usuarios` | Cuentas del sistema | Compatible con `AbstractUser` de Django, más `telefono` y `rol_id` | `password` (hash), `is_active` (desactivar sin borrar), `rol_id` |
| `asignaciones_tecnico` | Qué productores ve cada técnico | Un técnico solo ve a sus productores | `tecnico_id`, `productor_id` (UQ juntos), `activo` |
| `auditoria` | Quién hizo qué, cuándo y desde qué IP | Trazabilidad exigida por el documento | `usuario_id`, `accion`, `modulo`, `tabla`, `registro_id`, `detalle` (JSONB), `ip` |

### D. Núcleo (3 tablas)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `productores` | Ficha del productor | Es el actor central del proyecto | `codigo` (PROD-0001, automático), `dni` (8 dígitos, UQ), `comunidad_id`, `estado` |
| `parcelas` | Terrenos del productor (un productor puede tener varias) | Ahí se produce; guarda las variables del terreno que usa el ML | `codigo` (P-001, automático), `superficie_ha` > 0, `altitud_msnm`, `latitud`/`longitud` (para mapa y clima), `tipo_suelo`, `pendiente`, `disponibilidad_agua`, `sistema_riego` |
| `campanias` | **Tabla central:** parcela + cultivo + ciclo | Toda producción pertenece a una campaña; cada campaña cerrada es una fila de entrenamiento | `periodo` («2025-2026»), `cultivo_id`, `variedad_id`, `fecha_inicio`, `fecha_fin_prevista`, `fecha_siembra`, `superficie_sembrada_ha`, `estado` |

### E. Seguimiento de la campaña (5 tablas)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `seguimiento_etapas` | Línea de tiempo: etapas que alcanzó la campaña | Es lo que convierte el sistema en uno de **seguimiento** | `campania_id`, `etapa_id` (UQ juntos), `fecha_inicio`, `fecha_fin` |
| `actividades` | Labores realizadas (siembra, fertilización, riego…) | Responde al primer objetivo específico | `tipo_actividad_id`, `fecha`, `metodo`, `densidad_siembra` + `densidad_unidad` (KG_HA o PLANTAS_M2), `horas`, `costo`, `anulada` + `motivo_anulacion` (borrado lógico, Semana 7) |
| `uso_recursos` | Cantidad de cada recurso consumido | Origen de las variables semilla, fertilizante y jornales por hectárea | `recurso_id`, `cantidad`, `unidad_id`, `cantidad_base` (calculada) |
| `incidencias` | Eventos que afectan la producción | Variable del ML y base de las alertas | `tipo_incidencia_id`, `severidad` (BAJA, MEDIA, ALTA), `superficie_afectada_ha`, `agente_id`, `producto_aplicado` |
| `clima` | Datos climáticos diarios por parcela | Variable central del ML (precipitación, temperatura, heladas) | `parcela_id`, `fecha` (UQ juntos), temperaturas, `precipitacion_mm`, `humedad_pct`, `helada`, `fuente` (MANUAL o API) |

### F. Producción (1 tabla)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `producciones` | Resultado de la campaña | Contiene la **variable objetivo** del ML (`rendimiento_kg_ha`) | `campania_id` UQ, `fecha_cosecha`, `superficie_cosechada_ha`, `cantidad_producida` + `unidad_id` (lo que escribió el técnico), `produccion_kg` y `rendimiento_kg_ha` (calculados), `requiere_revision`, `incluir_en_entrenamiento` |

### G. Machine Learning (3 tablas)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `entrenamientos_ml` | Una ejecución de entrenamiento | Trazabilidad: cuántos datos y qué variables se usaron | `n_registros`, `n_entrenamiento`, `n_prueba`, `variables_usadas` (JSONB) |
| `modelos_ml` | Cada algoritmo entrenado con sus métricas | Comparar regresión lineal, Random Forest y Gradient Boosting; elegir el activo | `algoritmo`, `version`, `mae`, `rmse`, `r2`, `archivo` (.joblib), `activo` (solo uno) |
| `predicciones` | Cada predicción hecha y su comparación con la realidad | Permite evaluar el modelo de forma continua | `campania_id`, `modelo_id`, `variables_entrada` (copia exacta, JSONB), `rendimiento_predicho`, `rendimiento_real`, `error_abs`, `error_pct` |

### H. Sistema (3 tablas)

| Tabla | Para qué sirve | Por qué existe | Campos clave |
|---|---|---|---|
| `alertas` | Avisos para el personal del proyecto | Permite identificar **productores en riesgo** | `productor_id`, `tipo` (INCIDENCIA_SEVERA, SIN_ACTIVIDAD, RENDIMIENTO_BAJO), `atendida` |
| `parametros_sistema` | Umbrales configurables | El administrador ajusta reglas sin tocar código | `clave` UQ, `valor` |
| `importaciones` | Bitácora de cargas desde Excel o CSV | Los datos históricos son imprescindibles para el ML y hay que registrar errores por fila | `tipo`, `filas_totales`, `filas_ok`, `filas_error`, `detalle_errores` (JSONB), `estado` |

### Restricciones destacadas (además de PK/FK/NN)

- **Índices únicos parciales:**
  - `uq_campania_activa_por_parcela`: una sola campaña activa por parcela.
  - `uq_campania_parcela_periodo`: un cultivo por parcela y período (las canceladas no cuentan).
  - `uq_modelo_activo`: un solo modelo activo en todo el sistema.
- **Clave foránea compuesta** `(variedad_id, cultivo_id)` en `campanias`: la variedad debe ser del cultivo elegido.
- **CHECKs de calidad:** superficies > 0, producción ≥ 0, DNI de 8 dígitos, temperatura entre −30 y 45 °C (mínima ≤ máxima), humedad 0–100 %, latitud/longitud en rango, altitud 0–6500, período con formato `AAAA-AAAA+1`, densidad con su unidad, etc.

---

## 6. Triggers, funciones y restricciones

Están en `DB_sql/02_reglas_y_vista.sql`: **13 funciones y 24 triggers**. Existen porque ciertas reglas cruzan varias tablas y un CHECK simple no las puede expresar. Así la calidad de datos queda protegida **incluso si alguien inserta datos sin pasar por la aplicación** (importaciones, scripts, panel de administración).

| Función / trigger | Tablas | Qué hace | Por qué |
|---|---|---|---|
| `fn_set_actualizado_en` (9 triggers `trg_*_actualizado`) | productores, parcelas, campanias, actividades, uso_recursos, incidencias, clima, producciones, parametros_sistema | Actualiza `actualizado_en` en cada UPDATE | Trazabilidad de cambios |
| `fn_codigo_productor` + secuencia | productores | Genera `PROD-0001`, `PROD-0002`… si el código viene vacío | Código único sin que el técnico lo invente |
| `fn_codigo_parcela` + secuencia | parcelas | Genera `P-001`, `P-002`… | Ídem |
| `fn_proteger_rol_sistema` | roles | Impide borrar los roles del sistema | Que nadie deje el sistema sin roles base. **Implementada** en la migración `usuarios.0003_trigger_rol_sistema` |
| `fn_validar_asignacion` | asignaciones_tecnico | Solo permite asignar productores a usuarios cuyo rol tenga `limita_a_asignados` | Coherencia: no se asigna a un administrador |
| `fn_validar_campania` | campanias | Superficie sembrada ≤ superficie de la parcela; estado inicial solo `PLANIFICADA` o `EN_PRODUCCION`; **transiciones de estado válidas**; no cerrar sin producción | Regla central del modelo de datos. **Implementada completa (v3)** en `campanias.0003_fn_validar_campania_completa` (Semana 8): añade las transiciones `COSECHADA`/`CERRADA` a la versión parcial de la Semana 6, con `trg_campanias_validar` y `trg_campanias_actualizado` |
| `fn_validar_fecha_campania` (4 triggers) | actividades, uso_recursos, incidencias, seguimiento_etapas | La fecha debe estar dentro del período de la campaña (`fecha_inicio` a `fecha_fin_prevista`) y la campaña no puede estar cerrada ni cancelada | Todo dato debe ubicarse dentro del ciclo del cultivo. **Implementada** en `seguimiento.0002_funciones_y_triggers` (Semana 7) con `trg_actividades_fecha`; los sprints siguientes la reutilizarán en `uso_recursos`, `incidencias` y `seguimiento_etapas` |
| `fn_validar_etapa` | seguimiento_etapas | La etapa debe ser del cultivo de la campaña | Evita registrar «floración de tarwi» en una campaña de quinua |
| `fn_validar_incidencia` | incidencias | Superficie afectada ≤ superficie sembrada; solo incidencias biológicas pueden llevar `agente_id` | Datos coherentes |
| `fn_uso_recurso` | uso_recursos | La unidad debe ser compatible con el recurso; la actividad debe ser de la misma campaña; **calcula `cantidad_base`** (cantidad × factor) | Normalizar unidades para el ML |
| `fn_actividad_siembra` | actividades (AFTER) | Al registrar una siembra: fija `fecha_siembra` (la más temprana) y pasa la campaña de `PLANIFICADA` a `EN_PRODUCCION` | Automatiza el flujo. **Implementada en versión v2** en `seguimiento.0002` (Semana 7): solo cuenta siembras activas, se dispara también al anular/reactivar y deja `fecha_siembra` vacía sin revertir el estado de la campaña |
| `fn_validar_produccion` | producciones | Campaña activa; superficie cosechada ≤ sembrada; fecha de cosecha ≥ fecha de siembra; unidad de **masa**; **calcula `produccion_kg` y `rendimiento_kg_ha`**; marca `requiere_revision` si el rendimiento es atípico (según `parametros_sistema`) | Corazón del control de calidad. **Implementada** en `produccion.0002_funciones_y_triggers` (Semana 8), con `trg_producciones_validar` y `trg_producciones_actualizado` |
| `fn_produccion_post` | producciones (AFTER) | Pasa la campaña a `COSECHADA`; **rellena `rendimiento_real`, `error_abs` y `error_pct`** de las predicciones previas | Comparación predicho vs. real sin trabajo manual. **Implementada parcial** en `produccion.0002` (Semana 8): solo el `UPDATE` de la campaña, porque `predicciones` no existe hasta los **Sprints 13–14** (reemplazar con `CREATE OR REPLACE`) |

**Detalles que conviene recordar.**
- Desde la Semana 8, los triggers **implementados** en las migraciones propias son 15 de 24 (`trg_roles_proteger`, `trg_productores_actualizado`, `trg_productores_codigo`, `trg_parcelas_actualizado`, `trg_parcelas_codigo`, `trg_asignaciones_validar`, `trg_campanias_validar`, `trg_campanias_actualizado`, `trg_actividades_actualizado`, `trg_actividades_fecha`, `trg_actividades_siembra`, `trg_producciones_validar`, `trg_producciones_post`, `trg_producciones_actualizado` y `trg_parametros_sistema_actualizado`); el detalle está en `docs/evidencias_capitulo4.md`.
- Las fechas de actividades se validan de forma estricta contra `fecha_fin_prevista`. Si una cosecha se retrasa, hay que ampliar esa fecha (se puede relajar la regla más adelante).
- Si el rendimiento cae fuera de `rendimiento_min_plausible` o `rendimiento_max_plausible`, la producción queda marcada para revisión y **el administrador decide** si se incluye en el entrenamiento (`incluir_en_entrenamiento`).
- La densidad de siembra tiene un CHECK (número y unidad van juntos), pero **no** se obliga a que solo la actividad de siembra la use.
- Cargas históricas: la campaña se crea como `EN_PRODUCCION`, se inserta la producción (pasa a `COSECHADA`) y luego se actualiza a `CERRADA`.

---

## 7. La vista del dataset de Machine Learning

`vw_dataset_entrenamiento` arma **una fila por campaña `CERRADA`** cuya producción tenga `incluir_en_entrenamiento = TRUE`. Los valores faltantes quedan en `NULL` (se imputan en la preparación de datos).

| Grupo | Columnas |
|---|---|
| Identificación | `campania_id`, `periodo`, `anio_campania` |
| Cultivo | `cultivo`, `variedad` |
| Superficie y parcela | `superficie_sembrada_ha`, `altitud_msnm`, `tipo_suelo`, `pendiente`, `sistema_riego` |
| Clima (siembra a cosecha) | `precipitacion_acum_mm`, `temp_prom_c`, `humedad_prom_pct`, `n_heladas`, `dias_con_clima` |
| Recursos por hectárea | `semilla_kg_ha`, `fertilizante_kg_ha`, `jornales_ha`, `agua_m3_ha` |
| Manejo | `n_incidencias`, `severidad_max` (0–3), `n_aplicaciones` (fertilizaciones + controles fitosanitarios), `dias_ciclo` |
| **Variable objetivo** | `rendimiento_kg_ha` |

> **Advertencia (fuga de datos).** Esta vista resume el **ciclo completo**. Para predecir **durante** la campaña, el ML debe generar las mismas variables con una **fecha de corte**, para no usar información futura. `dias_con_clima` es solo un indicador de cobertura del clima, no un predictor.

---

## 8. Roles y permisos

**Modelo.** `usuarios` → `roles` → `roles_permisos` → `permisos`. Cada usuario tiene un solo rol. Al iniciar sesión, la API debe devolver la lista de permisos del usuario. **React solo oculta o muestra menús; el backend verifica en cada petición.**

**Roles iniciales** (`es_sistema = TRUE`, no se pueden borrar):

| Rol | `limita_a_asignados` | Qué puede |
|---|---|---|
| Administrador | No | Todo (los 55 permisos): usuarios, roles, catálogos, parámetros, importación, ML, auditoría |
| Técnico de campo | **Sí** | Ver, crear y editar en productores, parcelas, campañas, actividades, recursos, clima, incidencias y producción; ver catálogos; predecir y ver predicciones; dashboard; ver y atender alertas; ver y exportar reportes. **No** tiene permisos de «desactivar» |
| Coordinador | No | Solo lectura: esos módulos y catálogos, ver predicciones, dashboard, alertas, ver y exportar reportes |

**Los 55 permisos:** 40 de CRUD (`ver`, `crear`, `editar`, `desactivar` × 10 módulos: usuarios, catalogos, productores, parcelas, campanias, actividades, recursos, clima, incidencias, produccion) y 15 especiales: `roles.gestionar`, `asignaciones.gestionar`, `parametros.gestionar`, `importacion.ejecutar`, `ml.entrenar`, `ml.activar_modelo`, `ml.ver_modelos`, `ml.predecir`, `ml.ver_predicciones`, `dashboard.ver`, `alertas.ver`, `alertas.atender`, `reportes.ver`, `reportes.exportar`, `auditoria.ver`.

**Dos reglas distintas que se verifican juntas.**
- *Permiso:* responde «¿puede crear parcelas?».
- *Asignación:* responde «¿de qué productores?» (`asignaciones_tecnico`, solo para roles con `limita_a_asignados`).

**Precauciones (a implementar en la aplicación).**
- El administrador no debe poder quitarse a sí mismo `roles.gestionar` (bloquearía la administración).
- Los cambios en roles y permisos se registran en `auditoria`.

**Estado:** **Semana 1** — modelos, migración `0002` con la configuración inicial de los tres roles y trigger `trg_roles_proteger` (migración `0003`). **Semana 2** — verificación de permisos en **cada petición** con la clase `TienePermiso` (1 consulta cacheada) y tasa de login. **Semana 3** — los endpoints nuevos exigen `catalogos.*` y `productores.*` según la acción, con las mismas respuestas 401/403. Todas estas reglas están cubiertas por pruebas (37 en total).

---

## 9. Datos iniciales (seeds)

En `DB_sql/03_insert.sql`. Lo marcado **CONFIRMAR** es un supuesto a validar con el responsable del proyecto.

| Dato | Contenido |
|---|---|
| Roles | 3 (Administrador, Técnico de campo, Coordinador) con sus permisos |
| Permisos | 55 |
| Cultivos | Quinua, Cañihua, Tarwi |
| Tipos de actividad | 7 |
| Tipos de incidencia | 8 (helada, sequía, granizada, exceso de lluvia, plaga, enfermedad, daño por animales, otros) |
| Agentes | 5 de ejemplo: Kcona kcona (polilla de la quinua), Ticona (gusano cortador), Pulgón, Mildiu, Mancha foliar (**CONFIRMAR**) |
| Unidades | 9: kg, g, quintal (**CONFIRMAR 46 kg**), tonelada, ha, m³, litro, jornal, hora |
| Etapas fenológicas | 6 de ejemplo para quinua y cañihua: siembra, emergencia, desarrollo vegetativo, floración, maduración, cosecha (**CONFIRMAR**) |
| Parámetros | `dias_sin_actividad = 30`, `umbral_rendimiento_bajo = 800`, `rendimiento_min_plausible = 100`, `rendimiento_max_plausible = 5000` (**CONFIRMAR todos**) |

**No hay datos precargados** de provincias, distritos, comunidades, variedades ni recursos: los aporta el proyecto. La Semana 3 añadió el comando `cargar_ubicacion` (CSV/Excel, idempotente) y un CSV de **ejemplo inventado** (`datos/ejemplo_ubicaciones.csv`) para probar; se retira cuando el responsable entregue la lista real.

**Estado:** los 3 roles, los 55 permisos y las 101 asignaciones **ya están cargados** en la base real por la migración `backend/usuarios/migrations/0002_datos_iniciales.py` (idempotente y reversible). El resto de los seeds (cultivos, tipos, unidades, parámetros…) depende de tablas de sprints posteriores y se cargará cuando esas migraciones existan.

---

## 10. Qué NO hace la base de datos (trabajo de la aplicación)

No son fallas del diseño: son tareas del backend y del frontend.

| Tarea | Detalle |
|---|---|
| Login y tokens | JWT: `/api/auth/login/`, `/api/auth/refresh/` y una vista con los datos del usuario y sus permisos |
| **Rate limit del login** | **Esencial.** Limitación de peticiones por IP y por usuario, y bloqueo temporal tras varios fallos. Opciones: *throttling* de DRF y/o `django-axes` (verificar al implementar) |
| Verificar permisos | Clases de permiso de DRF que consulten `roles_permisos` en cada petición |
| Filtrar por asignación | Un técnico solo ve sus productores asignados |
| Escribir la auditoría | La tabla existe, pero alguien debe escribir en ella |
| Generar alertas | «Campaña sin actividades en 30 días» necesita un proceso programado que revise periódicamente |
| Importar Excel/CSV | Leer el archivo, validar fila por fila, registrar en `importaciones` |
| Clima por API | Consultar una API gratuita (Open-Meteo o NASA POWER) con las coordenadas de la parcela (**deseable**, el registro manual es el respaldo) |
| ML | Entrenar, guardar el `.joblib`, predecir, calcular métricas |
| Reportes | Exportar a PDF y Excel |
| Respaldos | Copias periódicas de la base de datos |
| Datos personales | DNI y teléfono visibles solo a roles autorizados (Ley N.° 29733) |

---

## 11. Plan de Machine Learning

- **Variable objetivo:** rendimiento en kg/ha.
- **Unidad de entrenamiento:** una campaña cerrada (una fila de la vista).
- **Modelos a comparar:** regresión lineal, Random Forest y Gradient Boosting. XGBoost solo si sobra tiempo y se justifica.
- **Métricas:** MAE, RMSE y R² (MAPE solo si no hay valores reales en cero).
- **Validación:** con pocos datos, usar validación cruzada en lugar de una sola división 80/20. Como referencia, con menos de 100 a 150 registros completos los resultados son frágiles.
- **Momento de predicción:** durante la campaña, solo con datos registrados hasta ese punto. **Por confirmar con el responsable del proyecto.**
- **Variables prohibidas como entrada:** producción, superficie cosechada, pérdida y fecha de cosecha (solo existen después de cosechar).
- **Un modelo único** con el cultivo como variable, salvo que los datos permitan uno por cultivo.
- **Guardado:** archivo `.joblib` en una carpeta del proyecto (por ejemplo `ml_models/`). Usar la **misma versión de scikit-learn** para entrenar y predecir. Cargar solo modelos generados por el propio equipo, nunca archivos subidos por usuarios (joblib usa pickle).
- **Render:** es solo la **hipótesis de despliegue** (aún no decidida, ver sección 2); hay que verificar sus características actuales antes de afirmarlas. Si se usa, su disco es temporal, así que un modelo reentrenado desde el sistema se perdería al reiniciar. Por eso se empieza entrenando fuera y subiendo el archivo con el código.
- **Trazabilidad:** cada entrenamiento registra su versión, fecha, métricas, número de registros y variables.

**Honestidad con los datos.**
- No se afirma que el modelo «predice con precisión» antes de evaluarlo: las métricas salen de los **datos reales**.
- Si no hay datos reales, se puede usar **datos sintéticos solo para probar el flujo técnico**, indicándolo con claridad. **Nunca** se presentan esas métricas como resultados de la tesis.
- Los datos históricos los debe aportar el responsable del proyecto antes de la fase de ML (a más tardar a mediados de enero si se sigue el calendario referencial).

---

## 12. Cómo pasar el diseño SQL a Django

> **Los archivos SQL son el diseño de referencia (modelo físico, sección 4.3.4 de la tesis).** En el sistema real, Django crea las tablas desde los modelos y las migraciones. **No ejecutar los SQL y luego `migrate` sobre la misma base**: Django intentaría crear las tablas otra vez y chocaría.

**Camino recomendado.**
1. Modelos de Django con `Meta.db_table` igual al nombre de las tablas del diseño, en apps por módulo (`usuarios`, `catalogos`, `productores`, `parcelas`, `campanias`, `seguimiento`, `produccion`, `ml`, `alertas`…).
2. Triggers, funciones, la vista y los índices únicos parciales como **migraciones `RunSQL`** (los índices parciales también se pueden declarar con `UniqueConstraint(condition=…)`).
3. Los datos iniciales como **migración de datos o fixtures** (`loaddata`), que cumplen el papel de «seeders».
4. Probar el resultado comparándolo con los SQL de referencia.

**Modelo de usuario.** Debe definirse **antes del primer `migrate`** y declararse con `AUTH_USER_MODEL = "usuarios.Usuario"`. Debe incluir `rol` como **clave foránea a `Rol`** (no un campo de texto) y `telefono`. Como los permisos son propios (`roles`/`permisos`), conviene no usar los grupos ni permisos de Django: al heredar de `AbstractUser`, se pueden eliminar asignando `groups = None` y `user_permissions = None` (verificar en la documentación de Django).

> **Estado:** los cuatro pasos de este camino ya están hechos para el app `usuarios` (Semana 1) y para `productores` (Semana 3): modelos con `db_table` del diseño, datos iniciales como migración (solo usuarios), triggers como `RunSQL` y comparación en `docs/comparacion_sprint1.md` y `docs/comparacion_semana3.md`. `groups = None` / `user_permissions = None` **funciona en Django 5.2** y evita las tablas `auth_user_groups` y `auth_user_user_permissions`.

**Notas útiles.**
- Los códigos `PROD-0001` y `P-001` los genera la base si llegan vacíos; Django debe enviarlos como `NULL` o vacío para que el trigger actúe (o generarlos en la aplicación, pero no duplicar la lógica).
- Los triggers recalculan `cantidad_base`, `produccion_kg` y `rendimiento_kg_ha`: los valores que mande Django para esos campos se sobrescriben.
- Los errores de los triggers llegan a Django como excepciones de base de datos; conviene traducirlos a mensajes claros para el usuario.
- `makemigrations` y `migrate` funcionan igual que en Laravel (`php artisan migrate`), pero el archivo de migración se genera a partir de los modelos.

---

## 13. Metodología y hoja de ruta (Scrum)

**Roles.** Product Owner: el responsable del proyecto (prioriza y aprueba). Desarrollador: Ivan Rony Condori Inquilla. Sprints de 2 semanas; revisión de sprint con demostración; tablero en Trello o GitHub Projects.

**Orden acordado: el sistema primero, el ML después.** Calendario **referencial** (sin fecha límite definida):

| Sprint | Objetivo |
|---|---|
| 0 | Requerimientos y alcance |
| 1 | Base de datos, login, roles y permisos |
| 2 | Productores y parcelas |
| 3 | Cultivos, variedades y campañas |
| 4 | Actividades y producción con rendimiento (**Demo 1**) |
| 5 | Recursos e insumos, clima |
| 6 | Incidencias y línea de tiempo |
| 7 | Validaciones de calidad de datos y auditoría |
| 8 | Dashboard y alertas |
| 9 | Reportes PDF y Excel |
| 10 | Pruebas y correcciones (**Entrega 1: sistema de seguimiento completo**) |
| 11 | Importación de datos históricos y vista de entrenamiento |
| 12 | ML: exploración, limpieza y transformación |
| 13 | ML: entrenamiento y evaluación |
| 14 | Integración y pantalla de predicción (**Demo 2**) |
| 15 | Predicho vs. real e historial de predicciones |
| 16 | Pruebas del ML, manual y documentación (**Entrega final**) |

> Las pantallas de React duplican el trabajo de cada sprint (API más interfaz). Se recomienda sumar un margen de 15 a 20 % y ajustar el calendario según la velocidad real del equipo tras los sprints 1 y 2.

**Alcance excluido (acordado):** sensores, app móvil nativa y modo sin conexión, cuentas para productores, análisis de costos y rentabilidad, modelos adicionales (XGBoost), mapa interactivo avanzado, recuperación de contraseña por correo.

---

## 14. Pendientes y preguntas abiertas

### Pendientes técnicos
1. ~~Completar `settings.py`~~ (hecho en la Semana 1).
2. ~~Modelo de usuario con rol (FK) y primera migración~~ (hecho: `usuarios.0001`–`0003`).
3. ~~Endpoints de login y refresh, y vista con los permisos del usuario~~ (hecho en la Semana 2; ver `docs/api_autenticacion.md`).
4. ~~Rate limit del login~~ (hecho en la Semana 2: throttle por IP + bloqueo por cuenta).
5. Modelos de Django del resto de tablas, con triggers y vista como migraciones. ~~Los de ubicación, productores, parcelas, campañas, catálogos y actividades ya están;~~ quedan recursos, clima, incidencias, producción, ML y sistema.
6. ~~Pantalla de login en React y rutas protegidas por permiso~~ (hecho en la Semana 2; el menú ya filtra por permiso).
7. Pantallas de cada módulo y administración de usuarios/roles desde React (cambio de contraseña y recuperación pendientes).
8. Diagrama entidad-relación y modelo lógico (Capítulo IV, 4.3.2 y 4.3.3).

### Actualizar en el documento de requerimientos (`.tex`)
- Subir el **bloqueo por intentos fallidos** de «deseable» a **esencial**.
- Ajustar el **CU-05**: las actividades se registran con la campaña `PLANIFICADA` o `EN_PRODUCCION`.
- Agregar: densidad de siembra, unidad en la producción, catálogo de agentes, y **administración de roles y permisos** (nuevo requerimiento funcional).
- Convertir la matriz de permisos en «configuración inicial de los tres roles».
- Opcional: tabla de tecnologías propuestas (sin versiones exactas).
- ~~Actualizar el `README.md` con la sección de base de datos y Docker~~ (hecho en la Semana 1).

### Preguntas para el responsable del proyecto
- **Entregar la lista real de provincias, distritos y comunidades** (la Semana 3 quedó con un CSV inventado en `datos/`; decisión 1).
- **Confirmar la regla de enmascarado de DNI/teléfono por rol** (propuesta actual: Administrador y Técnico completos, Coordinador enmascarado; decisión 4).
- ¿El productor que registra un técnico **se le asigna automáticamente**? (semana 4).
- ¿Cuándo se hace la predicción dentro del ciclo del cultivo?
- ¿Qué cultivos tendrán datos? (supuesto: quinua y cañihua)
- ¿Cuántas campañas históricas con rendimiento conocido existen y en qué formato están?
- ¿Cuál es la fecha límite para sustentar, y cuándo necesita el sistema funcionando?
- Valores a validar: el quintal (46 kg), los umbrales de rendimiento, los 30 días sin actividad, las etapas fenológicas y los agentes de ejemplo.
- ¿La densidad de siembra se mide en kg/ha, plantas/m² o ambas? (Semana 7, pregunta I: se implementaron **las dos** del diseño; la API exige valor+unidad juntos y `UNIDADES_DENSIDAD` del frontend fija la medida en un solo sitio).
- **¿Rechazar fechas futuras en actividades?** (Semana 7, pregunta H): implementado (`fecha ≤ hoy` en hora de **America/Lima**); pendiente de confirmar — si se admite planificar a futuro, se retira la comprobación.
- ¿Cuántos técnicos usarán el sistema a la vez? (supuesto: 20 usuarios simultáneos)
- ¿Qué plataforma y presupuesto habrá para el despliegue?
- ¿La universidad exige una plantilla o formato específico para el documento?

---

## 15. Instrucciones para agentes de IA

1. **Idioma:** responder en español. Nombres de tablas y campos en español, sin tildes ni eñe.
2. **No inventar.** Todo lo marcado como *por confirmar* o *CONFIRMAR* se pregunta; no se rellena con valores supuestos sin avisar.
3. **No presentar datos de ejemplo como reales.** Los datos sintéticos solo sirven para probar el flujo y deben identificarse como tales.
4. **No cambiar el diseño de la base de datos sin avisar**: cualquier cambio debe actualizarse en los tres archivos SQL, en este documento y volver a probarse.
5. **Respetar el orden de los archivos SQL:** `DB_sql/01_tablas.sql`, `DB_sql/02_reglas_y_vista.sql`, `DB_sql/03_insert.sql`. Usarlos solo en bases vacías de prueba, nunca junto con `migrate` sobre la misma base. Recuerda: son el diseño de muestra/referencia; las tablas reales las crea Django con sus migraciones.
6. **No ejecutar `migrate` antes de tener el modelo de usuario propio** declarado en `AUTH_USER_MODEL`.
7. **Entorno de trabajo:** Windows y PowerShell. El entorno vive en `backend/venv`: primero `cd backend`, luego `.\venv\Scripts\Activate.ps1`, y ejecutar los comandos uno por uno. Docker Desktop debe estar abierto para que la base esté disponible.
8. **Secretos:** nunca escribir claves en el código ni subirlas a Git. Van en `.env`, que está en `.gitignore`.
9. **Verificar versiones y características actuales** de librerías y plataformas (por ejemplo Render) antes de afirmarlas; cambian con el tiempo.
10. **Seguridad:** los permisos se verifican siempre en el backend. Contraseñas con hash. Rate limit en el login.
11. **Calidad de datos primero:** cualquier función que escriba datos debe respetar las reglas de negocio de las secciones 4 y 6, aunque la base también las imponga.
12. **Explicar con claridad:** el responsable del proyecto debe poder entender y defender cada decisión. Preferir soluciones simples y documentadas.
13. **Honestidad en el ML:** no prometer precisión; las métricas salen de los datos reales.

---

## 16. Índice de archivos y glosario

### Archivos del proyecto

| Archivo | Contenido |
|---|---|
| `README.md` | Descripción, tecnologías, estructura y cómo ejecutar en local (Docker, migrate, superusuario, admin, pruebas) |
| `requerimientos.tex` | Documento de requerimientos (LaTeX, XeLaTeX): RF, RNF, reglas de negocio, casos de uso, alcance, supuestos y criterios de aceptación. **Está fuera del repositorio**, en `D:\ProyectoJoseLuis\Documentos\Requerimeintos\requerimientos.tex` |
| `DB_sql/01_tablas.sql` | 32 tablas, restricciones, índices y comentarios (solo estructura). Carpeta **ignorada en Git** |
| `DB_sql/02_reglas_y_vista.sql` | 13 funciones, 24 triggers y la vista `vw_dataset_entrenamiento` |
| `DB_sql/03_insert.sql` | Roles, permisos, catálogos, unidades, agentes y parámetros iniciales |
| `backend/` | Proyecto Django `config` + app `usuarios`, `manage.py`, `requirements.txt`, `venv/` (ignorado en Git) |
| `backend/usuarios/models.py` | `Permiso`, `Rol`, `RolPermiso`, `Usuario` (Semana 1) |
| `backend/usuarios/migrations/` | `0001_initial` (4 tablas), `0002_datos_iniciales` (3 roles, 55 permisos, 101 asignaciones), `0003_trigger_rol_sistema` |
| `backend/usuarios/views.py` | Login, renovación, cierre de sesión, `/me` y alta de usuarios (Semana 2) |
| `backend/usuarios/permisos.py` | `TienePermiso` (clase reutilizable) y `permisos_de_peticion` (1 consulta) |
| `backend/usuarios/ratelimit.py` | Contador de fallos y bloqueo temporal del login (caché) |
| `backend/usuarios/excepciones.py` | `manejar_excepciones`: 429 en español con cabecera `Retry-After` |
| `backend/usuarios/autenticacion.py` | Lee el access desde la cookie `sigpa_access` (o Bearer) |
| `backend/usuarios/serializers.py` | Datos de sesión (`DatosUsuarioSerializer`) y alta (`CrearUsuarioSerializer`) |
| `backend/usuarios/urls.py` | `/api/auth/*` y `/api/usuarios/` |
| `backend/usuarios/admin.py` | Panel con los 4 modelos + acción «Desbloquear acceso» |
| `backend/usuarios/tests.py` | **20 pruebas** (`manage.py test usuarios`): Semana 1 y Semana 2 |
| `backend/usuarios/management/commands/crear_superusuario.py` | Crea el admin inicial desde `ADMIN_USERNAME`/`ADMIN_PASSWORD` del `.env` (idempotente) |
| `backend/productores/models.py` | `Provincia`, `Distrito`, `Comunidad`, `Productor` (Semana 3, `db_table` del diseño) |
| `backend/productores/migrations/` | `0001_initial` (4 tablas), `0002_funciones_y_triggers` (fechas, código `PROD-…`, reversible) |
| `backend/productores/serializers.py` | Lectura anidada, escritura con validaciones y enmascarado por rol (`ROLES_CON_DATOS_COMPLETOS`) |
| `backend/productores/views.py` | 5 viewsets con permisos por acción, `?busqueda=`, filtros y `…/estado/` (sin `DELETE`) |
| `backend/productores/urls.py` | `/api/ubicaciones/{provincias,distritos,comunidades}/` y `/api/productores/` |
| `backend/productores/admin.py` | Panel con filtros por jerarquía/estado, búsqueda y `creado_por` en el alta |
| `backend/productores/tests.py` | **17 pruebas** (numeradas 21–37); con las de `usuarios` suma 37 |
| `backend/productores/management/commands/cargar_ubicacion.py` | Carga idempotente de ubicación desde CSV/Excel (`openpyxl`), con informe de fallidas |
| `frontend/` | React con Vite (JavaScript), Axios y React Router (`node_modules/` ignorado en Git) |
| `frontend/src/api/` | Cliente Axios con cookies y renove *single-flight* + `mensajeDeError` |
| `frontend/src/context/` | `SesionProvider` (hidratación con `/me`) y `useSesion` |
| `frontend/src/routes/` | `RutaProtegida`, `RutaSoloInvitado` y `opcionesMenu.js` (menú = rutas, con permisos) |
| `frontend/src/pages/` | Login, Inicio, módulo en preparación, 403 y 404 |
| `docs/api_autenticacion.md` | Contrato de la API de sesión, ejemplos curl y mapeo HU-07..HU-14 |
| `docs/decisiones_seguridad.md` | Decisiones de la Semana 2 (tokens, cookies, rate limit, despliegue) |
| `docs/comparacion_sprint1.md` | Comparación columna por columna: `01_tablas.sql` vs migraciones Django, con las diferencias justificadas |
| `docs/decisiones_semana3.md` | Las 7 decisiones de la Semana 3 + preguntas abiertas |
| `docs/comparacion_semana3.md` | Diseño vs migraciones de `provincias`, `distritos`, `comunidades`, `productores` y sus 2 triggers |
| `docs/api_ubicacion_productores.md` | Contrato de los 4 recursos nuevos, errores verificados y ejemplos curl |
| `docs/coleccion_api_semana3.json` | Colección de Postman: 36 peticiones con `pm.test`, validadas 36/36 (sin secretos) |
| `docs/tablero.md` | Tablero de la Semana 3: HU-15..HU-22 con evidencias y próximos pasos |
| `datos/ejemplo_ubicaciones.csv` | Datos de ubicación **inventados** (pruebas); se retira con la lista real |
| `docker-compose.yml` | PostgreSQL 17 en Docker (en la raíz del proyecto) |
| `.env` | Variables de entorno: `DB_*`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_*` y `ADMIN_*` (**no** se sube a Git) |
| `.env.example` | Plantilla versionada de `.env` (sin secretos; sí va a Git) |
| `.gitignore` | Ignora `.env`, `DB_sql/`, `venv/`, `node_modules/`, `dist/`, `__pycache__` y `db.sqlite3` |
| `CONTEXTO_PROYECTO.md` | Este documento |

### Glosario

| Término | Significado |
|---|---|
| Campaña | Ciclo productivo de un cultivo en una parcela (por ejemplo 2025-2026) |
| Rendimiento | Producción por unidad de superficie, en kg/ha (producción total ÷ superficie cosechada) |
| Campaña cerrada | Campaña con producción y rendimiento real registrados; es una fila de entrenamiento |
| Dataset | Tabla plana con una fila por campaña cerrada, sus variables predictoras y el rendimiento real |
| Fuga de datos (*data leakage*) | Usar como entrada información que solo existe después del evento que se predice |
| Unidad base | Unidad a la que se normalizan todas las cantidades (kg, ha, m³, jornal, hora) |
| Trigger | Regla automática de la base de datos que se ejecuta al insertar, modificar o borrar |
| Seed | Dato inicial que se carga al crear la base (roles, catálogos, parámetros) |
| Rate limit | Límite de peticiones o intentos fallidos para proteger el login |
| Product Owner | Persona que prioriza el trabajo y aprueba las entregas en Scrum |
| JWT | Token firmado que el backend entrega al iniciar sesión y React envía en cada petición |
| msnm | Metros sobre el nivel del mar |
