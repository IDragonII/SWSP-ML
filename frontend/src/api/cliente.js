import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const cliente = axios.create({
  baseURL,
  withCredentials: true,
})

const RUTAS_AUTH = /\/auth\/(login|refresh|logout)\/?$/
// /auth/me no participa en el refresco de permisos: notificar un 403
// de la propia sesión provocaría un bucle de relecturas.
const RUTAS_SESION = /\/auth\/(login|refresh|logout|me)\/?$/

let renovacionEnCurso = null
const oyentesSesionInvalida = new Set()
const oyentesPermisoDenegado = new Set()

export function alExpirarSesion(fn) {
  oyentesSesionInvalida.add(fn)
  return () => oyentesSesionInvalida.delete(fn)
}

// Semana 14: un 403 significa que tus permisos cambiaron (o nunca los
// tuviste). El SesionProvider relee /auth/me para que menús, rutas y
// botones se recalculen sin recargar la página.
export function alDenegarPermiso(fn) {
  oyentesPermisoDenegado.add(fn)
  return () => oyentesPermisoDenegado.delete(fn)
}

function notificarSesionInvalida() {
  oyentesSesionInvalida.forEach((fn) => fn())
}

function notificarPermisoDenegado() {
  oyentesPermisoDenegado.forEach((fn) => fn())
}

export function renovarSesion() {
  if (!renovacionEnCurso) {
    renovacionEnCurso = cliente
      .post('/auth/refresh/')
      .then((respuesta) => respuesta.data)
      .finally(() => {
        renovacionEnCurso = null
      })
  }
  return renovacionEnCurso
}

cliente.interceptors.response.use(
  (respuesta) => respuesta,
  async (error) => {
    const config = error.config
    if (!config) return Promise.reject(error)

    const esRutaAuth = RUTAS_AUTH.test(config.url || '')
    const esRutaSesion = RUTAS_SESION.test(config.url || '')
    const yaReintentado = config._reintentado === true

    if (error.response?.status === 401 && !esRutaAuth && !yaReintentado) {
      config._reintentado = true
      try {
        await renovarSesion()
        return cliente(config)
      } catch {
        notificarSesionInvalida()
      }
    }

    if (
      error.response?.status === 403 &&
      !esRutaSesion &&
      !config._permisoNotificado
    ) {
      config._permisoNotificado = true
      notificarPermisoDenegado()
    }

    return Promise.reject(error)
  },
)
