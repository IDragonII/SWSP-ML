# Decisiones de la Semana 19 (Entrega 1)

Registro de decisiones técnicas, de arquitectura y de proceso tomadas durante
la Semana 19 (8–14 feb 2025). Número continuo desde la Semana 1 (ver
`docs/decisiones_semana*.md`).

---

## 1. Planificación y alcance

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **69** | Sprint 10 (Semana 19) = solo pruebas, seguridad, respaldo, rendimiento, docs; **cero funciones nuevas**. | Entrega 1 = consolidación y hardening; no hay tiempo para features. |
| **70** | Numeración de pruebas: **318–325** (total 325). Semana 18 cerró en 317 real. | Trazabilidad exacta; cada prueba nueva tiene número único. |
| **71** | `requerimientos.tex` v1.3 = versión anterior + incorporar **§2 agregados** de `matriz_reglas_calidad.md` + declarar **§3 huecos** en sección «Limitaciones conocidas». | Trazabilidad completa; no se tocan triggers nuevos, solo declaración. |
| **72** | Commit único «semana 19» + tag `entrega-1` al final; no commits intermedios. | Historial limpio; la entrega es un todo atómico. |
| **73** | Colección de la Entrega 1 = `coleccion_api_semana18.json` **re-ejecutada en verde**. | Garantiza que la API completa funciona contra el código entregado. |
| **74** | Las 17 preguntas al responsable **no se hacen** (no hay responsable disponible). | Decisión pragmática; las dudas ya están documentadas en decisiones previas. |

---

## 2. Seguridad y configuración de producción

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **75** | Bloque `PRODUCCION` en `settings.py` (env `PRODUCCION`, default 0) controla: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (env `SECURE_HSTS_SECONDS`, default 31536000), `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `SECURE_PROXY_SSL_HEADER`. | Centraliza endurecimiento; test 321 verifica `check --deploy` limpio. |
| **76** | `ADMIN_URL` configurable por env (`ADMIN_URL`, default `admin/`), normalizado con barra final; fluye al URLconf. | Ofuscación básica del admin; test 321 verifica inyección. |
| **77** | `JWT_COOKIE_SECURE = True` en producción (ya estaba en settings:133). | Cookies solo HTTPS. |
| **78** | Logout requiere cookie `sigpa_refresh` válida; sin ella → 401. | Consistencia con JWT stateless + blacklist. |
| **79** | `AllowAny` **solo** en `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/logout/`. Verificado por test 319. | Superficie mínima expuesta. |
| **80** | Anónimo → 401 en todas las demás rutas × 5 métodos (GET/POST/PUT/PATCH/DELETE). Nunca 2xx. Verificado por test 320. | Defensa en profundidad. |
| **81** | `raise_request_exception` es atributo del `Client` (constructor), **no** kwarg de `get()`. Usado en test 322. | Django 5.2 API correcta. |

---

## 3. Matriz de rutas y permisos

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **82** | Módulo `sistema/matriz_rutas.py` introspecta `actions ∩ http_method_names` de cada ViewSet; cruza con `TienePermiso.permiso_requerido` por rol. | Fórmula exacta replicada del código (`productores/views.py:PermisosPorAccion`). |
| **83** | `RUTAS_EXENTAS` = rutas `AllowAny` (login, refresh, logout). Verificación en test 319: matriz = respuestas reales = AllowAny. | Fuente única de verdad. |
| **84** | Comando `matriz_rutas` genera `docs/matriz_rutas_por_rol.md` (552 líneas). Test 319 exige que el archivo no se desactualice. | Documentación viva. |
| **85** | `TienePermiso` sin `permiso_requerido` → 403; **no hay atajo `is_superuser`** (el rol manda). Verificado en matriz. | Consistencia con diseño de permisos por rol. |
| **86** | DRF valida permisos **antes** del manejador → 403 antes que 405. Reflejado en `esperado()` de la matriz. | Comportamiento real del framework. |

---

## 4. Respaldo y restauración

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **87** | Módulo `sistema/respaldo.py`: `volcar_bytes()`, `restaurar()`, `crear_bd()`, `eliminar_bd()`. Usa `pg_dump`/`psql` vía **Docker** (`docker exec sigpa_db … -U sigpa_user`). No requiere cliente local. | Entorno real = Docker; evita dependencias del host. |
| **88** | `PGPASSWORD` vía `env` en `subprocess`, **nunca** en CLI. | Seguridad: no aparece en `ps aux`. |
| **89** | Comando `respaldo_bd`: vuelca a `RESPALDO_DIR` (.env) **fuera del repositorio** (guarda que lo exige); `--clean --if-exists`; poda `RESPALDO_KEEP` (default 10). | Respaldos no se versionan; rotación automática. |
| **90** | Test 325: canoniza volcado para comparar (elimina `\restrict`/`\unrestrict` aleatorios de pg_dump 17 y normaliza forma `= ANY ((ARRAY[..])::text[])` vs `= ANY (ARRAY[(..)::text, ..])`). | pg_dump 17 no es byte-estable tras restaurar; canonización honesta. |
| **91** | Test 325 afirma **28 tablas de dominio** (37 totales − 9 Django/third-party) y **25 triggers** (`pg_trigger WHERE NOT tgisinternal`). | Números reales del esquema actual. |

---

## 5. Rendimiento y volumen

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **92** | Comando `datos_volumen` idempotente (marca «Datos de volumen (Semana 19)»). Parámetros: `--productores`, `--parcelas`, `--campanias`, `--actividades`, `--clima-dias`. | Reutilizable; CI usa escala reducida; docs usan escala completa. |
| **93** | Volumen objetivo (F4): 500 prod, 1 000 parc, 1 200 camp (1 000 activas + 200 históricas cerradas), 20 000 act, 100 000 clima (1 000 × 100 días). | Representativo del proyecto real. |
| **94** | Estrategia de campañas: 200 históricas 2025-2026 → producir → cerrar a CERRADA; luego 1 000 activas 2026-2027 en **todas** las parcelas. Respeta `uq_campania_activa_por_parcela` y `uq_campania_parcela_periodo`. | Igual que `datos_demostracion` V2. |
| **95** | Test 324 usa escala reducida (30/60/72/1200/20) en base de pruebas limpia; mide 5 endpoints; umbral **<2 s** conservador. | Rápido en CI; detecta regresiones. |
| **96** | `docs/rendimiento_entrega1.md` documenta resultados reducidos + extrapolación; nota que volumen objetivo requiere BD limpia (recrear). | Honestidad sobre limitación de medición. |

---

## 6. Herramientas de calidad

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **97** | `pip-audit` 2.10.1 → **0 vulnerabilidades** (14 deps en `requirements.txt`). | Cadena de suministro limpia. |
| **98** | `npm audit` (npm 10.9.4) → **0 vulnerabilidades**. | Frontend limpio. |
| **99** | `gitleaks` 8.30.1 (binario en `Temp/opencode/gitleaks/`) escanea historial (17 commits, 1 FP en fixture `password="ClaveDePrueba123"`) y árbol (357 archivos, mismo FP). `.env` excluido por `.gitignore`. | Secretos fuera del repo confirmado. |
| **100** | CLI `gitleaks`: `git`/`dir` toman ruta posicional; sin `--source`, sin `--exclude`; flags útiles: `--redact`, `--no-banner`, `--report-format`, `--report-path`. | Uso correcto documentado. |

---

## 7. Huecos de calidad (declarados, no corregidos)

| Nº | Hueco | Acción |
|----|-------|--------|
| **101** | Fecha futura: solo API, no BD. | Declarado en `limitaciones_conocidas.md` y `requerimientos.tex` v1.3. |
| **102** | Revisión pendiente al cerrar: solo API. | Idem. |
| **103** | Requisitos de `revisar`: solo interfaz. | Idem. |
| **104** | Alertas sin triggers en BD (Semana 15). | Idem; riesgo aceptado con mitigación (aviso 36 h). |
| **105** | Fechas de cosecha futuras: admitidas por diseño. | Idem. |

---

## 8. Documentación de la entrega

| Nº | Archivo | Descripción |
|----|---------|-------------|
| **106** | `docs/seguridad_entrega1.md` | Informe completo F2 (tools, gitleaks FP, tabla W corregida, matriz, errores/logs, controles, riesgos). |
| **107** | `docs/matriz_rutas_por_rol.md` | 552 líneas generadas por `matriz_rutas`; test 319 exige vigencia. |
| **108** | `docs/rendimiento_entrega1.md` | Medición test 324 + extrapolación; nota sobre volumen objetivo. |
| **109** | `docs/limitaciones_conocidas.md` | Declaración formal de huecos (§3 matriz + alertas). |
| **110** | `docs/resumen_pruebas_entrega1.md` | Tabla 318–325 con descripción y estado. |
| **111** | `requerimientos.tex` v1.3 | Versión + agregados §2 + limitaciones §3. |
| **112** | `CONTEXTO.md` | Actualizado con estado Semana 19 (ver decisión 113). |
| **113** | `CONTEXTO.md` | Añadida sección «Semana 19 — Entrega 1» con resumen de archivos, pruebas, comandos y decisiones clave. |

---

## 9. Cierre y tag

| Nº | Decisión | Justificación |
|----|----------|---------------|
| **114** | Suite completa ≥ 325 pruebas en verde + `lint`/`build` OK → commit «semana 19» + tag `entrega-1`. | Puerta de calidad única. |
| **115** | Guion de video 5 min: (1) login 3 roles, (2) ciclo campaña, (3) dashboard/alertas, (4) respaldo/restauración, (5) seguridad (deploy, logs), (6) rendimiento. | Cobertura visual de la entrega. |
| **116** | Retrospectiva: qué funcionó (matriz viva, tests E2E, respaldo canonizado), qué mejorar (volumen en BD limpia, alertas con triggers). | Aprendizaje para Sprint 11. |