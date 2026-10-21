import { useEffect, useRef, useState } from 'react'
import {
  activarModelo,
  cancelarEntrenamiento,
  crearEntrenamiento,
  estadoDatos,
  listarEntrenamientos,
  resultadosEntrenamiento,
} from '../api/ml.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import BannerDemostracion from '../components/BannerDemostracion.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Tabla from '../components/Tabla.jsx'
import { useToast } from '../context/useToast.js'
import { useSesion } from '../context/useSesion.js'
import { fechaHoraCorta } from '../utils/fechas.js'

const ACTIVAS = ['PENDIENTE', 'PROCESANDO']
const SEGUNDO = 1000
const SONDEO_MS = 5000

function numero(texto, decimales = 2) {
  return texto === null || texto === undefined
    ? '—'
    : Number(texto).toLocaleString('es-PE', {
        maximumFractionDigits: decimales,
      })
}

function haceCuanto(valor) {
  if (!valor) return null
  const segundos = Math.max(
    0,
    Math.round((Date.now() - new Date(valor).getTime()) / SEGUNDO),
  )
  if (segundos < 60) return `hace ${segundos} s`
  const minutos = Math.floor(segundos / 60)
  return `hace ${minutos} min`
}

export default function Entrenar() {
  const { avisar } = useToast()
  const { tienePermiso } = useSesion()
  const [estado, setEstado] = useState(null)
  const [historial, setHistorial] = useState(null)
  // {id, datos}: el detalle solo se muestra si coincide con resultadoId
  const [guardado, setGuardado] = useState(null)
  const [resultadoId, setResultadoId] = useState(null)
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [recargaResultado, setRecargaResultado] = useState(0)
  const [confirmarAlta, setConfirmarAlta] = useState(false)
  const [creando, setCreando] = useState(false)
  const [cancelarId, setCancelarId] = useState(null)
  const [cancelando, setCancelando] = useState(false)
  const [activarId, setActivarId] = useState(null)
  const [activando, setActivando] = useState(false)
  const activaPrevia = useRef(null)

  function refrescar() {
    setRecarga((n) => n + 1)
  }

  // Carga de datos y detección de la transición de la tarea que se
  // seguía: al terminar se abren sus resultados (264).
  useEffect(() => {
    let activo = true
    Promise.all([estadoDatos(), listarEntrenamientos()])
      .then(([datos, tareas]) => {
        if (!activo) return
        setError(null)
        setEstado(datos)
        setHistorial(tareas)
        const activa = tareas.results.find((f) => ACTIVAS.includes(f.estado))
        const previa = activaPrevia.current
        activaPrevia.current = activa ? activa.id : null
        if (previa && !activa) {
          const terminada = tareas.results.find((f) => f.id === previa)
          if (terminada && terminada.estado === 'COMPLETADA') {
            if (terminada.resultado) setResultadoId(terminada.resultado)
          } else if (terminada && terminada.estado === 'FALLIDA') {
            setError(
              `El entrenamiento terminó en FALLIDA: ${terminada.error || 'sin detalle'}`,
            )
          }
        }
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
      })
    return () => {
      activo = false
    }
  }, [recarga])

  // Sondeo cada 5 s SOLO mientras haya tarea activa (263): sin tarea
  // no hay timer, ni batería ni ventana de throttle quemadas.
  useEffect(() => {
    if (!historial) return undefined
    const hayActiva = historial.results.some((f) =>
      ACTIVAS.includes(f.estado),
    )
    if (!hayActiva) return undefined
    const timer = setTimeout(refrescar, SONDEO_MS)
    return () => clearTimeout(timer)
    // refrescar es estable (solo setState con función), el encadenado
    // se apoya en historial que cambia con cada carga.
  }, [historial, recarga])

  // Detalle del resultado pedido (panel comparativo). El estado lleva
  // el id pedido: si cambia el id, lo guardado simplemente no se pinta.
  useEffect(() => {
    if (resultadoId === null || resultadoId === undefined) return undefined
    let activo = true
    resultadosEntrenamiento(resultadoId)
      .then((datos) => {
        if (activo) setGuardado({ id: resultadoId, datos })
      })
      .catch((e) => {
        if (activo) setError(mensajeDeError(e))
      })
    return () => {
      activo = false
    }
  }, [resultadoId, recargaResultado])

  async function alta() {
    setCreando(true)
    try {
      await crearEntrenamiento()
      setConfirmarAlta(false)
      setError(null)
      avisar('Entrenamiento en cola: el trabajador lo tomará en unos segundos.')
      refrescar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setCreando(false)
    }
  }

  async function cancelar() {
    setCancelando(true)
    try {
      await cancelarEntrenamiento(cancelarId)
      setCancelarId(null)
      avisar('Tarea cancelada.')
      refrescar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setCancelando(false)
    }
  }

  async function activar() {
    setActivando(true)
    try {
      const modelo = await activarModelo(activarId)
      setActivarId(null)
      avisar(`Modelo activo: ${modelo.algoritmo} v${modelo.version}.`)
      setRecargaResultado((n) => n + 1)
      refrescar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setActivando(false)
    }
  }

  if ((!estado || !historial) && !error) {
    return <Cargando texto="Cargando entrenamientos…" />
  }

  const tareas = historial ? historial.results : []
  const activa = tareas.find((f) => ACTIVAS.includes(f.estado)) || null
  const hayActiva = activa !== null
  const listo = estado ? estado.listo : false
  const pct = activa
    ? Math.max(0, Math.min(100, activa.progreso?.pct ?? 0))
    : 0
  const resultado =
    guardado && guardado.id === resultadoId ? guardado.datos : null
  const elegidoId = resultado
    ? (resultado.modelos.find((m) => m.algoritmo === resultado.criterio?.elegido)
        ?.id ?? null)
    : null

  return (
    <div>
      <div className="pagina-cabecera">
        <div>
          <h1>Entrenar modelos</h1>
          <p className="conteo">
            {estado
              ? `${estado.filas} campañas con datos · mínimo ${estado.minimo_entrenamiento} para entrenar`
              : 'Sin datos'}
          </p>
        </div>
        <div className="ficha-acciones">
          <button
            type="button"
            className="boton-primario"
            disabled={!listo || hayActiva}
            title={
              !listo
                ? 'Faltan campañas con datos suficientes'
                : hayActiva
                  ? 'Ya hay un entrenamiento en curso'
                  : 'Pedir un nuevo entrenamiento (máximo 5 por día)'
            }
            onClick={() => setConfirmarAlta(true)}
          >
            Entrenar ahora
          </button>
        </div>
      </div>

      {estado?.datos_demostracion && <BannerDemostracion />}

      <p className="texto-intro">
        El sistema lee la vista de datos del módulo (sin archivos), entrena
        los tres algoritmos con el criterio escrito y guarda el modelo en la
        base de datos. Solo puede haber un entrenamiento a la vez y hasta 5
        por día; el progreso se consulta mientras hay tarea en curso.
      </p>

      <Aviso>{error}</Aviso>

      {estado && (
        <div className="panel">
          <h2>Datos para entrenar</h2>
          <dl className="datos-rejilla">
            <div>
              <dt>Campañas aptas</dt>
              <dd>{estado.filas}</dd>
            </div>
            <div>
              <dt>Mínimo</dt>
              <dd>{estado.minimo_entrenamiento}</dd>
            </div>
            <div>
              <dt>Listo</dt>
              <dd>
                <Chip>{listo ? 'DATOS SUFICIENTES' : 'FALTAN DATOS'}</Chip>
              </dd>
            </div>
            <div>
              <dt>Origen del sello</dt>
              <dd>
                <Chip>{estado.origen_datos}</Chip>
              </dd>
            </div>
          </dl>
        </div>
      )}

      {activa && (
        <div className="panel">
          <h2>
            Entrenamiento en curso <Chip>{activa.estado}</Chip>
          </h2>
          <div className="barra-progreso" role="progressbar"
            aria-valuenow={pct} aria-valuemin="0" aria-valuemax="100"
            aria-label="Progreso del entrenamiento"
          >
            <span style={{ width: `${pct}%` }} />
          </div>
          <p className="conteo">
            {pct}% · {activa.progreso?.etapa ?? 'en cola'} · actividad{' '}
            {haceCuanto(activa.latido) || 'sin latido aún'} · pedido por{' '}
            {activa.usuario} el {fechaHoraCorta(activa.creado_en)}
          </p>
          <button
            type="button"
            className="boton-texto"
            onClick={() => setCancelarId(activa.id)}
          >
            Cancelar
          </button>
        </div>
      )}

      {resultado && (
        <div className="panel">
          <div className="pagina-cabecera">
            <div>
              <h2>Resultados del entrenamiento</h2>
              <p className="conteo">
                {fechaHoraCorta(resultado.fecha)} · {resultado.n_registros}{' '}
                campañas · {resultado.n_entrenamiento} de entrenamiento y{' '}
                {resultado.n_prueba} de prueba
              </p>
            </div>
            <div className="ficha-acciones">
              <button
                type="button"
                className="boton-texto"
                onClick={() => setResultadoId(null)}
              >
                Ocultar
              </button>
            </div>
          </div>

          {resultado.datos_demostracion && <BannerDemostracion />}

          <p className="texto-intro">
            El criterio escrito (docs/criterio_seleccion.md):{' '}
            {resultado.criterio?.motivo || 'sin veredicto registrado'}.
          </p>

          <Tabla
            filas={resultado.modelos}
            columnas={[
              {
                clave: 'algoritmo',
                etiqueta: 'Algoritmo',
                celda: (fila) =>
                  fila.algoritmo.replaceAll('_', ' ').toLowerCase(),
              },
              { clave: 'version', etiqueta: 'Versión', celda: (fila) => fila.version },
              { clave: 'mae', etiqueta: 'MAE', celda: (fila) => numero(fila.mae) },
              { clave: 'rmse', etiqueta: 'RMSE', celda: (fila) => numero(fila.rmse) },
              { clave: 'r2', etiqueta: 'R²', celda: (fila) => numero(fila.r2, 4) },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => (
                  <Chip>
                    {fila.activo
                      ? 'ACTIVO'
                      : fila.algoritmo === resultado.criterio?.elegido
                        ? 'RECOMENDADO'
                        : 'Inactivo'}
                  </Chip>
                ),
              },
              {
                clave: 'artefacto',
                etiqueta: 'Artefacto',
                celda: (fila) => (fila.en_bd ? 'En la BD' : 'Archivo'),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) =>
                  fila.id === elegidoId &&
                  !fila.activo &&
                  tienePermiso('ml.activar_modelo') ? (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setActivarId(fila.id)}
                    >
                      Activar este modelo
                    </button>
                  ) : (
                    '—'
                  ),
              },
            ]}
          />
        </div>
      )}

      <div className="pagina-cabecera">
        <div>
          <h2>Historial</h2>
          <p className="conteo">
            {historial
              ? `${historial.count} tarea(s) · máximo visible en la primera página`
              : 'Sin datos'}
          </p>
        </div>
      </div>

      {tareas.length === 0 ? (
        <div className="panel">
          <p>
            Aún no hay entrenamientos: usa «Entrenar ahora» para pedir el
            primero.
          </p>
        </div>
      ) : (
        <Tabla
          filas={tareas}
          columnas={[
            {
              clave: 'creado',
              etiqueta: 'Pedido',
              celda: (fila) => fechaHoraCorta(fila.creado_en),
            },
            {
              clave: 'estado',
              etiqueta: 'Estado',
              celda: (fila) => <Chip>{fila.estado}</Chip>,
            },
            {
              clave: 'progreso',
              etiqueta: 'Progreso',
              celda: (fila) =>
                `${fila.progreso?.pct ?? 0}% · ${fila.progreso?.etapa ?? 'en cola'}`,
            },
            {
              clave: 'latido',
              etiqueta: 'Actividad',
              celda: (fila) => haceCuanto(fila.latido) || '—',
            },
            { clave: 'usuario', etiqueta: 'Usuario', celda: (fila) => fila.usuario },
            {
              clave: 'detalle',
              etiqueta: 'Detalle',
              celda: (fila) => fila.error || fila.observacion || '—',
            },
            {
              clave: 'acciones',
              etiqueta: 'Acciones',
              acciones: true,
              celda: (fila) =>
                ACTIVAS.includes(fila.estado) ? (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => setCancelarId(fila.id)}
                  >
                    Cancelar
                  </button>
                ) : fila.estado === 'COMPLETADA' && fila.resultado ? (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => setResultadoId(fila.resultado)}
                  >
                    Ver resultados
                  </button>
                ) : (
                  '—'
                ),
            },
          ]}
        />
      )}

      <Modal
        abierto={confirmarAlta}
        titulo="Pedir un entrenamiento"
        texto={
          estado
            ? `Se entrenarán los tres algoritmos con ${estado.filas} campañas de la vista del sistema y el resultado quedará en la base de datos. Solo puede haber un entrenamiento a la vez y máximo 5 por día. ¿Continuar?`
            : ''
        }
        confirmar="Entrenar"
        ocupado={creando}
        onConfirmar={alta}
        onCerrar={() => setConfirmarAlta(false)}
      />

      <Modal
        abierto={cancelarId !== null}
        titulo="Cancelar el entrenamiento"
        texto="La tarea se marcará como cancelada y el trabajador detendrá el proceso en curso. Los entrenamientos ya terminados no se afectan. ¿Continuar?"
        confirmar="Cancelar tarea"
        nivel="peligro"
        ocupado={cancelando}
        onConfirmar={cancelar}
        onCerrar={() => setCancelarId(null)}
      />

      <Modal
        abierto={activarId !== null}
        titulo="Activar este modelo"
        texto="El modelo recomendado pasará a ser el vigente para todas las predicciones (el actual se desactiva). Se verifica la huella del contenido guardado y se hace una predicción de prueba antes de cambiarlo. ¿Continuar?"
        confirmar="Activar"
        ocupado={activando}
        onConfirmar={activar}
        onCerrar={() => setActivarId(null)}
      />
    </div>
  )
}
