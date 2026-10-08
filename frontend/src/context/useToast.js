import { useContext } from 'react'
import { ToastContext } from './toastContexto.js'

export function useToast() {
  const contexto = useContext(ToastContext)
  if (!contexto) {
    throw new Error('useToast debe usarse dentro de <ToastProvider>')
  }
  return contexto
}
