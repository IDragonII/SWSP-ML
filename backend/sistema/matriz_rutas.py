"""Matriz de rutas por rol (Semana 19 / Entrega 1).

Fuente única de verdad para el documento generado
`docs/matriz_rutas_por_rol.md` y para las pruebas 319 y 320:

- introspección de `config.urls` (solo el árbol `api/`: 107 rutas; el
  panel de Django queda fuera y se trata en `docs/seguridad_entrega1.md`);
- código de permiso por ruta y método con la MISMA fórmula que aplica la
  API en ejecución (`PermisosPorAccion.get_permissions`:
  `PERMISOS.get(accion, permiso_requerido)`, donde `accion` es el mapeo
  del método HTTP a la acción del router; sin acción → código base);
- permisos reales de cada rol leídos de `roles_permisos` (el superusuario
  se rige por su rol: no hay atajos para `is_superuser`).

El documento sale de introspección + BD, sin sondear la API; la prueba
319 comprueba que las respuestas reales (sondeos con los tres roles)
coinciden con este mismo cálculo, y la 320 que el anónimo no ve nada.
"""
import re
from pathlib import Path

from django.conf import settings
from django.urls import URLResolver, get_resolver
from rest_framework.permissions import AllowAny

from usuarios.models import RolPermiso

# Métodos que sondea la matriz. HEAD hereda de GET y OPTIONS lo resuelve
# DRF después de los permisos: se dejan fuera a propósito.
METODOS = ("get", "post", "put", "patch", "delete")

# Roles del sistema (los mismos de Entrega1Base y de usuarios/migrations).
ROLES = ("Administrador", "Coordinador", "Técnico de campo")

# Rutas sin permiso por diseño: solo validan la sesión ellas mismas.
# (`logout` es AllowAny porque lee la cookie de refresh directamente y,
# sin ella, responde 401: la sesión sigue protegida.)
RUTAS_EXENTAS = ("/api/auth/login/", "/api/auth/refresh/", "/api/auth/logout/")


def ruta_doc():
    """docs/matriz_rutas_por_rol.md, en la raíz del repositorio."""
    return Path(settings.BASE_DIR).parent / "docs" / "matriz_rutas_por_rol.md"


def _recorrer(patrones, prefijo=""):
    for patron in patrones:
        sufijo = str(patron.pattern)
        if isinstance(patron, URLResolver):
            yield from _recorrer(patron.url_patterns, prefijo + sufijo)
        else:
            yield prefijo + sufijo, patron


def _muestra(ruta):
    """Patrón de URL → URL de sondeo: `(?P<pk>…)` → 999999 y cualquier
    otro parámetro → `x` (detalle inexistente: 404, nunca datos reales)."""
    url = re.sub(r"\(\?P<pk>[^)]+\)", "999999", ruta)
    url = re.sub(r"\(\?P<[A-Za-z_][\w]*>[^)]+\)", "x", url)
    url = re.sub(r"\([^)]*\)", "x", url)
    return "/" + url.replace("^", "").replace("$", "")


def rutas_api():
    """Rutas del árbol `api/` con su introspección.

    Cada entrada: `ruta` (URL de sondeo), `tipo` ('viewset'|'apiview'),
    `permitidos` (métodos con manejador), `acciones` (método → acción,
    solo viewsets), `requerido` y `permisos_vista` (el dict PERMISOS,
    solo viewsets) y `allow_any`.
    """
    resultado = []
    for ruta, patron in _recorrer(get_resolver().url_patterns):
        if not ruta.startswith("api/"):
            continue
        func = patron.callback
        if hasattr(func, "actions"):
            vista = getattr(func, "cls", None)
            # DRF comprueba http_method_names ANTES del manejador: una
            # acción registrada en el router puede seguir respondiendo
            # 405 (p. ej. TipoActividadViewSet no admite POST de alta).
            http = set(getattr(vista, "http_method_names", METODOS))
            resultado.append({
                "ruta": _muestra(ruta),
                "tipo": "viewset",
                "permitidos": set(func.actions) & http,
                "acciones": dict(func.actions),
                "requerido": getattr(vista, "permiso_requerido", None),
                "permisos_vista": getattr(vista, "PERMISOS", {}),
                "allow_any": False,
            })
        else:
            vista = getattr(func, "view_class", None)
            clases = getattr(vista, "permission_classes", None)
            if clases is None:
                clases = tuple(
                    settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
                )
            http = set(getattr(vista, "http_method_names", METODOS))
            resultado.append({
                "ruta": _muestra(ruta),
                "tipo": "apiview",
                "permitidos": {
                    m
                    for m in METODOS
                    if vista is not None and hasattr(vista, m) and m in http
                },
                "acciones": None,
                "requerido": getattr(vista, "permiso_requerido", None),
                "permisos_vista": {},
                "allow_any": any(issubclass(c, AllowAny) for c in clases),
            })
    return resultado


def permisos_de_rol(nombre_rol):
    """Códigos de permiso que el rol tiene en la BD (máx. 1 consulta)."""
    return set(
        RolPermiso.objects.filter(rol__nombre=nombre_rol).values_list(
            "permiso__codigo", flat=True
        )
    )


def esperado(info, metodo, permisos=None, anon=False):
    """Estado que DEBE devolver la API.

    Valores: `401` sin sesión · `403` sin permiso · `405` método sin
    manejador · `manejo` respuesta de negocio (2xx o 400/404/409/422/429)
    · `exenta` ruta AllowAny (su propia validación de credenciales).
    """
    permitido = metodo in info["permitidos"]
    if info["allow_any"]:
        return "exenta" if permitido else "405"
    if anon:
        return "401"
    if info["tipo"] == "viewset":
        accion = info["acciones"].get(metodo)
        codigo = info["permisos_vista"].get(accion, info["requerido"])
    else:
        codigo = info["requerido"]
    if codigo and codigo not in permisos:
        return "403"
    return "manejo" if permitido else "405"


def aceptables(valor):
    """Estados HTTP admitidos para cada valor de `esperado`."""
    ok_2xx = set(range(200, 300))
    if valor == "401":
        return {401}
    if valor == "403":
        return {403}
    if valor == "405":
        return {405}
    if valor == "exenta":
        # AllowAny: su propia validación (401/400) o éxito; nunca 403/500.
        return ok_2xx | {400, 401, 404, 429}
    return ok_2xx | {400, 404, 409, 422, 429}


def generar_markdown():
    """El documento `docs/matriz_rutas_por_rol.md` completo."""
    rutas = sorted(rutas_api(), key=lambda i: i["ruta"])
    permisos = {rol: permisos_de_rol(rol) for rol in ROLES}
    exentas = sum(1 for i in rutas if i["allow_any"])
    lineas = [
        "# Matriz de rutas por rol (Entrega 1)",
        "",
        "> Generado por `python manage.py matriz_rutas` — **no editar a mano**.",
        "> Fuente: introspección de `config.urls` (árbol `api/`) +",
        "> `roles_permisos` en la base de datos. La prueba 319 comprueba",
        "> que las respuestas reales coinciden con esta tabla y la 320 que",
        "> el usuario anónimo no ve ninguna.",
        "",
        f"- Rutas `api/`: **{len(rutas)}** × {len(METODOS)} métodos "
        f"= {len(rutas) * len(METODOS)} filas.",
        f"- Permiten acceso sin token ({', '.join(RUTAS_EXENTAS)}): "
        f"{exentas} rutas, con su propia validación de credenciales.",
        f"- Permisos por rol en la BD: "
        + " · ".join(f"{rol}: {len(permisos[rol])}" for rol in ROLES),
        "- El panel de Django (`/admin/`) queda fuera de esta matriz: "
        "ver `docs/seguridad_entrega1.md`.",
        "",
        "Leyenda: `401` sin sesión · `403` sin permiso · `405` el método "
        "no existe en esa ruta · `manejo` = respuesta de negocio (2xx o "
        "400/404/409/422/429) · `exenta` = AllowAny (valida su propia "
        "credencial: sin ella responde 401).",
        "",
        "| Ruta | Método | Anónimo | " + " | ".join(ROLES) + " |",
        "|---|---|---|" + "---|" * (len(ROLES) + 1),
    ]
    for info in rutas:
        for metodo in METODOS:
            celdas = [esperado(info, metodo, anon=True)]
            celdas += [
                esperado(info, metodo, permisos[rol]) for rol in ROLES
            ]
            lineas.append(
                f"| {info['ruta']} | {metodo.upper()} | "
                + " | ".join(celdas)
                + " |"
            )
    lineas.append("")
    return "\n".join(lineas)
