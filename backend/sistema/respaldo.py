"""Respaldo y restauración de la base de datos (Semana 19 / Entrega 1).

La base vive en el contenedor Docker `sigpa_db` (postgres:17): el cliente
`pg_dump`/`psql` se ejecuta DENTRO del contenedor con `docker exec`, así
no hace falta instalar el cliente local. Si `pg_dump` existe en el PATH
de la máquina (despliegue nativo), se usa directamente con `PGPASSWORD`
en el entorno del proceso (nunca en la línea de comandos).

- El comando `respaldo_bd` vuelca a `RESPALDO_DIR` (.env), una carpeta
  FUERA del repositorio (hay una guarda que lo exige).
- La prueba 325 usa estas mismas funciones: vuelca la base de pruebas,
  la restaura en una base temporal y comprueba que los dos volcados
  coinciden byte a byte; la misma prueba afirma que las migraciones
  desde cero dejan 29 tablas de dominio y 25 triggers.
"""
import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings


class RespaldoError(Exception):
    """Fallo de la herramienta de respaldo (cliente ausente o pg_dump/psql)."""


def _base():
    bd = settings.DATABASES["default"]
    return bd["NAME"], bd["USER"], bd.get("HOST", "localhost"), bd.get("PORT", "5432")


def _cliente():
    """('local', None) si hay pg_dump en el PATH; si no, ('docker', contenedor)."""
    if shutil.which("pg_dump"):
        return "local", None
    contenedor = os.getenv("DB_DOCKER_CONTAINER", "").strip()
    if contenedor:
        return "docker", contenedor
    raise RespaldoError(
        "No hay pg_dump en el PATH ni DB_DOCKER_CONTAINER en el .env: "
        "instala el cliente de PostgreSQL o indica el contenedor."
    )


def _entorno(extra=None):
    entorno = dict(os.environ)
    _, usuario, _, _ = _base()
    password = os.getenv("DB_PASSWORD")
    if password:
        entorno.setdefault("PGPASSWORD", password)
    if extra:
        entorno.update(extra)
    return entorno


def _lanzar(argv, entrada=None):
    proceso = subprocess.run(
        argv, input=entrada, capture_output=True, env=_entorno()
    )
    if proceso.returncode != 0:
        detalle = proceso.stderr.decode("utf-8", "replace").strip()
        raise RespaldoError(f"{' '.join(argv[:3])}… falló: {detalle[:400]}")
    return proceso.stdout


def volcar_bytes(bd=None, extra=()):
    """pg_dump en texto plano de `bd` (por defecto la activa) → bytes."""
    nombre, usuario, host, puerto = _base()
    bd = bd or nombre
    modo, contenedor = _cliente()
    if modo == "docker":
        argv = ["docker", "exec", contenedor, "pg_dump", "-U", usuario, "-d", bd]
    else:
        argv = ["pg_dump", "-U", usuario, "-h", host, "-p", puerto, "-d", bd]
    argv += ["--no-owner", "--no-privileges", *extra]
    return _lanzar(argv)


def volcar_a_archivo(ruta, bd=None, extra=()):
    """pg_dump a `ruta` (creando carpetas si faltan) → bytes escritos."""
    datos = volcar_bytes(bd=bd, extra=extra)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return len(datos)


def restaurar(bd, datos):
    """psql -f - con `datos` (un volcado plano) sobre la base `bd`."""
    nombre, usuario, host, puerto = _base()
    modo, contenedor = _cliente()
    if modo == "docker":
        argv = [
            "docker", "exec", "-i", contenedor, "psql", "-U", usuario,
            "-d", bd, "-v", "ON_ERROR_STOP=1", "-1", "-f", "-",
        ]
    else:
        argv = [
            "psql", "-U", usuario, "-h", host, "-p", puerto, "-d", bd,
            "-v", "ON_ERROR_STOP=1", "-1", "-f", "-",
        ]
    return _lanzar(argv, entrada=datos)


def crear_bd(bd):
    """Crea una base de datos vacía (si no existe, no falla)."""
    _, usuario, host, puerto = _base()
    modo, contenedor = _cliente()
    if modo == "docker":
        argv = ["docker", "exec", contenedor, "createdb", "-U", usuario, bd]
    else:
        argv = ["createdb", "-U", usuario, "-h", host, "-p", puerto, bd]
    proceso = subprocess.run(argv, capture_output=True, env=_entorno())
    if proceso.returncode != 0:
        texto = proceso.stderr.decode("utf-8", "replace")
        if "already exists" not in texto:
            raise RespaldoError(f"createdb {bd}: {texto.strip()[:400]}")


def eliminar_bd(bd):
    """Elimina una base temporal de respaldo (si existe)."""
    _, usuario, host, puerto = _base()
    modo, contenedor = _cliente()
    if modo == "docker":
        argv = ["docker", "exec", contenedor, "dropdb", "-U", usuario, "--if-exists", bd]
    else:
        argv = ["dropdb", "-U", usuario, "-h", host, "-p", puerto, "--if-exists", bd]
    _lanzar(argv)
