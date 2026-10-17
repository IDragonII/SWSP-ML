import { cliente } from './cliente.js'

export function listarUsuarios(params = {}) {
  return cliente.get('/usuarios/', { params }).then((r) => r.data)
}

export function obtenerUsuario(id) {
  return cliente.get(`/usuarios/${id}/`).then((r) => r.data)
}

export function guardarUsuario(id, datos) {
  const peticion = id
    ? cliente.patch(`/usuarios/${id}/`, datos)
    : cliente.post('/usuarios/', datos)
  return peticion.then((r) => r.data)
}

export function desactivarUsuario(id) {
  return cliente.post(`/usuarios/${id}/desactivar/`).then((r) => r.data)
}

export function reactivarUsuario(id) {
  return cliente.post(`/usuarios/${id}/reactivar/`).then((r) => r.data)
}

export function restablecerClave(id, password) {
  return cliente
    .post(`/usuarios/${id}/restablecer-clave/`, { password })
    .then((r) => r.data)
}

export function desbloquearUsuario(id) {
  return cliente.post(`/usuarios/${id}/desbloquear/`).then((r) => r.data)
}

export function listarRoles() {
  return cliente.get('/roles/').then((r) => r.data)
}
