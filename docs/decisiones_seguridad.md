# Decisiones de seguridad — Semana 2 (autenticación, permisos y rate limit)

> Documento de la Semana 2 del plan. Cada decisión queda anotada con su valor
> concreto, la fuente verificada y el riesgo aceptado. Los valores marcados como
> *parámetro* viven en el `.env` (nunca en Git) y son configurables sin tocar código.

---

## 1. Duración de los tokens

| Token | Duración | Parámetro | Por qué |
|---|---|---|---|
| Acceso | **15 minutos** | `JWT_ACCESS_MINUTOS=15` | Corto: si se roba, expira rápido. Es el que viaja en cada petición. |
| Renovación (refresh) | **7 días** | `JWT_REFRESCO_DIAS=7` | Largo: permite volver al navegador sin repetir contraseña, con rotación en cada uso. |

- Valores permitidos por la especificación: acceso 15–30 min; renovación 1–7 días. Elegimos el extremo más seguro de cada rango.
- **Rotación**: `ROTATE_REFRESH_TOKENS=True` → cada renovación devuelve un refresh nuevo y `BLACKLIST_AFTER_ROTATION=True` → el refresh anterior queda en la lista negra (una renovación solo sirve una vez).
- `UPDATE_LAST_LOGIN=False`: la documentación de simplejwt advierte que escribir `last_login` en cada login añade transacciones y puede usarse como vector de denegación de servicio. El `last_login` del panel de Django se ignora.

## 2. Dónde guarda React los tokens

**Decisión: cookies `httpOnly` (no localStorage).**

| Cookie | Contenido | Atributos |
|---|---|---|
| `sigpa_access` | Token de acceso | `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age` = 15 min, `Secure` según `JWT_COOKIE_SECURE` |
| `sigpa_refresh` | Token de renovación | `HttpOnly`, `SameSite=Lax`, `Path=/api/auth/` (solo viaja a los endpoints de auth), `Max-Age` = 7 días, `Secure` según `JWT_COOKIE_SECURE` |

- **Riesgo aceptado y registrado**: al ser `HttpOnly`, el JavaScript del frontend **no puede leer** los tokens → un fallo XSS no los expone desde el almacenamiento del navegador (que habría sido el caso con localStorage). A cambio:
  - En desarrollo (`DEBUG=True`, localhost) `Secure=False` porque el tráfico es HTTP; **en producción `JWT_COOKIE_SECURE=True`** y todo por HTTPS.
  - `SameSite=Lax` impide que un sitio externo envíe las cookies en peticiones de tipo POST; además todos los POST son con `Content-Type: application/json`, lo que fuerza un *preflight* CORS que solo se aprueba para el origen exacto del frontend (`CORS_ALLOWED_ORIGINS`, con `CORS_ALLOW_CREDENTIALS=True`). No se usa la sesión de Django en la API, por lo que el middleware CSRF no aplica; la combinación anterior cumple su función.
- Además del valor del refresh en el cuerpo, los endpoints aceptan `Authorization: Bearer <access>` para clientes nativos (curl, pruebas de Django). El navegador no lo usa.
- **Fuente**: documentación de simplejwt sobre la *blacklist app* (https://django-rest-framework-simplejwt.readthedocs.io/en/stable/blacklist_app.html), verificada el 06/10/2026.

## 3. Cerrar sesión de verdad

- Se activa la **lista de tokens invalidados de simplejwt**: app `rest_framework_simplejwt.token_blacklist` en `INSTALLED_APPS`.
- **Tablas que agrega (verificadas en su documentación y en su código fuente)**:

| Tabla | Columnas | Nota |
|---|---|---|
| `token_blacklist_outstandingtoken` | `id`, `user_id` (FK a `usuarios`, `SET_NULL`), `jti` (único), `token`, `created_at`, `expires_at` | Todo refresh emitido queda registrado |
| `token_blacklist_blacklistedtoken` | `id`, `token_id` (OneToOne → outstanding, CASCADE), `blacklisted_at` | Marca de invalidación |

- Cerrar sesión = **black-list del refresh** (`RefreshToken(...).blacklist()`), borrado de las cookies y 401 en cualquier reuso. El access caduca solo en ≤15 min (es la contrapartida de tenerlo corto).
- La app de blacklist incluye su **propio admin** (se puede inspeccionar desde `/admin/`) y el comando `flushexpiredtokens` para limpiar tokens vencidos (cron en producción).

## 4. Qué devuelve el login

```json
POST /api/auth/login/
Set-Cookie: sigpa_access=...; HttpOnly; SameSite=Lax; Max-Age=900
Set-Cookie: sigpa_refresh=...; HttpOnly; SameSite=Lax; Path=/api/auth; Max-Age=604800
200 {
  "usuario": {
    "id": 1, "username": "admin", "nombre_completo": "…",
    "rol": { "id": 1, "nombre": "Administrador" },
    "permisos": ["usuarios.ver", "usuarios.crear", "..."]
  }
}
```

- **Los permisos viajan en la respuesta y NO dentro del token**: un cambio de rol/permiso se refleja en la siguiente consulta a `/api/auth/me/` sin esperar a que venza el access.
- **Mensaje de error genérico único**: `401 {"detail": "Credenciales incorrectas."}` para usuario inexistente, clave incorrecta **y usuario desactivado** — nunca se revela si la cuenta existe (prueba 10 y 11).

## 5. Rate limit — opciones verificadas antes de elegir

Se revisó la documentación vigente (06/10/2026) de las opciones actuales:

| Opción | Estado | ¿Cubre lo pedido? |
|---|---|---|
| **django-axes 8.3.1** (11-feb-2026) | Vigente, soporta Django 5.2; 429 por defecto, `Retry-After`, bloqueo por usuario/IP | Sí, pero añade 2 tablas (`AccessAttempt`/`AccessLog`), integración con DRF solo «funcional» vía señales y desbloqueo manual por comandos, no desde el panel |
| **django-ratelimit** 4.x | Vigente | Solo límite de peticiones (no bloquea cuenta); explícitamente no maneja IPs detrás de proxy |
| **DRF `ScopedRateThrottle` + implementación propia** | Incluido en DRF 3.18 (ya instalado) | Sí: límite por IP + bloqueo de cuenta con mensaje y tiempo exactos, acción «Desbloquear» en el panel, cero dependencias nuevas y cero tablas nuevas |

**Decisión: opción propia con DRF** (limite por IP con `ScopedRateThrottle` + bloqueo de cuenta en la caché de Django). Se elige por control total de los mensajes 429, desbloqueo desde el panel, sin tablas nuevas y sin dependencias.

## 6. Valores definidos

| Parámetro | Valor | Efecto |
|---|---|---|
| `LOGIN_RATE_IP` | `30/min` | Peticiones al login por IP cada minuto (contador en caché, se desconta solo) |
| `LOGIN_INTENTOS` | `5` | Intentos fallidos de una misma cuenta antes de bloquearla |
| `LOGIN_BLOQUEO_MINUTOS` | `15` | Minutos de bloqueo automático de la cuenta |
| (sin parámetro) | 429 | Respuesta tanto del límite por IP como del bloqueo de cuenta |

- **429 del bloqueo**: `{"detail": "Demasiados intentos fallidos. Inténtalo de nuevo en N minutos."}` — indica cuánto esperar y **no da pistas sobre la cuenta** (aplica igual a cuentas inexistentes).
- **429 del límite por IP**: `{"detail": "Demasiadas solicitudes. Intenta de nuevo en N segundos."}`.
- **Desbloqueo**: por tiempo (la caché vence sola) y **manual desde el panel de Django** (acción «Desbloquear acceso» sobre el usuario).
- **Log**: los eventos `login_fallido`, `login_bloqueado` y `login_desbloqueado` se escriben con el logger `sigpa.seguridad`. La tabla de auditoría real llega en el **Sprint 7**.

## 7. Superusuario y la clase de permisos

- **Decisión: el superusuario se rige por su rol.** La clase `TienePermiso` no hace atajos para `is_superuser`: consulta los códigos de `roles_permisos` a través del rol, igual que para cualquier usuario; lo mismo vale para la lista de permisos que devuelven login y `/me`.
- En la práctica el superusuario creado por `crear_superusuario` tiene el rol **Administrador**, que ya posee los 55 permisos.
- **Sin consultas repetidas**: los códigos se resuelven una vez por petición y se guardan en el objeto `request`; cualquier comprobación posterior dentro de la misma petición reutiliza esa lista.

## 8. Notas anotadas para el despliegue

1. **Contadores en memoria compartida**: el límite por IP y el bloqueo de cuenta usan la caché de Django (en desarrollo, `LocMemCache`). Si el sistema corre con varios procesos o servidores, hay que cambiar el backend de caché a uno compartido (Redis/Memcached); si no, cada proceso contaría por su cuenta.
2. **IP real detrás de proxy**: la IP que ve Django es la del proxy/nginx. Con DRF la identificación usa `X-Forwarded-For` cuando existe; en producción ese header solo debe ser aceptado desde el proxy de confianza, nunca expuesto directamente a Internet.
3. **Cookies `Secure`**: activar `JWT_COOKIE_SECURE=True` al pasar a HTTPS.
4. **`flushexpiredtokens`**: programar una tarea diaria para limpiar la tabla `token_blacklist_outstandingtoken`.
