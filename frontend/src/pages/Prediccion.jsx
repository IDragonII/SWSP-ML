import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import {
  listarCampaniasPredecibles,
  modeloActivo,
  predecir,
} from '../api/ml.js'
import Aviso from '../components/Aviso.jsx'
import BannerDemostracion from '../components/BannerDemostracion.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'
import { useSesion } from '../context/useSesion.js'

const CLAVES_FORM = ['semilla', 'fertilizante', 'mano_de_obra', 'agua']
const VACIOS = { semilla: '', fertilizante: '', mano_de_obra: '', agua: '' }

const CAMPOS = [
  ['semilla', 'Semilla (kg/ha)'],
  ['fertilizante', 'Fertilizante (kg/ha)'],
  ['mano_de_obra', 'Mano de obra (jornales/ha)'],
  ['agua', 'Agua (m³/ha)'],
]

function etiquetaCampania(campania) {
  const parcela = `${campania.parcela.codigo} · ${campania.parcela.productor.nombre_completo}`
  const cultivo = `${campania.cultivo} ${campania.variedad ?? ''}`.trim()
  const ha = Number(campania.superficie_sembrada_ha).toLocaleString('es-PE')
  return `${parcela} · ${cultivo} · ${campania.periodo} · ${ha} ha`
}

export default function Prediccion() {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [params, setParams] = useSearchParams()
  const campania = params.get('campania') ?? ''

  const [candidatas, setCandidatas] = useState(null)
  const [demostracion, setDemostracion] = useState(false)
  const [campos, setCampos] = useState(VACIOS)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [predecindo, setPredecindo] = useState(false)
  const [resultado, setResultado] = useState(null)

  const puedePredecir = tienePermiso('ml.predecir')

  useEffect(() => {
    let activo = true
    listarCampaniasPredecibles()
      .then((respuesta) => {
        if (!activo) return
        setError(null)
        setCandidatas(respuesta)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setCandidatas({ count: 0, results: [] })
      })
    // El banner de demostración lo puede leer quien ve modelos (240);
    // el resto lo ve junto al resultado, que trae la marca
    if (tienePermiso('ml.ver_modelos')) {
      modeloActivo()
        .then((m) => activo && setDemostracion(Boolean(m.datos_demostracion)))
        .catch(() => {})
    }
    return () => {
      activo = false
    }
  }, [tienePermiso])

  async function enviar(evento) {
    evento.preventDefault()
    if (!campania) {
      setError('Elige una campaña para predecir.')
      return
    }
    setPredecindo(true)
    setError(null)
    setErrores({})
    const datos = { campania: Number(campania) }
    for (const clave of CLAVES_FORM) {
      if (campos[clave] !== '') datos[clave] = campos[clave]
    }
    try {
      const prediccion = await predecir(datos)
      setResultado(prediccion)
      setDemostracion(Boolean(prediccion.datos_demostracion))
      avisar('Predicción guardada en el historial.')
    } catch (e) {
      const porCampo = Object.fromEntries(
        Object.entries(erroresDeCampo(e.response?.data)).filter(([clave]) =>
          CLAVES_FORM.includes(clave),
        ),
      )
      setErrores(porCampo)
      setError(
        Object.keys(porCampo).length === 0 ? mensajeDeError(e) : null,
      )
    } finally {
      setPredecindo(false)
    }
  }

  if (!candidatas && !error) return <Cargando texto="Cargando campañas…" />

  return (
    <div>
      <div className="pagina-cabecera">
        <div>
          <h1>Predicción de rendimiento</h1>
          <p className="conteo">
            Estima el rendimiento (kg/ha) de una campaña con el modelo
            activo, antes de cosechar.
          </p>
        </div>
      </div>

      {demostracion && <BannerDemostracion />}

      <form className="formulario" onSubmit={enviar}>
        <Campo
          id="prediccion-campania"
          etiqueta="Campaña"
          ayuda="Solo campañas planificadas o en producción; para el técnico, solo las de sus productores."
          error={error && !campania ? error : null}
        >
          <select
            id="prediccion-campania"
            value={campania}
            onChange={(evento) => {
              const siguiente = new URLSearchParams(params)
              if (evento.target.value) siguiente.set('campania', evento.target.value)
              else siguiente.delete('campania')
              setParams(siguiente)
            }}
          >
            <option value="">
              {candidatas?.count
                ? `Elige una campaña (${candidatas.count})`
                : 'No hay campañas predecibles'}
            </option>
            {candidatas?.results.map((fila) => (
              <option key={fila.id} value={fila.id}>
                {etiquetaCampania(fila)}
              </option>
            ))}
          </select>
        </Campo>

        <div className="filtros">
          {CAMPOS.map(([clave, etiqueta]) => (
            <Campo
              key={clave}
              id={`prediccion-${clave}`}
              etiqueta={etiqueta}
              ayuda="Opcional: lo dejes vacío y se usa lo registrado en la campaña."
              error={errores[clave]}
            >
              <input
                id={`prediccion-${clave}`}
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={campos[clave]}
                onChange={(evento) =>
                  setCampos({ ...campos, [clave]: evento.target.value })
                }
              />
            </Campo>
          ))}
        </div>

        <Aviso>{error}</Aviso>

        <div className="filtros-acciones">
          <button
            className="boton-primario"
            type="submit"
            disabled={!puedePredecir || predecindo || !campania}
          >
            {predecindo ? (
              <>
                <RuedaCarga etiqueta="Prediciendo…" />
                Prediciendo…
              </>
            ) : (
              'Predecir'
            )}
          </button>
        </div>
      </form>

      {resultado && (
        <section className="panel" aria-label="Resultado de la predicción">
          <h2>Resultado</h2>
          <p className="resultado-prediccion">
            {Number(resultado.rendimiento_predicho).toLocaleString('es-PE', {
              maximumFractionDigits: 2,
            })}{' '}
            <span className="resultado-unidad">kg/ha</span>
          </p>
          <div className="resultado-datos">
            <span>
              <strong>Producción estimada:</strong>{' '}
              {resultado.produccion_estimada_kg === null
                ? '—'
                : `${Number(resultado.produccion_estimada_kg).toLocaleString('es-PE', { maximumFractionDigits: 2 })} kg`}
            </span>
            <span>
              <strong>Confiabilidad:</strong> <Chip>{resultado.confiabilidad}</Chip>
            </span>
            <span>
              <strong>Modelo:</strong> {resultado.modelo.algoritmo} v
              {resultado.modelo.version} (MAE {resultado.modelo.mae})
            </span>
          </div>
          {resultado.datos_demostracion && <BannerDemostracion />}
          <p className="nota">{resultado.texto_estimacion}</p>
          {resultado.avisos.length > 0 && (
            <ul>
              {resultado.avisos.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
