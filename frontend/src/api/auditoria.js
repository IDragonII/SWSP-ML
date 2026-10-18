import { cliente } from './cliente.js'

// Las 16 acciones del modelo del backend (auditoria/models.py: ACCIONES)
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
  'EXPORTAR',
]

// Etiquetas en español de cada acción (las mismas del modelo)
export const ETIQUETAS_ACCION = {
  CREAR: 'Crear',
  MODIFICAR: 'Modificar',
  ELIMINAR: 'Eliminar',
  ACTIVAR: 'Activar',
  DESACTIVAR: 'Desactivar',
  ANULAR: 'Anular',
  REACTIVAR: 'Reactivar',
  ASIGNAR: 'Asignar',
  DESASIGNAR: 'Desasignar',
  LOGIN: 'Iniciar sesión',
  LOGOUT: 'Cerrar sesión',
  BLOQUEAR: 'Bloquear acceso',
  DESBLOQUEAR: 'Desbloquear acceso',
  RESTABLECER_CLAVE: 'Restablecer contraseña',
  CAMBIAR_CLAVE: 'Cambiar contraseña',
  EXPORTAR: 'Exportar',
}

export function listarAuditoria(params = {}) {
  return cliente.get('/auditoria/', { params }).then((r) => r.data)
}
