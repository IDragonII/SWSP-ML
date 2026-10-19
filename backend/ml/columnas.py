"""Lista fija de columnas exportadas del dataset (Semana 21).

La lista está definida en código a propósito: si mañana la vista suma
una columna nueva, esa columna NO sale en el archivo hasta que alguien
la declare aquí y en el catálogo de variables (pruebas 350 y 352). El
CSV solo lleva números internos (ids) y datos de la campaña: sin
nombres, DNI ni teléfonos (la vista no los tiene y la lista tampoco).

La consulta se construye desde la lista, nunca con SELECT *.
"""

# Orden de exportación = orden de lectura (fijo, estable, reproducible).
COLUMNAS_EXPORTADAS = (
    "campania_id",
    "parcela_id",
    "productor_id",
    "periodo",
    "anio_campania",
    "cultivo",
    "variedad",
    "superficie_sembrada_ha",
    "altitud_msnm",
    "tipo_suelo",
    "pendiente",
    "sistema_riego",
    "origen",
    "precipitacion_acum_mm",
    "temp_prom_c",
    "humedad_prom_pct",
    "n_heladas",
    "dias_con_clima",
    "dias_ventana_clima",
    "semilla_kg_ha",
    "fertilizante_kg_ha",
    "jornales_ha",
    "agua_m3_ha",
    "n_incidencias",
    "severidad_max",
    "n_aplicaciones",
    "dias_ciclo",
    "rendimiento_kg_ha",
)

# Datos personales: ni presentes en la vista ni permitidos en la lista.
COLUMNAS_PROHIBIDAS = ("dni", "nombres", "apellidos", "telefono")


def consulta_exportacion():
    """SELECT de la vista con exactamente las columnas declaradas."""
    lista = ", ".join(COLUMNAS_EXPORTADAS)
    return f"SELECT {lista} FROM vw_dataset_entrenamiento ORDER BY campania_id"


def columnas_seleccionadas():
    """Columnas que la consulta de exportación pide a PostgreSQL."""
    texto = consulta_exportacion()
    cuerpo = texto[len("SELECT "):].split(" FROM ", 1)[0]
    return tuple(c.strip() for c in cuerpo.split(","))
