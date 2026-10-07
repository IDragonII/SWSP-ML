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
