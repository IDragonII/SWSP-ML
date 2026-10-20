import { cliente } from './cliente.js'

// API de Machine Learning (S22, HU-172/HU-173/HU-177). Los cuatro
// recursos de docs/api_ml.md.

export function listarPredicciones(params = {}) {
  return cliente.get('/ml/predicciones/', { params }).then((r) => r.data)
}

export function obtenerPrediccion(id) {
  return cliente.get(`/ml/predicciones/${id}/`).then((r) => r.data)
}

export function predecir(datos) {
  return cliente.post('/ml/predicciones/', datos).then((r) => r.data)
}

export function listarModelos() {
  return cliente.get('/ml/modelos/').then((r) => r.data)
}

export function activarModelo(id) {
  return cliente.post(`/ml/modelos/${id}/activar/`, {}).then((r) => r.data)
}

export function modeloActivo() {
  return cliente.get('/ml/modelo-activo/').then((r) => r.data)
}

export function listarCampaniasPredecibles(params = {}) {
  return cliente.get('/ml/campanas-predecibles/', { params }).then((r) => r.data)
}
