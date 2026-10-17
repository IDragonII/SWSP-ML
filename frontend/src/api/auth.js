import { cliente } from './cliente.js'

export async function iniciarSesion(username, password) {
  const { data } = await cliente.post('/auth/login/', { username, password })
  return data.usuario
}

export async function obtenerSesion() {
  const { data } = await cliente.get('/auth/me/')
  return data.usuario
}

export async function cerrarSesion() {
  const { data } = await cliente.post('/auth/logout/')
  return data
}

// Semana 13 (HU-113): cambio de la propia contraseña; el backend devuelve
// el usuario actualizado y rota las cookies de sesión
export async function cambiarClave(password_actual, password_nueva) {
  const { data } = await cliente.post('/auth/cambiar-clave/', {
    password_actual,
    password_nueva,
  })
  return data
}
