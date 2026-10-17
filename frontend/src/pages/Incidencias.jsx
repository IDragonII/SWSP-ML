import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import {
  CATEGORIAS_INCIDENCIA,
  ESTADOS_INCIDENCIA,
  SEVERIDADES_INCIDENCIA,
  listarIncidencias,
} from '../api/incidencias.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import IncidenciaFicha from './IncidenciaFicha.jsx'
import IncidenciaFormulario from './IncidenciaFormulario.jsx'

export default function Incidencias() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const estado = params.get('estado') ?? ''
  const severidad = params.get('severidad') ?? ''
  const categoria = params.get('categoria') ?? ''
  const tipo = params.get('tipo') ?? ''
  const campania = params.get('campania') ?? ''
  const productor = params.get('productor') ?? ''
  const parcela = params.get('parcela') ?? ''
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${estado}|${severidad}|${categoria}|${tipo}|${campania}|${productor}|${parcela}|${fechaDesde}|${fechaHasta}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [tipos, setTipos] = useState([])
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
      listarTodo('/tipos-incidencia/', { activo: 'true' }),
      listarTodo('/campanias/', { desplegable: 1 }),
      listarTodo('/productores/', { desplegable: 1 }),
      listarTodo('/parcelas/', { desplegable: 1 }),
    ])
      .then(([listaTipos, listaCampanias, listaProductores, listaParcelas]) => {
        if (!activo) return
        setTipos(listaTipos)
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
    if (estado) filtros.estado = estado
    if (severidad) filtros.severidad = severidad
    if (categoria) filtros.categoria = categoria
    if (tipo) filtros.tipo = tipo
    if (campania) filtros.campania = campania
    if (productor) filtros.productor = productor
    if (parcela) filtros.parcela = parcela
    if (fechaDesde) filtros.fecha_desde = fechaDesde
    if (fechaHasta) filtros.fecha_hasta = fechaHasta
    if (pagina > 1) filtros.page = pagina
    listarIncidencias(filtros)
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
    estado,
    severidad,
    categoria,
    tipo,
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
      estado ||
      severidad ||
      categoria ||
      tipo ||
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
          <h1>Incidencias</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        <div className="filtros-acciones">
          {tienePermiso('incidencias.crear') && (
            <button
              className="boton-primario"
              type="button"
              onClick={() => setAltaAbierta(true)}
            >
              Registrar incidencia
            </button>
          )}
        </div>
      </div>

      <form
        className="filtros"
        onSubmit={(event) => {
          event.preventDefault()
          cambiar({ busqueda: texto.trim(), page: null })
        }}
      >
        <Campo id="filtro-busqueda" etiqueta="Buscar">
          <input
            id="filtro-busqueda"
            type="search"
            value={texto}
            placeholder="Código de parcela, productor, agente o descripción"
            onChange={(event) => setTexto(event.target.value)}
          />
        </Campo>
        <Campo id="filtro-estado" etiqueta="Estado">
          <select
            id="filtro-estado"
            value={estado}
            onChange={(event) => cambiar({ estado: event.target.value, page: null })}
          >
            <option value="">Todos</option>
            {ESTADOS_INCIDENCIA.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-severidad" etiqueta="Severidad">
          <select
            id="filtro-severidad"
            value={severidad}
            onChange={(event) =>
              cambiar({ severidad: event.target.value, page: null })
            }
          >
            <option value="">Todas</option>
            {SEVERIDADES_INCIDENCIA.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-categoria" etiqueta="Categoría">
          <select
            id="filtro-categoria"
            value={categoria}
            onChange={(event) =>
              cambiar({ categoria: event.target.value, page: null })
            }
          >
            <option value="">Todas</option>
            {CATEGORIAS_INCIDENCIA.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-tipo" etiqueta="Tipo">
          <select
            id="filtro-tipo"
            value={tipo}
            onChange={(event) => cambiar({ tipo: event.target.value, page: null })}
          >
            <option value="">Todos</option>
            {tipos.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </select>
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
          <p>No hay incidencias que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o registra una incidencia desde el
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
                etiqueta: 'Fecha',
                celda: (fila) => fila.fecha,
              },
              {
                clave: 'tipo',
                etiqueta: 'Tipo',
                celda: (fila) => (
                  <>
                    {fila.tipo_incidencia.nombre}{' '}
                    <Chip>{fila.tipo_incidencia.categoria}</Chip>
                  </>
                ),
              },
              {
                clave: 'severidad',
                etiqueta: 'Severidad',
                celda: (fila) => <Chip>{fila.severidad}</Chip>,
              },
              {
                clave: 'agente',
                etiqueta: 'Agente',
                celda: (fila) => fila.agente?.nombre ?? '—',
              },
              {
                clave: 'superficie',
                etiqueta: 'Superficie (ha)',
                celda: (fila) => fila.superficie_afectada_ha ?? '—',
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
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => (
                  <Chip>{fila.anulada ? 'ANULADA' : 'ACTIVA'}</Chip>
                ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {tienePermiso('incidencias.editar') && !fila.anulada && (
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
        <IncidenciaFormulario
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
        <IncidenciaFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {fichaId !== null && (
        <IncidenciaFicha
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
