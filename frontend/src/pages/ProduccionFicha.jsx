import { useCallback, useEffect, useState } from 'react'
import {
  deshacerCosecha,
  obtenerProduccion,
  revisarProduccion,
} from '../api/produccion.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import ProduccionFormulario from './ProduccionFormulario.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

const CALIDAD = {
  PRIMERA: 'Primera',
  SEGUNDA: 'Segunda',
  TERCERA: 'Tercera',
}

export default function ProduccionFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [nota, setNota] = useState('')
  const [incluir, setIncluir] = useState(true)
  const [motivo, setMotivo] = useState('')
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditar = tienePermiso('produccion.editar')
  const puedeGestionar = tienePermiso('produccion.desactivar')
  const campaniaCerrada = ficha?.campania?.estado === 'CERRADA'

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerProduccion(id)
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

  async function enviarRevision(evento) {
    evento.preventDefault()
    const limpio = nota.trim()
    if (!limpio) return
    setOcupado(true)
    try {
      await revisarProduccion(id, limpio, incluir)
      avisar('Revisión registrada.')
      setNota('')
      recargar()
    } catch (e) {
      avisar(mensajeDeError(e), 'error')
    } finally {
      setOcupado(false)
    }
  }

  function pedirDeshacer() {
    const limpio = motivo.trim()
    if (!limpio) return
    setConfirmacion({
      titulo: 'Deshacer cosecha',
      texto: `¿Deshacer la cosecha? La producción se eliminará y la campaña volverá a EN_PRODUCCION. El motivo quedará registrado: «${limpio}».`,
      confirmar: 'Deshacer cosecha',
      nivel: 'peligro',
      accion: async () => {
        setOcupado(true)
        try {
          await deshacerCosecha(id, limpio)
          avisar('Cosecha deshecha. La campaña volvió a EN_PRODUCCION.')
          onCerrar?.()
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
      titulo={ficha ? `Producción del ${ficha.fecha_cosecha}` : 'Producción'}
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
              <Chip>{ficha.campania.estado}</Chip>{' '}
              <span className="nota">{`${ficha.produccion_kg} kg · ${ficha.rendimiento_kg_ha} kg/ha`}</span>
            </p>
            <div className="ficha-acciones">
              {puedeEditar && !campaniaCerrada && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setEditando(true)}
                >
                  Editar
                </button>
              )}
              {puedeGestionar && ficha.requiere_revision && (
                <button
                  type="button"
                  className="boton-primario"
                  onClick={() =>
                    document.getElementById('nota-revision')?.focus()
                  }
                >
                  Revisar producción
                </button>
              )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          {ficha.motivo_revision && (
            <section className="panel">
              <h2>
                {ficha.requiere_revision
                  ? 'Revisión pendiente'
                  : 'Revisión'}
              </h2>
              <dl className="datos-rejilla">
                <Dato rotulo="Motivo" valor={ficha.motivo_revision} />
                {ficha.incluir_en_entrenamiento !== undefined && (
                  <Dato
                    rotulo="En entrenamiento"
                    valor={
                      ficha.incluir_en_entrenamiento ? 'Sí' : 'No'
                    }
                  />
                )}
              </dl>
            </section>
          )}

          <section className="panel">
            <h2>Datos de la cosecha</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Fecha de cosecha" valor={ficha.fecha_cosecha} />
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
                rotulo="Cantidad"
                valor={`${ficha.cantidad_producida} ${ficha.unidad.simbolo}`}
              />
              <Dato
                rotulo="Producción"
                valor={`${ficha.produccion_kg} kg`}
              />
              <Dato
                rotulo="Superficie cosechada"
                valor={`${ficha.superficie_cosechada_ha} ha`}
              />
              <Dato
                rotulo="Rendimiento"
                valor={`${ficha.rendimiento_kg_ha} kg/ha`}
              />
              <Dato
                rotulo="Pérdida"
                valor={ficha.perdida_kg !== null ? `${ficha.perdida_kg} kg` : null}
              />
              <Dato
                rotulo="Calidad"
                valor={CALIDAD[ficha.calidad] ?? ficha.calidad}
              />
              <Dato
                rotulo="Requiere revisión"
                valor={ficha.requiere_revision ? 'Sí' : 'No'}
              />
              <Dato rotulo="Observaciones" valor={ficha.observaciones} />
              {ficha.registrado_por !== undefined && (
                <Dato rotulo="Registrado por" valor={ficha.registrado_por} />
              )}
            </dl>
          </section>

          {puedeGestionar && ficha.requiere_revision && (
            <section className="panel">
              <h2>Registrar revisión</h2>
              <form onSubmit={enviarRevision}>
                <Campo
                  id="nota-revision"
                  etiqueta="Nota de revisión"
                  ayuda="Obligatorio: se añade al motivo original para trazabilidad."
                >
                  <textarea
                    id="nota-revision"
                    rows={2}
                    value={nota}
                    onChange={(e) => setNota(e.target.value)}
                  />
                </Campo>
                <Campo
                  id="incluir-entrenamiento"
                  etiqueta="Incluir en el entrenamiento"
                  ayuda="Decide si esta producción entra en el dataset del modelo."
                >
                  <select
                    id="incluir-entrenamiento"
                    value={incluir ? 'true' : 'false'}
                    onChange={(e) => setIncluir(e.target.value === 'true')}
                  >
                    <option value="true">Sí</option>
                    <option value="false">No</option>
                  </select>
                </Campo>
                <div className="formulario-acciones">
                  <button
                    type="submit"
                    className="boton-primario"
                    disabled={ocupado || !nota.trim()}
                  >
                    {ocupado ? (
                      <>
                        <RuedaCarga etiqueta="Procesando…" />
                        Procesando…
                      </>
                    ) : (
                      'Registrar revisión'
                    )}
                  </button>
                </div>
              </form>
            </section>
          )}

          {puedeGestionar && !campaniaCerrada && (
            <section className="panel">
              <h2>Deshacer cosecha</h2>
              <Campo
                id="motivo-deshacer"
                etiqueta="Motivo"
                ayuda="Obligatorio: la producción se eliminará y la campaña volverá a EN_PRODUCCION."
              >
                <input
                  id="motivo-deshacer"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </Campo>
              <button
                type="button"
                className="boton-peligro"
                disabled={ocupado || !motivo.trim()}
                onClick={pedirDeshacer}
              >
                Deshacer cosecha
              </button>
            </section>
          )}
        </>
      )}

      {editando && (
        <ProduccionFormulario
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
