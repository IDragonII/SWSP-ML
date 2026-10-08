import { cliente } from './cliente.js'

export function listarParcelas(params = {}) {
  return cliente.get('/parcelas/', { params }).then((r) => r.data)
}

export function obtenerParcela(id) {
  return cliente.get(`/parcelas/${id}/`).then((r) => r.data)
}

export function guardarParcela(id, datos) {
  const peticion = id
    ? cliente.patch(`/parcelas/${id}/`, datos)
    : cliente.post('/parcelas/', datos)
  return peticion.then((r) => r.data)
}

export function estadoParcela(id, estado) {
  return cliente.patch(`/parcelas/${id}/estado/`, { estado }).then((r) => r.data)
}

// Mismos valores que las listas cerradas del backend (models.Parcela)
export const TIPOS_SUELO = [
  ['ARENOSO', 'Arenoso'],
  ['FRANCO', 'Franco'],
  ['ARCILLOSO', 'Arcilloso'],
  ['OTRO', 'Otro'],
]

export const PENDIENTES = [
  ['PLANA', 'Plana'],
  ['SUAVE', 'Suave'],
  ['MODERADA', 'Moderada'],
  ['FUERTE', 'Fuerte'],
]

export const DISPONIBILIDADES_AGUA = [
  ['ESCASA', 'Escasa'],
  ['MEDIA', 'Media'],
  ['ABUNDANTE', 'Abundante'],
]

export const SISTEMAS_RIEGO = [
  ['SECANO', 'Secano'],
  ['GRAVEDAD', 'Gravedad'],
  ['ASPERSION', 'Aspersión'],
  ['GOTEO', 'Goteo'],
]
