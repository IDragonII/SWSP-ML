# Seguridad — Entrega 1 (Semana 19)

Informe de auditoría y endurecimiento de la Entrega 1. Acompaña a las
pruebas **319–323** (`backend/sistema/tests_entrega1.py`), a la matriz
generada `docs/matriz_rutas_por_rol.md` y a `docs/decisiones_seguridad.md`.

## 1. Herramientas: resultado

| Herramienta | Versión | Alcance | Resultado |
|---|---|---|---|
| `pip-audit -r backend/requirements.txt` | 2.10.1 | 14 dependencias fijadas de `requirements.txt` | **Sin vulnerabilidades conocidas** |
| `npm audit` (en `frontend/`) | npm 10.9.4 | `package-lock.json` completo | **0 vulnerabilidades** |
| `gitleaks git` | 8.30.1 | Historial completo del repositorio (17 commits escaneados; 18 en `HEAD`) | **1 hallazgo → falso positivo** (§2) |
| `gitleaks dir` | 8.30.1 | 357 archivos versionados (`git ls-files -co --exclude-standard`) | **1 hallazgo → el mismo falso positivo** |

Comandos exactos (reproducibles):

```bash
pip-audit -r backend/requirements.txt
cd frontend && npm audit
gitleaks git <ruta-repositorio> --no-banner --redact --report-format json --report-path historial.json
git ls-files -co --exclude-standard | xargs gitleaks dir --no-banner --redact --report-format json --report-path arbol.json
```

## 2. Hallazgo de gitleaks clasificado

`generic-api-key` en `backend/usuarios/tests.py` (línea 86 del commit
`a46fec4a` «semana 1», hoy línea 94): el literal `password="ClaveDePrueba123"`
de un usuario de prueba. **No es una credencial real**: el usuario solo
existe en la base de datos de las pruebas (`Usuario.objects.create_superuser`
dentro de un `TestCase`). Se clasifica como falso positivo y no se reescribe
el historial por una clave de fixture; la única clave secreta real del
proyecto (`SECRET_KEY`) vive en `.env`, que `.gitignore` excluye y que
gitleaks no alcanza ni en el historial ni en el árbol (§1, `ls-files`
con `--exclude-standard`).

## 3. Endurecimiento de despliegue (`config/settings.py`, `config/urls.py`)

Nueva bandera `PRODUCCION=1` en el `.env` (apagada en desarrollo local):

| Ajuste | Valor con `PRODUCCION=1` | Aviso de `check --deploy` que cubre |
|---|---|---|
| `SECURE_SSL_REDIRECT` | `True` | W008 |
| `SESSION_COOKIE_SECURE` | `True` | W012 |
| `CSRF_COOKIE_SECURE` | `True` | W016 |
| `SECURE_HSTS_SECONDS` | `31536000` (1 año, configurable) | W004 |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | W005 |
| `SECURE_HSTS_PRELOAD` | `True` | W021 |
| `SECURE_PROXY_SSL_HEADER` | `("HTTP_X_FORWARDED_PROTO", "https")` | detrás de proxy TLS |

Además, **la ruta del panel de Django es configurable** con `ADMIN_URL`
(`config/urls.py`, por defecto `admin/`, siempre con barra final): en
producción se sirve con una ruta no estándar para no anunciar `/admin/`.

Prueba **321**: `manage.py check --deploy` con `DEBUG=False`,
`PRODUCCION=1`, `SECRET_KEY` aleatoria (≥50 caracteres) y
`ADMIN_URL=panel-interno/` → **«System check identified no issues
(0 silenced)»** — ni un aviso silenciado, todo por configuración.
La misma prueba verifica que `ADMIN_URL` fluye al `URLconf`.

Valores recomendados para el `.env` de producción:

```bash
DEBUG=False
PRODUCCION=1
SECRET_KEY=<aleatoria, token_urlsafe(48) o superior>
ALLOWED_HOSTS=<dominio>
CORS_ALLOWED_ORIGINS=https://<dominio>
JWT_COOKIE_SECURE=1
ADMIN_URL=<ruta-no-estandar>/
```

## 4. Superficie de la API: matriz por rol (pruebas 319 y 320)

- **107 rutas** bajo `/api/` × 5 métodos (GET/POST/PUT/PATCH/DELETE) =
  535 comprobaciones; las 191 rutas del panel de Django quedan **fuera**
  de la matriz (se protegen con `ADMIN_URL`, sesión Django + CSRF y las
  recomendaciones de §6).
- **Solo 3 rutas son `AllowAny`**: `/api/auth/login/`, `/api/auth/refresh/`
  y `/api/auth/logout/`. Las dos primeras validan sus propias credenciales;
  `logout` lee la cookie de refresh y **sin ella responde 401** (comprobado:
  la sesión sigue protegida). Todo lo demás nace en **401** para el
  anónimo — la prueba 320 lo verifica método por método (nunca 2xx).
- **Prueba 319**: las respuestas reales con los tres roles coinciden con
  `docs/matriz_rutas_por_rol.md`, que se genera desde la introspección del
  `URLconf` + `roles_permisos` con `python manage.py matriz_rutas` (si el
  documento queda desactualizado, la prueba falla).

## 5. Errores y registros (pruebas 322 y 323)

- **322**: con `DEBUG=False`, una excepción interna devuelve un **500
  genérico** — sin `Traceback`, `Exception Value` ni rutas de `settings.py`
  en la respuesta (el trazo solo va al registro del servidor).
- **323**: tras un flujo de login correcto, login fallido, alta por API,
  cambio de contraseña con clave errónea y logout, el log de
  `sigpa.seguridad` **no contiene ninguna contraseña, token JWT («eyJ»)
  ni `SECRET_KEY`**, y sí registra los eventos legítimos
  (`login_correcto`, `login_fallido`).

## 6. Controles vigentes que respaldan el informe

- **JWT en cookies httpOnly + `SameSite=Lax`** (`decisiones_seguridad.md` §2):
  decisión mantenida; el riesgo aceptado anotado es que el token no sea
  legible desde JavaScript (mitiga XSS) a cambio de gestionarlo solo en
  servidor. `JWT_COOKIE_SECURE=1` en producción.
- **Rate limit de login** por IP (`ScopedRateThrottle`, 30/min, clave por
  `REMOTE_ADDR`, sin fiarse de `X-Forwarded-For`) + **bloqueo de cuenta**
  a los 5 fallos durante 15 min — pruebas 215 y 220.
- **Cambio obligatorio de contraseña** (`DebeCambiarClave`, HU-112): toda
  la API queda en 403 hasta cambiarla, salvo las 5 rutas de sesión.
- **CORS**: origen único del frontend con credenciales (`CORS_ALLOWED_ORIGINS`).
- **API nace cerrada** (DRF por defecto `IsAuthenticated` + `TienePermiso`),
  permiso por código leído del rol (**el superusuario no tiene atajo:
  se rige por su rol**) y matriz de permisos 121/14/32 (admin/coordinador/
  técnico) reflejada en `docs/matriz_rutas_por_rol.md`.
- **Auditoría de eventos** (LOGIN, CREAR, EXPORTAR…) con pantalla y
  reporte, verificable en la prueba 318.

## 7. Riesgos aceptados y limitaciones

1. **Panel de Django fuera de la matriz 319/320**: se protege por
   `ADMIN_URL` no estándar, sesión y CSRF; recomendación de despliegue:
   no exponerlo en Internet sin restricción de red (firewall/VPN).
2. **HSTS solo con `PRODUCCION=1`**: activarlo en local castigaría el
   navegador HTTP; por eso vive tras la bandera.
3. **Falso positivo de gitleaks** en la clave de fixture de test (§2):
   se documenta en lugar de reescribir el historial.
4. **`SECURE_PROXY_SSL_HEADER`** solo es válido detrás de un proxy que
   fije `X-Forwarded-Proto`: desplegar sin proxy exige dejarlo fuera
   (la bandera `PRODUCCION` lo emite siempre; ver §3).
