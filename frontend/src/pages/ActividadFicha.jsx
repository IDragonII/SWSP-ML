import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import {
  anularActividad,
  obtenerActividad,
  reactivarActividad,
} from '../api/actividades.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import ActividadFormulario from './ActividadFormulario.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function ActividadFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditar = tienePermiso('actividades.editar')
  const puedeDesactivar = tienePermiso('actividades.desactivar')
  const esSiembra = ficha?.tipo_actividad?.codigo === 'SIEMBRA'

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerActividad(id)
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
      titulo: 'Anular actividad',
      texto: `¿Anular esta actividad? El motivo quedará registrado: «${limpio}».${
        esSiembra
          ? ' Al ser una siembra, la fecha de siembra de la campaña se recalculará.'
          : ''
      }`,
      confirmar: 'Anular actividad',
      nivel: 'peligro',
      accion: async () => {
        setOcupado(true)
        try {
          await anularActividad(id, limpio)
          avisar('Actividad anulada.')
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
      titulo: 'Reactivar actividad',
      texto:
        '¿Reactivar esta actividad? La campaña debe seguir abierta y la fecha dentro de su período. Al ser una siembra, la fecha de siembra de la campaña se recalculará otra vez.',
      confirmar: 'Reactivar',
      accion: async () => {
        setOcupado(true)
        try {
          await reactivarActividad(id)
          avisar('Actividad reactivada.')
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
      titulo={ficha ? `Actividad del ${ficha.fecha}` : 'Actividad'}
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
              {ficha.tipo_actividad.nombre} <Chip>{ficha.anulada ? 'ANULADA' : 'ACTIVA'}</Chip>
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
                  Anular actividad
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
            <h2>Datos de la actividad</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Fecha" valor={ficha.fecha} />
              <Dato rotulo="Tipo" valor={ficha.tipo_actividad.nombre} />
              <Dato
                rotulo="Campaña"
                valor={`${ficha.campania.periodo} · ${ficha.campania.cultivo.nombre}`}
              />
              <Dato
                rotulo="Parcela"
                valor={ficha.campania.parcela.codigo}
              />
              <Dato
                rotulo="Productor"
                valor={ficha.campania.parcela.productor.nombre_completo}
              />
              <Dato rotulo="Método" valor={ficha.metodo} />
              <Dato
                rotulo="Densidad"
                valor={
                  ficha.densidad_siembra
                    ? `${ficha.densidad_siembra} ${
                        UNIDADES[ficha.densidad_unidad] ?? ficha.densidad_unidad
                      }`
                    : null
                }
              />
              <Dato rotulo="Horas" valor={ficha.horas} />
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
              <h2>Anular actividad</h2>
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
                  'Anular actividad'
                )}
              </button>
            </section>
          )}
        </>
      )}

      {editando && (
        <ActividadFormulario
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

const UNIDADES = {
  KG_HA: 'kg/ha',
  PLANTAS_M2: 'plantas/m²',
}
