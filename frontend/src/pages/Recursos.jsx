import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import {
  CATEGORIAS_RECURSO,
  listarUsosRecursos,
} from '../api/usosRecursos.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import RecursoFicha from './RecursoFicha.jsx'
import RecursoFormulario from './RecursoFormulario.jsx'

export default function Recursos() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const campania = params.get('campania') ?? ''
  const categoria = params.get('categoria') ?? ''
  const recurso = params.get('recurso') ?? ''
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''
  const estado = params.get('estado') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${campania}|${categoria}|${recurso}|${fechaDesde}|${fechaHasta}|${estado}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [campanias, setCampanias] = useState([])
  const [recursos, setRecursos] = useState([])
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
      listarTodo('/campanias/', { desplegable: 1 }),
      listarTodo('/recursos/', { desplegable: 1 }),
    ])
      .then(([listaCampanias, listaRecursos]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setRecursos(listaRecursos)
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
    if (campania) filtros.campania = campania
    if (categoria) filtros.categoria = categoria
    if (recurso) filtros.recurso = recurso
    if (fechaDesde) filtros.fecha_desde = fechaDesde
    if (fechaHasta) filtros.fecha_hasta = fechaHasta
    if (estado) filtros.estado = estado
    if (pagina > 1) filtros.page = pagina
    listarUsosRecursos(filtros)
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
  }, [busqueda, campania, categoria, recurso, fechaDesde, fechaHasta, estado, pagina, clave])

  const hayFiltros = Boolean(
    busqueda || campania || categoria || recurso || fechaDesde || fechaHasta || estado,
  )

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Recursos e insumos</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        {tienePermiso('recursos.crear') && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            Nuevo uso de recurso
          </button>
        )}
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
            placeholder="Parcela, productor, recurso u observaciones"
            onChange={(event) => setTexto(event.target.value)}
          />
        </Campo>
        <Campo id="filtro-campania" etiqueta="Campaña">
          <select
            id="filtro-campania"
            value={campania}
            onChange={(event) => cambiar({ campania: event.target.value, page: null })}
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
        <Campo id="filtro-categoria" etiqueta="Categoría">
          <select
            id="filtro-categoria"
            value={categoria}
            onChange={(event) => cambiar({ categoria: event.target.value, page: null })}
          >
            <option value="">Todas</option>
            {CATEGORIAS_RECURSO.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-recurso" etiqueta="Recurso">
          <select
            id="filtro-recurso"
            value={recurso}
            onChange={(event) => cambiar({ recurso: event.target.value, page: null })}
          >
            <option value="">Todos</option>
            {recursos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nombre} ({r.categoria})
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
        <Campo id="filtro-estado" etiqueta="Estado">
          <select
            id="filtro-estado"
            value={estado}
            onChange={(event) => cambiar({ estado: event.target.value, page: null })}
          >
            <option value="">Todos</option>
            <option value="ACTIVA">Activos</option>
            <option value="ANULADA">Anulados</option>
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
          <p>No hay usos de recursos que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o registra un uso de recurso nuevo.
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
                clave: 'recurso',
                etiqueta: 'Recurso',
                celda: (fila) => (
                  <>
                    {fila.recurso.nombre}{' '}
                    <Chip>{fila.recurso.categoria}</Chip>
                  </>
                ),
              },
              {
                clave: 'cantidad',
                etiqueta: 'Cantidad',
                celda: (fila) => `${fila.cantidad} ${fila.unidad.simbolo}`,
              },
              {
                clave: 'cantidad_base',
                etiqueta: 'En unidad base',
                celda: (fila) => fila.cantidad_base,
              },
              {
                clave: 'campania',
                etiqueta: 'Campaña',
                celda: (fila) => `${fila.campania.periodo} · ${fila.campania.cultivo.nombre}`,
              },
              {
                clave: 'costo',
                etiqueta: 'Costo',
                celda: (fila) => (fila.costo !== null ? `S/ ${fila.costo}` : '—'),
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
                celda: (fila) =>
                  tienePermiso('recursos.editar') && !fila.anulada ? (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setEdicionId(fila.id)}
                    >
                      Editar
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setFichaId(fila.id)}
                    >
                      Ver ficha
                    </button>
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
        <RecursoFormulario
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
        <RecursoFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {fichaId !== null && (
        <RecursoFicha
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
