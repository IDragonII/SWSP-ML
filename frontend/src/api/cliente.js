import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const cliente = axios.create({
  baseURL,
  withCredentials: true,
})

const RUTAS_AUTH = /\/auth\/(login|refresh|logout)\/?$/

let renovacionEnCurso = null
const oyentesSesionInvalida = new Set()

export function alExpirarSesion(fn) {
  oyentesSesionInvalida.add(fn)
  return () => oyentesSesionInvalida.delete(fn)
}

function notificarSesionInvalida() {
  oyentesSesionInvalida.forEach((fn) => fn())
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

    return Promise.reject(error)
  },
)
