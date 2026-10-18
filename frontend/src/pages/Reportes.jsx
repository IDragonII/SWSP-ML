import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ESTADOS_CAMPANIA } from '../api/campanias.js'
import { dashboardFiltros } from '../api/dashboard.js'
import { mensajeDeError } from '../api/errores.js'
import {
  descargarReporte,
  listarReportes,
  vistaPrevia,
} from '../api/reportes.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import Tabla from '../components/Tabla.jsx'
import { useToast } from '../context/useToast.js'

// Los mismos filtros del panel, con sus mismos nombres de parámetro;
// el catálogo decide cuáles se muestran en cada reporte
const PARAMETROS_FILTRO = [
  'periodo',
  'cultivo',
  'provincia',
  'distrito',
  'comunidad',
  'estado',
  'estado_productor',
]

const OPCIONES_VACIAS = {
  periodos: [],
  cultivos: [],
  provincias: [],
  distritos: [],
  comunidades: [],
}

// Etiquetas de los filtros, las mismas que usa el servidor en los archivos
const ETIQUETAS_FILTRO = {
  periodo: 'Período',
  cultivo: 'Cultivo',
  provincia: 'Provincia',
  distrito: 'Distrito',
  comunidad: 'Comunidad',
  estado: 'Estado de campaña',
  estado_productor: 'Estado del productor',
}

// Texto del «todas/todos» inicial de cada filtro con vacío permitido
const FILTROS_SIN_VALOR = {
  periodo: 'Todos',
  cultivo: 'Todos',
  provincia: 'Todas',
  distrito: 'Todos',
  comunidad: 'Todas',
  estado: 'Todos',
}

// Valores que acepta estado_productor; sin filtro, el servidor usa ACTIVO
const ESTADOS_PRODUCTOR = [
  ['', 'Solo activos (por defecto)'],
  ['ACTIVO', 'Solo activos'],
  ['INACTIVO', 'Solo inactivos'],
  ['TODOS', 'Todos'],
]

// Etiquetas del resumen por cultivo (las mismas de la hoja «Resumen»)
const COLUMNAS_RESUMEN = [
  { clave: 'etiqueta', etiqueta: 'Cultivo' },
  { clave: 'campanias', etiqueta: 'Campañas' },
  { clave: 'superficie_ha', etiqueta: 'Ha cosechadas' },
  { clave: 'produccion_kg', etiqueta: 'Producción (kg)' },
  { clave: 'toneladas', etiqueta: 'Producción (ton)' },
  { clave: 'rendimiento_kg_ha', etiqueta: 'Rendimiento (kg/ha)' },
  { clave: 'provisionales', etiqueta: 'Provisionales' },
  { clave: 'excluidas_revision', etiqueta: 'Excluidas por revisión' },
  { clave: 'pocos_datos', etiqueta: 'Pocos datos' },
]

function entero(valor) {
  return new Intl.NumberFormat('es-PE').format(valor)
}

function guardarArchivo(archivo, nombre) {
  const url = URL.createObjectURL(archivo)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function celdaResumen(columna) {
  return (fila) => {
    const valor = fila[columna.clave]
    if (valor === null || valor === undefined || valor === '') return '—'
    if (typeof valor === 'boolean') return valor ? 'Sí' : 'No'
    return String(valor)
  }
}

function Tarjeta({ rotulo, valor }) {
  return (
    <div className="tarjeta">
      <dt>{rotulo}</dt>
      <dd>{valor}</dd>
    </div>
  )
}

export default function Reportes() {
  const { avisar } = useToast()
  const [params, setParams] = useSearchParams()

  const [catalogo, setCatalogo] = useState(null)
  const [errorCatalogo, setErrorCatalogo] = useState(null)
  const [opciones, setOpciones] = useState(OPCIONES_VACIAS)
  const [previa, setPrevia] = useState(null)
  const [previaCargada, setPreviaCargada] = useState(null)
  const [errorPrevia, setErrorPrevia] = useState(null)
  const [descargando, setDescargando] = useState(null)

  const periodo = params.get('periodo') ?? ''
  const cultivo = params.get('cultivo') ?? ''
  const provincia = params.get('provincia') ?? ''
  const distrito = params.get('distrito') ?? ''
  const comunidad = params.get('comunidad') ?? ''
  const estado = params.get('estado') ?? ''
  const estadoProductor = params.get('estado_productor') ?? ''
  const tipoElegido = params.get('reporte') ?? ''
  const hayFiltros = PARAMETROS_FILTRO.some((clave) => params.get(clave))

  // El reporte elegido, o el primero de los disponibles; un tipo sin
  // permiso (o desconocido en la URL) cae en el primero
  const reporte =
    catalogo?.find((item) => item.tipo === tipoElegido) ?? catalogo?.[0] ?? null

  // Huella de la última petición de vista previa: mientras no coincida,
  // la tabla está refrescando (el patrón de las demás páginas)
  const clavePrevia = [
    reporte?.tipo ?? '',
    periodo,
    cultivo,
    provincia,
    distrito,
    comunidad,
    estado,
    estadoProductor,
  ].join('|')
  const refrescando = previa !== null && previaCargada !== clavePrevia

  const valores = {
    periodo,
    cultivo,
    provincia,
    distrito,
    comunidad,
    estado,
    estado_productor: estadoProductor,
  }

  // Catálogo: solo los reportes que este usuario puede usar
  useEffect(() => {
    let activo = true
    listarReportes()
      .then((lista) => {
        if (!activo) return
        setCatalogo(lista)
      })
      .catch((e) => activo && setErrorCatalogo(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [])

  // Opciones de los selects, en cascada provincia → distrito (como el panel)
  useEffect(() => {
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
        // Sin opciones la página sigue siendo usable con los valores actuales
      })
    return () => {
      activo = false
    }
  }, [provincia, distrito])

  // Vista previa: se recarga con cada cambio de reporte o de filtro
  useEffect(() => {
    if (!reporte) return undefined
    let activo = true
    const candidatos = {
      periodo,
      cultivo,
      provincia,
      distrito,
      comunidad,
      estado,
      estado_productor: estadoProductor,
    }
    const filtros = {}
    for (const clave of reporte.filtros) {
      if (candidatos[clave]) filtros[clave] = candidatos[clave]
    }
    vistaPrevia(reporte.tipo, filtros)
      .then((datos) => {
        if (!activo) return
        setErrorPrevia(null)
        setPrevia(datos)
        setPreviaCargada(clavePrevia)
      })
      .catch((e) => {
        if (!activo) return
        setErrorPrevia(mensajeDeError(e))
        setPreviaCargada(clavePrevia)
      })
    return () => {
      activo = false
    }
  }, [
    reporte,
    periodo,
    cultivo,
    provincia,
    distrito,
    comunidad,
    estado,
    estadoProductor,
    clavePrevia,
  ])

  function cambiarFiltro(clave, valor) {
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

  function cambiarReporte(tipo) {
    const nuevo = new URLSearchParams(params)
    nuevo.set('reporte', tipo)
    setParams(nuevo)
  }

  function limpiarFiltros() {
    const nuevo = new URLSearchParams(params)
    PARAMETROS_FILTRO.forEach((clave) => nuevo.delete(clave))
    setParams(nuevo)
  }

  async function descargar(formato) {
    if (!reporte || descargando) return
    setDescargando(formato)
    try {
      const { archivo, nombre } = await descargarReporte(
        reporte.tipo,
        formato,
        PARAMETROS_FILTRO.reduce((filtros, clave) => {
          if (valores[clave] && reporte.filtros.includes(clave)) {
            filtros[clave] = valores[clave]
          }
          return filtros
        }, {}),
      )
      guardarArchivo(
        archivo,
        nombre || `reporte_${reporte.tipo}.${formato}`,
      )
      avisar(nombre ? `Descarga lista: ${nombre}` : 'Descarga lista')
    } catch (error) {
      avisar(mensajeDeError(error), 'error')
    } finally {
      setDescargando(null)
    }
  }

  function opcionesDe(clave) {
    if (clave === 'periodo') {
      return opciones.periodos.map((valor) => ({ valor, etiqueta: valor }))
    }
    if (clave === 'estado') {
      return ESTADOS_CAMPANIA.map(([valor, etiqueta]) => ({ valor, etiqueta }))
    }
    if (clave === 'estado_productor') {
      return ESTADOS_PRODUCTOR.map(([valor, etiqueta]) => ({ valor, etiqueta }))
    }
    const lista = opciones[`${clave}s`] ?? []
    return lista.map((elemento) => ({
      valor: String(elemento.id),
      etiqueta: elemento.nombre,
    }))
  }

  const previaVisible = previa && reporte && previa.tipo === reporte.tipo
  const filasDetalle = (previaVisible?.filas ?? []).map((fila, indice) => ({
    ...fila,
    id: indice,
  }))
  const columnasDetalle = (previaVisible?.columnas ?? []).map((columna) => ({
    clave: columna.clave,
    etiqueta: columna.etiqueta,
    celda: (fila) => fila[columna.clave] || '—',
  }))

  return (
    <>
      <h1>Reportes</h1>
      <p className="texto-intro">
        Elige un reporte, afina los filtros, comprueba la vista previa y
        descárgalo en Excel o PDF. Los archivos no incluyen DNI ni teléfono.
      </p>

      <Aviso>{errorCatalogo}</Aviso>
      {!catalogo && !errorCatalogo ? (
        <Cargando texto="Cargando reportes…" />
      ) : (
        catalogo &&
        reporte && (
          <section className="panel" aria-labelledby="reporte-titulo">
            <h2 id="reporte-titulo">{reporte.nombre}</h2>
            <p className="nota">{reporte.descripcion}</p>

            {catalogo.length > 1 && (
              <Campo id="reporte-tipo" etiqueta="Reporte">
                <select
                  id="reporte-tipo"
                  value={reporte.tipo}
                  onChange={(evento) => cambiarReporte(evento.target.value)}
                >
                  {catalogo.map((item) => (
                    <option key={item.tipo} value={item.tipo}>
                      {item.nombre}
                    </option>
                  ))}
                </select>
              </Campo>
            )}

            <div className="filtros" role="group" aria-label="Filtros del reporte">
              {reporte.filtros.map((clave) => (
                <Campo
                  key={clave}
                  id={`filtro-${clave}`}
                  etiqueta={ETIQUETAS_FILTRO[clave]}
                >
                  <select
                    id={`filtro-${clave}`}
                    value={valores[clave] ?? ''}
                    onChange={(evento) =>
                      cambiarFiltro(clave, evento.target.value)
                    }
                  >
                    {FILTROS_SIN_VALOR[clave] && (
                      <option value="">{FILTROS_SIN_VALOR[clave]}</option>
                    )}
                    {opcionesDe(clave).map((opcion) => (
                      <option key={opcion.valor} value={opcion.valor}>
                        {opcion.etiqueta}
                      </option>
                    ))}
                  </select>
                </Campo>
              ))}
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

            <Aviso>{errorPrevia}</Aviso>
            {!previaVisible && !errorPrevia ? (
              <Cargando texto="Cargando la vista previa…" />
            ) : (
              previaVisible && (
                <>
                  <p className="nota">
                    Filtros: {previa.filtros_texto} · {previa.aviso_privacidad}
                  </p>
                  {previa.advertencias.map((advertencia) => (
                    <p className="nota" key={advertencia}>
                      {advertencia}
                    </p>
                  ))}

                  {previa.resumen.por_cultivo ? (
                    <>
                      <Tabla
                        columnas={COLUMNAS_RESUMEN.map((columna) => ({
                          ...columna,
                          celda: celdaResumen(columna),
                        }))}
                        filas={previa.resumen.por_cultivo.map(
                          (fila, indice) => ({
                            ...fila,
                            id: fila.clave ?? indice,
                          }),
                        )}
                        refrescando={refrescando}
                      />
                      <dl className="tarjetas">
                        <Tarjeta
                          rotulo="Campañas"
                          valor={entero(previa.resumen.totales.campanias)}
                        />
                        <Tarjeta
                          rotulo="Ha cosechadas"
                          valor={previa.resumen.totales.superficie_ha}
                        />
                        <Tarjeta
                          rotulo="Producción (kg)"
                          valor={previa.resumen.totales.produccion_kg}
                        />
                        <Tarjeta
                          rotulo="Rendimiento (kg/ha)"
                          valor={previa.resumen.totales.rendimiento_kg_ha}
                        />
                      </dl>
                    </>
                  ) : (
                    <dl className="tarjetas">
                      <Tarjeta
                        rotulo="Productores"
                        valor={entero(previa.resumen.productores)}
                      />
                      <Tarjeta
                        rotulo="Filas"
                        valor={entero(previa.resumen.filas)}
                      />
                      <Tarjeta
                        rotulo="Superficie de parcelas (ha)"
                        valor={previa.resumen.superficie_parcelas_ha}
                      />
                      <Tarjeta
                        rotulo="Superficie sembrada (ha)"
                        valor={previa.resumen.superficie_sembrada_ha}
                      />
                    </dl>
                  )}

                  <p className="nota">
                    {entero(previa.total_filas)}{' '}
                    {previa.total_filas === 1 ? 'fila' : 'filas'} · Excel admite
                    hasta {entero(previa.limites.xlsx)} · PDF hasta{' '}
                    {entero(previa.limites.pdf)}
                  </p>

                  <div
                    className="filtros-acciones"
                    role="group"
                    aria-label="Descargas"
                  >
                    <button
                      className="boton-primario"
                      type="button"
                      onClick={() => descargar('xlsx')}
                      disabled={descargando !== null}
                    >
                      {descargando === 'xlsx' ? (
                        <>
                          <RuedaCarga etiqueta="Descargando…" />
                          Descargando…
                        </>
                      ) : (
                        'Descargar Excel'
                      )}
                    </button>
                    <button
                      className="boton-primario"
                      type="button"
                      onClick={() => descargar('pdf')}
                      disabled={descargando !== null}
                    >
                      {descargando === 'pdf' ? (
                        <>
                          <RuedaCarga etiqueta="Descargando…" />
                          Descargando…
                        </>
                      ) : (
                        'Descargar PDF'
                      )}
                    </button>
                  </div>

                  {previa.total_filas === 0 && (
                    <p className="nota">No hay filas con estos filtros.</p>
                  )}
                  <Tabla
                    columnas={columnasDetalle}
                    filas={filasDetalle}
                    refrescando={refrescando}
                  />
                </>
              )
            )}
          </section>
        )
      )}
      {catalogo && catalogo.length === 0 && (
        <p className="nota">
          No tienes reportes disponibles con tus permisos actuales.
        </p>
      )}
    </>
  )
}
