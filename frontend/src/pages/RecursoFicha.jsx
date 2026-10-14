import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import {
  anularUsoRecurso,
  obtenerUsoRecurso,
  reactivarUsoRecurso,
} from '../api/usosRecursos.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import RecursoFormulario from './RecursoFormulario.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function RecursoFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditar = tienePermiso('recursos.editar')
  const puedeDesactivar = tienePermiso('recursos.desactivar')

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerUsoRecurso(id)
      .then((datos) => {
        if (!activo) return
        setError(null)
        setFicha(datos)
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [id, recarga])

  function pedirAnulacion() {
    const limpio = motivo.trim()
    if (!limpio) return
    setConfirmacion({
      titulo: 'Anular uso de recurso',
      texto: `¿Anular este uso de recurso? El motivo quedará registrado: «${limpio}».`,
      confirmar: 'Anular uso',
      nivel: 'peligro',
      accion: async () => {
        setOcupado(true)
        try {
          await anularUsoRecurso(id, limpio)
          avisar('Uso de recurso anulado.')
          setMotivo('')
          recargar()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    })
  }

  function pedirReactivacion() {
    setConfirmacion({
      titulo: 'Reactivar uso de recurso',
      texto:
        '¿Reactivar este uso de recurso? La campaña debe seguir abierta y la fecha dentro de su período.',
      confirmar: 'Reactivar',
      accion: async () => {
        setOcupado(true)
        try {
          await reactivarUsoRecurso(id)
          avisar('Uso de recurso reactivado.')
          recargar()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    })
  }

  async function ejecutarConfirmacion() {
    if (!confirmacion) return
    await confirmacion.accion()
    setConfirmacion(null)
  }

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `Uso de recurso del ${ficha.fecha}` : 'Uso de recurso'}
      ocupado={ocupado}
      onCerrar={onCerrar}
    >
      {error && !ficha ? (
        <Aviso>{error}</Aviso>
      ) : !ficha ? (
        <Cargando />
      ) : (
        <>
          <div className="ficha-cabecera">
            <p className="ficha-estado">
              {ficha.recurso.nombre} <Chip>{ficha.recurso.categoria}</Chip>{' '}
              <Chip>{ficha.anulada ? 'ANULADA' : 'ACTIVA'}</Chip>
            </p>
            <div className="ficha-acciones">
              {puedeEditar && !ficha.anulada && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setEditando(true)}
                >
                  Editar
                </button>
              )}
              {puedeDesactivar && !ficha.anulada && (
                <button
                  type="button"
                  className="boton-peligro"
                  disabled={ocupado}
                  onClick={() =>
                    document.getElementById('motivo-anulacion')?.focus()
                  }
                >
                  Anular uso
                </button>
              )}
              {puedeDesactivar && ficha.anulada && (
                <button
                  type="button"
                  className="boton-primario"
                  disabled={ocupado}
                  onClick={pedirReactivacion}
                >
                  Reactivar
                </button>
              )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          {ficha.anulada && (
            <section className="panel">
              <h2>Anulación</h2>
              <dl className="datos-rejilla">
                <Dato rotulo="Motivo" valor={ficha.motivo_anulacion} />
              </dl>
            </section>
          )}

          <section className="panel">
            <h2>Datos del uso</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Fecha" valor={ficha.fecha} />
              <Dato rotulo="Recurso" valor={ficha.recurso.nombre} />
              <Dato rotulo="Categoría" valor={ficha.recurso.categoria} />
              <Dato
                rotulo="Tipo de unidad"
                valor={ficha.recurso.tipo_unidad}
              />
              <Dato
                rotulo="Cantidad"
                valor={`${ficha.cantidad} ${ficha.unidad.simbolo}`}
              />
              <Dato
                rotulo="En unidad base"
                valor={ficha.cantidad_base}
              />
              <Dato
                rotulo="Campaña"
                valor={`${ficha.campania.periodo} · ${ficha.campania.cultivo.nombre}`}
              />
              <Dato
                rotulo="Actividad"
                valor={
                  ficha.actividad
                    ? `${ficha.actividad.fecha} — ${ficha.actividad.tipo.nombre}`
                    : null
                }
              />
              <Dato
                rotulo="Costo"
                valor={ficha.costo !== null ? `S/ ${ficha.costo}` : null}
              />
              <Dato rotulo="Observaciones" valor={ficha.observaciones} />
              {ficha.registrado_por !== undefined && (
                <Dato rotulo="Registrado por" valor={ficha.registrado_por} />
              )}
            </dl>
          </section>

          {puedeDesactivar && !ficha.anulada && (
            <section className="panel">
              <h2>Anular uso de recurso</h2>
              <Campo
                id="motivo-anulacion"
                etiqueta="Motivo de la anulación"
                ayuda="Obligatorio: el registro se conserva y queda como anulado."
              >
                <input
                  id="motivo-anulacion"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </Campo>
              <button
                type="button"
                className="boton-peligro"
                disabled={ocupado || !motivo.trim()}
                onClick={pedirAnulacion}
              >
                {ocupado ? (
                  <>
                    <RuedaCarga etiqueta="Procesando…" />
                    Procesando…
                  </>
                ) : (
                  'Anular uso'
                )}
              </button>
            </section>
          )}
        </>
      )}

      {editando && (
        <RecursoFormulario
          id={id}
          abierto
          onGuardado={() => {
            setEditando(false)
            recargar()
          }}
          onCancelar={() => setEditando(false)}
        />
      )}

      <Modal
        abierto={confirmacion !== null}
        titulo={confirmacion?.titulo}
        texto={confirmacion?.texto}
        confirmar={confirmacion?.confirmar}
        nivel={confirmacion?.nivel}
        ocupado={ocupado}
        onConfirmar={ejecutarConfirmacion}
        onCerrar={() => setConfirmacion(null)}
      />
    </Modal>
  )
}
