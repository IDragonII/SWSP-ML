import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { mensajeDeError } from '../api/errores.js'
import { listarPredicciones, obtenerPrediccion } from '../api/ml.js'
import Aviso from '../components/Aviso.jsx'
import BannerDemostracion from '../components/BannerDemostracion.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'

const PESTANAS = [
  ['pendiente', 'Pendientes'],
  ['comparada', 'Comparadas'],
  ['todas', 'Todas'],
]

function fecha(texto) {
  return texto ? new Date(texto).toLocaleDateString('es-PE') : '—'
}

function numero(texto) {
  return texto === null || texto === undefined
    ? '—'
    : Number(texto).toLocaleString('es-PE', { maximumFractionDigits: 2 })
}

export default function PrediccionHistorial() {
  const [params, setParams] = useSearchParams()
  const comparacion = params.get('comparacion') ?? 'pendiente'
  const pagina = Number(params.get('page') ?? 1)

  const clave = `${comparacion}|${pagina}`
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [error, setError] = useState(null)
  const [ficha, setFicha] = useState(null)
  const refrescando = datos !== null && claveCargada !== clave

  function cambiar(cambios) {
    const siguiente = new URLSearchParams(params)
    for (const [claveCambio, valor] of Object.entries(cambios)) {
      if (valor === null || valor === undefined || valor === '') {
        siguiente.delete(claveCambio)
      } else {
        siguiente.set(claveCambio, String(valor))
      }
    }
    setParams(siguiente)
  }

  useEffect(() => {
    let activo = true
    const filtros = { comparacion }
    if (pagina > 1) filtros.page = pagina
    listarPredicciones(filtros)
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
  }, [comparacion, pagina, clave])

  function verFicha(id) {
    obtenerPrediccion(id)
      .then((prediccion) => setFicha(prediccion))
      .catch((e) => setError(mensajeDeError(e)))
  }

  if (!datos && !error) return <Cargando texto="Cargando predicciones…" />

  const hayDemostracion =
    datos?.results.some((fila) => fila.datos_demostracion) ?? false

  return (
    <div>
      <div className="pagina-cabecera">
        <div>
          <h1>Historial de predicciones</h1>
          <p className="conteo">
            {datos ? `${datos.count} en esta pestaña` : 'Sin datos'}
          </p>
        </div>
      </div>

      {hayDemostracion && <BannerDemostracion />}

      <div className="pestanas" role="tablist" aria-label="Comparación con lo real">
        {PESTANAS.map(([valor, etiqueta]) => (
          <button
            key={valor}
            type="button"
            role="tab"
            aria-selected={comparacion === valor}
            className={`pestana${comparacion === valor ? ' activa' : ''}`}
            onClick={() => cambiar({ comparacion: valor, page: null })}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>
            {comparacion === 'pendiente'
              ? 'No hay predicciones pendientes de comparar: cuando la campaña se coseche, el sistema completa el rendimiento real.'
              : 'No hay predicciones en esta pestaña.'}
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
                celda: (fila) => fecha(fila.fecha),
              },
              {
                clave: 'campania',
                etiqueta: 'Campaña',
                celda: (fila) =>
                  `${fila.campania.parcela.codigo} · ${fila.campania.cultivo.nombre}`,
              },
              {
                clave: 'modelo',
                etiqueta: 'Modelo',
                celda: (fila) => `${fila.modelo.algoritmo} v${fila.modelo.version}`,
              },
              {
                clave: 'predicho',
                etiqueta: 'Predicho (kg/ha)',
                celda: (fila) => numero(fila.rendimiento_predicho),
              },
              {
                clave: 'real',
                etiqueta: 'Real (kg/ha)',
                celda: (fila) => numero(fila.rendimiento_real),
              },
              {
                clave: 'error',
                etiqueta: 'Error',
                celda: (fila) =>
                  fila.error_pct === null
                    ? 'Pendiente'
                    : `${numero(fila.error_pct)} %`,
              },
              {
                clave: 'confiabilidad',
                etiqueta: 'Confiabilidad',
                celda: (fila) => <Chip>{fila.confiabilidad}</Chip>,
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => verFicha(fila.id)}
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

      <Modal
        abierto={ficha !== null}
        titulo="Ficha de la predicción"
        tamano="ficha"
        onCerrar={() => setFicha(null)}
      >
        {ficha && (
          <div>
            <p>
              <strong>Campaña:</strong> {ficha.campania.parcela.codigo} ·{' '}
              {ficha.campania.cultivo.nombre} · {ficha.campania.periodo} (
              {ficha.campania.estado})
            </p>
            <p>
              <strong>Modelo:</strong> {ficha.modelo.algoritmo} v
              {ficha.modelo.version} (MAE {ficha.modelo.mae})
            </p>
            <p>
              <strong>Rendimiento predicho:</strong>{' '}
              {numero(ficha.rendimiento_predicho)} kg/ha ·{' '}
              <strong>Producción estimada:</strong>{' '}
              {numero(ficha.produccion_estimada_kg)} kg
            </p>
            <p>
              <strong>Real:</strong> {numero(ficha.rendimiento_real)} kg/ha ·{' '}
              <strong>Error:</strong> {numero(ficha.error_abs)} kg/ha (
              {numero(ficha.error_pct)} %)
            </p>
            <p>
              <strong>Confiabilidad:</strong> <Chip>{ficha.confiabilidad}</Chip>
            </p>
            {ficha.datos_demostracion && <BannerDemostracion />}
            <p className="nota">{ficha.texto_estimacion}</p>
            {ficha.avisos.length > 0 && (
              <div>
                <strong>Avisos</strong>
                <ul>
                  {ficha.avisos.map((aviso) => (
                    <li key={aviso}>{aviso}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="nota">
              Predicha el {fecha(ficha.fecha)}
              {ficha.creado_por ? ` por ${ficha.creado_por}` : ''}.
            </p>
          </div>
        )}
      </Modal>
    </div>
  )
}
