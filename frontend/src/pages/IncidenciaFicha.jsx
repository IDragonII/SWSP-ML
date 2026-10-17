import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import {
  anularIncidencia,
  obtenerIncidencia,
  reactivarIncidencia,
} from '../api/incidencias.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import IncidenciaFormulario from './IncidenciaFormulario.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function IncidenciaFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditar = tienePermiso('incidencias.editar')
  const puedeDesactivar = tienePermiso('incidencias.desactivar')

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerIncidencia(id)
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
      titulo: 'Anular incidencia',
      texto: `¿Anular esta incidencia? El registro se conserva y el motivo quedará registrado: «${limpio}». Las anuladas no cuentan en el dataset ni en los resúmenes.`,
      confirmar: 'Anular incidencia',
      nivel: 'peligro',
      accion: async () => {
        setOcupado(true)
        try {
          await anularIncidencia(id, limpio)
          avisar('Incidencia anulada.')
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
      titulo: 'Reactivar incidencia',
      texto:
        '¿Reactivar esta incidencia? La campaña debe seguir abierta y la fecha dentro de su período.',
      confirmar: 'Reactivar',
      accion: async () => {
        setOcupado(true)
        try {
          await reactivarIncidencia(id)
          avisar('Incidencia reactivada.')
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
      titulo={ficha ? `Incidencia del ${ficha.fecha}` : 'Incidencia'}
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
              {ficha.tipo_incidencia.nombre}{' '}
              <Chip>{ficha.tipo_incidencia.categoria}</Chip>{' '}
              <Chip>{ficha.severidad}</Chip>{' '}
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
                  Anular incidencia
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
            <h2>Datos de la incidencia</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Fecha" valor={ficha.fecha} />
              <Dato rotulo="Tipo" valor={ficha.tipo_incidencia.nombre} />
              <Dato rotulo="Categoría" valor={ficha.tipo_incidencia.categoria} />
              <Dato rotulo="Severidad" valor={ficha.severidad} />
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
              <Dato
                rotulo="Superficie afectada"
                valor={
                  ficha.superficie_afectada_ha !== null
                    ? `${ficha.superficie_afectada_ha} ha`
                    : null
                }
              />
              <Dato
                rotulo="Agente"
                valor={
                  ficha.agente
                    ? `${ficha.agente.nombre} (${ficha.agente.tipo})`
                    : null
                }
              />
              <Dato rotulo="Producto aplicado" valor={ficha.producto_aplicado} />
              <Dato rotulo="Descripción" valor={ficha.descripcion} />
            </dl>
          </section>

          <section className="panel">
            <h2>Trazabilidad</h2>
            <dl className="datos-rejilla">
              {ficha.registrado_por !== undefined && (
                <Dato rotulo="Registrado por" valor={ficha.registrado_por} />
              )}
              <Dato rotulo="Creado" valor={ficha.creado_en} />
              <Dato rotulo="Última edición" valor={ficha.actualizado_en} />
            </dl>
          </section>

          {puedeDesactivar && !ficha.anulada && (
            <section className="panel">
              <h2>Anular incidencia</h2>
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
                  'Anular incidencia'
                )}
              </button>
            </section>
          )}
        </>
      )}

      {editando && (
        <IncidenciaFormulario
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
