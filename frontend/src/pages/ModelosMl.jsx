import { useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import { activarModelo, listarModelos } from '../api/ml.js'
import Aviso from '../components/Aviso.jsx'
import BannerDemostracion from '../components/BannerDemostracion.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Tabla from '../components/Tabla.jsx'
import { useToast } from '../context/useToast.js'

function fecha(texto) {
  return texto ? new Date(texto).toLocaleDateString('es-PE') : '—'
}

function numero(texto, decimales = 2) {
  return texto === null || texto === undefined
    ? '—'
    : Number(texto).toLocaleString('es-PE', {
        maximumFractionDigits: decimales,
      })
}

export default function ModelosMl() {
  const { avisar } = useToast()
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [activarId, setActivarId] = useState(null)
  const [activando, setActivando] = useState(false)

  useEffect(() => {
    let activo = true
    listarModelos()
      .then((respuesta) => {
        if (!activo) return
        setError(null)
        setDatos(respuesta)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setDatos({ count: 0, results: [] })
      })
    return () => {
      activo = false
    }
  }, [recarga])

  async function activar() {
    setActivando(true)
    try {
      const modelo = await activarModelo(activarId)
      avisar(
        `Modelo activo: ${modelo.algoritmo} v${modelo.version}.`,
      )
      setActivarId(null)
      setError(null)
      setRecarga((n) => n + 1)
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setActivando(false)
    }
  }

  if (!datos && !error) return <Cargando texto="Cargando modelos…" />

  const hayDemostracion =
    datos?.results.some((fila) => fila.datos_demostracion) ?? false
  const porActivar = datos?.results.find((fila) => fila.id === activarId)

  return (
    <div>
      <div className="pagina-cabecera">
        <div>
          <h1>Modelos de Machine Learning</h1>
          <p className="conteo">
            {datos
              ? `${datos.count} entrenamientos registrados · un solo modelo activo`
              : 'Sin datos'}
          </p>
        </div>
      </div>

      {hayDemostracion && <BannerDemostracion />}

      <p className="texto-intro">
        El criterio escrito (docs/criterio_seleccion.md) elige el modelo de
        menor RMSE; solo el modelo elegido tiene el artefacto (archivo con
        manifiesto o contenido en la base de datos) y puede activarse.
        Activar verifica huella y una predicción de prueba antes de cambiar
        el modelo vigente.
      </p>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>
            No hay modelos registrados: entrena desde la pantalla{' '}
            <strong>Entrenar</strong> o con{' '}
            <code>python manage.py entrenar_modelos</code> y registra con{' '}
            <code>python manage.py registrar_modelo</code>.
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            filas={datos.results}
            columnas={[
              {
                clave: 'algoritmo',
                etiqueta: 'Algoritmo',
                celda: (fila) => fila.algoritmo.replaceAll('_', ' ').toLowerCase(),
              },
              {
                clave: 'version',
                etiqueta: 'Versión',
                celda: (fila) => fila.version,
              },
              { clave: 'mae', etiqueta: 'MAE', celda: (fila) => numero(fila.mae) },
              {
                clave: 'rmse',
                etiqueta: 'RMSE',
                celda: (fila) => numero(fila.rmse),
              },
              {
                clave: 'r2',
                etiqueta: 'R²',
                celda: (fila) => numero(fila.r2, 4),
              },
              {
                clave: 'origen',
                etiqueta: 'Origen de los datos',
                celda: (fila) => (
                  <Chip>
                    {fila.datos_demostracion
                      ? 'DEMOSTRACIÓN'
                      : fila.entrenamiento.origen_datos}
                  </Chip>
                ),
              },
              {
                clave: 'entrenamiento',
                etiqueta: 'Entrenado',
                celda: (fila) =>
                  `${fecha(fila.entrenamiento.fecha)} · ${fila.entrenamiento.n_registros} campañas`,
              },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => <Chip>{fila.activo ? 'ACTIVO' : 'Inactivo'}</Chip>,
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) =>
                  fila.activo ? (
                    '—'
                  ) : (
                    <button
                      type="button"
                      className="boton-texto"
                      disabled={!fila.archivo && !fila.en_bd}
                      title={
                        fila.archivo || fila.en_bd
                          ? 'Hacerlo el modelo vigente'
                          : 'Solo el modelo elegido por el criterio tiene el artefacto'
                      }
                      onClick={() => setActivarId(fila.id)}
                    >
                      Activar
                    </button>
                  ),
              },
            ]}
          />
        )
      )}

      <Modal
        abierto={activarId !== null}
        titulo="Activar este modelo"
        texto={
          porActivar
            ? `El modelo ${porActivar.algoritmo} v${porActivar.version} pasará a ser el vigente para todas las predicciones (el actual se desactiva). Se verifica la huella del artefacto (archivo o contenido en la BD) y se hace una predicción de prueba antes de cambiarlo. ¿Continuar?`
            : ''
        }
        confirmar="Activar"
        ocupado={activando}
        onConfirmar={activar}
        onCerrar={() => setActivarId(null)}
      />
    </div>
  )
}
