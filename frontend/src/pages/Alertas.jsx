import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import {
  ESTADOS_ALERTA,
  TIPOS_ALERTA,
  atenderAlerta,
  estadoEvaluacion,
  evaluarAlertas,
  etiquetaTipo,
  listarAlertas,
  obtenerAlerta,
  reabrirAlerta,
} from '../api/alertas.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Paginacion from '../components/Paginacion.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'

function fechaCorta(valor) {
  if (!valor) return '—'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return valor
  return fecha.toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })
}

function AtenderAlerta({ alerta, abierto, onAtendida, onCancelar }) {
  const { avisar } = useToast()
  const [nota, setNota] = useState('')
  const [error, setError] = useState(null)
  const [guardando, setGuardando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      await atenderAlerta(alerta.id, nota.trim())
      avisar('Alerta atendida.')
      onAtendida?.()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo="Atender alerta"
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>
      <p className="nota">{alerta.mensaje}</p>
      <form onSubmit={enviar} className="formulario-pagina">
        <section className="panel">
          <Campo
            id="nota-atencion"
            etiqueta="Nota de atención (opcional)"
            ayuda="Máximo 250 caracteres. Queda registrada en la alerta y en la auditoría."
          >
            <textarea
              id="nota-atencion"
              rows="3"
              maxLength="250"
              value={nota}
              onChange={(evento) => setNota(evento.target.value)}
            />
          </Campo>
        </section>
        <div className="formulario-acciones">
          <button className="boton-primario" type="submit" disabled={guardando}>
            {guardando ? (
              <>
                <RuedaCarga etiqueta="Atendiendo…" />
                Atendiendo…
              </>
            ) : (
              'Atender'
            )}
          </button>
          <button
            className="boton-secundario"
            type="button"
            onClick={onCancelar}
          >
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  )
}

function FichaAlerta({ id, abierto, onCerrar }) {
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!abierto) return undefined
    let activo = true
    obtenerAlerta(id)
      .then((datos) => {
        if (!activo) return
        setError(null)
        setFicha(datos)
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [id, abierto])

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo="Alerta"
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
              <Chip>{ficha.atendida ? 'ATENDIDA' : 'PENDIENTE'}</Chip>{' '}
              <Chip>{etiquetaTipo(ficha.tipo)}</Chip>
            </p>
          </div>
          <section className="panel">
            <h2>Datos de la alerta</h2>
            <dl className="datos-rejilla">
              <div>
                <dt>Mensaje</dt>
                <dd>{ficha.mensaje}</dd>
              </div>
              <div>
                <dt>Productor</dt>
                <dd>
                  {ficha.productor_nombre} ({ficha.productor_codigo})
                </dd>
              </div>
              <div>
                <dt>Campaña</dt>
                <dd>{ficha.campania_periodo}</dd>
              </div>
              <div>
                <dt>Creada</dt>
                <dd>{fechaCorta(ficha.creada_en)}</dd>
              </div>
              <div>
                <dt>Atendida</dt>
                <dd>{ficha.atendida_en ? fechaCorta(ficha.atendida_en) : '—'}</dd>
              </div>
              <div>
                <dt>Atendida por</dt>
                <dd>{ficha.atendida_por_nombre ?? '—'}</dd>
              </div>
              <div>
                <dt>Nota de atención</dt>
                <dd>{ficha.nota_atencion ?? '—'}</dd>
              </div>
            </dl>
            {ficha.atendida && ficha.atendida_por === null && (
              <p className="nota">
                Se cerró automáticamente: volverá a abrirse si la condición
                vuelve a cumplirse.
              </p>
            )}
          </section>
        </>
      )}
    </Modal>
  )
}

export default function Alertas() {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [params, setParams] = useSearchParams()

  const estado = params.get('estado') ?? 'PENDIENTES'
  const tipo = params.get('tipo') ?? ''
  const campania = params.get('campania') ?? ''
  const productor = params.get('productor') ?? ''
  const busqueda = params.get('busqueda') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${estado}|${tipo}|${campania}|${productor}|${busqueda}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [evaluacion, setEvaluacion] = useState(null)
  const [campanias, setCampanias] = useState([])
  const [productores, setProductores] = useState([])
  const [error, setError] = useState(null)
  const [fichaId, setFichaId] = useState(null)
  const [atendiendo, setAtendiendo] = useState(null)
  const [reabriendo, setReabriendo] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [evaluando, setEvaluando] = useState(false)
  const refrescando = datos !== null && claveCargada !== clave

  const puedeEvaluar = tienePermiso('parametros.gestionar')
  const puedeAtender = tienePermiso('alertas.atender')

  function refrescar() {
    setRecarga((n) => n + 1)
  }

  if (busquedaPrevia !== busqueda) {
    setBusquedaPrevia(busqueda)
    setTexto(busqueda)
  }

  function cambiar(cambios) {
    const nuevo = new URLSearchParams(params)
    for (const [claveCambio, valor] of Object.entries(cambios)) {
      if (valor === null || valor === undefined || valor === '') {
        nuevo.delete(claveCambio)
      } else {
        nuevo.set(claveCambio, String(valor))
      }
    }
    setParams(nuevo)
  }

  useEffect(() => {
    let activo = true
    Promise.all([
      listarTodo('/campanias/', { desplegable: 1 }),
      listarTodo('/productores/', { desplegable: 1 }),
    ])
      .then(([listaCampanias, listaProductores]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setProductores(listaProductores)
      })
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    let activo = true
    estadoEvaluacion()
      .then((datos) => activo && setEvaluacion(datos))
      .catch(() => activo && setEvaluacion(null))
    return () => {
      activo = false
    }
  }, [recarga])

  useEffect(() => {
    let activo = true
    const filtros = { estado }
    if (tipo) filtros.tipo = tipo
    if (campania) filtros.campania = campania
    if (productor) filtros.productor = productor
    if (busqueda) filtros.busqueda = busqueda
    if (pagina > 1) filtros.page = pagina
    listarAlertas(filtros)
      .then((respuesta) => {
        if (!activo) return
        setError(null)
        setDatos(respuesta)
        setClaveCargada(clave)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setClaveCargada(clave)
      })
    return () => {
      activo = false
    }
  }, [estado, tipo, campania, productor, busqueda, pagina, clave])

  const hayFiltros = Boolean(tipo || campania || productor || busqueda)

  async function evaluarAhora() {
    setEvaluando(true)
    try {
      const resultado = await evaluarAlertas(false)
      avisar(
        `Evaluación completada: ${resultado.creadas} creada(s), ` +
          `${resultado.cerradas} cerrada(s).`,
      )
      refrescar()
    } catch (e) {
      avisar(mensajeDeError(e), 'error')
    } finally {
      setEvaluando(false)
    }
  }

  async function confirmarReabrir() {
    if (!reabriendo) return
    setOcupado(true)
    try {
      await reabrirAlerta(reabriendo.id)
      avisar('Alerta reabierta.')
      setReabriendo(null)
      refrescar()
    } catch (e) {
      avisar(mensajeDeError(e), 'error')
    } finally {
      setOcupado(false)
    }
  }

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Alertas</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        <div className="filtros-acciones">
          {puedeEvaluar && (
            <button
              className="boton-primario"
              type="button"
              disabled={evaluando}
              onClick={evaluarAhora}
            >
              {evaluando ? (
                <>
                  <RuedaCarga etiqueta="Evaluando…" />
                  Evaluando…
                </>
              ) : (
                'Evaluar ahora'
              )}
            </button>
          )}
        </div>
      </div>

      {evaluacion && evaluacion.atrasada && (
        <Aviso>
          La evaluación automática de alertas está atrasada
          {evaluacion.ultima_evaluacion
            ? ` (última: ${fechaCorta(evaluacion.ultima_evaluacion)})`
            : ' (aún no se ha ejecutado)'}
          . El proceso diario debe correr al menos cada{' '}
          {evaluacion.umbral_horas} horas.
        </Aviso>
      )}

      <div className="pestanas" role="tablist" aria-label="Estado de las alertas">
        {ESTADOS_ALERTA.map(([valor, etiqueta]) => (
          <button
            key={valor}
            type="button"
            role="tab"
            aria-selected={estado === valor}
            className={`pestana${estado === valor ? ' activa' : ''}`}
            onClick={() => cambiar({ estado: valor, page: null })}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      <form
        className="filtros"
        onSubmit={(evento) => {
          evento.preventDefault()
          cambiar({ busqueda: texto.trim(), page: null })
        }}
      >
        <Campo id="filtro-busqueda" etiqueta="Buscar">
          <input
            id="filtro-busqueda"
            type="search"
            value={texto}
            placeholder="Mensaje, código o nombre del productor"
            onChange={(evento) => setTexto(evento.target.value)}
          />
        </Campo>
        <Campo id="filtro-tipo" etiqueta="Tipo">
          <select
            id="filtro-tipo"
            value={tipo}
            onChange={(evento) => cambiar({ tipo: evento.target.value, page: null })}
          >
            <option value="">Todos</option>
            {TIPOS_ALERTA.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-campania" etiqueta="Campaña">
          <select
            id="filtro-campania"
            value={campania}
            onChange={(evento) =>
              cambiar({ campania: evento.target.value, page: null })
            }
          >
            <option value="">Todas</option>
            {campanias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.parcela.productor.nombre_completo} - {c.parcela.codigo} -{' '}
                {c.cultivo.nombre} ({c.periodo})
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-productor" etiqueta="Productor">
          <select
            id="filtro-productor"
            value={productor}
            onChange={(evento) =>
              cambiar({ productor: evento.target.value, page: null })
            }
          >
            <option value="">Todos</option>
            {productores.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre_completo}
              </option>
            ))}
          </select>
        </Campo>
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {hayFiltros && (
            <button
              className="boton-secundario"
              type="button"
              onClick={() => setParams({ estado })}
            >
              Limpiar
            </button>
          )}
        </div>
      </form>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay alertas en esta pestaña.</p>
          <p className="nota">
            Las alertas se crean solas con la evaluación diaria (incidencias
            severas, campañas sin actividad y rendimientos bajos).
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            refrescando={refrescando}
            filas={datos.results}
            columnas={[
              {
                clave: 'creada_en',
                etiqueta: 'Creada',
                celda: (fila) => fechaCorta(fila.creada_en),
              },
              {
                clave: 'tipo',
                etiqueta: 'Tipo',
                celda: (fila) => <Chip>{etiquetaTipo(fila.tipo)}</Chip>,
              },
              {
                clave: 'productor',
                etiqueta: 'Productor',
                celda: (fila) =>
                  `${fila.productor_nombre} (${fila.productor_codigo})`,
              },
              {
                clave: 'campania',
                etiqueta: 'Campaña',
                celda: (fila) => fila.campania_periodo,
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
                  <Chip>{fila.atendida ? 'ATENDIDA' : 'PENDIENTE'}</Chip>
                ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {puedeAtender && !fila.atendida && (
                      <button
                        type="button"
                        className="boton-texto"
                        onClick={() => setAtendiendo(fila)}
                      >
                        Atender
                      </button>
                    )}
                    {puedeAtender && fila.atendida && (
                      <button
                        type="button"
                        className="boton-texto"
                        onClick={() => setReabriendo(fila)}
                      >
                        Reabrir
                      </button>
                    )}
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setFichaId(fila.id)}
                    >
                      Ver ficha
                    </button>
                  </>
                ),
              },
            ]}
          />
        )
      )}

      {datos && (
        <Paginacion
          conteo={datos.count}
          pagina={pagina}
          porPagina={20}
          onCambio={(siguiente) => cambiar({ page: siguiente })}
        />
      )}

      {atendiendo && (
        <AtenderAlerta
          key={atendiendo.id}
          alerta={atendiendo}
          abierto
          onAtendida={() => {
            setAtendiendo(null)
            refrescar()
          }}
          onCancelar={() => setAtendiendo(null)}
        />
      )}

      {fichaId !== null && (
        <FichaAlerta
          id={fichaId}
          abierto
          onCerrar={() => setFichaId(null)}
        />
      )}

      <Modal
        abierto={reabriendo !== null}
        titulo="Reabrir alerta"
        texto={
          reabriendo
            ? '¿Reabrir esta alerta? Volverá a la pestaña de pendientes y quedará registrada en la auditoría. Solo se pueden reabrir las atendidas a mano.'
            : ''
        }
        confirmar="Reabrir"
        ocupado={ocupado}
        onConfirmar={confirmarReabrir}
        onCerrar={() => setReabriendo(null)}
      />
    </>
  )
}
