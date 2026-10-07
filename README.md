# SIGPA-GA

**Sistema web para el seguimiento de productores con algoritmos de Machine Learning en el Proyecto de Mejora Agroproductiva de Granos Andinos en Puno – 2025**

> **Estado actual:** Semana 3 completada — ubicación (provincias, distritos, comunidades) y productores con API REST, triggers de fechas y código automático, comando de carga CSV/Excel y panel admin. 37 pruebas verdes. Pendiente: parcelas, campañas y pantallas.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework |
| Autenticación | `djangorestframework-simplejwt` + `token_blacklist` (login/refresh/logout/me en cookies httpOnly) |
| CORS | `django-cors-headers` (`CORS_ALLOW_CREDENTIALS`, origen del Vite dev) |
| Variables de entorno | `python-dotenv` (lee `.env` de la raíz) |
| Carga de archivos | `openpyxl` (comando `cargar_ubicacion`: CSV y Excel) |
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
│   ├── productores/               # Semana 3: ubicación y productores
│   │   ├── models.py              # Provincia, Distrito, Comunidad, Productor
│   │   ├── serializers.py         # Lectura anidada, escritura y enmascarado
│   │   ├── views.py               # 5 viewsets con permisos por acción
│   │   ├── urls.py                # /api/ubicaciones/* y /api/productores/
│   │   ├── admin.py               # Panel con filtros y creado_por
│   │   ├── tests.py               # 17 pruebas (numeradas 21-37)
│   │   ├── management/commands/   # cargar_ubicacion (CSV y Excel)
│   │   └── migrations/            # 0001 tablas, 0002 funciones y triggers
│   ├── manage.py
│   └── requirements.txt
├── DB_sql/                        # Diseño de referencia (ignorado en Git)
├── datos/
│   ├── ejemplo_ubicaciones.csv    # Datos de prueba de ubicación (inventados)
│   └── LEEME.md
├── docs/
│   ├── api_autenticacion.md       # Endpoints, cookies, rate limit y mapeo HU-07..14
│   ├── api_ubicacion_productores.md  # Contrato de los 4 recursos nuevos
│   ├── coleccion_api_semana3.json # 36 peticiones de Postman (validadas)
│   ├── decisiones_seguridad.md    # Por qué cada decisión de la Semana 2
│   ├── decisiones_semana3.md      # Decisiones de la Semana 3
│   ├── comparacion_sprint1.md     # Diseño SQL vs migraciones Django (usuarios)
│   ├── comparacion_semana3.md     # Diseño SQL vs migraciones (ubicación/productores)
│   └── tablero.md                 # HU-15..HU-22 con evidencias
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

- **Panel de administración:** `http://127.0.0.1:8000/admin/`. Las credenciales se toman de `ADMIN_USERNAME` y `ADMIN_PASSWORD` en `.env` (copia `.env.example` si no tienes uno; el comando `crear_superusuario` es idempotente y no pisa usuarios existentes). En el panel también se gestionan las provincias, distritos, comunidades y productores.
- **Carga de ubicación:** `python manage.py cargar_ubicacion --archivo ..\datos\ejemplo_ubicaciones.csv` (acepta `.csv` y `.xlsx`, es **idempotente** e informa de filas creadas, existentes y fallidas).
- **Pruebas:** `python manage.py test` (**37 pruebas**: 20 de usuarios/autenticación + 17 de ubicación y productores).
- El diseño de las tablas está en `DB_sql/` (solo referencia; **no** se ejecuta sobre la base real) y su comparación con lo creado por Django en `docs/comparacion_sprint1.md` (usuarios) y `docs/comparacion_semana3.md` (ubicación y productores).

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
La API de ubicación y productores (HU-15..HU-22) está en
`docs/api_ubicacion_productores.md`, con sus decisiones en
`docs/decisiones_semana3.md` y una colección de Postman validada en
`docs/coleccion_api_semana3.json` (36 peticiones; las claves de prueba no se
suben: están en `.credenciales`).

## Próximos pasos

- Parcelas y campañas, con sus triggers (`fn_codigo_parcela`) y endpoints; resto de catálogos.
- Asignación de productores a técnicos y el filtro «solo mis productores».
- Pantallas de cada módulo en React (el menú y las rutas ya filtran por permiso).
- Administración de usuarios/roles desde React, cambio de contraseña y recuperación.
- Dashboard, alertas, reportes y el módulo de Machine Learning.

## Autor

Ivan Rony Condori Inquilla
