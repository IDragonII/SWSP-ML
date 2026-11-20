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
const RUTA_LOGIN = /\/auth\/login\/?$/

// Render free se duerma a los 15 min y tarda ~1 min en despertar; el
// proxy de Netlify corta a los 26 s, así que el primer intento tras el
// sueño puede volver 502/503/504 o caerse en la red. Solo se reintenta
// lo inocuo: GET y el login (reintentarlo no duplica nada); los POST
// de negocio no se tocan para no duplicar altas.
const ESTADOS_AGOTADOS = new Set([502, 503, 504])
const MAX_INTENTOS_ROJO = 3
const ESPERA_REINTENTO_MS = 10000
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

    // Despertar de Render (ver ESPERA_REINTENTO_MS): solo GET y login
    const esGet = (config.method || 'get').toLowerCase() === 'get'
    const reintentable = esGet || RUTA_LOGIN.test(config.url || '')
    const intentos = config._intentosRojo || 0
    const falloDeRed =
      !error.response || ESTADOS_AGOTADOS.has(error.response.status)
    if (reintentable && falloDeRed && intentos < MAX_INTENTOS_ROJO) {
      config._intentosRojo = intentos + 1
      await new Promise((resolver) => setTimeout(resolver, ESPERA_REINTENTO_MS))
      return cliente(config)
    }

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
