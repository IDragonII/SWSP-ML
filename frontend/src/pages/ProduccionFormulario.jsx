import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import {
  CALIDADES,
  guardarProduccion,
  obtenerProduccion,
} from '../api/produccion.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  campania: '',
  fecha_cosecha: '',
  superficie_cosechada_ha: '',
  cantidad_producida: '',
  unidad: '',
  perdida_kg: '',
  calidad: '',
  observaciones: '',
}

export default function ProduccionFormulario({
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
  const [campaniaEdicion, setCampaniaEdicion] = useState(null)
  const [unidades, setUnidades] = useState([])
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado
  const campaniaActual = esEdicion
    ? campaniaEdicion
    : campanias.find((c) => String(c.id) === String(form.campania))

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    Promise.all([
      esEdicion
        ? Promise.resolve([])
        : listarTodo('/campanias/', { produccion: 1, desplegable: 1 }),
      listarTodo('/unidades/', { tipo: 'MASA', activo: 'true' }),
    ])
      .then(([listaCampanias, listaUnidades]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setUnidades(listaUnidades)
      })
      .catch(() => {})
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [esEdicion])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerProduccion(id)
      .then((produccion) => {
        if (!activo) return
        setForm({
          campania: String(produccion.campania.id),
          fecha_cosecha: produccion.fecha_cosecha,
          superficie_cosechada_ha: String(produccion.superficie_cosechada_ha),
          cantidad_producida: String(produccion.cantidad_producida),
          unidad: String(produccion.unidad.id),
          perdida_kg:
            produccion.perdida_kg === null
              ? ''
              : String(produccion.perdida_kg),
          calidad: produccion.calidad ?? '',
          observaciones: produccion.observaciones ?? '',
        })
        setCampaniaEdicion({
          id: produccion.campania.id,
          fecha_inicio: produccion.campania.fecha_siembra,
          fecha_siembra: produccion.campania.fecha_siembra,
          superficie_sembrada_ha: produccion.campania.superficie_sembrada_ha,
          cultivo: produccion.campania.cultivo,
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
    if (!form.fecha_cosecha) {
      fallos.fecha_cosecha = 'La fecha de cosecha es obligatoria.'
    } else if (
      campaniaActual?.fecha_siembra &&
      form.fecha_cosecha < campaniaActual.fecha_siembra
    ) {
      fallos.fecha_cosecha = `La fecha de cosecha no puede ser anterior a la fecha de siembra (${campaniaActual.fecha_siembra}).`
    } else if (
      campaniaActual &&
      form.fecha_cosecha < campaniaActual.fecha_inicio
    ) {
      fallos.fecha_cosecha = `La fecha de cosecha no puede ser anterior al inicio de la campaña (${campaniaActual.fecha_inicio}).`
    }
    if (!form.superficie_cosechada_ha.trim()) {
      fallos.superficie_cosechada_ha = 'La superficie cosechada es obligatoria.'
    } else if (Number(form.superficie_cosechada_ha) <= 0) {
      fallos.superficie_cosechada_ha =
        'La superficie cosechada debe ser mayor que 0.'
    } else if (
      campaniaActual &&
      Number(form.superficie_cosechada_ha) >
        Number(campaniaActual.superficie_sembrada_ha)
    ) {
      fallos.superficie_cosechada_ha = `La superficie cosechada no puede superar la sembrada (${campaniaActual.superficie_sembrada_ha} ha).`
    }
    if (!form.cantidad_producida.trim()) {
      fallos.cantidad_producida = 'La cantidad producida es obligatoria.'
    } else if (Number(form.cantidad_producida) < 0) {
      fallos.cantidad_producida = 'La cantidad producida no puede ser negativa.'
    }
    if (!form.unidad) fallos.unidad = 'La unidad es obligatoria.'
    if (form.perdida_kg.trim() && Number(form.perdida_kg) < 0) {
      fallos.perdida_kg = 'La pérdida no puede ser negativa.'
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

    // La campaña no cambia al editar (deshacer y registrar otra)
    const datos = {
      fecha_cosecha: form.fecha_cosecha,
      superficie_cosechada_ha: form.superficie_cosechada_ha.trim(),
      cantidad_producida: form.cantidad_producida.trim(),
      unidad: Number(form.unidad),
      perdida_kg: form.perdida_kg.trim() || null,
      calidad: form.calidad || null,
      observaciones: form.observaciones.trim(),
    }
    if (!esEdicion) {
      datos.campania = Number(form.campania)
    }

    setGuardando(true)
    try {
      const guardada = await guardarProduccion(id, datos)
      if (guardada.requiere_revision) {
        avisar(
          `Producción registrada: rendimiento atípico (${guardada.rendimiento_kg_ha} kg/ha), requiere revisión.`,
        )
      } else if (
        !esEdicion &&
        guardada.campania?.estado === 'COSECHADA'
      ) {
        avisar(
          `Producción registrada: ${guardada.produccion_kg} kg (${guardada.rendimiento_kg_ha} kg/ha). La campaña pasó a COSECHADA.`,
        )
      } else {
        avisar(esEdicion ? 'Producción guardada.' : 'Producción registrada.')
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
      titulo={esEdicion ? 'Editar producción' : 'Registrar producción'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos de la cosecha</h2>
            {!esEdicion && (
              <Campo
                id="campania"
                etiqueta="Campaña"
                error={errores.campania}
                ayuda={
                  campaniaActual
                    ? `Cultivo: ${campaniaActual.cultivo.nombre}. Superficie sembrada: ${campaniaActual.superficie_sembrada_ha} ha.`
                    : 'Solo aparecen las campañas en producción con siembra registrada y sin cosecha.'
                }
              >
                <select
                  id="campania"
                  value={form.campania}
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
            )}
            <Campo
              id="fecha_cosecha"
              etiqueta="Fecha de cosecha"
              error={errores.fecha_cosecha}
              ayuda="No puede ser anterior a la fecha de siembra ni al inicio de la campaña."
            >
              <input
                id="fecha_cosecha"
                type="date"
                value={form.fecha_cosecha}
                onChange={(e) => cambiar('fecha_cosecha', e.target.value)}
              />
            </Campo>
            <Campo
              id="superficie_cosechada_ha"
              etiqueta="Superficie cosechada (ha)"
              error={errores.superficie_cosechada_ha}
              ayuda={
                campaniaActual
                  ? `Como máximo la superficie sembrada (${campaniaActual.superficie_sembrada_ha} ha).`
                  : 'Debe ser mayor que 0 y no superar la superficie sembrada.'
              }
            >
              <input
                id="superficie_cosechada_ha"
                inputMode="decimal"
                placeholder="1.00"
                value={form.superficie_cosechada_ha}
                onChange={(e) =>
                  cambiar('superficie_cosechada_ha', e.target.value)
                }
              />
            </Campo>
          </section>

          <section className="panel">
            <h2>Rendimiento y calidad</h2>
            <Campo
              id="cantidad_producida"
              etiqueta="Cantidad producida"
              error={errores.cantidad_producida}
              ayuda="La cantidad en kg y el rendimiento kg/ha los calcula el sistema."
            >
              <input
                id="cantidad_producida"
                inputMode="decimal"
                placeholder="70"
                value={form.cantidad_producida}
                onChange={(e) => cambiar('cantidad_producida', e.target.value)}
              />
            </Campo>
            <Campo
              id="unidad"
              etiqueta="Unidad"
              error={errores.unidad}
              ayuda="Solo unidades de masa activas (kg, quintal o tonelada)."
            >
              <select
                id="unidad"
                value={form.unidad}
                onChange={(e) => cambiar('unidad', e.target.value)}
              >
                <option value="">Elige una unidad</option>
                {unidades.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.nombre} ({u.simbolo})
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="perdida_kg"
              etiqueta="Pérdida (kg)"
              error={errores.perdida_kg}
              ayuda="Pérdida registrada durante la cosecha, si la hubo."
            >
              <input
                id="perdida_kg"
                inputMode="decimal"
                placeholder="0"
                value={form.perdida_kg}
                onChange={(e) => cambiar('perdida_kg', e.target.value)}
              />
            </Campo>
            <Campo id="calidad" etiqueta="Calidad" error={errores.calidad}>
              <select
                id="calidad"
                value={form.calidad}
                onChange={(e) => cambiar('calidad', e.target.value)}
              >
                <option value="">Sin calificar</option>
                {CALIDADES.map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
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
                'Registrar producción'
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
