# SIGPA-GA

**Sistema web para el seguimiento de productores con algoritmos de Machine Learning en el Proyecto de Mejora Agroproductiva de Granos Andinos en Puno – 2025**

> **Estado actual:** Semana 23 completada — el sistema cubre las 10 áreas del diseño (usuarios/roles, ubicación, productores, parcelas, catálogos, campañas, seguimiento, producción, ML y auditoría) con API REST, triggers, frontend completo por permisos y 416 pruebas verdes. Pendiente: pulir entregas y documentación final.

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
│   ├── usuarios/                  # Modelos, admin, API, pruebas y comando crear_superusuario
│   ├── productores/               # Ubicación, productores, parcelas y asignaciones
│   ├── catalogos/                 # Cultivos, variedades, etapas, unidades, recursos, agentes
│   ├── campanias/                 # Campañas con estados y línea de tiempo
│   ├── seguimiento/               # Actividades, uso de recursos, clima e incidencias
│   ├── produccion/                # Cosecha, rendimiento y revisión
│   ├── importaciones/             # Importación de histórico (S20) y vista del dataset ML
│   ├── alertas/                   # Reglas, evaluación y gestión de alertas
│   ├── auditoria/                 # Eventos inmutables de auditoría
│   ├── dashboard/                 # Indicadores del panel
│   ├── reportes/                  # Informes y exportación
│   ├── ml/                        # Dataset, entrenamiento, modelos y predicciones
│   ├── sistema/                   # Parámetros, trabajador ML, respaldo y comandos varios
│   ├── manage.py
│   └── requirements.txt
├── datos/
│   ├── ejemplo_ubicaciones.csv    # Datos de prueba de ubicación (inventados)
│   └── LEEME.md
├── docs/                          # Decisiones, APIs, verificaciones y manuales
├── frontend/                      # React con Vite (login, menú por permisos y todas las pantallas)
│   └── src/
│       ├── api/                   # Cliente axios (cookies + renove single-flight)
│       ├── context/               # SesionProvider / useSesion
│       ├── components/            # Layout, Tabla, Modal, Paginacion, RuedaCarga…
│       ├── pages/                 # Pantallas de cada módulo
│       ├── routes/                # Rutas protegidas y menú por permisos
│       ├── utils/                 # Utilidades (detalle de auditoría, etc.)
│       └── scripts/               # Chequeo automático del menú (corre con npm run lint)
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

El camino completo (verificado desde una base vacía) es: base de datos →
entorno → migraciones → catálogos y ubicación → superusuario → backend →
frontend.

### 1. Base de datos (Docker)

```powershell
docker compose up -d
```

### 2. Entorno y backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env   # y rellenar DB_*, SECRET_KEY y ADMIN_*
python manage.py migrate               # crea las tablas y carga roles/permisos
python manage.py cargar_catalogos      # catálogos completos (idempotente)
python manage.py cargar_ubicacion      # provincias/distritos/comunidades de ejemplo
python manage.py runserver
```

Se abre en `http://127.0.0.1:8000`. Si PowerShell bloquea la activación del
entorno, ejecuta una sola vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Notas de cada paso:

- `migrate` trae de serie 3 roles (Administrador 55 permisos, Técnico de
  campo 32, Coordinador 14), 55 permisos, 26 filas base de catálogos y los 5
  parámetros del sistema; es la base que después solo crece.
- `cargar_catalogos` añade variedades, etapas fenológicas, agentes, recursos
  y el quintal; es idempotente (crea solo lo que falta, no pisa nada).
- `cargar_ubicacion` lee `datos/ejemplo_ubicaciones.csv` (acepta `.csv` y
  `.xlsx` con columnas provincia, distrito y comunidad); también es
  idempotente e informa de filas creadas, existentes y fallidas. **Sin estas
  ubicaciones no se puede registrar ningún productor.**
- **Pruebas:** `python manage.py test` (**416 pruebas** de las 11 apps del
  backend).
- El diseño de las tablas está en `DB_sql/` (solo referencia; **no** se
  ejecuta sobre la base real).

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Se abre en `http://localhost:5173` y redirige al login. Crea un `.env` a partir de
`.env.example` (`VITE_API_URL=http://localhost:8000/api`). Verifica con `npm run lint`
(y `npm run build`): el lint incluye además un chequeo que falla si una entrada del
menú no tiene pantalla real.

### 4. Administrador inicial (superusuario)

```powershell
cd backend
python manage.py crear_superusuario
```

- El username **no siempre es `admin`**: es el valor de `ADMIN_USERNAME` en
  tu `.env` (puede ser el nombre que quieras); la clave es `ADMIN_PASSWORD`.
- Es idempotente: si ese usuario ya existe no lo modifica.
- Crea la cuenta con el rol **Administrador** (los 55 permisos); con ella se
  entra tanto a la app (`http://localhost:5173`) como al panel
  `http://127.0.0.1:8000/admin/`, donde también se gestionan ubicaciones y
  productores.

### 5. Usuarios iniciales desde el sistema

Con la cuenta del Administrador entra a **Usuarios** en la app y crea los
otros dos roles (username a libre elección; aquí se sugieren `coordinador` y
`tecnico`):

| Usuario sugerido | Rol | Alcance |
|---|---|---|
| `ADMIN_USERNAME` (el tuyo) | Administrador | Todo el menú (55 permisos) + `/admin/` |
| `coordinador` | Coordinador | Solo lectura (14 permisos): no ve Usuarios, Roles ni Auditoría |
| `tecnico` | Técnico de campo | Crea y edita en campo (32 permisos); **solo ve los productores que se le asignen** |

Notas:

- **Cada usuario debe usar su propia contraseña, distinta y segura** (no
  reutilizar la del Administrador ni compartirla entre usuarios). El backend
  las valida con los validadores de Django y rechaza las débiles (cortas,
  comunes, numéricas o iguales al username).
- El Técnico de campo tiene `limita_a_asignados`: hasta que no se le asignen
  productores (ficha del productor → asignar técnico) verá listados vacíos.
- Las contraseñas de cada cuenta guárdalas en tu propio `.credenciales`
  (ignorado por Git), que es donde este proyecto las deja.

### 6. Probar la sesión rápido (sin navegador)

```powershell
curl.exe -s -c cookies.txt -H "Content-Type: application/json" `
  -d '{"username":"TU_USUARIO","password":"TU_CLAVE"}' http://localhost:8000/api/auth/login/
curl.exe -s -b cookies.txt http://localhost:8000/api/auth/me/
```

El contrato completo (cookies, errores, rate limit y mapeo HU-07..HU-14) está en
`docs/api_autenticacion.md`; las decisiones de seguridad, en `docs/decisiones_seguridad.md`.
La API de ubicación y productores (HU-15..HU-22) está en
`docs/api_ubicacion_productores.md`, con sus decisiones en
`docs/decisiones_semana3.md` y una colección de Postman validada en
`docs/coleccion_api_semana3.json` (36 peticiones; las claves de prueba no se
suben: están en tu `.credenciales` local).

## Opcional: datos de demostración

Para probar los flujos de ML y el dashboard con datos de relleno (todo
inventado y marcado como tal):

```powershell
cd backend
python manage.py datos_demostracion
```

Crea productores, parcelas, campañas (incluido el bloque V4 con patrón
aprendible para entrenar) y producciones. Para que la pantalla Entrenar
muestre el aviso de honestidad, define `ML_ORIGEN_DATOS=demostración` en
`.env` y reinicia el backend. Es idempotente: se puede ejecutar varias veces
sin duplicar nada.

## Próximos pasos

- Cierre de la Semana 23 (documentación y entrega).
- Ajustes finales de pulido y verificación de la interfaz con los 3 roles.

## Autor

Ivan Rony Condori Inquilla
