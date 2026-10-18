import { listarTodo } from './catalogos.js'
import { cliente } from './cliente.js'

// Administración de roles (Semana 14): roles-admin exige roles.gestionar
// en cada acción; /roles/ (ligero) sigue siendo el de Usuarios y pide
// usuarios.ver, por eso el desplegable «basado en» usa roles-admin.

export function listarRolesAdmin(params = {}) {
  return cliente.get('/roles-admin/', { params }).then((r) => r.data)
}

export function obtenerRol(id) {
  return cliente.get(`/roles-admin/${id}/`).then((r) => r.data)
}

export function crearRol(datos) {
  return cliente.post('/roles-admin/', datos).then((r) => r.data)
}

export function editarRol(id, datos) {
  return cliente.patch(`/roles-admin/${id}/`, datos).then((r) => r.data)
}

export function guardarPermisosRol(id, permisos) {
  return cliente
    .put(`/roles-admin/${id}/permisos/`, { permisos })
    .then((r) => r.data)
}

export function desactivarRol(id) {
  return cliente.post(`/roles-admin/${id}/desactivar/`).then((r) => r.data)
}

export function reactivarRol(id) {
  return cliente.post(`/roles-admin/${id}/reactivar/`).then((r) => r.data)
}

export function obtenerCatalogoPermisos() {
  return cliente.get('/permisos-catalogo/').then((r) => r.data)
}

export function listarTodosLosRoles() {
  return listarTodo('/roles-admin/')
}
