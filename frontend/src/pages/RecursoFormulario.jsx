import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import {
  guardarUsoRecurso,
  obtenerUsoRecurso,
} from '../api/usosRecursos.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  campania: '',
  recurso: '',
  actividad: '',
  fecha: '',
  cantidad: '',
  unidad: '',
  costo: '',
  observaciones: '',
}

function hoyLima() {
  // La API rechaza fechas futuras según la hora local de Lima (pregunta H)
  const ahora = new Date()
  const fecha = new Date(ahora.getTime() - 5 * 60 * 60 * 1000)
  return fecha.toISOString().slice(0, 10)
}

export default function RecursoFormulario({
  id,
  campaniaInicial = '',
  actividadInicial = '',
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(() => ({
    ...VACIO,
    campania: campaniaInicial ? String(campaniaInicial) : '',
    actividad: actividadInicial ? String(actividadInicial) : '',
  }))
  const [campanias, setCampanias] = useState([])
  const [recursos, setRecursos] = useState([])
  const [actividades, setActividades] = useState([])
  const [unidades, setUnidades] = useState([])
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado
  const campaniaActual = campanias.find(
    (c) => String(c.id) === String(form.campania),
  )
  const recursoActual = recursos.find(
    (r) => String(r.id) === String(form.recurso),
  )
  const maxFecha = hoyLima()

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    Promise.all([
      listarTodo('/campanias/', { desplegable: 1 }),
      listarTodo('/recursos/', { desplegable: 1 }),
    ])
      .then(([listaCampanias, listaRecursos]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setRecursos(listaRecursos)
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
    obtenerUsoRecurso(id)
      .then((uso) => {
        if (!activo) return
        setForm({
          campania: String(uso.campania.id),
          recurso: String(uso.recurso.id),
          actividad: uso.actividad ? String(uso.actividad.id) : '',
          fecha: uso.fecha,
          cantidad: String(uso.cantidad),
          unidad: String(uso.unidad.id),
          costo: uso.costo === null ? '' : String(uso.costo),
          observaciones: uso.observaciones ?? '',
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

  // Las unidades del desplegable se limitan al tipo del recurso elegido
  // (regla de la Semana 9: semilla en kg, diésel en m3, jornales en jornal…)
  useEffect(() => {
    let activo = true
    if (!recursoActual) return undefined
    listarTodo('/unidades/', {
      tipo: recursoActual.tipo_unidad,
      activo: 'true',
    })
      .then((lista) => activo && setUnidades(lista))
      .catch(() => activo && setUnidades([]))
    return () => {
      activo = false
    }
  }, [recursoActual])

  useEffect(() => {
    let activo = true
    if (!form.campania) return undefined
    listarTodo('/actividades/', { campania: form.campania })
      .then((lista) => {
        if (!activo) return
        setActividades(lista.filter((a) => !a.anulada))
      })
      .catch(() => activo && setActividades([]))
    return () => {
      activo = false
    }
  }, [form.campania])

  const actividadActual = actividades.find(
    (a) => String(a.id) === String(form.actividad),
  )

  function validarCliente() {
    const fallos = {}
    if (!form.campania) fallos.campania = 'La campaña es obligatoria.'
    if (!form.recurso) fallos.recurso = 'El recurso es obligatorio.'
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
    if (!form.cantidad.trim()) {
      fallos.cantidad = 'La cantidad es obligatoria.'
    } else if (Number(form.cantidad) <= 0) {
      fallos.cantidad = 'La cantidad debe ser mayor que 0.'
    }
    if (!form.unidad) fallos.unidad = 'La unidad es obligatoria.'
    if (form.costo.trim() && Number(form.costo) < 0) {
      fallos.costo = 'El costo no puede ser negativo.'
    }
    if (actividadActual && form.fecha && actividadActual.fecha !== form.fecha) {
      fallos.fecha = `Si la actividad está vinculada, la fecha debe coincir con la de la actividad (${actividadActual.fecha}).`
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

    // En edición la campaña no viaja: la API la rechaza aunque sea la
    // misma (hay que anular y registrar otro uso)
    const datos = {
      recurso: Number(form.recurso),
      actividad: form.actividad ? Number(form.actividad) : null,
      fecha: form.fecha,
      cantidad: form.cantidad.trim(),
      unidad: Number(form.unidad),
      costo: form.costo.trim() || null,
      observaciones: form.observaciones.trim(),
    }
    if (!esEdicion) datos.campania = Number(form.campania)

    setGuardando(true)
    try {
      const guardado = await guardarUsoRecurso(id, datos)
      avisar(esEdicion ? 'Uso de recurso guardado.' : 'Uso de recurso creado.')
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
      titulo={esEdicion ? 'Editar uso de recurso' : 'Nuevo uso de recurso'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos del uso</h2>
            <Campo
              id="campania"
              etiqueta="Campaña"
              error={errores.campania}
              ayuda={
                campaniaActual
                  ? `Período de la campaña: ${campaniaActual.fecha_inicio} a ${campaniaActual.fecha_fin_prevista}.`
                  : 'Elige la campaña donde se registra el uso.'
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
              id="recurso"
              etiqueta="Recurso"
              error={errores.recurso}
              ayuda={
                recursoActual
                  ? `Categoría ${recursoActual.categoria}: se mide en unidades de tipo ${recursoActual.tipo_unidad.toLowerCase()}.`
                  : 'El recurso determina las unidades admisibles.'
              }
            >
              <select
                id="recurso"
                value={form.recurso}
                onChange={(e) => {
                  cambiar('recurso', e.target.value)
                  cambiar('unidad', '')
                }}
              >
                <option value="">Elige un recurso</option>
                {recursos.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nombre} ({r.categoria})
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="actividad"
              etiqueta="Actividad (opcional)"
              error={errores.actividad}
              ayuda="Si la vinculas, la fecha del uso debe coincir con la de la actividad."
            >
              <select
                id="actividad"
                value={form.actividad}
                onChange={(e) => cambiar('actividad', e.target.value)}
              >
                <option value="">Sin actividad</option>
                {actividades.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.fecha} — {a.tipo_actividad.nombre}
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
            <Campo
              id="cantidad"
              etiqueta="Cantidad"
              error={errores.cantidad}
              ayuda="La base de datos convierte la cantidad a la unidad base."
            >
              <input
                id="cantidad"
                inputMode="decimal"
                placeholder="16"
                value={form.cantidad}
                onChange={(e) => cambiar('cantidad', e.target.value)}
              />
            </Campo>
            <Campo
              id="unidad"
              etiqueta="Unidad"
              error={errores.unidad}
              ayuda="Solo aparecen las unidades del tipo que admite el recurso."
            >
              <select
                id="unidad"
                value={form.unidad}
                disabled={!recursoActual}
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
          </section>

          <section className="panel">
            <h2>Costo y observaciones</h2>
            <Campo
              id="costo"
              etiqueta="Costo (S/)"
              error={errores.costo}
              ayuda="Costo total del uso en soles."
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
                'Crear uso de recurso'
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
