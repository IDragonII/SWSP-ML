import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import { listarTodo } from '../api/catalogos.js'
import { cerrarCampania, obtenerCampania } from '../api/campanias.js'
import Aviso from '../components/Aviso.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import ActividadFicha from './ActividadFicha.jsx'
import ActividadFormulario from './ActividadFormulario.jsx'
import CampaniaFormulario from './CampaniaFormulario.jsx'
import ProduccionFicha from './ProduccionFicha.jsx'
import ProduccionFormulario from './ProduccionFormulario.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function CampaniaFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [ficha, setFicha] = useState(null)
  const [actividades, setActividades] = useState([])
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [nuevaActividad, setNuevaActividad] = useState(false)
  const [actividadEditando, setActividadEditando] = useState(null)
  const [actividadFichaId, setActividadFichaId] = useState(null)
  const [produccionAbierta, setProduccionAbierta] = useState(false)
  const [produccionEditando, setProduccionEditando] = useState(null)
  const [produccionFichaId, setProduccionFichaId] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditarCampania = tienePermiso('campanias.editar')
  const puedeCrearActividad = tienePermiso('actividades.crear')
  const puedeCrearProduccion = tienePermiso('produccion.crear')
  const puedeCerrarCampania = tienePermiso('campanias.desactivar')

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  function puedeRegistrarProduccion() {
    return (
      puedeCrearProduccion &&
      ficha?.estado === 'EN_PRODUCCION' &&
      ficha?.fecha_siembra &&
      !ficha?.produccion
    )
  }

  function pedirCierre() {
    setConfirmacion({
      titulo: 'Cerrar campaña',
      texto: `¿Cerrar la campaña ${ficha.periodo}? Una vez cerrada no admite actividades ni cambios en la producción. Esta acción es irreversible.`,
      confirmar: 'Cerrar campaña',
      nivel: 'peligro',
      accion: async () => {
        setOcupado(true)
        try {
          await cerrarCampania(id)
          avisar('Campaña cerrada.')
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

  useEffect(() => {
    let activo = true
    obtenerCampania(id)
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

  useEffect(() => {
    let activo = true
    listarTodo('/actividades/', { campania: id })
      .then((lista) => activo && setActividades(lista))
      .catch(() => activo && setActividades([]))
    return () => {
      activo = false
    }
  }, [id, recarga])

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `Campaña ${ficha.periodo}` : 'Campaña'}
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
              <Chip>{ficha.estado}</Chip>{' '}
              <span className="nota">
                {ficha.actividades_activas} actividad(es) activa(s)
              </span>
            </p>
            <div className="ficha-acciones">
              {puedeCrearActividad &&
                ficha.estado !== 'CERRADA' &&
                ficha.estado !== 'CANCELADA' && (
                  <button
                    type="button"
                    className="boton-primario"
                    onClick={() => setNuevaActividad(true)}
                  >
                    Registrar actividad
                  </button>
                )}
              {puedeRegistrarProduccion() && (
                <button
                  type="button"
                  className="boton-primario"
                  onClick={() => setProduccionAbierta(true)}
                >
                  Registrar producción
                </button>
              )}
              {puedeCerrarCampania && ficha.estado === 'COSECHADA' && (
                <button
                  type="button"
                  className="boton-peligro"
                  onClick={pedirCierre}
                >
                  Cerrar campaña
                </button>
              )}
              {puedeEditarCampania && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setEditando(true)}
                >
                  Editar campaña
                </button>
              )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          <section className="panel">
            <h2>Datos de la campaña</h2>
            <dl className="datos-rejilla">
              <Dato
                rotulo="Productor"
                valor={ficha.parcela.productor.nombre_completo}
              />
              <Dato rotulo="Parcela" valor={ficha.parcela.codigo} />
              <Dato rotulo="Cultivo" valor={ficha.cultivo.nombre} />
              <Dato rotulo="Variedad" valor={ficha.variedad.nombre} />
              <Dato rotulo="Ciclo" valor={`${ficha.fecha_inicio} → ${ficha.fecha_fin_prevista}`} />
              <Dato rotulo="Fecha de siembra" valor={ficha.fecha_siembra} />
              <Dato rotulo="Sembrada" valor={`${ficha.superficie_sembrada_ha} ha`} />
              <Dato rotulo="Última actividad" valor={ficha.fecha_ultima_actividad} />
              <Dato rotulo="Observaciones" valor={ficha.observaciones} />
              <Dato rotulo="Creado por" valor={ficha.creado_por} />
            </dl>
          </section>

          <section className="panel">
            <h2>Actividades</h2>
            {actividades.length > 0 ? (
              <Tabla
                filas={actividades}
                columnas={[
                  {
                    clave: 'fecha',
                    etiqueta: 'Fecha',
                    celda: (actividad) => actividad.fecha,
                  },
                  {
                    clave: 'tipo',
                    etiqueta: 'Tipo',
                    celda: (actividad) => actividad.tipo_actividad.nombre,
                  },
                  {
                    clave: 'metodo',
                    etiqueta: 'Método',
                    celda: (actividad) => actividad.metodo || '—',
                  },
                  {
                    clave: 'estado',
                    etiqueta: 'Estado',
                    celda: (actividad) => (
                      <Chip>{actividad.anulada ? 'ANULADA' : 'ACTIVA'}</Chip>
                    ),
                  },
                  {
                    clave: 'acciones',
                    etiqueta: 'Acciones',
                    acciones: true,
                    celda: (actividad) =>
                      !actividad.anulada && tienePermiso('actividades.editar') ? (
                        <button
                          type="button"
                          className="boton-texto"
                          onClick={() => setActividadEditando(actividad.id)}
                        >
                          Editar
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="boton-texto"
                          onClick={() => setActividadFichaId(actividad.id)}
                        >
                          Ver ficha
                        </button>
                      ),
                  },
                ]}
              />
            ) : (
              <p className="nota">
                Esta campaña todavía no tiene actividades registradas.
              </p>
            )}
          </section>

          <section className="panel">
            <h2>Producción</h2>
            {ficha.produccion ? (
              <dl className="datos-rejilla">
                <Dato
                  rotulo="Fecha de cosecha"
                  valor={ficha.produccion.fecha_cosecha}
                />
                <Dato
                  rotulo="Producción"
                  valor={`${ficha.produccion.produccion_kg} kg`}
                />
                <Dato
                  rotulo="Rendimiento"
                  valor={`${ficha.produccion.rendimiento_kg_ha} kg/ha`}
                />
                <Dato rotulo="Revisión" valor={ficha.produccion.requiere_revision ? <Chip>REQUIERE REVISIÓN</Chip> : 'Sin revisión'} />
                <div>
                  <dt>Acciones</dt>
                  <dd>
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setProduccionFichaId(ficha.produccion.id)}
                    >
                      Ver ficha de producción
                    </button>
                    {tienePermiso('produccion.editar') &&
                      ficha.estado !== 'CERRADA' && (
                        <button
                          type="button"
                          className="boton-texto"
                          onClick={() =>
                            setProduccionEditando(ficha.produccion.id)
                          }
                        >
                          Editar producción
                        </button>
                      )}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="nota">
                {ficha.estado === 'PLANIFICADA'
                  ? 'La campaña está planificada: registra la siembra para poder capturar la cosecha.'
                  : ficha.estado === 'EN_PRODUCCION' && !ficha.fecha_siembra
                    ? 'La campaña aún no tiene siembra registrada: registra la actividad de siembra antes de la producción.'
                    : ficha.estado === 'EN_PRODUCCION'
                      ? 'Esta campaña todavía no tiene cosecha registrada.'
                      : ficha.estado === 'CANCELADA'
                        ? 'La campaña está cancelada y no admite producción.'
                        : 'Esta campaña no tiene producción registrada.'}
              </p>
            )}
          </section>
        </>
      )}

      {editando && (
        <CampaniaFormulario
          id={id}
          abierto
          onGuardado={() => {
            setEditando(false)
            recargar()
          }}
          onCancelar={() => {
            setEditando(false)
            recargar()
          }}
        />
      )}

      {nuevaActividad && ficha && (
        <ActividadFormulario
          campaniaInicial={ficha.id}
          abierto
          onGuardado={() => {
            setNuevaActividad(false)
            recargar()
          }}
          onCancelar={() => setNuevaActividad(false)}
        />
      )}

      {actividadEditando !== null && (
        <ActividadFormulario
          id={actividadEditando}
          abierto
          onGuardado={() => {
            setActividadEditando(null)
            recargar()
          }}
          onCancelar={() => {
            setActividadEditando(null)
            recargar()
          }}
        />
      )}

      {actividadFichaId !== null && (
        <ActividadFicha
          id={actividadFichaId}
          abierto
          onCerrar={() => {
            setActividadFichaId(null)
            recargar()
          }}
        />
      )}

      {produccionAbierta && ficha && (
        <ProduccionFormulario
          campaniaInicial={ficha.id}
          abierto
          onGuardado={() => {
            setProduccionAbierta(false)
            recargar()
          }}
          onCancelar={() => setProduccionAbierta(false)}
        />
      )}

      {produccionEditando !== null && (
        <ProduccionFormulario
          id={produccionEditando}
          abierto
          onGuardado={() => {
            setProduccionEditando(null)
            recargar()
          }}
          onCancelar={() => {
            setProduccionEditando(null)
            recargar()
          }}
        />
      )}

      {produccionFichaId !== null && (
        <ProduccionFicha
          id={produccionFichaId}
          abierto
          onCerrar={() => {
            setProduccionFichaId(null)
            recargar()
          }}
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
