import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import RuedaCarga from './RuedaCarga.jsx'

// Pila de modales abiertos: Escape solo cierra el de arriba y el scroll
// del body se bloquea mientras haya al menos uno (se restaura al cerrar el último).
const pila = []
let overflowOriginal = null

export default function Modal({
  abierto,
  titulo,
  texto,
  children,
  tamano = 'confirmacion',
  confirmar = 'Confirmar',
  cancelar = 'Cancelar',
  nivel = 'primario',
  ocupado = false,
  onConfirmar,
  onCerrar,
}) {
  const idTitulo = useId()
  const dialogo = useRef(null)
  const botonConfirmar = useRef(null)
  const ocupadoRef = useRef(ocupado)
  const alCerrarRef = useRef(onCerrar)

  useEffect(() => {
    ocupadoRef.current = ocupado
    alCerrarRef.current = onCerrar
  })

  useEffect(() => {
    if (!abierto) return undefined
    const propio = {}
    pila.push(propio)
    if (overflowOriginal === null) {
      overflowOriginal = document.body.style.overflow
      document.body.style.overflow = 'hidden'
    }
    ;(botonConfirmar.current ?? dialogo.current)?.focus()
    const alPulsar = (evento) => {
      const esElDeArriba = pila[pila.length - 1] === propio
      if (evento.key === 'Escape' && esElDeArriba && !ocupadoRef.current) {
        alCerrarRef.current?.()
      }
    }
    document.addEventListener('keydown', alPulsar)
    return () => {
      document.removeEventListener('keydown', alPulsar)
      const posicion = pila.indexOf(propio)
      if (posicion >= 0) pila.splice(posicion, 1)
      if (pila.length === 0 && overflowOriginal !== null) {
        document.body.style.overflow = overflowOriginal
        overflowOriginal = null
      }
    }
  }, [abierto])

  if (!abierto) return null

  const conContenido = children !== undefined && children !== null

  return createPortal(
    <div
      className="modal-fondo"
      onClick={(evento) => {
        if (evento.target === evento.currentTarget && !ocupado) onCerrar?.()
      }}
    >
      <div
        ref={dialogo}
        className={`modal modal--${tamano}`}
        role="dialog"
        aria-modal="true"
        aria-busy={ocupado}
        aria-labelledby={idTitulo}
        tabIndex={-1}
      >
        <div className="modal-cabecera">
          <h2 className="modal-titulo" id={idTitulo}>
            {titulo}
          </h2>
          {conContenido && (
            <button
              type="button"
              className="modal-cerrar"
              aria-label="Cerrar"
              disabled={ocupado}
              onClick={onCerrar}
            >
              ✕
            </button>
          )}
        </div>
        {texto && <p className="modal-texto">{texto}</p>}
        {conContenido ? (
          <div className="modal-cuerpo">{children}</div>
        ) : (
          <div className="modal-acciones">
            <button
              type="button"
              className="boton-secundario"
              disabled={ocupado}
              onClick={onCerrar}
            >
              {cancelar}
            </button>
            <button
              ref={botonConfirmar}
              type="button"
              className={nivel === 'peligro' ? 'boton-peligro' : 'boton-primario'}
              disabled={ocupado}
              onClick={onConfirmar}
            >
              {ocupado ? (
                <>
                  <RuedaCarga etiqueta="Procesando…" />
                  Procesando…
                </>
              ) : (
                confirmar
              )}
            </button>
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
