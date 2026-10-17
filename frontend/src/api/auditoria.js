import { cliente } from './cliente.js'

// Las 15 acciones del modelo del backend (auditoria/models.py)
export const ACCIONES_AUDITORIA = [
  'CREAR',
  'MODIFICAR',
  'ELIMINAR',
  'ACTIVAR',
  'DESACTIVAR',
  'ANULAR',
  'REACTIVAR',
  'ASIGNAR',
  'DESASIGNAR',
  'LOGIN',
  'LOGOUT',
  'BLOQUEAR',
  'DESBLOQUEAR',
  'RESTABLECER_CLAVE',
  'CAMBIAR_CLAVE',
]

export function listarAuditoria(params = {}) {
  return cliente.get('/auditoria/', { params }).then((r) => r.data)
}
