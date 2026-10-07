# SIGPA-GA

**Sistema web para el seguimiento de productores con algoritmos de Machine Learning en el Proyecto de Mejora Agroproductiva de Granos Andinos en Puno – 2025**

> **Estado actual:** Semana 2 completada — autenticación JWT en cookies httpOnly, permisos por vista, rate limit del login y el arranque de React (login, rutas protegidas y menú por permisos). 20 pruebas verdes. Pendiente: resto de módulos de la base y pantallas.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework |
| Autenticación | `djangorestframework-simplejwt` + `token_blacklist` (login/refresh/logout/me en cookies httpOnly) |
| CORS | `django-cors-headers` (`CORS_ALLOW_CREDENTIALS`, origen del Vite dev) |
| Variables de entorno | `python-dotenv` (lee `.env` de la raíz) |
| Base de datos | PostgreSQL 17 en Docker (`docker-compose.yml`) |
| Frontend | React 19 (Vite), Axios con renove *single-flight*, React Router 7 |
| Control de versiones | Git |

## Estructura

```
Sistema/
├── backend/
│   ├── config/                    # settings.py (JWT, throttle, caché, CORS, logs)
│   ├── usuarios/                  # Modelos, admin, API y pruebas
│   │   ├── models.py              # Permiso, Rol, RolPermiso, Usuario
│   │   ├── views.py               # login, refresh, logout, me, crear usuario
│   │   ├── permisos.py            # Clase TienePermiso (reutilizable)
│   │   ├── ratelimit.py           # Bloqueo por intentos fallidos (caché)
│   │   ├── excepciones.py         # Respuestas 429 en español + Retry-After
│   │   ├── autenticacion.py       # Lee el access desde la cookie
│   │   ├── serializers.py         # Datos de sesión y alta de usuario
│   │   ├── urls.py                # /api/auth/* y /api/usuarios/
│   │   ├── admin.py               # Panel + acción «Desbloquear acceso»
│   │   ├── tests.py               # 20 pruebas (semanas 1 y 2)
│   │   ├── management/commands/   # crear_superusuario
│   │   └── migrations/            # 0001 estructura, 0002 datos, 0003 trigger
│   ├── manage.py
│   └── requirements.txt
├── DB_sql/                        # Diseño de referencia (ignorado en Git)
├── docs/
│   ├── api_autenticacion.md       # Endpoints, cookies, rate limit y mapeo HU-07..14
│   ├── decisiones_seguridad.md    # Por qué cada decisión de la Semana 2
│   └── comparacion_sprint1.md     # Diseño SQL vs migraciones Django
├── frontend/                      # React con Vite (login, rutas y menú por permisos)
│   └── src/
│       ├── api/                   # Cliente axios (cookies + renove single-flight)
│       ├── context/               # SesionProvider / useSesion
│       ├── components/            # Layout con menú filtrado por permisos
│       ├── pages/                 # Login, Inicio, 403, 404
│       └── routes/                # Rutas protegidas y configuración del menú
├── .env.example                   # Plantilla de variables de entorno (sí va a Git)
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Requisitos previos

- Python 3.12 o 3.13
- Docker Desktop (PostgreSQL 17)
- Node.js 22 (LTS) y npm
- Git

## Ejecución en local

### 1. Base de datos (Docker)

```powershell
docker compose up -d
```

### 2. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate              # crea las tablas y carga roles/permisos
python manage.py crear_superusuario   # crea el admin desde ADMIN_* del .env
python manage.py runserver
```

Se abre en `http://127.0.0.1:8000`. Si PowerShell bloquea la activación del entorno, ejecuta una sola vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

- **Panel de administración:** `http://127.0.0.1:8000/admin/`. Las credenciales se toman de `ADMIN_USERNAME` y `ADMIN_PASSWORD` en `.env` (copia `.env.example` si no tienes uno; el comando `crear_superusuario` es idempotente y no pisa usuarios existentes).
- **Pruebas:** `python manage.py test usuarios` (**20 pruebas**: semilla, trigger, panel y toda la autenticación de la Semana 2).
- El diseño de las tablas está en `DB_sql/` (solo referencia; **no** se ejecuta sobre la base real) y su comparación con lo creado por Django en `docs/comparacion_sprint1.md`.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Se abre en `http://localhost:5173` y redirige al login. Crea un `.env` a partir de
`.env.example` (`VITE_API_URL=http://localhost:8000/api`). Verifica con `npm run lint`
y `npm run build`.

### 4. Probar la sesión rápido (sin navegador)

```powershell
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/
curl.exe -s -b cookies.txt http://localhost:8000/api/auth/me/
```

El contrato completo (cookies, errores, rate limit y mapeo HU-07..HU-14) está en
`docs/api_autenticacion.md`; las decisiones de seguridad, en `docs/decisiones_seguridad.md`.

## Próximos pasos

- Resto de modelos (catálogos, productores, parcelas, campañas…) con sus migraciones y sus endpoints.
- Pantallas de cada módulo (el menú y las rutas ya filtran por permiso).
- Administración de usuarios/roles desde React, cambio de contraseña y recuperación.
- Dashboard, alertas, reportes y el módulo de Machine Learning.

## Autor

Ivan Rony Condori Inquilla
