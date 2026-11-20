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
// el usuario actualizado y rota las cookies de sesión. Con la marca S24
// debe_cambiar_credenciales se envía además username_nuevo.
export async function cambiarClave(password_actual, password_nueva, usernameNuevo) {
  const cuerpo = { password_actual, password_nueva }
  if (usernameNuevo) cuerpo.username_nuevo = usernameNuevo
  const { data } = await cliente.post('/auth/cambiar-clave/', cuerpo)
  return data
}
