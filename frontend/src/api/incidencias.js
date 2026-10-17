import { cliente } from './cliente.js'

export function listarIncidencias(params = {}) {
  return cliente.get('/incidencias/', { params }).then((r) => r.data)
}

export function obtenerIncidencia(id) {
  return cliente.get(`/incidencias/${id}/`).then((r) => r.data)
}

export function guardarIncidencia(id, datos) {
  const peticion = id
    ? cliente.patch(`/incidencias/${id}/`, datos)
    : cliente.post('/incidencias/', datos)
  return peticion.then((r) => r.data)
}

// HU-88: anulación lógica con motivo obligatorio; la reactivación exige
// que la campaña siga abierta y la fecha dentro de su período
export function anularIncidencia(id, motivo) {
  return cliente
    .post(`/incidencias/${id}/anular/`, { motivo })
    .then((r) => r.data)
}

export function reactivarIncidencia(id) {
  return cliente.post(`/incidencias/${id}/reactivar/`).then((r) => r.data)
}

// Mismos valores del modelo Incidencia.SEVERIDADES y de las categorías
// del catálogo de tipos de incidencia
export const SEVERIDADES_INCIDENCIA = [
  ['BAJA', 'Baja'],
  ['MEDIA', 'Media'],
  ['ALTA', 'Alta'],
]

export const CATEGORIAS_INCIDENCIA = [
  ['CLIMATICA', 'Climática'],
  ['BIOLOGICA', 'Biológica'],
  ['OTRA', 'Otra'],
]

export const ESTADOS_INCIDENCIA = [
  ['ACTIVA', 'Activa'],
  ['ANULADA', 'Anulada'],
]
