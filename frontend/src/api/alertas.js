import { cliente } from './cliente.js'

// Estados de la pestaña del listado (HU-127) y tipos del modelo Alerta
export const ESTADOS_ALERTA = [
  ['PENDIENTES', 'Pendientes'],
  ['ATENDIDAS', 'Atendidas'],
  ['TODAS', 'Todas'],
]

export const TIPOS_ALERTA = [
  ['INCIDENCIA_SEVERA', 'Incidencia severa'],
  ['SIN_ACTIVIDAD', 'Sin actividad'],
  ['RENDIMIENTO_BAJO', 'Rendimiento bajo'],
]

export function etiquetaTipo(tipo) {
  const encontrado = TIPOS_ALERTA.find(([valor]) => valor === tipo)
  return encontrado ? encontrado[1] : tipo
}

export function listarAlertas(params = {}) {
  return cliente.get('/alertas/', { params }).then((r) => r.data)
}

export function obtenerAlerta(id) {
  return cliente.get(`/alertas/${id}/`).then((r) => r.data)
}

export function resumenAlertas() {
  return cliente.get('/alertas/resumen/').then((r) => r.data)
}

export function productoresEnRiesgo() {
  return cliente.get('/alertas/productores-en-riesgo/').then((r) => r.data)
}

export function estadoEvaluacion() {
  return cliente.get('/alertas/evaluacion/').then((r) => r.data)
}

// Evaluación manual (HU-131): parametros.gestionar y una cada 5 minutos
export function evaluarAlertas(dryRun = false) {
  return cliente
    .post('/alertas/evaluar/', { dry_run: dryRun })
    .then((r) => r.data)
}

// Atención manual (HU-125): nota opcional de hasta 250 caracteres
export function atenderAlerta(id, nota) {
  return cliente
    .post(`/alertas/${id}/atender/`, { nota })
    .then((r) => r.data)
}

// Reapertura a mano (HU-125): lo cerrado automáticamente se reabre solo
export function reabrirAlerta(id) {
  return cliente.post(`/alertas/${id}/reabrir/`).then((r) => r.data)
}
