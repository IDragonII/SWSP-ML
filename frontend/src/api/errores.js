export function mensajeDeError(error) {
  if (!error?.response) {
    return 'No se pudo conectar con el servidor. Revisa que el backend esté en marcha.'
  }

  const { status, data } = error.response

  if (typeof data?.detail === 'string') return data.detail

  if (status === 400 && data) {
    if (Array.isArray(data.non_field_errors) && data.non_field_errors[0]) {
      return data.non_field_errors[0]
    }
    const primerCampo = Object.entries(data).find(
      ([, mensajes]) =>
        (Array.isArray(mensajes) && mensajes.length > 0) ||
        (typeof mensajes === 'string' && mensajes.length > 0),
    )
    if (primerCampo) {
      return Array.isArray(primerCampo[1]) ? primerCampo[1][0] : primerCampo[1]
    }
  }

  if (status === 401) return 'Sesión expirada. Vuelve a iniciar sesión.'
  if (status === 403) return 'No tienes permiso para realizar esta acción.'
  if (status === 404) return 'No encontrado.'
  if (status === 429) return 'Demasiadas solicitudes. Espera unos segundos e inténtalo de nuevo.'
  if (status >= 500) return 'El servidor tuvo un problema. Inténtalo de nuevo en unos segundos.'

  return `Error inesperado (${status}).`
}

export function erroresDeCampo(data) {
  if (!data || typeof data !== 'object') return {}
  const salida = {}
  for (const [campo, mensajes] of Object.entries(data)) {
    if (campo === 'non_field_errors') continue
    if (Array.isArray(mensajes) && mensajes.length > 0) {
      salida[campo] = mensajes[0]
    } else if (typeof mensajes === 'string') {
      salida[campo] = mensajes
    }
  }
  return salida
}
