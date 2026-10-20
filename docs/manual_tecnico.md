# Manual técnico - SIGPA-GA

Instalación, configuración, operación y mantenimiento del sistema.
Complementa [`manual_usuario.md`](manual_usuario.md) (uso por rol) y
[`api_ml.md`](api_ml.md) (contrato de la API de Machine Learning).

---

## 1. Requisitos

- **Python 3.13** (probado) con `venv`.
- **Node.js 18+** (usa `fetch` el validador de colecciones) para el
  frontend y las pruebas de API.
- **PostgreSQL 17** (probado en el contenedor Docker `sigpa_db`).
- `pg_dump`/`psql`: si no están en el PATH local, el sistema los usa
  **a través de `docker exec`** en el contenedor de `.env`
  (`DB_DOCKER_CONTAINER`).

## 2. Instalación

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
# Solo si se van a ejecutar los notebooks (análisis local):
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt

# Frontend
cd ..\frontend
npm install
npm run lint   # 0 problemas
npm run build  # 0 errores
```

## 3. Configuración (`.env` en la raíz del repositorio)

Nunca se sube a Git. Variables principales (los valores son del entorno
de desarrollo):

| Variable | Para qué |
|---|---|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` | Django. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Para `manage.py crear_superusuario`. |
| `LOGIN_RATE_IP`, `LOGIN_INTENTOS`, `LOGIN_BLOQUEO_MINUTOS` | Throttle del login (por defecto 30/min por IP; subirlo p. ej. a `120/min` cuando se valida una colección completa). |
| `API_PAGE_SIZE` | Tamaño de página de la API (20). |
| `RESPALDO_DIR`, `RESPALDO_KEEP` | Carpeta de respaldos (fuera de Git) y cuántos conserva. |
| `DB_DOCKER_CONTAINER` | Contenedor para `pg_dump`/`psql` vía `docker exec`. |
| `IMPORTACION_DIR` | Carpeta del histórico importado (Semana 20). |
| `ML_EXPORT_DIR` | Carpeta de datasets de Machine Learning: **fuera del repositorio y de sincronizadas en la nube**; el comando rechaza rutas dentro de Git. |

`ML_PREDICCION_RATE` (opcional) ajusta el límite de predicciones por
hora y usuario (por defecto `30/hour`).

## 4. Arranque y migraciones

```powershell
cd backend
.\venv\Scripts\python.exe manage.py migrate        # aplica todo, incl. ml/0001 y produccion/0003
.\venv\Scripts\python.exe manage.py check          # 0 issues
.\venv\Scripts\python.exe manage.py makemigrations --check   # sin cambios pendientes
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

# En otra terminal:
cd frontend ; npm run dev
```

Revertir hasta el punto previo a las tablas de Machine Learning (la
migración `produccion/0003` depende de `ml/0001`, así que se revierte
primero la función completa y luego las tablas):

```powershell
.\venv\Scripts\python.exe manage.py migrate produccion 0002   # restaura fn_produccion_post parcial
.\venv\Scripts\python.exe manage.py migrate ml zero
```

## 5. Datos de demostración

```powershell
.\venv\Scripts\python.exe manage.py datos_demostracion        # datos de operación (idempotente)
.\venv\Scripts\python.exe manage.py datos_ml_demostracion     # CSV de demostración del ML en ML_EXPORT_DIR
```

`datos_ml_demostracion` genera 48 filas con un patrón lineal
**inventado** (semilla 42, determinista) y las marca como
`demostracion`; con las 13 campañas reales de la BD de desarrollo el
criterio no elige ningún modelo (ninguno mejora a la línea base), por
eso la demostración del flujo usa ese CSV. **Ninguna cifra de
demostración se presenta como resultado de tesis.**

## 6. Machine Learning: pipeline completo

```powershell
# 1) Exportar el dataset de la BD (vista vw_dataset_entrenamiento)
.\venv\Scripts\python.exe manage.py exportar_dataset

# 2) Entrenar los 3 candidatos y aplicar el criterio escrito
.\venv\Scripts\python.exe manage.py entrenar_modelos --version-modelo 1
#    -> ml_models/<algoritmo>_v1.joblib + manifiesto.json
#    -> ml_models/resultados_v1.json
#    -> docs/informe_resultados_ml.md

# 3) Registrar en la BD (permiso ml.entrenar) y activar (ml.activar_modelo)
.\venv\Scripts\python.exe manage.py registrar_modelo --usuario admin `
    --version-modelo 1 --desarrollo --activar
```

- `--desarrollo` es **obligatorio** para modelos entrenados con datos
  de demostración (decisión 221).
- El registro verifica la huella SHA-256 del `.joblib` contra
  `ml_models/manifiesto.json` y hace una predicción de prueba **antes**
  de tocar la base; la activación repite esas comprobaciones y deja
  un solo modelo activo, con auditoría `ACTIVAR`/`DESACTIVAR`.
- La versión usa `--version-modelo` (no `--version`: lo reserva Django).
- `--dry-run` valida sin escribir nada.
- Los notebooks (`notebooks/`) reproducen el entrenamiento sin subir
  salidas; el informe vive en `docs/informe_resultados_ml.md`.

## 7. Respaldo de la base

```powershell
.\venv\Scripts\python.exe manage.py respaldo_bd
```

Escribe en `RESPALDO_DIR` (fuera de Git) y conserva los últimos
`RESPALDO_KEEP`. Usa `pg_dump` local si existe; si no, `docker exec`
sobre `DB_DOCKER_CONTAINER`. **Si el motor de Docker está colgado, el
comando se queda esperando**: revisar `docker ps` antes de ejecutarlo.
Restaurar es `psql`/`docker exec psql` sobre el `.sql` generado.

## 8. Alertas

- Generación en vivo: 13 ganchos `transaction.on_commit`
  (`alertas/signals.py`).
- Barrido de atraso: `manage.py evaluar_alertas` (programar con cron o
  tarea programada cada ≤ 36 h). El endpoint `/api/alertas/evaluacion/`
  informa si el proceso está atrasado; la pantalla lo muestra.
- Sin worker/cron las alertas no se cierran solas: es la limitación
  declarada en [`limitaciones_conocidas.md`](limitaciones_conocidas.md).

## 9. Pruebas y colección de la API

```powershell
.\venv\Scripts\python.exe manage.py test          # 392 pruebas
cd ..\frontend ; npm run lint ; npm run build
```

La colección final es `docs/coleccion_api_semana22.json` (**598
peticiones**, 1125 aserciones). Se valida con el pipeline habitual:
BD temporal, migrate, siembra de usuarios + datos, servidor en el 8001
con `LOGIN_RATE_IP=120/min` y el validador de Node (`validar.js`, que
resuelve `{{variables}}` y la cabecera `sin-sesion`); se borra la BD y
se detiene el servidor al terminar. La siembra de la Semana 22 añade
las 3 campañas y el modelo activo de demostración que necesitan los
ítems 569-598.

Regenerar la matriz de rutas tras tocar la API:

```powershell
.\venv\Scripts\python.exe manage.py matriz_rutas   # docs/matriz_rutas_por_rol.md
```

## 10. Averías frecuentes

| Síntoma | Causa y arreglo |
|---|---|
| `docker ps` no responde y los respaldos cuelgan | Motor Docker colgado: reiniciar Docker Desktop y comprobar `docker ps` antes de `respaldo_bd`. |
| `test_sigpa_ga` no deja crear la BD de prueba | BD huérfana de un run interrumpido: borrarla (`DROP DATABASE ... WITH (FORCE)`) o usar `--keepdb`. |
| `Demasiadas solicitudes` en login o predicciones | Throttles: `LOGIN_RATE_IP` por IP y `ML_PREDICCION_RATE` por usuario. |
| `RuntimeError` en un POST sin barra final | La API usa rutas con `/` final (`APPEND_SLASH`); respetar el contrato de `docs/api_*.md`. |
| `El archivo … no coincide con el manifiesto` | El `.joblib` fue regenerado sin reentrenar o el manifiesto quedó viejo: repetir `entrenar_modelos` y copiar ambos artefactos juntos. |
