import { cliente } from './cliente.js'

export function listarActividades(params = {}) {
  return cliente.get('/actividades/', { params }).then((r) => r.data)
}

export function obtenerActividad(id) {
  return cliente.get(`/actividades/${id}/`).then((r) => r.data)
}

export function guardarActividad(id, datos) {
  const peticion = id
    ? cliente.patch(`/actividades/${id}/`, datos)
    : cliente.post('/actividades/', datos)
  return peticion.then((r) => r.data)
}

export function anularActividad(id, motivo) {
  return cliente
    .post(`/actividades/${id}/anular/`, { motivo })
    .then((r) => r.data)
}

export function reactivarActividad(id) {
  return cliente.post(`/actividades/${id}/reactivar/`).then((r) => r.data)
}

// Mismos valores que models.Actividad.UNIDADES_DENSIDAD (el backend admite
// las dos medidas; la del proyecto está por confirmar — pregunta I)
export const UNIDADES_DENSIDAD = [
  ['KG_HA', 'kg/ha'],
  ['PLANTAS_M2', 'plantas/m²'],
]
