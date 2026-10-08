import { cliente } from './cliente.js'

export async function listarTodo(ruta, params = {}) {
  const resultados = []
  let pagina = 1
  for (;;) {
    const { data } = await cliente.get(ruta, { params: { ...params, page: pagina } })
    resultados.push(...data.results)
    if (!data.next || data.results.length === 0) break
    pagina += 1
  }
  return resultados
}

export function obtenerProvincias() {
  return listarTodo('/ubicaciones/provincias/', { activo: 'true' })
}

export function obtenerDistritos(provincia) {
  if (!provincia) return Promise.resolve([])
  return listarTodo('/ubicaciones/distritos/', { activo: 'true', provincia })
}

export function obtenerComunidades(distrito) {
  if (!distrito) return Promise.resolve([])
  return listarTodo('/ubicaciones/comunidades/', { activo: 'true', distrito })
}

export function tecnicosDisponibles() {
  return cliente.get('/asignaciones/tecnicos-disponibles/').then((r) => r.data)
}
