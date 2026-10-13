import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import {
  UNIDADES_DENSIDAD,
  guardarActividad,
  obtenerActividad,
} from '../api/actividades.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  campania: '',
  tipo_actividad: '',
  fecha: '',
  metodo: '',
  densidad_siembra: '',
  densidad_unidad: '',
  horas: '',
  costo: '',
  observaciones: '',
}

function hoyLima() {
  // La API rechaza fechas futuras según la hora local de Lima (pregunta H)
  const ahora = new Date()
  const fecha = new Date(ahora.getTime() - 5 * 60 * 60 * 1000)
  return fecha.toISOString().slice(0, 10)
}

export default function ActividadFormulario({
  id,
  campaniaInicial = '',
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(() => ({
    ...VACIO,
    campania: campaniaInicial,
  }))
  const [campanias, setCampanias] = useState([])
  const [tipos, setTipos] = useState([])
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado
  const campaniaActual = campanias.find(
    (c) => String(c.id) === String(form.campania),
  )
  const tipoActual = tipos.find((t) => String(t.id) === String(form.tipo_actividad))
  const esSiembra = tipoActual?.codigo === 'SIEMBRA'
  const maxFecha = hoyLima()

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    const filtrosCampanias = { desplegable: 1 }
    Promise.all([
      listarTodo('/campanias/', filtrosCampanias),
      listarTodo('/tipos-actividad/', { activo: 'true' }),
    ])
      .then(([listaCampanias, listaTipos]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setTipos(listaTipos)
      })
      .catch(() => {})
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerActividad(id)
      .then((actividad) => {
        if (!activo) return
        setForm({
          campania: String(actividad.campania.id),
          tipo_actividad: String(actividad.tipo_actividad.id),
          fecha: actividad.fecha,
          metodo: actividad.metodo ?? '',
          densidad_siembra:
            actividad.densidad_siembra === null
              ? ''
              : String(actividad.densidad_siembra),
          densidad_unidad: actividad.densidad_unidad ?? '',
          horas: actividad.horas === null ? '' : String(actividad.horas),
          costo: actividad.costo === null ? '' : String(actividad.costo),
          observaciones: actividad.observaciones ?? '',
        })
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

  function validarCliente() {
    const fallos = {}
    if (!form.campania) fallos.campania = 'La campaña es obligatoria.'
    if (!form.tipo_actividad) {
      fallos.tipo_actividad = 'El tipo de actividad es obligatorio.'
    }
    if (!form.fecha) {
      fallos.fecha = 'La fecha es obligatoria.'
    } else if (form.fecha > maxFecha) {
      fallos.fecha = 'La fecha no puede ser futura.'
    } else if (
      campaniaActual &&
      (form.fecha < campaniaActual.fecha_inicio ||
        form.fecha > campaniaActual.fecha_fin_prevista)
    ) {
      fallos.fecha = `La fecha debe estar dentro del período de la campaña (${campaniaActual.fecha_inicio} a ${campaniaActual.fecha_fin_prevista}).`
    }
    if (esSiembra) {
      const tieneDensidad = Boolean(form.densidad_siembra.trim())
      const tieneUnidad = Boolean(form.densidad_unidad)
      if (tieneDensidad !== tieneUnidad) {
        fallos.densidad_siembra =
          'La densidad de siembra y su unidad deben ir juntas (o dejar ambas vacías).'
      } else if (tieneDensidad && Number(form.densidad_siembra) <= 0) {
        fallos.densidad_siembra = 'La densidad de siembra debe ser mayor que 0.'
      }
    }
    if (form.horas.trim() && Number(form.horas) < 0) {
      fallos.horas = 'Las horas no pueden ser negativas.'
    }
    if (form.costo.trim() && Number(form.costo) < 0) {
      fallos.costo = 'El costo no puede ser negativo.'
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

    // En edición la campaña y el tipo no viajan: la API los rechaza aunque
    // el valor sea el mismo (anula y registra otra actividad)
    const datos = {
      fecha: form.fecha,
      metodo: form.metodo.trim(),
      horas: form.horas.trim() || null,
      costo: form.costo.trim() || null,
      observaciones: form.observaciones.trim(),
    }
    if (!esEdicion) {
      datos.campania = Number(form.campania)
      datos.tipo_actividad = Number(form.tipo_actividad)
    }
    if (esSiembra && form.densidad_siembra.trim()) {
      datos.densidad_siembra = form.densidad_siembra.trim()
      datos.densidad_unidad = form.densidad_unidad
    }

    setGuardando(true)
    try {
      const guardada = await guardarActividad(id, datos)
      const campania = guardada.campania
      if (
        !esEdicion &&
        campania?.estado === 'EN_PRODUCCION' &&
        campania?.fecha_siembra
      ) {
        avisar(
          `Actividad registrada. La campaña pasó a EN_PRODUCCION (fecha de siembra: ${campania.fecha_siembra}).`,
        )
      } else {
        avisar(esEdicion ? 'Actividad guardada.' : 'Actividad creada.')
      }
      onGuardado?.(guardada)
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
      titulo={esEdicion ? 'Editar actividad' : 'Nueva actividad'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos de la actividad</h2>
            <Campo
              id="campania"
              etiqueta="Campaña"
              error={errores.campania}
              ayuda={
                campaniaActual
                  ? `Período de la campaña: ${campaniaActual.fecha_inicio} a ${campaniaActual.fecha_fin_prevista}.`
                  : 'Elige la campaña donde se registra la actividad.'
              }
            >
              <select
                id="campania"
                value={form.campania}
                disabled={esEdicion}
                onChange={(e) => cambiar('campania', e.target.value)}
              >
                <option value="">Elige una campaña</option>
                {campanias.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.parcela.productor.nombre_completo} — {c.parcela.codigo} —{' '}
                    {c.cultivo.nombre} ({c.periodo})
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="tipo_actividad"
              etiqueta="Tipo de actividad"
              error={errores.tipo_actividad}
              ayuda={
                esSiembra
                  ? 'Al elegir SIEMBRA, la campaña pasa a EN_PRODUCCION y queda fijada su fecha de siembra.'
                  : undefined
              }
            >
              <select
                id="tipo_actividad"
                value={form.tipo_actividad}
                disabled={esEdicion}
                onChange={(e) => cambiar('tipo_actividad', e.target.value)}
              >
                <option value="">Elige un tipo</option>
                {tipos.map((tipo) => (
                  <option key={tipo.id} value={tipo.id}>
                    {tipo.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="fecha"
              etiqueta="Fecha"
              error={errores.fecha}
              ayuda="No puede ser futura y debe caer dentro del período de la campaña."
            >
              <input
                id="fecha"
                type="date"
                max={maxFecha}
                value={form.fecha}
                onChange={(e) => cambiar('fecha', e.target.value)}
              />
            </Campo>
            <Campo id="metodo" etiqueta="Método" error={errores.metodo}>
              <input
                id="metodo"
                placeholder="Arado de disco, aspersión manual…"
                value={form.metodo}
                onChange={(e) => cambiar('metodo', e.target.value)}
              />
            </Campo>
            {esSiembra && (
              <>
                <Campo
                  id="densidad_siembra"
                  etiqueta="Densidad de siembra"
                  error={errores.densidad_siembra}
                  ayuda="Valor y unidad deben ir juntos (o dejar ambos vacíos)."
                >
                  <input
                    id="densidad_siembra"
                    inputMode="decimal"
                    placeholder="80"
                    value={form.densidad_siembra}
                    onChange={(e) =>
                      cambiar('densidad_siembra', e.target.value)
                    }
                  />
                </Campo>
                <Campo
                  id="densidad_unidad"
                  etiqueta="Unidad de densidad"
                  error={errores.densidad_unidad}
                >
                  <select
                    id="densidad_unidad"
                    value={form.densidad_unidad}
                    onChange={(e) =>
                      cambiar('densidad_unidad', e.target.value)
                    }
                  >
                    <option value="">Elige una unidad</option>
                    {UNIDADES_DENSIDAD.map(([valor, etiqueta]) => (
                      <option key={valor} value={valor}>
                        {etiqueta}
                      </option>
                    ))}
                  </select>
                </Campo>
              </>
            )}
          </section>

          <section className="panel">
            <h2>Esfuerzo y observaciones</h2>
            <Campo
              id="horas"
              etiqueta="Horas de trabajo"
              error={errores.horas}
              ayuda="Jornales o horas-hombre dedicadas."
            >
              <input
                id="horas"
                inputMode="decimal"
                placeholder="7.5"
                value={form.horas}
                onChange={(e) => cambiar('horas', e.target.value)}
              />
            </Campo>
            <Campo
              id="costo"
              etiqueta="Costo (S/)"
              error={errores.costo}
              ayuda="Costo total de la actividad en soles."
            >
              <input
                id="costo"
                inputMode="decimal"
                placeholder="120.50"
                value={form.costo}
                onChange={(e) => cambiar('costo', e.target.value)}
              />
            </Campo>
            <Campo
              id="observaciones"
              etiqueta="Observaciones"
              error={errores.observaciones}
            >
              <textarea
                id="observaciones"
                rows={3}
                value={form.observaciones}
                onChange={(e) => cambiar('observaciones', e.target.value)}
              />
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
                'Crear actividad'
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
