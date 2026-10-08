import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ToastContext } from './toastContexto.js'

const MAXIMO = 3
const DURACION_OK = 4000
let consecutivo = 0

export function ToastProvider({ children }) {
  const [avisos, setAvisos] = useState([])
  const temporizadores = useRef(new Map())

  const quitar = useCallback((id) => {
    const temporizador = temporizadores.current.get(id)
    if (temporizador) {
      clearTimeout(temporizador)
      temporizadores.current.delete(id)
    }
    setAvisos((previos) => previos.filter((aviso) => aviso.id !== id))
  }, [])

  const avisar = useCallback(
    (texto, nivel = 'ok') => {
      if (!texto) return
      consecutivo += 1
      const id = consecutivo
      setAvisos((previos) => [...previos, { id, texto, nivel }].slice(-MAXIMO))
      // Los errores se quedan hasta que el usuario pulse la ✕.
      if (nivel !== 'error') {
        temporizadores.current.set(
          id,
          setTimeout(() => quitar(id), DURACION_OK),
        )
      }
    },
    [quitar],
  )

  useEffect(
    () => () => {
      for (const temporizador of temporizadores.current.values()) {
        clearTimeout(temporizador)
      }
      temporizadores.current.clear()
    },
    [],
  )

  const valor = useMemo(() => ({ avisar }), [avisar])

  return (
    <ToastContext.Provider value={valor}>
      {children}
      <div className="toasts">
        {avisos.map((aviso) => (
          <div
            key={aviso.id}
            className={aviso.nivel === 'error' ? 'toast toast-error' : 'toast'}
            role={aviso.nivel === 'error' ? 'alert' : 'status'}
          >
            <span>{aviso.texto}</span>
            <button
              type="button"
              className="toast-cerrar"
              aria-label="Cerrar aviso"
              onClick={() => quitar(aviso.id)}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
