import { cliente } from './cliente.js'

export function listarProducciones(params = {}) {
  return cliente.get('/producciones/', { params }).then((r) => r.data)
}

export function obtenerProduccion(id) {
  return cliente.get(`/producciones/${id}/`).then((r) => r.data)
}

export function guardarProduccion(id, datos) {
  const peticion = id
    ? cliente.patch(`/producciones/${id}/`, datos)
    : cliente.post('/producciones/', datos)
  return peticion.then((r) => r.data)
}

export function revisarProduccion(id, nota, incluirEnEntrenamiento) {
  return cliente
    .post(`/producciones/${id}/revisar/`, {
      nota,
      incluir_en_entrenamiento: incluirEnEntrenamiento,
    })
    .then((r) => r.data)
}

export function deshacerCosecha(id, motivo) {
  return cliente
    .post(`/producciones/${id}/deshacer-cosecha/`, { motivo })
    .then((r) => r.data)
}

export const CALIDADES = [
  ['PRIMERA', 'Primera'],
  ['SEGUNDA', 'Segunda'],
  ['TERCERA', 'Tercera'],
]
