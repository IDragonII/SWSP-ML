import { cliente } from './cliente.js'

export function listarParametros() {
  return cliente.get('/parametros/').then((r) => r.data)
}

export function guardarParametro(clave, valor) {
  return cliente.patch(`/parametros/${clave}/`, { valor }).then((r) => r.data)
}
