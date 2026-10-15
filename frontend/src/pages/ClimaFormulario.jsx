import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import { guardarClima, obtenerClima } from '../api/clima.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  parcela: '',
  fecha: '',
  temp_min: '',
  temp_max: '',
  temp_prom: '',
  precipitacion_mm: '',
  humedad_pct: '',
  viento_ms: '',
  radiacion_mj: '',
  helada: false,
}

function hoyLima() {
  // La API rechaza fechas futuras según la hora local de Lima (pregunta H)
  const ahora = new Date()
  const fecha = new Date(ahora.getTime() - 5 * 60 * 60 * 1000)
  return fecha.toISOString().slice(0, 10)
}

export default function ClimaFormulario({
  id,
  parcelaInicial = '',
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(() => ({
    ...VACIO,
    parcela: parcelaInicial ? String(parcelaInicial) : '',
  }))
  const [parcelas, setParcelas] = useState([])
  const [registro, setRegistro] = useState(null)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)
  const [confirmar, setConfirmar] = useState(false)

  const cargando = !listo || !hidratado
  const maxFecha = hoyLima()
  const heladaDerivada = form.temp_min.trim() !== ''
  const esRegistroApi = esEdicion && registro?.fuente === 'API'

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    listarTodo('/parcelas/', { desplegable: 1 })
      .then((lista) => activo && setParcelas(lista))
      .catch(() => {})
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerClima(id)
      .then((clima) => {
        if (!activo) return
        setForm({
          parcela: String(clima.parcela.id),
          fecha: clima.fecha,
          temp_min: clima.temp_min ?? '',
          temp_max: clima.temp_max ?? '',
          temp_prom: clima.temp_prom ?? '',
          precipitacion_mm: clima.precipitacion_mm ?? '',
          humedad_pct: clima.humedad_pct ?? '',
          viento_ms: clima.viento_ms ?? '',
          radiacion_mj: clima.radiacion_mj ?? '',
          helada: Boolean(clima.helada),
        })
        setRegistro(clima)
        setError(null)
        setHidratado(true)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setHidratado(true)
      })
    return () => {
      activo = false
    }
  }, [id, esEdicion])

  function medida(campo) {
    return form[campo].trim() === '' ? null : form[campo].trim()
  }

  function validarCliente() {
    const fallos = {}
    if (!form.parcela) fallos.parcela = 'La parcela es obligatoria.'
    if (!form.fecha) {
      fallos.fecha = 'La fecha es obligatoria.'
    } else if (form.fecha > maxFecha) {
      fallos.fecha = 'La fecha no puede ser futura.'
    } else if (form.fecha < '2000-01-01') {
      fallos.fecha = 'La fecha no puede ser anterior al 1 de enero de 2000.'
    }
    const minima = medida('temp_min')
    const maxima = medida('temp_max')
    if (minima !== null && (Number(minima) < -30 || Number(minima) > 45)) {
      fallos.temp_min = 'La temperatura mínima debe estar entre -30 y 45 °C.'
    }
    if (maxima !== null && (Number(maxima) < -30 || Number(maxima) > 45)) {
      fallos.temp_max = 'La temperatura máxima debe estar entre -30 y 45 °C.'
    }
    if (minima !== null && maxima !== null && Number(minima) > Number(maxima)) {
      fallos.temp_min = 'La mínima no puede ser mayor que la máxima.'
    }
    const promedio = medida('temp_prom')
    if (promedio !== null && (Number(promedio) < -30 || Number(promedio) > 45)) {
      fallos.temp_prom = 'La temperatura promedio debe estar entre -30 y 45 °C.'
    }
    if (medida('precipitacion_mm') !== null && Number(medida('precipitacion_mm')) < 0) {
      fallos.precipitacion_mm = 'La precipitación no puede ser negativa.'
    }
    const humedad = medida('humedad_pct')
    if (humedad !== null && (Number(humedad) < 0 || Number(humedad) > 100)) {
      fallos.humedad_pct = 'La humedad debe estar entre 0 y 100 %.'
    }
    if (medida('viento_ms') !== null && Number(medida('viento_ms')) < 0) {
      fallos.viento_ms = 'El viento no puede ser negativo.'
    }
    if (medida('radiacion_mj') !== null && Number(medida('radiacion_mj')) < 0) {
      fallos.radiacion_mj = 'La radiación no puede ser negativa.'
    }
    const algunaMedida = [
      minima,
      maxima,
      promedio,
      medida('precipitacion_mm'),
      humedad,
      medida('viento_ms'),
      medida('radiacion_mj'),
    ].some((valor) => valor !== null)
    if (!algunaMedida && !form.helada) {
      fallos.helada = (
        'Indica al menos una medida meteorológica o marca la helada.'
      )
    }
    return fallos
  }

  async function enviar(event) {
    event.preventDefault()
    setErrores({})
    setError(null)

    const fallos = validarCliente()
    if (Object.keys(fallos).length > 0) {
      setErrores(fallos)
      return
    }

    const datos = {
      parcela: Number(form.parcela),
      fecha: form.fecha,
      temp_min: medida('temp_min'),
      temp_max: medida('temp_max'),
      temp_prom: medida('temp_prom'),
      precipitacion_mm: medida('precipitacion_mm'),
      humedad_pct: medida('humedad_pct'),
      viento_ms: medida('viento_ms'),
      radiacion_mj: medida('radiacion_mj'),
      helada: heladaDerivada ? false : Boolean(form.helada),
    }
    if (esRegistroApi) datos.confirmar_reemplazo = confirmar

    setGuardando(true)
    try {
      const guardado = await guardarClima(id, datos)
      avisar(
        esEdicion ? 'Registro de clima guardado.' : 'Registro de clima creado.',
      )
      onGuardado?.(guardado)
    } catch (e) {
      if (e.response?.status === 400) {
        const campos = erroresDeCampo(e.response.data)
        setErrores(campos)
        if (Object.keys(campos).length > 0) return
      }
      avisar(mensajeDeError(e), 'error')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo={esEdicion ? 'Editar registro de clima' : 'Registrar clima'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos del registro</h2>
            <Campo
              id="parcela"
              etiqueta="Parcela"
              error={errores.parcela}
              ayuda="Una sola fila por parcela y día."
            >
              <select
                id="parcela"
                value={form.parcela}
                disabled={esEdicion}
                onChange={(e) => cambiar('parcela', e.target.value)}
              >
                <option value="">Elige una parcela</option>
                {parcelas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.codigo} — {p.productor.nombre_completo}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="fecha"
              etiqueta="Fecha"
              error={errores.fecha}
              ayuda="No puede ser futura (hora de Lima)."
            >
              <input
                id="fecha"
                type="date"
                max={maxFecha}
                value={form.fecha}
                onChange={(e) => cambiar('fecha', e.target.value)}
              />
            </Campo>
            {esRegistroApi && (
              <Campo
                id="confirmar-reemplazo"
                etiqueta="Reemplazar registro de la API"
                error={errores.confirmar_reemplazo}
                ayuda="Este registro proviene de la API meteorológica: al guardarlo quedará como MANUAL."
              >
                <label>
                  <input
                    id="confirmar-reemplazo"
                    type="checkbox"
                    checked={confirmar}
                    onChange={(e) => setConfirmar(e.target.checked)}
                  />
                  {' '}Entiendo que este registro pasará a MANUAL
                </label>
              </Campo>
            )}
          </section>

          <section className="panel">
            <h2>Temperaturas (°C)</h2>
            <Campo
              id="temp_min"
              etiqueta="Mínima"
              error={errores.temp_min}
              ayuda="Entre -30 y 45 °C. Si hay mínima, la helada la deriva el servidor del umbral del sistema."
            >
              <input
                id="temp_min"
                inputMode="decimal"
                placeholder="5.0"
                value={form.temp_min}
                onChange={(e) => cambiar('temp_min', e.target.value)}
              />
            </Campo>
            <Campo
              id="temp_max"
              etiqueta="Máxima"
              error={errores.temp_max}
              ayuda="Entre -30 y 45 °C y no menor que la mínima."
            >
              <input
                id="temp_max"
                inputMode="decimal"
                placeholder="15.0"
                value={form.temp_max}
                onChange={(e) => cambiar('temp_max', e.target.value)}
              />
            </Campo>
            <Campo
              id="temp_prom"
              etiqueta="Promedio (opcional)"
              error={errores.temp_prom}
              ayuda="Déjalo vacío y el servidor guardará el punto medio de mínima y máxima."
            >
              <input
                id="temp_prom"
                inputMode="decimal"
                placeholder="10.0"
                value={form.temp_prom}
                onChange={(e) => cambiar('temp_prom', e.target.value)}
              />
            </Campo>
          </section>

          <section className="panel">
            <h2>Otras medidas</h2>
            <Campo
              id="precipitacion_mm"
              etiqueta="Precipitación (mm)"
              error={errores.precipitacion_mm}
              ayuda="Acumulado del día, sin valores negativos."
            >
              <input
                id="precipitacion_mm"
                inputMode="decimal"
                placeholder="12.5"
                value={form.precipitacion_mm}
                onChange={(e) => cambiar('precipitacion_mm', e.target.value)}
              />
            </Campo>
            <Campo
              id="humedad_pct"
              etiqueta="Humedad (%)"
              error={errores.humedad_pct}
              ayuda="Entre 0 y 100 %."
            >
              <input
                id="humedad_pct"
                inputMode="decimal"
                placeholder="75"
                value={form.humedad_pct}
                onChange={(e) => cambiar('humedad_pct', e.target.value)}
              />
            </Campo>
            <Campo
              id="viento_ms"
              etiqueta="Viento máximo (m/s)"
              error={errores.viento_ms}
              ayuda="Velocidad máxima del día en metros por segundo."
            >
              <input
                id="viento_ms"
                inputMode="decimal"
                placeholder="4.2"
                value={form.viento_ms}
                onChange={(e) => cambiar('viento_ms', e.target.value)}
              />
            </Campo>
            <Campo
              id="radiacion_mj"
              etiqueta="Radiación (MJ/m²)"
              error={errores.radiacion_mj}
              ayuda="Radiación solar acumulada del día."
            >
              <input
                id="radiacion_mj"
                inputMode="decimal"
                placeholder="18.5"
                value={form.radiacion_mj}
                onChange={(e) => cambiar('radiacion_mj', e.target.value)}
              />
            </Campo>
            <Campo
              id="helada"
              etiqueta="Helada"
              error={errores.helada}
              ayuda={
                heladaDerivada
                  ? 'Con temperatura mínima, el servidor marca la helada según el umbral del sistema.'
                  : 'Márcala si hubo helada y no registras la temperatura mínima.'
              }
            >
              <label>
                <input
                  id="helada"
                  type="checkbox"
                  checked={heladaDerivada ? false : form.helada}
                  disabled={heladaDerivada}
                  onChange={(e) => cambiar('helada', e.target.checked)}
                />
                {' '}Hubo helada este día
              </label>
            </Campo>
          </section>

          <div className="formulario-acciones">
            <button
              className="boton-primario"
              type="submit"
              disabled={guardando}
            >
              {guardando ? (
                <>
                  <RuedaCarga etiqueta="Guardando…" />
                  Guardando…
                </>
              ) : esEdicion ? (
                'Guardar cambios'
              ) : (
                'Registrar clima'
              )}
            </button>
            <button
              className="boton-secundario"
              type="button"
              onClick={onCancelar}
            >
              {esEdicion ? 'Cerrar' : 'Cancelar'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}
