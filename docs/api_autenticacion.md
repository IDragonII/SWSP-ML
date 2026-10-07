# API de autenticación — Semana 2 (12–18 oct)

Referencia de los endpoints de sesión y permisos implementados en `backend/usuarios/`.
Todas las rutas van bajo `/api/` (montadas en `config/urls.py`). Todo el detalle de
decisiones de seguridad está en [`decisiones_seguridad.md`](decisiones_seguridad.md).

## Resumen

| Método | Ruta | Qué hace | Auth |
|---|---|---|---|
| POST | `/api/auth/login/` | Inicia sesión y fija cookies | — |
| POST | `/api/auth/refresh/` | Renueva access (+ rotación de refresh) | Cookie `sigpa_refresh` |
| POST | `/api/auth/logout/` | Blacklista el refresh y borra cookies | Cualquiera de las dos |
| GET | `/api/auth/me/` | Devuelve usuario, rol y permisos | Access |
| POST | `/api/usuarios/` | Crea un usuario (prueba de permisos) | Access + `usuarios.crear` |

## Cookies de sesión

| Cookie | Duración | Atributos |
|---|---|---|
| `sigpa_access` | 15 min (`JWT_ACCESS_MINUTOS`) | `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` si `JWT_COOKIE_SECURE=True` |
| `sigpa_refresh` | 7 días (`JWT_REFRESCO_DIAS`) | `HttpOnly`, `SameSite=Lax`, `Path=/api/auth/`, `Secure` si `JWT_COOKIE_SECURE=True` |

También se acepta `Authorization: Bearer <access>` para clientes que no usen cookies.
Los refresh se **rotan** en cada renovación y el anterior queda **blacklisteado**
(`rest_framework_simplejwt.token_blacklist`); cerrar sesión blacklistea el actual.

## Endpoints

### POST `/api/auth/login/`

```json
{ "username": "admin", "password": "********" }
```

**200** (cookies en la respuesta):

```json
{
  "usuario": {
    "id": 1,
    "username": "admin",
    "nombre_completo": "admin",
    "rol": { "id": 4, "nombre": "Administrador" },
    "permisos": ["actividades.crear", "...", "usuarios.ver"]
  }
}
```

**Errores:**

| Código | Cuerpo | Cuándo |
|---|---|---|
| 401 | `{"detail": "Credenciales incorrectas."}` | Clave mala, usuario inexistente o desactivado — **respuesta idéntica en los tres casos** |
| 429 | `{"detail": "Demasiados intentos fallidos. Inténtalo de nuevo en N minuto(s).", "retry_after": N}` + cabecera `Retry-After` | Cuenta bloqueada: `LOGIN_INTENTOS` (5) fallos → `LOGIN_BLOQUEO_MINUTOS` (15) min |
| 429 | `{"detail": "Demasiadas solicitudes. Intenta de nuevo en N segundos.", "retry_after": N}` | Límite por IP: `LOGIN_RATE_IP` (30/min), throttle `ScopedRateThrottle` |

Con la cuenta bloqueada **ni siquiera la contraseña correcta entra**. El fallo no revela
si el usuario existe.

### POST `/api/auth/refresh/`

Sin cuerpo: lee la cookie `sigpa_refresh`.

- **200** → `{"access": "...", "refresh": "..."}` + cookies nuevas (rotación).
- **401** → `{"detail": "Sesión inválida o expirada."}` si el refresh es basura,
  está vencido, ya rotado o blacklisteado (por logout).

### POST `/api/auth/logout/`

- **200** → `{"detail": "Sesión cerrada."}`; blacklista el refresh y borra las cookies.
- **401** → `{"detail": "No hay sesión activa."}` si no hay cookies o ya están invalidadas.

### GET `/api/auth/me/`

- **200** → `{"usuario": {…}}` (mismo objeto del login: rol + permisos actuales).
- **401** → sin token o con token basura/vencido.

Los permisos **no viajan en el token**: se leen de la base en cada consulta, por lo que
un cambio de rol/permisos se refleja en la siguiente llamada (verificado por la prueba 20).

### POST `/api/usuarios/`

```json
{ "username": "nuevo", "password": "Productor2026!", "rol": 2 }
```

- **200** → `{"detail": "Usuario creado.", "usuario": {…}}` — solo con permiso `usuarios.crear`.
- **401** sin sesión · **403** `{"detail": "No tienes permiso para realizar esta acción."}`
  con sesión pero sin permiso (clase `TienePermiso`, `permiso_requerido` en la vista).
- **400** validaciones: contraseña débil, usuario repetido, rol inexistente o vacío.

**Nota:** el superusuario **no tiene atajos**: se rige por los permisos de su rol
(comprobado con un superusuario cuyo rol es Coordinador → 403).

## Rate limit y bloqueo (implementación propia con DRF)

Se revisaron `django-axes` 8.3.1 y `django-ratelimit` antes de elegir; la decisión y
los valores están en `decisiones_seguridad.md` §5–6.

1. **Por IP** — `ScopedRateThrottle` con `throttle_scope = 'login'`
   (`DEFAULT_THROTTLE_RATES`), caché `LocMemCache` (caché compartida en despliegue).
2. **Por cuenta** — contador de fallos en caché (`usuarios/ratelimit.py`): 5 fallos
   seguidos → bloqueo de 15 min; un acierto limpia el contador; la acción
   **«Desbloquear acceso»** del panel admin lo reinicia a mano.
3. **Auditoría** — logger `sigpa.seguridad` con los eventos `login_fallido`,
   `login_bloqueado`, `login_correcto` y `login_desbloqueado`.

## Ejemplo de flujo con curl (PowerShell)

```powershell
# 1. Login (guarda cookies en un archivo)
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/

# 2. Quién soy (usa las cookies)
curl.exe -s -b cookies.txt http://localhost:8000/api/auth/me/

# 3. Renovar
curl.exe -s -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/auth/refresh/

# 4. Cerrar sesión
curl.exe -s -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/auth/logout/
```

## Cobertura de HU-07 a HU-14

> Los textos de los HU no están en este repositorio; este es el **mapeo propuesto**
> con la evidencia de cada uno.

| HU | Interpretación | Implementación | Evidencia |
|---|---|---|---|
| HU-07 | Iniciar sesión | `POST /api/auth/login/` + pantalla `Login.jsx` | Pruebas 9–11; render verificado |
| HU-08 | Renovar la sesión | `POST /api/auth/refresh/` con rotación + renove automático *single-flight* en `src/api/cliente.js` | Pruebas 12–13 |
| HU-09 | Cerrar sesión | `POST /api/auth/logout/` con blacklist + `cerrarSesion()` en React | Prueba 18 |
| HU-10 | Datos del usuario actual | `GET /api/auth/me/` + hidratación de `SesionProvider` | Pruebas 14, 20 |
| HU-11 | Verificación de permisos en API | Clase `TienePermiso` + `permiso_requerido` + `POST /api/usuarios/` | Pruebas 15–16 |
| HU-12 | Protección del login | Throttle por IP + bloqueo por cuenta + logs + acción admin | Pruebas 17, 19 |
| HU-13 | Sesión persistente en React | Cookies httpOnly + interceptor que renueva y reintenta al cargar | Verificación manual con Edge headless |
| HU-14 | Menú/rutas por permisos | `opcionesMenu.js` (permiso por opción) + `RutaProtegida` + `tienePermiso()` | `npm run lint`/`build`; rutas generadas desde la misma configuración |

Las pantallas de administración de usuarios/roles, cambio de contraseña y recuperación
quedan fuera de esta semana (ver `CONTEXTO_PROYECTO.md` §14).
