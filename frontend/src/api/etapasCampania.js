import { cliente } from './cliente.js'

export function listarEtapasCampania(params = {}) {
  return cliente.get('/etapas-campania/', { params }).then((r) => r.data)
}

export function obtenerEtapaCampania(id) {
  return cliente.get(`/etapas-campania/${id}/`).then((r) => r.data)
}

export function guardarEtapaCampania(id, datos) {
  const peticion = id
    ? cliente.patch(`/etapas-campania/${id}/`, datos)
    : cliente.post('/etapas-campania/', datos)
  return peticion.then((r) => r.data)
}
