import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { etiquetaTipo, resumenAlertas } from '../api/alertas.js'
import {
  AGRUPACIONES,
  dashboardCampaniasEstado,
  dashboardFiltros,
  dashboardProduccion,
  dashboardResumen,
} from '../api/dashboard.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { opcionesMenu } from '../routes/opcionesMenu.js'

// Los 5 estados del modelo Campania, en orden de avance (HU-135)
const ESTADOS_CAMPANIA = [
  ['PLANIFICADA', 'Planificadas', 'var(--helecho)'],
  ['EN_PRODUCCION', 'En producción', 'var(--helecho)'],
  ['COSECHADA', 'Cosechadas', 'var(--bosque)'],
  ['CERRADA', 'Cerradas', 'var(--bosque)'],
  ['CANCELADA', 'Canceladas', 'var(--apagado)'],
]

const PARAMETROS_FILTRO = [
  'periodo',
  'cultivo',
  'provincia',
  'distrito',
  'comunidad',
]

const OPCIONES_VACIAS = {
  periodos: [],
  cultivos: [],
  provincias: [],
  distritos: [],
  comunidades: [],
}

function saludoPorHora() {
  const hora = new Date().getHours()
  if (hora < 13) return 'Buenos días'
  if (hora < 20) return 'Buenas tardes'
  return 'Buenas noches'
}

function fechaCorta(valor) {
  if (!valor) return null
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return valor
  return fecha.toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })
}

// Las cifras agregadas llegan como texto con 2 decimales; sin dato es null
function cifra(valor, unidad = '') {
  if (valor === null || valor === undefined) return '—'
  return unidad ? `${valor} ${unidad}` : String(valor)
}

function numeroGrafico(valor) {
  return valor === null || valor === undefined ? 0 : Number(valor)
}

function Grafico({ etiqueta, datos, claveValor = 'total', nombreValor, colorPorFila }) {
  return (
    <div
      className="grafico-envoltura"
      role="img"
      aria-label={etiqueta}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--linea)" />
          <XAxis
            dataKey="etiqueta"
            tick={{ fontSize: 12, fill: 'var(--tinta)' }}
            stroke="var(--apagado)"
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12, fill: 'var(--tinta)' }}
            stroke="var(--apagado)"
            width={40}
          />
          <Tooltip
            formatter={(valor) => [
              new Intl.NumberFormat('es-PE').format(valor),
              nombreValor,
            ]}
          />
          <Bar dataKey={claveValor} name={nombreValor} fill="var(--helecho)">
            {datos.map((fila) => (
              <Cell key={fila.clave} fill={colorPorFila(fila)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Tarjetas({ resumen }) {
  const { tienePermiso } = useSesion()
  const tarjetas = [
    ['Productores activos', cifra(resumen.productores.activos)],
    ['Productores inactivos', cifra(resumen.productores.inactivos)],
    ['Con campaña activa', cifra(resumen.productores.con_campania_activa)],
    ['Superficie sembrada (ha)', cifra(resumen.superficie_sembrada_ha)],
    ['Campañas aptas para entrenar', cifra(resumen.aptas_entrenar)],
    [
      'Revisiones pendientes',
      cifra(resumen.revisiones_pendientes),
      '/produccion?requiere_revision=true',
    ],
    ['Alertas pendientes', cifra(resumen.alertas.pendientes)],
    ['Alertas totales', cifra(resumen.alertas.total)],
  ]
  return (
    <dl className="tarjetas">
      {tarjetas.map(([rotulo, valor, ruta]) => (
        <div className="tarjeta" key={rotulo}>
          <dt>{rotulo}</dt>
          <dd>
            {ruta && tienePermiso('produccion.ver') ? (
              <Link to={ruta}>{valor}</Link>
            ) : (
              valor
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}

export default function Inicio() {
  const { usuario, tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const vePanel = tienePermiso('dashboard.ver')
  const veAlertas = tienePermiso('alertas.ver')

  const periodo = params.get('periodo') ?? ''
  const cultivo = params.get('cultivo') ?? ''
  const provincia = params.get('provincia') ?? ''
  const distrito = params.get('distrito') ?? ''
  const comunidad = params.get('comunidad') ?? ''
  const agrupar = params.get('agrupar') === 'distrito' ? 'distrito' : 'cultivo'
  const hayFiltros = PARAMETROS_FILTRO.some((clave) => params.get(clave))

  const [resumen, setResumen] = useState(null)
  const [errorResumen, setErrorResumen] = useState(null)
  const [alertas, setAlertas] = useState(null)
  const [errorAlertas, setErrorAlertas] = useState(null)
  const [campaniasEstado, setCampaniasEstado] = useState(null)
  const [errorCampanias, setErrorCampanias] = useState(null)
  const [opciones, setOpciones] = useState(OPCIONES_VACIAS)
  const [produccion, setProduccion] = useState(null)
  const [errorProduccion, setErrorProduccion] = useState(null)

  useEffect(() => {
    if (!vePanel) return undefined
    let activo = true
    dashboardResumen()
      .then((datos) => {
        if (!activo) return
        setErrorResumen(null)
        setResumen(datos)
      })
      .catch((e) => activo && setErrorResumen(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [vePanel])

  useEffect(() => {
    if (!vePanel || !veAlertas) return undefined
    let activo = true
    resumenAlertas()
      .then((datos) => {
        if (!activo) return
        setErrorAlertas(null)
        setAlertas(datos)
      })
      .catch((e) => activo && setErrorAlertas(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [vePanel, veAlertas])

  useEffect(() => {
    if (!vePanel) return undefined
    let activo = true
    dashboardCampaniasEstado(periodo ? { periodo } : {})
      .then((datos) => {
        if (!activo) return
        setErrorCampanias(null)
        setCampaniasEstado(datos)
      })
      .catch((e) => activo && setErrorCampanias(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [vePanel, periodo])

  useEffect(() => {
    if (!vePanel) return undefined
    let activo = true
    const filtros = {}
    if (provincia) filtros.provincia = provincia
    if (distrito) filtros.distrito = distrito
    dashboardFiltros(filtros)
      .then((datos) => {
        if (!activo) return
        setOpciones(datos)
      })
      .catch(() => {
        // Sin opciones el panel sigue siendo usable con los valores del alcance
      })
    return () => {
      activo = false
    }
  }, [vePanel, provincia, distrito])

  useEffect(() => {
    if (!vePanel) return undefined
    let activo = true
    const filtros = { agrupar }
    if (periodo) filtros.periodo = periodo
    if (cultivo) filtros.cultivo = cultivo
    if (provincia) filtros.provincia = provincia
    if (distrito) filtros.distrito = distrito
    if (comunidad) filtros.comunidad = comunidad
    dashboardProduccion(filtros)
      .then((datos) => {
        if (!activo) return
        setErrorProduccion(null)
        setProduccion(datos)
      })
      .catch((e) => activo && setErrorProduccion(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [vePanel, agrupar, periodo, cultivo, provincia, distrito, comunidad])

  function cambiarParametro(clave, valor) {
    const nuevo = new URLSearchParams(params)
    if (valor) nuevo.set(clave, valor)
    else nuevo.delete(clave)
    // La ubicación es en cascada: al estrechar se limpian los niveles de abajo
    if (clave === 'provincia') {
      nuevo.delete('distrito')
      nuevo.delete('comunidad')
    }
    if (clave === 'distrito') nuevo.delete('comunidad')
    setParams(nuevo)
  }

  function cambiarAgrupacion(valor) {
    const nuevo = new URLSearchParams(params)
    if (valor === 'cultivo') nuevo.delete('agrupar')
    else nuevo.set('agrupar', valor)
    setParams(nuevo)
  }

  function limpiarFiltros() {
    const nuevo = new URLSearchParams(params)
    PARAMETROS_FILTRO.forEach((clave) => nuevo.delete(clave))
    setParams(nuevo)
  }

  const modulos = opcionesMenu.filter(
    (opcion) =>
      opcion.ruta !== '/' && (!opcion.permiso || tienePermiso(opcion.permiso)),
  )
  const nombre = usuario.nombre_completo || usuario.username

  const filasEstado = campaniasEstado
    ? ESTADOS_CAMPANIA.map(([clave, etiqueta]) => ({
        clave,
        etiqueta,
        total: campaniasEstado.estados[clave] ?? 0,
      }))
    : []
  const totalCampaniasEstado = filasEstado.reduce(
    (suma, fila) => suma + fila.total,
    0,
  )

  const filasProduccion = (produccion?.filas ?? []).map((fila) => ({
    ...fila,
    id: fila.clave,
    kg: numeroGrafico(fila.produccion_kg),
  }))
  const rotuloAgrupacion =
    agrupar === 'cultivo' ? 'Cultivo' : 'Distrito'

  return (
    <>
      <h1>
        {saludoPorHora()}, {nombre}
      </h1>
      <p className="texto-intro">
        Has iniciado sesión con el rol <strong>{usuario.rol?.nombre}</strong>. Este menú
        se arma según tus permisos; el backend vuelve a comprobar cada permiso en cada
        petición.
      </p>

      {vePanel && (
        <>
          <section className="panel" aria-labelledby="panel-titulo">
            <h2 id="panel-titulo">Panel de indicadores</h2>
            <p className="nota">
              Cifras de tu alcance{resumen?.generado_en
                ? ` · actualizado el ${fechaCorta(resumen.generado_en)}`
                : ''}
              . Los datos sin registro aparecen como «—», nunca como cero.
            </p>
            <Aviso>{errorResumen}</Aviso>
            {!resumen && !errorResumen ? (
              <Cargando texto="Cargando el panel…" />
            ) : (
              resumen && <Tarjetas resumen={resumen} />
            )}
          </section>

          {veAlertas && (
            <section className="panel" aria-labelledby="alertas-titulo">
              <h2 id="alertas-titulo">Alertas pendientes por tipo</h2>
              <Aviso>{errorAlertas}</Aviso>
              {alertas ? (
                <>
                  <dl className="datos-rejilla">
                    <div>
                      <dt>Pendientes</dt>
                      <dd>{alertas.pendientes}</dd>
                    </div>
                    {Object.entries(alertas.por_tipo).map(([tipo, cuenta]) => (
                      <div key={tipo}>
                        <dt>{etiquetaTipo(tipo)}</dt>
                        <dd>{cuenta}</dd>
                      </div>
                    ))}
                  </dl>
                  <p className="nota">
                    <Link to="/alertas">Ver el listado de alertas</Link>
                  </p>
                </>
              ) : (
                !errorAlertas && <Cargando texto="Cargando alertas…" />
              )}
            </section>
          )}

          <h2 className="visualmente-oculto">Indicadores con filtros</h2>
          <div className="filtros" role="group" aria-label="Filtros del panel">
            <Campo id="filtro-periodo" etiqueta="Período">
              <select
                id="filtro-periodo"
                value={periodo}
                onChange={(evento) =>
                  cambiarParametro('periodo', evento.target.value)
                }
              >
                <option value="">Todos</option>
                {opciones.periodos.map((valor) => (
                  <option key={valor} value={valor}>
                    {valor}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo id="filtro-cultivo" etiqueta="Cultivo">
              <select
                id="filtro-cultivo"
                value={cultivo}
                onChange={(evento) =>
                  cambiarParametro('cultivo', evento.target.value)
                }
              >
                <option value="">Todos</option>
                {opciones.cultivos.map((valor) => (
                  <option key={valor.id} value={valor.id}>
                    {valor.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo id="filtro-provincia" etiqueta="Provincia">
              <select
                id="filtro-provincia"
                value={provincia}
                onChange={(evento) =>
                  cambiarParametro('provincia', evento.target.value)
                }
              >
                <option value="">Todas</option>
                {opciones.provincias.map((valor) => (
                  <option key={valor.id} value={valor.id}>
                    {valor.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo id="filtro-distrito" etiqueta="Distrito">
              <select
                id="filtro-distrito"
                value={distrito}
                onChange={(evento) =>
                  cambiarParametro('distrito', evento.target.value)
                }
              >
                <option value="">Todos</option>
                {opciones.distritos.map((valor) => (
                  <option key={valor.id} value={valor.id}>
                    {valor.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo id="filtro-comunidad" etiqueta="Comunidad">
              <select
                id="filtro-comunidad"
                value={comunidad}
                onChange={(evento) =>
                  cambiarParametro('comunidad', evento.target.value)
                }
              >
                <option value="">Todas</option>
                {opciones.comunidades.map((valor) => (
                  <option key={valor.id} value={valor.id}>
                    {valor.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <div className="filtros-acciones">
              <button
                type="button"
                className="boton-secundario"
                onClick={limpiarFiltros}
                disabled={!hayFiltros}
              >
                Limpiar filtros
              </button>
            </div>
          </div>

          <section className="panel" aria-labelledby="campanias-estado-titulo">
            <h2 id="campanias-estado-titulo">Campañas por estado</h2>
            <p className="nota">
              {periodo
                ? `Solo el período ${periodo}.`
                : 'Todos los períodos de tu alcance.'}{' '}
              La serie siempre muestra los 5 estados.
            </p>
            <Aviso>{errorCampanias}</Aviso>
            {!campaniasEstado && !errorCampanias ? (
              <Cargando texto="Cargando campañas…" />
            ) : totalCampaniasEstado === 0 ? (
              <p className="nota">
                No hay campañas en tu alcance{periodo ? ` en el período ${periodo}` : ''}.
              </p>
            ) : (
              <Grafico
                etiqueta={`Campañas por estado${periodo ? ` del período ${periodo}` : ''}: ${filasEstado
                  .map((fila) => `${fila.total} ${fila.etiqueta.toLowerCase()}`)
                  .join(', ')}`}
                datos={filasEstado}
                nombreValor="Campañas"
                colorPorFila={(fila) =>
                  ESTADOS_CAMPANIA.find(([clave]) => clave === fila.clave)?.[2] ??
                  'var(--helecho)'
                }
              />
            )}
          </section>

          <section className="panel" aria-labelledby="produccion-titulo">
            <h2 id="produccion-titulo">Producción agrupada</h2>
            <p className="nota">
              Rendimiento ponderado (kilogramos ÷ superficie cosechada), el mismo
              que manda en el cierre de campaña; el promedio simple se muestra solo
              para comparar. Excluye producciones que requieren revisión.
            </p>
            <div className="pestanas" role="tablist" aria-label="Agrupación de la producción">
              {AGRUPACIONES.map(([valor, etiqueta]) => (
                <button
                  key={valor}
                  type="button"
                  role="tab"
                  aria-selected={agrupar === valor}
                  className={`pestana${agrupar === valor ? ' activa' : ''}`}
                  onClick={() => cambiarAgrupacion(valor)}
                >
                  {etiqueta}
                </button>
              ))}
            </div>
            <Aviso>{errorProduccion}</Aviso>
            {!produccion && !errorProduccion ? (
              <Cargando texto="Cargando producción…" />
            ) : filasProduccion.length === 0 ? (
              errorProduccion ? null : (
                <p className="nota">
                  No hay producciones registradas con estos filtros.
                </p>
              )
            ) : (
              <>
                <Grafico
                  etiqueta={`Producción por ${rotuloAgrupacion.toLowerCase()}: ${filasProduccion
                    .map((fila) => `${fila.etiqueta} ${fila.produccion_kg ?? 'sin datos'} kilogramos`)
                    .join(', ')}`}
                  datos={filasProduccion}
                  claveValor="kg"
                  nombreValor="Kilogramos"
                  colorPorFila={() => 'var(--bosque)'}
                />
                <Tabla
                  filas={filasProduccion}
                  columnas={[
                    {
                      clave: 'etiqueta',
                      etiqueta: rotuloAgrupacion,
                      celda: (fila) => fila.etiqueta,
                    },
                    {
                      clave: 'campanias',
                      etiqueta: 'Campañas',
                      celda: (fila) => fila.campanias,
                    },
                    {
                      clave: 'superficie_ha',
                      etiqueta: 'Superficie cosechada (ha)',
                      celda: (fila) => cifra(fila.superficie_ha),
                    },
                    {
                      clave: 'produccion_kg',
                      etiqueta: 'Producción (kg)',
                      celda: (fila) => cifra(fila.produccion_kg),
                    },
                    {
                      clave: 'rendimiento_kg_ha',
                      etiqueta: 'Rendimiento ponderado (kg/ha)',
                      celda: (fila) => cifra(fila.rendimiento_kg_ha),
                    },
                    {
                      clave: 'rendimiento_promedio_kg_ha',
                      etiqueta: 'Promedio simple (kg/ha)',
                      celda: (fila) => cifra(fila.rendimiento_promedio_kg_ha),
                    },
                    {
                      clave: 'senales',
                      etiqueta: 'Señales',
                      celda: (fila) => (
                        <>
                          {fila.provisional && <Chip>PROVISIONAL</Chip>}{' '}
                          {fila.pocos_datos && <Chip>POCOS DATOS</Chip>}
                          {!fila.provisional && !fila.pocos_datos && '—'}
                        </>
                      ),
                    },
                  ]}
                />
                {produccion?.totales && (
                  <p className="nota">
                    Total: {produccion.totales.campanias} campañas ·{' '}
                    {cifra(produccion.totales.superficie_ha, 'ha')} ·{' '}
                    {cifra(produccion.totales.produccion_kg, 'kg')} ·{' '}
                    {cifra(produccion.totales.rendimiento_kg_ha, 'kg/ha')} (ponderado).
                  </p>
                )}
              </>
            )}
          </section>
        </>
      )}

      <section className="panel">
        <h2>Tus módulos</h2>
        {modulos.length > 0 ? (
          <ul className="enlaces-modulos">
            {modulos.map((opcion) => (
              <li key={opcion.ruta}>
                <Link to={opcion.ruta}>{opcion.nombre}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>Solo tienes acceso al inicio. Pide los permisos que necesites al administrador.</p>
        )}
        <p className="nota">
          Los módulos listados se irán habilitando en los próximos sprints; el resto se
          muestra según el rol.
        </p>
      </section>
    </>
  )
}
