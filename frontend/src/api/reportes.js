import { cliente } from './cliente.js'

// Reportes descargables (Semana 17, HU-141..HU-149): catálogo, vista
// previa y descarga en Excel/PDF. El archivo viaja en memoria (blob) y
// su nombre llega en la cabecera Content-Disposition.

export function listarReportes() {
  return cliente.get('/reportes/').then((r) => r.data.reportes)
}

export function vistaPrevia(tipo, params = {}) {
  return cliente
    .get(`/reportes/${tipo}/vista-previa/`, { params })
    .then((r) => r.data)
}

export async function descargarReporte(tipo, formato, params = {}) {
  try {
    const respuesta = await cliente.post(
      `/reportes/${tipo}/exportar/`,
      { formato },
      { params, responseType: 'blob' },
    )
    return {
      archivo: respuesta.data,
      nombre: nombreDe(respuesta.headers['content-disposition']),
    }
  } catch (error) {
    throw await errorLegible(error)
  }
}

function nombreDe(disposicion = '') {
  const coincidencia = /filename="?([^";]+)"?/i.exec(disposicion)
  return coincidencia ? coincidencia[1].trim() : null
}

// Con responseType blob el cuerpo del error también es un blob: se
// convierte a JSON para que mensajeDeError pueda leerlo.
async function errorLegible(error) {
  const datos = error?.response?.data
  if (datos instanceof Blob) {
    try {
      error.response.data = JSON.parse(await datos.text())
    } catch {
      error.response.data = null
    }
  }
  return error
}
