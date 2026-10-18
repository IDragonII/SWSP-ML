import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { productoresEnRiesgo } from '../api/alertas.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Cargando from '../components/Cargando.jsx'
import Tabla from '../components/Tabla.jsx'

export default function ProductoresRiesgo() {
  const navegar = useNavigate()
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let activo = true
    productoresEnRiesgo()
      .then((respuesta) => {
        if (!activo) return
        setError(null)
        setDatos(respuesta)
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [])

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Productores en riesgo</h1>
          <p className="conteo">
            {datos ? `${datos.results.length} con alertas pendientes` : 'Sin datos'}
          </p>
        </div>
      </div>

      <p className="nota">
        Cada productor agrupa sus alertas pendientes. El riesgo se evalúa
        solo con las campañas activas: incidencias severas, campañas sin
        actividad y rendimientos bajos.
      </p>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay productores en riesgo: ninguna alerta está pendiente.</p>
        </div>
      ) : (
        datos && (
          <Tabla
            filas={datos.results}
            columnas={[
              {
                clave: 'productor_codigo',
                etiqueta: 'Código',
                celda: (fila) => fila.productor_codigo,
              },
              {
                clave: 'productor_nombre',
                etiqueta: 'Productor',
                celda: (fila) => fila.productor_nombre,
              },
              {
                clave: 'distrito',
                etiqueta: 'Ubicación',
                celda: (fila) => `${fila.distrito} · ${fila.provincia}`,
              },
              {
                clave: 'pendientes',
                etiqueta: 'Alertas pendientes',
                celda: (fila) => fila.pendientes,
              },
              {
                clave: 'tipos',
                etiqueta: 'Tipos',
                celda: (fila) => fila.tipos.join(', '),
              },
              {
                clave: 'ultima_alerta',
                etiqueta: 'Última alerta',
                celda: (fila) =>
                  fila.ultima_alerta
                    ? `${fila.ultima_alerta}${
                        fila.ultima_alerta_en
                          ? ` (${new Date(fila.ultima_alerta_en).toLocaleDateString('es-PE')})`
                          : ''
                      }`
                    : '—',
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => {
                      navegar(`/alertas?productor=${fila.productor}`)
                    }}
                  >
                    Ver alertas
                  </button>
                ),
              },
            ]}
          />
        )
      )}
    </>
  )
}
