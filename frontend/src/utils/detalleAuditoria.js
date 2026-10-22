// Resumen legible del campo `detalle` de un evento de auditoría
// (Semana 23): la BD guarda el JSON exacto y aquí solo se traduce a un
// texto corto para la pantalla; lo crudo sigue disponible con el
// botón «JSON» de la tabla. Si no se reconoce la forma, se devuelve
// null y la celda muestra «Detalle técnico».

const ETIQUETAS_ORIGEN = {
  real: 'real del sistema',
  demostracion: 'demostración',
  'demostración': 'demostración',
}

const ETIQUETAS_ESTADO = {
  PLANIFICADA: 'planificada',
  EN_PRODUCCION: 'en producción',
  CERRADA: 'cerrada',
  CANCELADA: 'cancelada',
}

function etiquetaOrigen(valor) {
  const clave = String(valor ?? '').toLowerCase()
  return ETIQUETAS_ORIGEN[clave] ?? (clave || 'desconocido')
}

function numero(valor) {
  return Number(valor).toLocaleString('es-PE', { maximumFractionDigits: 2 })
}

function huellaCorta(sha) {
  const texto = String(sha ?? '')
  return texto.length > 12 ? `${texto.slice(0, 8)}…` : texto
}

function listaCorta(items, max = 3) {
  const vistos = items.slice(0, max).join(', ')
  return items.length > max ? `${vistos}… (+${items.length - max})` : vistos
}

function descripcionFiltros(filtros) {
  const entradas = Object.entries(filtros ?? {})
  if (entradas.length === 0) return 'sin filtros'
  const pares = entradas.map(([clave, valor]) => `${clave}=${valor}`)
  return `filtros: ${listaCorta(pares)}`
}

/** Texto corto en español del `detalle` de una fila de auditoría. */
export function describirDetalle(fila) {
  const d = fila?.detalle
  if (!d || typeof d !== 'object' || Array.isArray(d)) return null

  // Exportación del dataset de ML (comando exportar_dataset)
  if ('sha256' in d && 'filas' in d) {
    return (
      `${numero(d.filas)} filas · SHA-256 ${huellaCorta(d.sha256)}` +
      ` · origen: ${etiquetaOrigen(d.origen_datos)}`
    )
  }

  // Exportación de un reporte (bitácora, productores, …)
  if ('formato' in d && 'filas' in d) {
    const tipo = d.tipo ? String(d.tipo) : 'reporte'
    return (
      `${tipo} en ${String(d.formato).toUpperCase()} · ` +
      `${numero(d.filas)} filas · ${descripcionFiltros(d.filtros)}`
    )
  }

  // Alta de un modelo (registro.registrar con contenido o archivo)
  if (d.tabla === 'modelos_ml' && 'n_registros' in d) {
    const artefacto =
      d.artefacto === 'contenido'
        ? 'guardado en la BD'
        : `archivo ${d.archivo ?? ''}`.trim()
    return (
      `Modelo ${d.algoritmo} v${d.version} · ` +
      `${numero(d.n_registros)} registros · ` +
      `origen: ${etiquetaOrigen(d.origen_datos)} · ${artefacto}`
    )
  }

  // Activar / desactivar el modelo activo
  if (d.tabla === 'modelos_ml' && d.algoritmo) {
    return `Modelo ${d.algoritmo} v${d.version}`
  }

  // Predicción con el modelo activo
  if (d.tabla === 'predicciones') {
    return (
      `Predicción de la campaña ${d.campania} con ${d.modelo} · ` +
      `${numero(d.rendimiento_predicho)} kg/ha`
    )
  }

  // Resumen del evaluador de alertas
  if (d.resumen === true) {
    return (
      `Resumen: ${numero(d.creadas ?? 0)} alertas creadas · ` +
      `${numero(d.cerradas ?? 0)} cerradas`
    )
  }

  // Atender / reabrir una alerta
  if (typeof d.operacion === 'string') {
    return d.nota ? `${d.operacion} — ${d.nota}` : d.operacion
  }

  // Importación de un histórico
  if ('filas_totales' in d) {
    const conError = d.filas_error
      ? ` · ${numero(d.filas_error)} con error`
      : ''
    return (
      `${d.archivo ?? 'archivo'} · ${numero(d.filas_ok ?? 0)} de ` +
      `${numero(d.filas_totales)} filas correctas${conError}`
    )
  }

  // Permisos de un rol: creación o modificación
  if (Array.isArray(d.permisos)) {
    return `${d.permisos.length} permisos: ${listaCorta(d.permisos, 4)}`
  }
  if (Array.isArray(d.agregados) || Array.isArray(d.quitados)) {
    return `+${(d.agregados ?? []).length} / −${(d.quitados ?? []).length} permisos`
  }

  // Bloqueo de acceso por intentos fallidos
  if (typeof d.username === 'string') {
    return `Usuario ${d.username}`
  }

  // Parámetro del sistema modificado
  if (typeof d.clave === 'string') {
    return `Parámetro ${d.clave}`
  }

  // Orden de las etapas fenológicas de un cultivo
  if (Array.isArray(d.orden) && d.cultivo !== undefined) {
    return `Etapas del cultivo ${d.cultivo} reordenadas (${d.orden.length})`
  }

  // Revisión de una cosecha
  if ('incluir_en_entrenamiento' in d) {
    const si = d.incluir_en_entrenamiento ? 'sí' : 'no'
    const nota = d.nota ? `${d.nota} · ` : ''
    return `${nota}incluir en entrenamiento: ${si}`
  }

  // Campaña: cambio de estado y borrados con motivo
  if ('estado' in d) {
    const etiqueta =
      ETIQUETAS_ESTADO[d.estado] ?? String(d.estado).toLowerCase()
    return d.motivo
      ? `Estado ${etiqueta} · motivo: ${d.motivo}`
      : `Estado ${etiqueta}`
  }
  if (d.campania !== undefined && d.motivo) {
    return `Campaña ${d.campania} · motivo: ${d.motivo}`
  }
  if (d.motivo) {
    return `Motivo: ${d.motivo}`
  }

  return null
}
