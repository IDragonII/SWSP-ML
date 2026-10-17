import { cliente } from './cliente.js'

export function listarCampanias(params = {}) {
  return cliente.get('/campanias/', { params }).then((r) => r.data)
}

export function obtenerCampania(id) {
  return cliente.get(`/campanias/${id}/`).then((r) => r.data)
}

export function guardarCampania(id, datos) {
  const peticion = id
    ? cliente.patch(`/campanias/${id}/`, datos)
    : cliente.post('/campanias/', datos)
  return peticion.then((r) => r.data)
}

export function iniciarCampania(id) {
  return cliente.post(`/campanias/${id}/iniciar/`).then((r) => r.data)
}

export function cancelarCampania(id, motivo) {
  return cliente
    .post(`/campanias/${id}/cancelar/`, { motivo })
    .then((r) => r.data)
}

export function cerrarCampania(id) {
  return cliente.post(`/campanias/${id}/cerrar/`).then((r) => r.data)
}

export function obtenerLineaTiempo(id) {
  return cliente.get(`/campanias/${id}/linea-tiempo/`).then((r) => r.data)
}

// Mismos valores que models.Campania.ESTADOS.
export const ESTADOS_CAMPANIA = [
  ['PLANIFICADA', 'Planificada'],
  ['EN_PRODUCCION', 'En producción'],
  ['COSECHADA', 'Cosechada'],
  ['CERRADA', 'Cerrada'],
  ['CANCELADA', 'Cancelada'],
]
