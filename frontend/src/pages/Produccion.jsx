import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import { ESTADOS_CAMPANIA } from '../api/campanias.js'
import { listarProducciones } from '../api/produccion.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import ProduccionFicha from './ProduccionFicha.jsx'
import ProduccionFormulario from './ProduccionFormulario.jsx'

export default function Produccion() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const requiereRevision = params.get('requiere_revision') ?? ''
  const estado = params.get('estado') ?? ''
  const cultivo = params.get('cultivo') ?? ''
  const periodo = params.get('periodo') ?? ''
  const campania = params.get('campania') ?? ''
  const productor = params.get('productor') ?? ''
  const parcela = params.get('parcela') ?? ''
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${requiereRevision}|${estado}|${cultivo}|${periodo}|${campania}|${productor}|${parcela}|${fechaDesde}|${fechaHasta}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [textoPeriodo, setTextoPeriodo] = useState(periodo)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [periodoPrevio, setPeriodoPrevio] = useState(periodo)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [cultivos, setCultivos] = useState([])
  const [campanias, setCampanias] = useState([])
  const [productores, setProductores] = useState([])
  const [parcelas, setParcelas] = useState([])
  const [error, setError] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [fichaId, setFichaId] = useState(null)
  const refrescando = datos !== null && claveCargada !== clave

  function refrescar() {
    setRecarga((n) => n + 1)
  }

  if (busquedaPrevia !== busqueda) {
    setBusquedaPrevia(busqueda)
    setTexto(busqueda)
  }
  if (periodoPrevio !== periodo) {
    setPeriodoPrevio(periodo)
    setTextoPeriodo(periodo)
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
      listarTodo('/cultivos/', { activo: 'true' }),
      listarTodo('/campanias/', { desplegable: 1 }),
      listarTodo('/productores/', { desplegable: 1 }),
      listarTodo('/parcelas/', { desplegable: 1 }),
    ])
      .then(([listaCultivos, listaCampanias, listaProductores, listaParcelas]) => {
        if (!activo) return
        setCultivos(listaCultivos)
        setCampanias(listaCampanias)
        setProductores(listaProductores)
        setParcelas(listaParcelas)
      })
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    let activo = true
    const filtros = {}
    if (busqueda) filtros.busqueda = busqueda
    if (requiereRevision) filtros.requiere_revision = requiereRevision
    if (estado) filtros.estado = estado
    if (cultivo) filtros.cultivo = cultivo
    if (periodo) filtros.periodo = periodo
    if (campania) filtros.campania = campania
    if (productor) filtros.productor = productor
    if (parcela) filtros.parcela = parcela
    if (fechaDesde) filtros.fecha_desde = fechaDesde
    if (fechaHasta) filtros.fecha_hasta = fechaHasta
    if (pagina > 1) filtros.page = pagina
    listarProducciones(filtros)
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
  }, [
    busqueda,
    requiereRevision,
    estado,
    cultivo,
    periodo,
    campania,
    productor,
    parcela,
    fechaDesde,
    fechaHasta,
    pagina,
    clave,
  ])

  const hayFiltros = Boolean(
    busqueda ||
      requiereRevision ||
      estado ||
      cultivo ||
      periodo ||
      campania ||
      productor ||
      parcela ||
      fechaDesde ||
      fechaHasta,
  )

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Producción</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        <div className="filtros-acciones">
          {tienePermiso('produccion.crear') && (
            <button
              className="boton-primario"
              type="button"
              onClick={() => setAltaAbierta(true)}
            >
              Registrar producción
            </button>
          )}
        </div>
      </div>

      <form
        className="filtros"
        onSubmit={(event) => {
          event.preventDefault()
          cambiar({
            busqueda: texto.trim(),
            periodo: textoPeriodo.trim(),
            page: null,
          })
        }}
      >
        <Campo id="filtro-busqueda" etiqueta="Buscar">
          <input
            id="filtro-busqueda"
            type="search"
            value={texto}
            placeholder="Código de parcela, productor o cultivo"
            onChange={(event) => setTexto(event.target.value)}
          />
        </Campo>
        <Campo
          id="filtro-requiere-revision"
          etiqueta="Requiere revisión"
        >
          <select
            id="filtro-requiere-revision"
            value={requiereRevision}
            onChange={(event) =>
              cambiar({ requiere_revision: event.target.value, page: null })
            }
          >
            <option value="">Todas</option>
            <option value="true">Sí</option>
            <option value="false">No</option>
          </select>
        </Campo>
        <Campo id="filtro-estado" etiqueta="Estado de la campaña">
          <select
            id="filtro-estado"
            value={estado}
            onChange={(event) => cambiar({ estado: event.target.value, page: null })}
          >
            <option value="">Todos</option>
            {ESTADOS_CAMPANIA.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-cultivo" etiqueta="Cultivo">
          <select
            id="filtro-cultivo"
            value={cultivo}
            onChange={(event) => cambiar({ cultivo: event.target.value, page: null })}
          >
            <option value="">Todos</option>
            {cultivos.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-periodo" etiqueta="Período">
          <input
            id="filtro-periodo"
            value={textoPeriodo}
            placeholder="2025-2026"
            onChange={(event) => setTextoPeriodo(event.target.value)}
          />
        </Campo>
        <Campo id="filtro-campania" etiqueta="Campaña">
          <select
            id="filtro-campania"
            value={campania}
            onChange={(event) =>
              cambiar({ campania: event.target.value, page: null })
            }
          >
            <option value="">Todas</option>
            {campanias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.parcela.productor.nombre_completo} — {c.parcela.codigo} —{' '}
                {c.cultivo.nombre} ({c.periodo})
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-productor" etiqueta="Productor">
          <select
            id="filtro-productor"
            value={productor}
            onChange={(event) =>
              cambiar({ productor: event.target.value, page: null })
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
        <Campo id="filtro-parcela" etiqueta="Parcela">
          <select
            id="filtro-parcela"
            value={parcela}
            onChange={(event) => cambiar({ parcela: event.target.value, page: null })}
          >
            <option value="">Todas</option>
            {parcelas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.codigo} — {p.productor.nombre_completo}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-fecha-desde" etiqueta="Fecha desde">
          <input
            id="filtro-fecha-desde"
            type="date"
            value={fechaDesde}
            onChange={(event) =>
              cambiar({ fecha_desde: event.target.value, page: null })
            }
          />
        </Campo>
        <Campo id="filtro-fecha-hasta" etiqueta="Fecha hasta">
          <input
            id="filtro-fecha-hasta"
            type="date"
            value={fechaHasta}
            onChange={(event) =>
              cambiar({ fecha_hasta: event.target.value, page: null })
            }
          />
        </Campo>
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {hayFiltros && (
            <button
              className="boton-secundario"
              type="button"
              onClick={() => setParams({})}
            >
              Limpiar
            </button>
          )}
        </div>
      </form>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay producciones que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o registra una producción desde el
            botón superior.
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            refrescando={refrescando}
            filas={datos.results}
            columnas={[
              {
                clave: 'fecha',
                etiqueta: 'Fecha de cosecha',
                celda: (fila) => fila.fecha_cosecha,
              },
              {
                clave: 'campania',
                etiqueta: 'Campaña',
                celda: (fila) =>
                  `${fila.campania.periodo} · ${fila.campania.cultivo.nombre}`,
              },
              {
                clave: 'parcela',
                etiqueta: 'Parcela',
                celda: (fila) => fila.campania.parcela.codigo,
              },
              {
                clave: 'productor',
                etiqueta: 'Productor',
                celda: (fila) => fila.campania.parcela.productor.nombre_completo,
              },
              {
                clave: 'produccion',
                etiqueta: 'Producción',
                celda: (fila) => `${fila.produccion_kg} kg`,
              },
              {
                clave: 'superficie',
                etiqueta: 'Superficie (ha)',
                celda: (fila) => `${fila.superficie_cosechada_ha} ha`,
              },
              {
                clave: 'rendimiento',
                etiqueta: 'Rendimiento',
                celda: (fila) => `${fila.rendimiento_kg_ha} kg/ha`,
              },
              {
                clave: 'estado',
                etiqueta: 'Estado campaña',
                celda: (fila) => <Chip>{fila.campania.estado}</Chip>,
              },
              {
                clave: 'revision',
                etiqueta: 'Revisión',
                celda: (fila) =>
                  fila.requiere_revision ? (
                    <Chip>{'⚠ REQUIERE REVISIÓN'}</Chip>
                  ) : (
                    'Sin revisión'
                  ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {tienePermiso('produccion.editar') &&
                      fila.campania.estado !== 'CERRADA' && (
                        <button
                          type="button"
                          className="boton-texto"
                          onClick={() => setEdicionId(fila.id)}
                        >
                          Editar
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

      {edicionId !== null && (
        <ProduccionFormulario
          id={edicionId}
          abierto
          onGuardado={() => {
            setEdicionId(null)
            refrescar()
          }}
          onCancelar={() => {
            setEdicionId(null)
            refrescar()
          }}
        />
      )}

      {altaAbierta && (
        <ProduccionFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {fichaId !== null && (
        <ProduccionFicha
          id={fichaId}
          abierto
          onCerrar={() => {
            setFichaId(null)
            refrescar()
          }}
        />
      )}
    </>
  )
}
