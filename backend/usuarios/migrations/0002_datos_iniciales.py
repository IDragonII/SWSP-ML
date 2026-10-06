"""Datos iniciales: 3 roles, 55 permisos y 101 asignaciones (DB_sql/03_insert.sql).

Idempotente (get_or_create por clave única) y reversible (borra solo lo sembrado).
"""
from django.db import migrations

MODULOS = [
    ("usuarios", "Usuarios"),
    ("catalogos", "Catálogos"),
    ("productores", "Productores"),
    ("parcelas", "Parcelas"),
    ("campanias", "Campañas"),
    ("actividades", "Actividades"),
    ("recursos", "Recursos e insumos"),
    ("clima", "Clima"),
    ("incidencias", "Incidencias"),
    ("produccion", "Producción"),
]
ACCIONES = ["ver", "crear", "editar", "desactivar"]

PERMISOS_ESPECIALES = [
    ("roles.gestionar", "Roles", "gestionar", "Crear roles y asignarles permisos"),
    ("asignaciones.gestionar", "Asignaciones", "gestionar", "Asignar productores a técnicos"),
    ("parametros.gestionar", "Parámetros", "gestionar", "Configurar parámetros y umbrales del sistema"),
    ("importacion.ejecutar", "Importación", "ejecutar", "Cargar datos históricos desde Excel o CSV"),
    ("ml.entrenar", "Machine Learning", "entrenar", "Entrenar modelos de predicción"),
    ("ml.activar_modelo", "Machine Learning", "activar_modelo", "Elegir el modelo activo"),
    ("ml.ver_modelos", "Machine Learning", "ver_modelos", "Ver resultados de evaluación de los modelos"),
    ("ml.predecir", "Machine Learning", "predecir", "Solicitar una predicción de rendimiento"),
    ("ml.ver_predicciones", "Machine Learning", "ver_predicciones", "Ver el historial de predicciones"),
    ("dashboard.ver", "Dashboard", "ver", "Ver el dashboard de indicadores"),
    ("alertas.ver", "Alertas", "ver", "Ver alertas"),
    ("alertas.atender", "Alertas", "atender", "Marcar alertas como atendidas"),
    ("reportes.ver", "Reportes", "ver", "Ver reportes"),
    ("reportes.exportar", "Reportes", "exportar", "Exportar reportes a Excel y PDF"),
    ("auditoria.ver", "Auditoría", "ver", "Consultar el registro de auditoría"),
]

ROLES = [
    ("Administrador", "Gestiona usuarios, catálogos, parámetros y Machine Learning", True, False),
    ("Técnico de campo", "Registra y da seguimiento a sus productores asignados", True, True),
    ("Coordinador", "Consulta indicadores, avances y reportes (solo lectura)", True, False),
]

SEGUIMIENTO = [
    "productores", "parcelas", "campanias", "actividades",
    "recursos", "clima", "incidencias", "produccion",
]
TECNICO_ACCIONES = ("ver", "crear", "editar")
TECNICO_CODIGOS = [
    "catalogos.ver", "ml.predecir", "ml.ver_predicciones", "dashboard.ver",
    "alertas.ver", "alertas.atender", "reportes.ver", "reportes.exportar",
]
COORD_PREFAJOS = ["catalogos"] + SEGUIMIENTO
COORD_CODIGOS = [
    "ml.ver_predicciones", "dashboard.ver", "alertas.ver",
    "reportes.ver", "reportes.exportar",
]


def codigos_semillados():
    return [f"{m}.{a}" for m, _ in MODULOS for a in ACCIONES] + [
        c[0] for c in PERMISOS_ESPECIALES
    ]


def forward(apps, schema_editor):
    Permiso = apps.get_model("usuarios", "Permiso")
    Rol = apps.get_model("usuarios", "Rol")
    RolPermiso = apps.get_model("usuarios", "RolPermiso")

    for codigo_modulo, nombre in MODULOS:
        for accion in ACCIONES:
            Permiso.objects.get_or_create(
                codigo=f"{codigo_modulo}.{accion}",
                defaults={
                    "modulo": nombre,
                    "accion": accion,
                    "descripcion": f"{accion.capitalize()} {nombre.lower()}",
                },
            )

    for codigo, modulo, accion, descripcion in PERMISOS_ESPECIALES:
        Permiso.objects.get_or_create(
            codigo=codigo,
            defaults={"modulo": modulo, "accion": accion, "descripcion": descripcion},
        )

    for nombre, descripcion, es_sistema, limita in ROLES:
        Rol.objects.get_or_create(
            nombre=nombre,
            defaults={
                "descripcion": descripcion,
                "es_sistema": es_sistema,
                "limita_a_asignados": limita,
            },
        )

    permisos = {p.codigo: p for p in Permiso.objects.all()}
    roles = {r.nombre: r for r in Rol.objects.all()}

    asignaciones = {"Administrador": set(permisos)}
    asignaciones["Técnico de campo"] = {
        c for c in permisos
        if (c.split(".", 1)[0] in SEGUIMIENTO and c.split(".", 1)[1] in TECNICO_ACCIONES)
        or c in TECNICO_CODIGOS
    }
    asignaciones["Coordinador"] = {
        c for c in permisos
        if (c.split(".", 1)[0] in COORD_PREFAJOS and c.split(".", 1)[1] == "ver")
        or c in COORD_CODIGOS
    }

    for nombre_rol, codigos in asignaciones.items():
        rol = roles[nombre_rol]
        for codigo in codigos:
            RolPermiso.objects.get_or_create(rol=rol, permiso=permisos[codigo])


def reverse(apps, schema_editor):
    Permiso = apps.get_model("usuarios", "Permiso")
    Rol = apps.get_model("usuarios", "Rol")

    Rol.objects.filter(nombre__in=[nombre for nombre, *_ in ROLES]).delete()
    Permiso.objects.filter(codigo__in=codigos_semillados()).delete()


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0001_initial")]
    operations = [migrations.RunPython(forward, reverse)]
