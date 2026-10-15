import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  obtenerComunidades,
  obtenerDistritos,
  obtenerProvincias,
  listarTodo,
} from '../api/catalogos.js'
import { FUENTES_CLIMA, listarClima } from '../api/clima.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import ClimaConsulta from './ClimaConsulta.jsx'
import ClimaFicha from './ClimaFicha.jsx'
import ClimaFormulario from './ClimaFormulario.jsx'

export default function Climas() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const parcela = params.get('parcela') ?? ''
  const productor = params.get('productor') ?? ''
  const comunidad = params.get('comunidad') ?? ''
  const distrito = params.get('distrito') ?? ''
  const provincia = params.get('provincia') ?? ''
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''
  const fuente = params.get('fuente') ?? ''
  const heladas = params.get('heladas') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${parcela}|${productor}|${comunidad}|${distrito}|${provincia}|${fechaDesde}|${fechaHasta}|${fuente}|${heladas}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [parcelas, setParcelas] = useState([])
  const [productores, setProductores] = useState([])
  const [provincias, setProvincias] = useState([])
  const [distritos, setDistritos] = useState([])
  const [comunidades, setComunidades] = useState([])
  const [error, setError] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [consultaAbierta, setConsultaAbierta] = useState(false)
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
      listarTodo('/parcelas/', { desplegable: 1 }),
      listarTodo('/productores/', { desplegable: 1 }),
      obtenerProvincias(),
    ])
      .then(([listaParcelas, listaProductores, listaProvincias]) => {
        if (!activo) return
        setParcelas(listaParcelas)
        setProductores(listaProductores)
        setProvincias(listaProvincias)
      })
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [])

  // Desplegables en cascada: distritos de la provincia y comunidades del
  // distrito elegidos en los filtros (sin provincia o distrito, la
  // helper devuelve una lista vacía)
  useEffect(() => {
    let activo = true
    obtenerDistritos(provincia || null)
      .then((lista) => activo && setDistritos(lista))
      .catch(() => activo && setDistritos([]))
    return () => {
      activo = false
    }
  }, [provincia])

  useEffect(() => {
    let activo = true
    obtenerComunidades(distrito || null)
      .then((lista) => activo && setComunidades(lista))
      .catch(() => activo && setComunidades([]))
    return () => {
      activo = false
    }
  }, [distrito])

  useEffect(() => {
    let activo = true
    const filtros = {}
    if (busqueda) filtros.busqueda = busqueda
    if (parcela) filtros.parcela = parcela
    if (productor) filtros.productor = productor
    if (comunidad) filtros.comunidad = comunidad
    if (distrito) filtros.distrito = distrito
    if (provincia) filtros.provincia = provincia
    if (fechaDesde) filtros.fecha_desde = fechaDesde
    if (fechaHasta) filtros.fecha_hasta = fechaHasta
    if (fuente) filtros.fuente = fuente
    if (heladas) filtros.heladas = heladas
    if (pagina > 1) filtros.page = pagina
    listarClima(filtros)
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
    parcela,
    productor,
    comunidad,
    distrito,
    provincia,
    fechaDesde,
    fechaHasta,
    fuente,
    heladas,
    pagina,
    clave,
  ])

  const hayFiltros = Boolean(
    busqueda ||
      parcela ||
      productor ||
      comunidad ||
      distrito ||
      provincia ||
      fechaDesde ||
      fechaHasta ||
      fuente ||
      heladas,
  )

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Registro de clima</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        <div className="filtros-acciones">
          {tienePermiso('clima.crear') && (
            <>
              <button
                className="boton-secundario"
                type="button"
                onClick={() => setConsultaAbierta(true)}
              >
                Consultar API
              </button>
              <button
                className="boton-primario"
                type="button"
                onClick={() => setAltaAbierta(true)}
              >
                Registrar clima
              </button>
            </>
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
            placeholder="Código de parcela, productor o comunidad"
            onChange={(event) => setTexto(event.target.value)}
          />
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
        <Campo id="filtro-provincia" etiqueta="Provincia">
          <select
            id="filtro-provincia"
            value={provincia}
            onChange={(event) =>
              cambiar({
                provincia: event.target.value,
                distrito: '',
                comunidad: '',
                page: null,
              })
            }
          >
            <option value="">Todas</option>
            {provincias.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-distrito" etiqueta="Distrito">
          <select
            id="filtro-distrito"
            value={distrito}
            disabled={!provincia}
            onChange={(event) =>
              cambiar({ distrito: event.target.value, comunidad: '', page: null })
            }
          >
            <option value="">Todos</option>
            {distritos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-comunidad" etiqueta="Comunidad">
          <select
            id="filtro-comunidad"
            value={comunidad}
            disabled={!distrito}
            onChange={(event) =>
              cambiar({ comunidad: event.target.value, page: null })
            }
          >
            <option value="">Todas</option>
            {comunidades.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
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
        <Campo id="filtro-fuente" etiqueta="Fuente">
          <select
            id="filtro-fuente"
            value={fuente}
            onChange={(event) => cambiar({ fuente: event.target.value, page: null })}
          >
            <option value="">Todas</option>
            {FUENTES_CLIMA.map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-heladas" etiqueta="Heladas">
          <select
            id="filtro-heladas"
            value={heladas}
            onChange={(event) =>
              cambiar({ heladas: event.target.value, page: null })
            }
          >
            <option value="">Todos</option>
            <option value="1">Con helada</option>
            <option value="0">Sin helada</option>
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
          <p>No hay registros de clima que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros, registra un día a mano o consulta la
            API meteorológica.
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
                clave: 'parcela',
                etiqueta: 'Parcela',
                celda: (fila) => fila.parcela.codigo,
              },
              {
                clave: 'productor',
                etiqueta: 'Productor',
                celda: (fila) => fila.parcela.productor.nombre_completo,
              },
              {
                clave: 'temperaturas',
                etiqueta: 'Mín / prom / máx (°C)',
                celda: (fila) =>
                  `${fila.temp_min ?? '—'} / ${fila.temp_prom ?? '—'} / ${fila.temp_max ?? '—'}`,
              },
              {
                clave: 'precipitacion',
                etiqueta: 'Precipitación',
                celda: (fila) =>
                  fila.precipitacion_mm !== null
                    ? `${fila.precipitacion_mm} mm`
                    : '—',
              },
              {
                clave: 'helada',
                etiqueta: 'Helada',
                celda: (fila) => (fila.helada ? <Chip>SÍ</Chip> : 'No'),
              },
              {
                clave: 'fuente',
                etiqueta: 'Fuente',
                celda: (fila) => (
                  <Chip>{fila.fuente === 'API' ? 'API' : 'MANUAL'}</Chip>
                ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {tienePermiso('clima.editar') && (
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
        <ClimaFormulario
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
        <ClimaFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {consultaAbierta && (
        <ClimaConsulta
          abierto
          onGuardado={refrescar}
          onCancelar={() => {
            setConsultaAbierta(false)
            refrescar()
          }}
        />
      )}

      {fichaId !== null && (
        <ClimaFicha
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
