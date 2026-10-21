// Fechas en hora de Lima para las tablas y fichas (formato corto, es-PE).

const OPCIONES_FECHA = { day: 'numeric', month: 'numeric', year: '2-digit' }
const OPCIONES_HORA = { hour: 'numeric', minute: '2-digit' }

export function fechaCorta(valor) {
  if (!valor) return '—'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return valor
  return fecha.toLocaleDateString('es-PE', OPCIONES_FECHA)
}

export function horaCorta(valor) {
  if (!valor) return '—'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return ''
  return fecha.toLocaleTimeString('es-PE', OPCIONES_HORA)
}

export function fechaHoraCorta(valor) {
  if (!valor) return '—'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return valor
  return fecha.toLocaleString('es-PE', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}
