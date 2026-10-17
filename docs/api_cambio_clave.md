# API de cambio de contraseña — `POST /api/auth/cambiar-clave/` (RF-73, HU-112..HU-113)

> Documentación de la Semana 13. Ver `decisiones_semana13.md` para las
> decisiones de diseño y `verificacion_ui_semana13.md` para el checklist
> de navegador.

## 1. Flujo completo (HU-112/HU-113)

1. Un **administrador** usa «Restablecer contraseña» en la ficha de un
   usuario (Semana 12). La API coloca la **marca de sesión** (las otras
   sesiones del usuario quedan invalidadas) y ahora, además, **`debe_cambiar_clave = TRUE`**.
2. El usuario entra con su **contraseña temporal**: `login` devuelve
   `usuario.debe_cambiar_clave: true` en el payload (también lo expone
   `GET /api/auth/me/`).
3. La **puerta** `DebeCambiarClave` responde **403 «Debes cambiar tu
   contraseña antes de continuar.»** a toda la API excepto a las rutas
   libres (§2). El frontend redirige además a `/cambiar-clave`.
4. El usuario llama a `POST /api/auth/cambiar-clave/` con su contraseña
   actual y la nueva (§3).
5. El backend: valida con los **validadores de Django con el usuario de
   la sesión** (similitud con username incluida), ejecuta en un bloque
   atómico `set_password` + `debe_cambiar_clave=False` + **marca de
   sesión** (las otras sesiones se cierran) + evento **CAMBIAR_CLAVE**,
   limpia el contador de intentos, espera a que arranque el segundo
   siguiente a la marca y devuelve **cookies de sesión nuevas**: la
   interfaz sigue dentro sin volver a entrar.

## 2. Rutas libres de la puerta

Mientras `debe_cambiar_clave` está activo, solo responden:

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `POST /api/auth/logout/`
- `GET  /api/auth/me/`
- `POST /api/auth/cambiar-clave/`

Todo lo demás (incluido `GET /api/usuarios/` o `GET /api/roles/`)
responde **403** con el mensaje de la puerta, **antes** de cualquier
otra comprobación de permisos. El anónimo sigue recibiendo **401**.

## 3. El endpoint

| Método | Ruta | Permiso | Respuesta |
|---|---|---|---|
| POST | `/api/auth/cambiar-clave/` | `IsAuthenticated` (+ ruta libre de la puerta) | 200 / 400 / 401 / 429 |

**Cuerpo** (JSON):

```json
{
  "password_actual": "SigpaGA2026!",
  "password_nueva": "NuevaClave2026!"
}
```

**200**:

```json
{
  "detail": "Contraseña actualizada.",
  "usuario": { "id": 3, "username": "coordinador", "debe_cambiar_clave": false, "…": "…" }
}
```

La respuesta rota las cookies `sigpa_access`/`sigpa_refresh` (emite
tokens nuevos) y **el refresh anterior deja de servir** (401 en
`refresh`/`me`).

### Errores

| Código | Causa | Mensaje |
|---|---|---|
| 400 | `password_actual` incorrecta | «La contraseña actual no es correcta.» (cadena plana, no lista; no distingue si el usuario existe) |
| 400 | `password_nueva` inválida | Validadores de Django en la clave (obligatoria, longitud, numérica, común, **similar al usuario**), en forma de lista por campo |
| 400 | Faltan campos | «Este campo es obligatorio.» (por campo) |
| 401 | Sesión expirada o sin cookies | Estándar de JWT |
| 429 | Más de 5 intentos en la hora | «Demasiados intentos de cambio de contraseña. Intenta de nuevo en N minuto(s).» + `{"retry_after": N}` + cabecera **`Retry-After`** |

- El límite (§4) se registra **antes** de validar: cuenta todas las
  peticiones al endpoint, válidas o no.
- Un **cambio exitoso limpia la ventana**: el usuario que acierta no
  queda castigado por los intentos fallidos previos.
- Los validadores se ejecutan con **`user` de la sesión**, de modo que
  `admin_clave123` para un usuario `admin` se rechaza por similitud.

## 4. Límite de intentos

- **5 intentos** por usuario y hora (`usuarios/ratelimit.py`, clave de
  caché `sigpa:cambio_clave:{username}`).
- El **sexto** recibe **429** con `retry_after` (segundos restantes) y
  cabecera `Retry-After`; la ventana no se limpia por logout ni por el
  paso del tiempo hasta expirar la clave de caché.
- Diferente del **bloqueo de login** (por IP, marca `bloqueado` en la
  cuenta): aquí no se bloquea el acceso, solo se enfría el endpoint de
  cambio.

## 5. Notas de implementación (hallazgos de F4)

- La puerta **no llegaba** a los viewsets que sobrescriben
  `get_permissions()` (p. ej. `PermisosPorAccion` de productores) ni a
  `RolViewSet`; se antepone explícitamente en ambos.
- El `iat` de los tokens tiene precisión de **segundo**: sin esperar a
  que arranque el segundo siguiente a la marca, las cookies recién
  emitidas en el mismo segundo quedaban invalidadas (401 al instante).
  Se usa `esperar_tras_marca(user_id)` en `cambiar-clave` y en `login`.
- `validate_password` sin `user` no revisaba la similitud con el nombre
  de usuario; se pasa `context={'request': request}` en el serializer
  para que `UserAttributeSimilarityValidator` funcione.

## Coleccion de pruebas (Postman)

docs/coleccion_api_semana13.json — validada en la fase F7: **430/430 peticiones
con codigo y aserciones en verde (793/793 aserciones)**; los items nuevos de
cambio de clave son los **411-421** (restablecer con marca, puerta 403 con
rutas libres /me y cambiar-clave, validadores con el usuario y la contrasena
actual, cookies nuevas sin relogin y ciclo completo), **422-428** (limite de 5
intentos/hora → 429 con retry_after) y **429-430** (evento CAMBIAR_CLAVE).

