import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { mensajeDeError } from '../api/errores.js'
import { listarTodo } from '../api/catalogos.js'
import { listarAlertas } from '../api/alertas.js'
import {
  cerrarCampania,
  obtenerCampania,
  obtenerLineaTiempo,
} from '../api/campanias.js'
import { listarEtapasCampania } from '../api/etapasCampania.js'
import Aviso from '../components/Aviso.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import LineaTiempo from '../components/LineaTiempo.jsx'
import Modal from '../components/Modal.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import ActividadFicha from './ActividadFicha.jsx'
import ActividadFormulario from './ActividadFormulario.jsx'
import CampaniaFormulario from './CampaniaFormulario.jsx'
import EtapaFormulario from './EtapaFormulario.jsx'
import IncidenciaFormulario from './IncidenciaFormulario.jsx'
import ProduccionFicha from './ProduccionFicha.jsx'
import ProduccionFormulario from './ProduccionFormulario.jsx'
import RecursoFormulario from './RecursoFormulario.jsx'

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
  const navegar = useNavigate()
  const [ficha, setFicha] = useState(null)
  const [actividades, setActividades] = useState([])
  const [lineaTiempo, setLineaTiempo] = useState(null)
  const [etapas, setEtapas] = useState([])
  const [alertas, setAlertas] = useState([])
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [nuevaActividad, setNuevaActividad] = useState(false)
  const [actividadEditando, setActividadEditando] = useState(null)
  const [actividadFichaId, setActividadFichaId] = useState(null)
  const [produccionAbierta, setProduccionAbierta] = useState(false)
  const [produccionEditando, setProduccionEditando] = useState(null)
  const [produccionFichaId, setProduccionFichaId] = useState(null)
  const [recursoAbierto, setRecursoAbierto] = useState(false)
  const [nuevaIncidencia, setNuevaIncidencia] = useState(false)
  const [nuevaEtapa, setNuevaEtapa] = useState(false)
  const [etapaEditandoId, setEtapaEditandoId] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditarCampania = tienePermiso('campanias.editar')
  const puedeCrearActividad = tienePermiso('actividades.crear')
  const puedeCrearProduccion = tienePermiso('produccion.crear')
  const puedeCrearRecurso = tienePermiso('recursos.crear')
  const puedeCrearIncidencia = tienePermiso('incidencias.crear')
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

  useEffect(() => {
    let activo = true
    obtenerLineaTiempo(id)
      .then((datos) => activo && setLineaTiempo(datos))
      .catch(() => activo && setLineaTiempo(null))
    listarEtapasCampania({ campania: id })
      .then((respuesta) => activo && setEtapas(respuesta.results ?? []))
      .catch(() => activo && setEtapas([]))
    if (tienePermiso('alertas.ver')) {
      listarAlertas({ campania: id, estado: 'TODAS' })
        .then((respuesta) => activo && setAlertas(respuesta.results ?? []))
        .catch(() => activo && setAlertas([]))
    }
    return () => {
      activo = false
    }
  }, [id, recarga, tienePermiso])

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
              {puedeCrearRecurso &&
                ficha.estado !== 'CERRADA' &&
                ficha.estado !== 'CANCELADA' && (
                  <button
                    type="button"
                    className="boton-primario"
                    onClick={() => setRecursoAbierto(true)}
                  >
                    Registrar recurso
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
            <div className="ficha-cabecera">
              <h2>Línea de tiempo</h2>
              <div className="ficha-acciones">
                {puedeEditarCampania &&
                  ficha.estado !== 'CERRADA' &&
                  ficha.estado !== 'CANCELADA' && (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setNuevaEtapa(true)}
                    >
                      Registrar etapa
                    </button>
                  )}
              </div>
            </div>
            <LineaTiempo datos={lineaTiempo} />
            {etapas.length > 0 && (
              <Tabla
                filas={etapas}
                columnas={[
                  {
                    clave: 'etapa',
                    etiqueta: 'Etapa',
                    celda: (fila) => (
                      <strong>
                        {fila.etapa.nombre}{' '}
                        <span className="nota">(orden {fila.etapa.orden})</span>
                      </strong>
                    ),
                  },
                  {
                    clave: 'fecha_inicio',
                    etiqueta: 'Inicio',
                    celda: (fila) => fila.fecha_inicio,
                  },
                  {
                    clave: 'fecha_fin',
                    etiqueta: 'Fin',
                    celda: (fila) =>
                      fila.fecha_fin ?? <Chip>EN CURSO</Chip>,
                  },
                  {
                    clave: 'observaciones',
                    etiqueta: 'Observaciones',
                    celda: (fila) => fila.observaciones || '—',
                  },
                  {
                    clave: 'acciones',
                    etiqueta: 'Acciones',
                    acciones: true,
                    celda: (fila) =>
                      puedeEditarCampania &&
                      ficha.estado !== 'CERRADA' &&
                      ficha.estado !== 'CANCELADA' ? (
                        <button
                          type="button"
                          className="boton-texto"
                          onClick={() => setEtapaEditandoId(fila.id)}
                        >
                          Editar
                        </button>
                      ) : (
                        <span className="nota">Solo lectura</span>
                      ),
                  },
                ]}
              />
            )}
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

          <section className="panel">
            <h2>Resumen de recursos</h2>
            {ficha.resumen_recursos && ficha.resumen_recursos.length > 0 ? (
              <>
                <Tabla
                  filas={ficha.resumen_recursos}
                  columnas={[
                    {
                      clave: 'categoria',
                      etiqueta: 'Categoría',
                      celda: (fila) => <Chip>{fila.categoria}</Chip>,
                    },
                    {
                      clave: 'total',
                      etiqueta: 'Total',
                      celda: (fila) => `${fila.total} ${fila.unidad}`,
                    },
                    {
                      clave: 'total_ha',
                      etiqueta: 'Por hectárea',
                      celda: (fila) =>
                        fila.total_ha === null
                          ? '—'
                          : `${fila.total_ha} ${fila.unidad}/ha`,
                    },
                    {
                      clave: 'registros',
                      etiqueta: 'Registros',
                      celda: (fila) => fila.registros,
                    },
                  ]}
                />
                <p className="nota">
                  Suma de los usos activos en la unidad base de cada
                  categoría; el combustible se muestra en litros. Los usos
                  anulados (incluidos los de la cascada) no cuentan.
                </p>
              </>
            ) : (
              <p className="nota">
                {ficha.estado === 'CANCELADA'
                  ? 'La campaña está cancelada y no admite usos de recursos.'
                  : 'Esta campaña todavía no tiene usos de recursos registrados.'}
              </p>
            )}
          </section>

          <section className="panel">
            <h2>Resumen de clima</h2>
            {ficha.resumen_clima && ficha.resumen_clima.dias_con_clima > 0 ? (
              <>
                <dl className="datos-rejilla">
                  <Dato
                    rotulo="Precipitación acumulada"
                    valor={
                      ficha.resumen_clima.precipitacion_acum_mm !== null
                        ? `${ficha.resumen_clima.precipitacion_acum_mm} mm`
                        : null
                    }
                  />
                  <Dato
                    rotulo="Temperatura promedio"
                    valor={
                      ficha.resumen_clima.temp_prom_c !== null
                        ? `${ficha.resumen_clima.temp_prom_c} °C`
                        : null
                    }
                  />
                  <Dato
                    rotulo="Humedad promedio"
                    valor={
                      ficha.resumen_clima.humedad_prom_pct !== null
                        ? `${ficha.resumen_clima.humedad_prom_pct} %`
                        : null
                    }
                  />
                  <Dato rotulo="Heladas" valor={ficha.resumen_clima.n_heladas} />
                  <Dato
                    rotulo="Cobertura"
                    valor={`${ficha.resumen_clima.cobertura_pct} %`}
                  />
                  <Dato
                    rotulo="Días con clima"
                    valor={`${ficha.resumen_clima.dias_con_clima} de ${ficha.resumen_clima.dias_ventana}`}
                  />
                </dl>
                <p className="nota">
                  {ficha.resumen_clima.provisional
                    ? `Ventana provisional (la campaña aún no tiene fecha de cosecha): de ${ficha.resumen_clima.desde} hasta hoy.`
                    : `Ventana de la campaña: de ${ficha.resumen_clima.desde} a ${ficha.resumen_clima.hasta}.`}
                </p>
              </>
            ) : (
              <p className="nota">
                Esta campaña todavía no tiene registros de clima en su ventana.
              </p>
            )}
          </section>

          <section className="panel">
            <div className="ficha-cabecera">
              <h2>Incidencias</h2>
              <div className="ficha-acciones">
                {puedeCrearIncidencia &&
                  ficha.estado !== 'CERRADA' &&
                  ficha.estado !== 'CANCELADA' && (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setNuevaIncidencia(true)}
                    >
                      Registrar incidencia
                    </button>
                  )}
                <button
                  type="button"
                  className="boton-texto"
                  onClick={() => {
                    navegar(`/incidencias?campania=${ficha.id}`)
                    onCerrar?.()
                  }}
                >
                  Ver todas
                </button>
              </div>
            </div>
            {ficha.resumen_incidencias && ficha.resumen_incidencias.total > 0 ? (
              <>
                <dl className="datos-rejilla">
                  <Dato rotulo="Activas" valor={ficha.resumen_incidencias.total} />
                  <Dato
                    rotulo="Por severidad"
                    valor={`Baja ${ficha.resumen_incidencias.por_severidad.baja} · Media ${ficha.resumen_incidencias.por_severidad.media} · Alta ${ficha.resumen_incidencias.por_severidad.alta}`}
                  />
                  <Dato
                    rotulo="Severidad máxima"
                    valor={ficha.resumen_incidencias.severidad_maxima}
                  />
                  <Dato
                    rotulo="Última incidencia"
                    valor={ficha.resumen_incidencias.ultima_fecha}
                  />
                  <Dato
                    rotulo="Mayor superficie"
                    valor={
                      ficha.resumen_incidencias.mayor_superficie_ha !== null
                        ? `${ficha.resumen_incidencias.mayor_superficie_ha} ha`
                        : null
                    }
                  />
                </dl>
                <p className="nota">
                  Solo cuentan las incidencias activas; las anuladas no se
                  incluyen en el resumen ni en el dataset.
                </p>
              </>
            ) : (
              <p className="nota">
                Esta campaña todavía no tiene incidencias activas.
              </p>
            )}
          </section>

          {tienePermiso('alertas.ver') && (
            <section className="panel">
              <div className="ficha-cabecera">
                <h2>Alertas</h2>
                <div className="ficha-acciones">
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => {
                      navegar(`/alertas?campania=${ficha.id}`)
                      onCerrar?.()
                    }}
                  >
                    Ver todas
                  </button>
                </div>
              </div>
              {alertas.length > 0 ? (
                <>
                  <Tabla
                    filas={alertas}
                    columnas={[
                      {
                        clave: 'creada_en',
                        etiqueta: 'Creada',
                        celda: (fila) =>
                          new Date(fila.creada_en).toLocaleDateString('es-PE'),
                      },
                      {
                        clave: 'tipo',
                        etiqueta: 'Tipo',
                        celda: (fila) => <Chip>{fila.tipo}</Chip>,
                      },
                      {
                        clave: 'mensaje',
                        etiqueta: 'Mensaje',
                        celda: (fila) => fila.mensaje,
                      },
                      {
                        clave: 'estado',
                        etiqueta: 'Estado',
                        celda: (fila) => (
                          <Chip>
                            {fila.atendida ? 'ATENDIDA' : 'PENDIENTE'}
                          </Chip>
                        ),
                      },
                    ]}
                  />
                  <p className="nota">
                    Solo se muestran las 20 alertas más recientes de la
                    campaña; usa «Ver todas» para atenderlas.
                  </p>
                </>
              ) : (
                <p className="nota">
                  Esta campaña no tiene alertas registradas.
                </p>
              )}
            </section>
          )}
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

      {recursoAbierto && ficha && (
        <RecursoFormulario
          campaniaInicial={ficha.id}
          abierto
          onGuardado={() => {
            setRecursoAbierto(false)
            recargar()
          }}
          onCancelar={() => setRecursoAbierto(false)}
        />
      )}

      {nuevaIncidencia && ficha && (
        <IncidenciaFormulario
          campaniaInicial={ficha.id}
          abierto
          onGuardado={() => {
            setNuevaIncidencia(false)
            recargar()
          }}
          onCancelar={() => setNuevaIncidencia(false)}
        />
      )}

      {nuevaEtapa && ficha && (
        <EtapaFormulario
          campaniaInicial={ficha.id}
          abierto
          onGuardado={() => {
            setNuevaEtapa(false)
            recargar()
          }}
          onCancelar={() => setNuevaEtapa(false)}
        />
      )}

      {etapaEditandoId !== null && ficha && (
        <EtapaFormulario
          id={etapaEditandoId}
          campaniaInicial={ficha.id}
          abierto
          onGuardado={() => {
            setEtapaEditandoId(null)
            recargar()
          }}
          onCancelar={() => {
            setEtapaEditandoId(null)
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
