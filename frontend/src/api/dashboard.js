import { cliente } from './cliente.js'

// Panel de indicadores (Semana 16, HU-133..HU-140): cuatro lecturas
// bajo el permiso dashboard.ver, todas de solo lectura.
export const AGRUPACIONES = [
  ['cultivo', 'Por cultivo'],
  ['distrito', 'Por distrito'],
]

export function dashboardResumen() {
  return cliente.get('/dashboard/resumen/').then((r) => r.data)
}

export function dashboardCampaniasEstado(params = {}) {
  return cliente
    .get('/dashboard/campanias-estado/', { params })
    .then((r) => r.data)
}

export function dashboardProduccion(params = {}) {
  return cliente.get('/dashboard/produccion/', { params }).then((r) => r.data)
}

export function dashboardFiltros(params = {}) {
  return cliente.get('/dashboard/filtros/', { params }).then((r) => r.data)
}
