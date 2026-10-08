import { cliente } from './cliente.js'

export function listarProductores(params = {}) {
  return cliente.get('/productores/', { params }).then((r) => r.data)
}

export function obtenerProductor(id) {
  return cliente.get(`/productores/${id}/`).then((r) => r.data)
}

export function guardarProductor(id, datos) {
  const peticion = id
    ? cliente.patch(`/productores/${id}/`, datos)
    : cliente.post('/productores/', datos)
  return peticion.then((r) => r.data)
}

export function estadoProductor(id, estado) {
  return cliente.patch(`/productores/${id}/estado/`, { estado }).then((r) => r.data)
}

export function listarAsignaciones(productor) {
  return cliente
    .get('/asignaciones/', { params: { productor } })
    .then((r) => r.data)
}

export function asignarTecnico({ tecnico, productor }) {
  return cliente.post('/asignaciones/', { tecnico, productor }).then((r) => r.data)
}

export function estadoAsignacion(id, activo) {
  return cliente.patch(`/asignaciones/${id}/estado/`, { activo }).then((r) => r.data)
}
