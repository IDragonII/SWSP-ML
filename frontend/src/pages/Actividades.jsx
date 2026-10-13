import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import { listarActividades } from '../api/actividades.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import ActividadFicha from './ActividadFicha.jsx'
import ActividadFormulario from './ActividadFormulario.jsx'

export default function Actividades() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const campania = params.get('campania') ?? ''
  const tipo = params.get('tipo') ?? ''
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''
  const productor = params.get('productor') ?? ''
  const estado = params.get('estado') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${campania}|${tipo}|${fechaDesde}|${fechaHasta}|${productor}|${estado}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [campanias, setCampanias] = useState([])
  const [tipos, setTipos] = useState([])
  const [productores, setProductores] = useState([])
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
      listarTodo('/tipos-actividad/', { activo: 'true' }),
      listarTodo('/productores/', { desplegable: 1 }),
    ])
      .then(([listaCampanias, listaTipos, listaProductores]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setTipos(listaTipos)
        setProductores(listaProductores)
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
    if (tipo) filtros.tipo = tipo
    if (fechaDesde) filtros.fecha_desde = fechaDesde
    if (fechaHasta) filtros.fecha_hasta = fechaHasta
    if (productor) filtros.productor = productor
    if (estado) filtros.estado = estado
    if (pagina > 1) filtros.page = pagina
    listarActividades(filtros)
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
  }, [busqueda, campania, tipo, fechaDesde, fechaHasta, productor, estado, pagina, clave])

  const hayFiltros = Boolean(
    busqueda || campania || tipo || fechaDesde || fechaHasta || productor || estado,
  )

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Actividades</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        {tienePermiso('actividades.crear') && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            Nueva actividad
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
            placeholder="Parcela, productor, método u observaciones"
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
            <option value="">Todas</option>
            <option value="ACTIVA">Activas</option>
            <option value="ANULADA">Anuladas</option>
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
          <p>No hay actividades que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o registra una actividad nueva.
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
                celda: (fila) => fila.tipo_actividad.nombre,
              },
              {
                clave: 'campania',
                etiqueta: 'Campaña',
                celda: (fila) => `${fila.campania.periodo} · ${fila.campania.cultivo.nombre}`,
              },
              {
                clave: 'parcela',
                etiqueta: 'Parcela',
                celda: (fila) => (
                  <span className="chip-codigo">{fila.campania.parcela.codigo}</span>
                ),
              },
              {
                clave: 'productor',
                etiqueta: 'Productor',
                celda: (fila) => fila.campania.parcela.productor.nombre_completo,
              },
              {
                clave: 'metodo',
                etiqueta: 'Método',
                celda: (fila) => fila.metodo || '—',
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
                  tienePermiso('actividades.editar') && !fila.anulada ? (
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
        <ActividadFormulario
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
        <ActividadFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {fichaId !== null && (
        <ActividadFicha
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
