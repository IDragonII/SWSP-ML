import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import { ESTADOS_CAMPANIA, listarCampanias } from '../api/campanias.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import CampaniaFicha from './CampaniaFicha.jsx'
import CampaniaFormulario from './CampaniaFormulario.jsx'
import ParcelaFicha from './ParcelaFicha.jsx'
import ProductorFicha from './ProductorFicha.jsx'

export default function Campanias() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const estado = params.get('estado') ?? ''
  const cultivo = params.get('cultivo') ?? ''
  const periodo = params.get('periodo') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${estado}|${cultivo}|${periodo}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [textoPeriodo, setTextoPeriodo] = useState(periodo)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [periodoPrevio, setPeriodoPrevio] = useState(periodo)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [cultivos, setCultivos] = useState([])
  const [error, setError] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [parcelaFichaId, setParcelaFichaId] = useState(null)
  const [productorFichaId, setProductorFichaId] = useState(null)
  const [campaniaFichaId, setCampaniaFichaId] = useState(null)
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
    listarTodo('/cultivos/', { activo: 'true' })
      .then((lista) => {
        if (activo) setCultivos(lista)
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
    if (cultivo) filtros.cultivo = cultivo
    if (periodo) filtros.periodo = periodo
    if (pagina > 1) filtros.page = pagina
    listarCampanias(filtros)
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
  }, [busqueda, estado, cultivo, periodo, pagina, clave])

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Campañas</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        {tienePermiso('campanias.crear') && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            Nueva campaña
          </button>
        )}
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
            placeholder="Productor, parcela, cultivo o variedad"
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
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {(busqueda || estado || cultivo || periodo) && (
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
          <p>No hay campañas que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o registra una campaña nueva.
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            refrescando={refrescando}
            filas={datos.results}
            columnas={[
              {
                clave: 'productor',
                etiqueta: 'Productor',
                celda: (fila) => (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => setProductorFichaId(fila.parcela.productor.id)}
                  >
                    {fila.parcela.productor.nombre_completo}
                  </button>
                ),
              },
              {
                clave: 'parcela',
                etiqueta: 'Parcela',
                celda: (fila) => (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => setParcelaFichaId(fila.parcela.id)}
                  >
                    <span className="chip-codigo">{fila.parcela.codigo}</span>
                  </button>
                ),
              },
              {
                clave: 'cultivo',
                etiqueta: 'Cultivo',
                celda: (fila) => fila.cultivo.nombre,
              },
              {
                clave: 'variedad',
                etiqueta: 'Variedad',
                celda: (fila) => fila.variedad.nombre,
              },
              {
                clave: 'periodo',
                etiqueta: 'Período',
                celda: (fila) => fila.periodo,
              },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => <Chip>{fila.estado}</Chip>,
              },
              {
                clave: 'etapa_actual',
                etiqueta: 'Etapa',
                celda: (fila) =>
                  fila.etapa_actual ? (
                    <>
                      {fila.etapa_actual.nombre}{' '}
                      <Chip>
                        {fila.etapa_actual.en_curso ? 'EN CURSO' : 'CERRADA'}
                      </Chip>
                    </>
                  ) : (
                    <span className="nota">Sin etapas</span>
                  ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {tienePermiso('campanias.editar') && (
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
                      onClick={() => setCampaniaFichaId(fila.id)}
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
        <CampaniaFormulario
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
        <CampaniaFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {campaniaFichaId !== null && (
        <CampaniaFicha
          id={campaniaFichaId}
          abierto
          onCerrar={() => {
            setCampaniaFichaId(null)
            refrescar()
          }}
        />
      )}

      {parcelaFichaId !== null && (
        <ParcelaFicha
          id={parcelaFichaId}
          abierto
          onCerrar={() => {
            setParcelaFichaId(null)
            refrescar()
          }}
        />
      )}

      {productorFichaId !== null && (
        <ProductorFicha
          id={productorFichaId}
          abierto
          onCerrar={() => {
            setProductorFichaId(null)
            refrescar()
          }}
        />
      )}
    </>
  )
}
