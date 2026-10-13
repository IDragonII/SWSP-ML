import { cliente } from './cliente.js'

export async function listarTodo(ruta, params = {}) {
  const resultados = []
  let pagina = 1
  for (;;) {
    const { data } = await cliente.get(ruta, { params: { ...params, page: pagina } })
    // Los desplegables (?desplegable=1) devuelven una lista sin paginar
    if (Array.isArray(data)) return [...resultados, ...data]
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

// API de un catálogo de la Semana 5: recibe la ruta base
// ('/cultivos/', '/unidades/', …) y devuelve el CRUD sin DELETE.
export function apiCatalogo(ruta) {
  return {
    listar(params = {}) {
      return cliente.get(ruta, { params }).then((r) => r.data)
    },
    obtener(id) {
      return cliente.get(`${ruta}${id}/`).then((r) => r.data)
    },
    guardar(id, datos) {
      const peticion = id
        ? cliente.patch(`${ruta}${id}/`, datos)
        : cliente.post(ruta, datos)
      return peticion.then((r) => r.data)
    },
    cambiarEstado(id, activo) {
      return cliente
        .patch(`${ruta}${id}/estado/`, { activo })
        .then((r) => r.data)
    },
    desplegable(params = {}) {
      return cliente
        .get(ruta, { params: { ...params, desplegable: 1 } })
        .then((r) => r.data)
    },
  }
}
