import { cliente } from './cliente.js'

export function listarUsosRecursos(params = {}) {
  return cliente.get('/usos-recursos/', { params }).then((r) => r.data)
}

export function obtenerUsoRecurso(id) {
  return cliente.get(`/usos-recursos/${id}/`).then((r) => r.data)
}

export function guardarUsoRecurso(id, datos) {
  const peticion = id
    ? cliente.patch(`/usos-recursos/${id}/`, datos)
    : cliente.post('/usos-recursos/', datos)
  return peticion.then((r) => r.data)
}

export function anularUsoRecurso(id, motivo) {
  return cliente
    .post(`/usos-recursos/${id}/anular/`, { motivo })
    .then((r) => r.data)
}

export function reactivarUsoRecurso(id) {
  return cliente.post(`/usos-recursos/${id}/reactivar/`).then((r) => r.data)
}

// Mismos valores que catalogos.Recurso.CATEGORIAS (el usuario elige por
// nombre; el tipo de unidad lo decide la regla de la Semana 9)
export const CATEGORIAS_RECURSO = [
  ['SEMILLA', 'Semilla'],
  ['FERTILIZANTE', 'Fertilizante'],
  ['ABONO', 'Abono'],
  ['MANO_OBRA', 'Mano de obra'],
  ['AGUA', 'Agua'],
  ['COMBUSTIBLE', 'Combustible'],
  ['MAQUINARIA', 'Maquinaria'],
  ['FITOSANITARIO', 'Fitosanitario'],
]
