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
      ([, mensajes]) => Array.isArray(mensajes) && mensajes.length > 0,
    )
    if (primerCampo) return primerCampo[1][0]
  }

  if (status === 401) return 'Sesión expirada. Vuelve a iniciar sesión.'
  if (status === 403) return 'No tienes permiso para realizar esta acción.'
  if (status === 429) return 'Demasiadas solicitudes. Espera unos segundos e inténtalo de nuevo.'
  if (status >= 500) return 'El servidor tuvo un problema. Inténtalo de nuevo en unos segundos.'

  return `Error inesperado (${status}).`
}
