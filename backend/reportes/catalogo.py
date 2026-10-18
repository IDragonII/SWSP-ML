"""Catálogo declarativo de los reportes (Semana 17, HU-141..HU-149).

Cada reporte declara su permiso de módulo —la segunda capa del doble
permiso (reportes.* + el ver del módulo de donde salen los datos)—, sus
filtros y sus columnas. Los límites por formato son constantes del
código y se leen en cada llamada (las pruebas los ajustan con mock).

El cliente no puede elegir columnas ni orden: todo está fijado aquí, en
el servidor (evita consultas arbitrarias).
"""

# Formatos que acepta la exportación (otro valor → 400)
FORMATOS = ("xlsx", "pdf")

CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}

# Límites de filas por formato: si se superan, 400 con el número de
# filas y la sugerencia de afinar filtros o usar Excel (nunca se trunca
# en silencio)
LIMITE_EXCEL_FILAS = 20000
LIMITE_PDF_FILAS = 1000

# Aviso de privacidad que acompaña siempre a los reportes
AVISO_PRIVACIDAD = "Este reporte no incluye DNI ni teléfono"

# Aviso de los reportes marcados «sensible» (Semana 18, HU-155/HU-156):
# va en la hoja Resumen, en el pie del PDF y en la confirmación de la
# interfaz antes de descargar
AVISO_CONFIDENCIALIDAD = (
    "Contiene información sensible de auditoría: solo para uso interno y "
    "de verificación. No es evidencia oficial."
)

# Filtros comunes (los mismos del panel, con la misma validación)
FILTROS_COMUNES = ("periodo", "cultivo", "provincia", "distrito", "comunidad", "estado")

# Filtros propios de cada reporte nuevo (Semana 18)
FILTROS_ACTIVIDADES = FILTROS_COMUNES + (
    "tipo_actividad",
    "fecha_actividad_desde",
    "fecha_actividad_hasta",
    "estado_actividad",
)
# El reporte de auditoría usa los filtros de su pantalla más el rango de
# fechas (obligatorio: se valida en consultas, con máximo 366 días)
FILTROS_AUDITORIA = (
    "fecha_desde",
    "fecha_hasta",
    "usuario",
    "accion",
    "modulo",
    "tabla",
    "registro",
    "ip",
)

# Etiquetas de los filtros, para el texto de los archivos y el encabezado
ETIQUETAS_FILTROS = {
    "periodo": "Período",
    "cultivo": "Cultivo",
    "provincia": "Provincia",
    "distrito": "Distrito",
    "comunidad": "Comunidad",
    "estado": "Estado de campaña",
    "estado_productor": "Estado del productor",
    "tipo_actividad": "Tipo de actividad",
    "fecha_actividad_desde": "Actividad desde",
    "fecha_actividad_hasta": "Actividad hasta",
    "estado_actividad": "Estado de la actividad",
    "fecha_desde": "Fecha desde",
    "fecha_hasta": "Fecha hasta",
    "usuario": "Usuario",
    "accion": "Acción",
    "modulo": "Módulo",
    "tabla": "Tabla",
    "registro": "Registro",
    "ip": "IP",
}
ESTADOS_PRODUCTOR_FILTRO = {
    "ACTIVO": "solo activos",
    "INACTIVO": "solo inactivos",
    "TODOS": "todos",
}
ESTADOS_ACTIVIDAD_FILTRO = {
    "ACTIVAS": "solo activas",
    "ANULADAS": "solo anuladas",
    "TODAS": "todas",
}

# Columnas fijas de cada reporte: (clave, etiqueta, tipo[, decimales])
# tipos: texto | numero | entero | fecha | fecha_hora | booleano |
#        estado_productor | estado_campania  — «dec» solo afecta a Excel
#        y PDF (por defecto 2)
COLUMNAS_PRODUCTORES = (
    {"clave": "codigo", "etiqueta": "Código", "tipo": "texto"},
    {"clave": "productor", "etiqueta": "Productor", "tipo": "texto"},
    {"clave": "estado", "etiqueta": "Estado", "tipo": "estado_productor"},
    {"clave": "provincia", "etiqueta": "Provincia", "tipo": "texto"},
    {"clave": "distrito", "etiqueta": "Distrito", "tipo": "texto"},
    {"clave": "comunidad", "etiqueta": "Comunidad", "tipo": "texto"},
    {"clave": "parcelas_activas", "etiqueta": "Parcelas activas", "tipo": "entero"},
    {
        "clave": "superficie_parcelas_ha",
        "etiqueta": "Superficie de parcelas (ha)",
        "tipo": "numero",
    },
    {"clave": "campania", "etiqueta": "Campaña", "tipo": "texto"},
    {"clave": "cultivo", "etiqueta": "Cultivo", "tipo": "texto"},
    {"clave": "variedad", "etiqueta": "Variedad", "tipo": "texto"},
    {
        "clave": "estado_campania",
        "etiqueta": "Estado de la campaña",
        "tipo": "estado_campania",
    },
    {
        "clave": "superficie_sembrada_ha",
        "etiqueta": "Superficie sembrada (ha)",
        "tipo": "numero",
    },
)

COLUMNAS_PRODUCTIVO = (
    {"clave": "periodo", "etiqueta": "Período", "tipo": "texto"},
    {"clave": "cultivo", "etiqueta": "Cultivo", "tipo": "texto"},
    {"clave": "variedad", "etiqueta": "Variedad", "tipo": "texto"},
    {"clave": "codigo_productor", "etiqueta": "Código del productor", "tipo": "texto"},
    {"clave": "productor", "etiqueta": "Nombre del productor", "tipo": "texto"},
    {"clave": "parcela", "etiqueta": "Código de parcela", "tipo": "texto"},
    {"clave": "distrito", "etiqueta": "Distrito", "tipo": "texto"},
    {"clave": "fecha_cosecha", "etiqueta": "Fecha de cosecha", "tipo": "fecha"},
    {
        "clave": "superficie_cosechada_ha",
        "etiqueta": "Superficie cosechada (ha)",
        "tipo": "numero",
    },
    {"clave": "produccion_kg", "etiqueta": "Producción (kg)", "tipo": "numero", "dec": 0},
    {
        "clave": "rendimiento_kg_ha",
        "etiqueta": "Rendimiento (kg/ha)",
        "tipo": "numero",
    },
    {
        "clave": "estado_campania",
        "etiqueta": "Estado de la campaña",
        "tipo": "estado_campania",
    },
    {"clave": "requiere_revision", "etiqueta": "Revisión pendiente", "tipo": "booleano"},
)

# Reporte de actividades (Semana 18, RF-68): sin costo, observaciones
# ni motivo de anulación (los tres van en la ficha, no en el reporte).
# «responsable» se omite para roles con limita_a_asignados (columnas_de)
COLUMNAS_ACTIVIDADES = (
    {"clave": "fecha", "etiqueta": "Fecha", "tipo": "fecha"},
    {"clave": "productor", "etiqueta": "Productor", "tipo": "texto"},
    {"clave": "parcela", "etiqueta": "Parcela", "tipo": "texto"},
    {"clave": "distrito", "etiqueta": "Distrito", "tipo": "texto"},
    {"clave": "campania", "etiqueta": "Campaña", "tipo": "texto"},
    {"clave": "cultivo", "etiqueta": "Cultivo", "tipo": "texto"},
    {
        "clave": "estado_campania",
        "etiqueta": "Estado de la campaña",
        "tipo": "estado_campania",
    },
    {"clave": "tipo_actividad", "etiqueta": "Tipo de actividad", "tipo": "texto"},
    {"clave": "metodo", "etiqueta": "Método", "tipo": "texto"},
    {"clave": "densidad", "etiqueta": "Densidad de siembra", "tipo": "texto"},
    {"clave": "horas", "etiqueta": "Horas", "tipo": "numero", "dec": 1},
    {"clave": "estado_actividad", "etiqueta": "Estado de la actividad", "tipo": "texto"},
    {"clave": "responsable", "etiqueta": "Responsable", "tipo": "texto"},
)

# Reporte de auditoría (Semana 18): un evento por fila, con el detalle
# reducido a un resumen sin valores libres (se arma en consultas)
COLUMNAS_AUDITORIA = (
    {"clave": "fecha", "etiqueta": "Fecha y hora", "tipo": "fecha_hora"},
    {"clave": "usuario", "etiqueta": "Usuario", "tipo": "texto"},
    {"clave": "accion", "etiqueta": "Acción", "tipo": "texto"},
    {"clave": "modulo", "etiqueta": "Módulo", "tipo": "texto"},
    {"clave": "tabla", "etiqueta": "Tabla", "tipo": "texto"},
    {"clave": "registro_id", "etiqueta": "Registro", "tipo": "entero"},
    {"clave": "ip", "etiqueta": "IP", "tipo": "texto"},
    {"clave": "detalle", "etiqueta": "Detalle", "tipo": "texto"},
)

# Columnas del resumen por cultivo (hoja «Resumen» y primera tabla del PDF)
COLUMNAS_RESUMEN_PRODUCTIVO = (
    {"clave": "etiqueta", "etiqueta": "Cultivo", "tipo": "texto"},
    {"clave": "campanias", "etiqueta": "Campañas", "tipo": "entero"},
    {"clave": "superficie_ha", "etiqueta": "Ha cosechadas", "tipo": "numero"},
    {"clave": "produccion_kg", "etiqueta": "Producción (kg)", "tipo": "numero", "dec": 0},
    {"clave": "toneladas", "etiqueta": "Producción (ton)", "tipo": "numero"},
    {
        "clave": "rendimiento_kg_ha",
        "etiqueta": "Rendimiento (kg/ha)",
        "tipo": "numero",
    },
    {"clave": "provisionales", "etiqueta": "Provisionales", "tipo": "entero"},
    {
        "clave": "excluidas_revision",
        "etiqueta": "Excluidas por revisión",
        "tipo": "entero",
    },
    {"clave": "pocos_datos", "etiqueta": "Pocos datos", "tipo": "booleano"},
)

REPORTES = {
    "productores": {
        "tipo": "productores",
        "nombre": "Reporte de productores",
        "descripcion": (
            "Productores con su ubicación, parcelas, superficie, cultivo "
            "y campaña."
        ),
        "permiso": "productores.ver",
        "filtros": FILTROS_COMUNES + ("estado_productor",),
        "columnas": COLUMNAS_PRODUCTORES,
    },
    "productivo": {
        "tipo": "productivo",
        "nombre": "Reporte productivo",
        "descripcion": (
            "Producción y rendimiento por cultivo, con el detalle por "
            "campaña."
        ),
        "permiso": "produccion.ver",
        "filtros": FILTROS_COMUNES,
        "columnas": COLUMNAS_PRODUCTIVO,
    },
    "actividades": {
        "tipo": "actividades",
        "nombre": "Reporte de actividades",
        "descripcion": (
            "Actividades registradas por fecha, con su campaña, cultivo, "
            "tipo y responsable."
        ),
        "permiso": "actividades.ver",
        "filtros": FILTROS_ACTIVIDADES,
        "columnas": COLUMNAS_ACTIVIDADES,
    },
    "auditoria": {
        "tipo": "auditoria",
        "nombre": "Reporte de auditoría",
        "descripcion": (
            "Eventos de la bitácora en un rango de fechas, con su "
            "detalle resumido. Información sensible."
        ),
        "permiso": "auditoria.ver",
        "filtros": FILTROS_AUDITORIA,
        "columnas": COLUMNAS_AUDITORIA,
        "sensible": True,
        "aviso": AVISO_CONFIDENCIALIDAD,
    },
}


def limite_de(formato):
    """Máximo de filas para un formato (se lee en cada llamada)."""
    if formato == "xlsx":
        return LIMITE_EXCEL_FILAS
    return LIMITE_PDF_FILAS


def obtener(tipo):
    """El reporte con ese tipo, o None si no existe (→ 404)."""
    return REPORTES.get(tipo)


def disponibles(permisos):
    """Reportes que el usuario puede usar: reportes.ver ya se exigió en
    la vista; aquí se filtra por la segunda capa (ver del módulo)."""
    return [reporte for reporte in REPORTES.values() if reporte["permiso"] in permisos]


def columnas_de(reporte, usuario):
    """Columnas efectivas de un reporte para este usuario.

    En el reporte de actividades, la columna «responsable» se omite por
    completo para los roles con limita_a_asignados (Técnico de campo):
    su vista se limita a sus asignados y el sistema no le muestra quién
    registró el trabajo (mismo criterio que registrado_por en las
    fichas). No es una celda vacía: la columna no existe.
    """
    columnas = reporte["columnas"]
    if reporte["tipo"] != "actividades":
        return columnas
    rol = getattr(usuario, "rol", None)
    if rol is not None and rol.limita_a_asignados:
        return tuple(
            columna for columna in columnas if columna["clave"] != "responsable"
        )
    return columnas
