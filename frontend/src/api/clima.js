import { cliente } from './cliente.js'

export function listarClima(params = {}) {
  return cliente.get('/clima/', { params }).then((r) => r.data)
}

export function obtenerClima(id) {
  return cliente.get(`/clima/${id}/`).then((r) => r.data)
}

export function guardarClima(id, datos) {
  const peticion = id
    ? cliente.patch(`/clima/${id}/`, datos)
    : cliente.post('/clima/', datos)
  return peticion.then((r) => r.data)
}

// HU-84: baja lecturas de la API meteorológica para una parcela con
// coordenadas (máx. 92 días); la respuesta es el informe de la consulta
export function consultaApiMeteorologica(datos) {
  return cliente.post('/clima/consulta-api/', datos).then((r) => r.data)
}

// Mismos valores del modelo Clima.fuente (el backend solo admite MANUAL y
// API en el filtro del listado)
export const FUENTES_CLIMA = [
  ['MANUAL', 'Manual'],
  ['API', 'API meteorológica'],
]
