import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import {
  guardarIncidencia,
  obtenerIncidencia,
  SEVERIDADES_INCIDENCIA,
} from '../api/incidencias.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  campania: '',
  tipo_incidencia: '',
  fecha: '',
  severidad: '',
  descripcion: '',
  superficie_afectada_ha: '',
  agente: '',
  producto_aplicado: '',
}

function hoyLima() {
  // La API rechaza fechas futuras según la hora local de Lima (igual
  // que clima y actividades)
  const ahora = new Date()
  const fecha = new Date(ahora.getTime() - 5 * 60 * 60 * 1000)
  return fecha.toISOString().slice(0, 10)
}

export default function IncidenciaFormulario({
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
    campania: campaniaInicial ? String(campaniaInicial) : '',
  }))
  const [campanias, setCampanias] = useState([])
  const [tipos, setTipos] = useState([])
  const [agentes, setAgentes] = useState([])
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado
  const maxFecha = hoyLima()
  const campaniaActual = campanias.find(
    (c) => String(c.id) === String(form.campania),
  )
  const tipoActual = tipos.find(
    (t) => String(t.id) === String(form.tipo_incidencia),
  )
  const esBiologica = tipoActual?.categoria === 'BIOLOGICA'

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    Promise.all([
      listarTodo('/campanias/', { desplegable: 1 }),
      listarTodo('/tipos-incidencia/', { activo: 'true' }),
      listarTodo('/agentes/', { activo: 'true' }),
    ])
      .then(([listaCampanias, listaTipos, listaAgentes]) => {
        if (!activo) return
        setCampanias(listaCampanias)
        setTipos(listaTipos)
        setAgentes(listaAgentes)
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
    obtenerIncidencia(id)
      .then((incidencia) => {
        if (!activo) return
        setForm({
          campania: String(incidencia.campania.id),
          tipo_incidencia: String(incidencia.tipo_incidencia.id),
          fecha: incidencia.fecha,
          severidad: incidencia.severidad,
          descripcion: incidencia.descripcion ?? '',
          superficie_afectada_ha:
            incidencia.superficie_afectada_ha === null
              ? ''
              : String(incidencia.superficie_afectada_ha),
          agente: incidencia.agente ? String(incidencia.agente.id) : '',
          producto_aplicado: incidencia.producto_aplicado ?? '',
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
    if (!esEdicion && !form.campania) {
      fallos.campania = 'La campaña es obligatoria.'
    }
    if (!form.tipo_incidencia) {
      fallos.tipo_incidencia = 'El tipo de incidencia es obligatorio.'
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
    if (!form.severidad) {
      fallos.severidad = 'La severidad es obligatoria.'
    }
    if (!form.descripcion.trim()) {
      fallos.descripcion = 'La descripción es obligatoria.'
    }
    if (
      form.superficie_afectada_ha.trim() &&
      Number(form.superficie_afectada_ha.trim()) < 0
    ) {
      fallos.superficie_afectada_ha =
        'La superficie afectada no puede ser negativa.'
    }
    if (form.producto_aplicado.trim().length > 100) {
      fallos.producto_aplicado =
        'El producto aplicado admite como máximo 100 caracteres.'
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

    // En edición la campaña no viaja: la API la rechaza aunque el valor
    // sea el mismo (anula y registra otra incidencia)
    const datos = {
      tipo_incidencia: Number(form.tipo_incidencia),
      fecha: form.fecha,
      severidad: form.severidad,
      descripcion: form.descripcion.trim(),
      superficie_afectada_ha: form.superficie_afectada_ha.trim() || null,
      agente: esBiologica && form.agente ? Number(form.agente) : null,
      producto_aplicado: form.producto_aplicado.trim(),
    }
    if (!esEdicion) {
      datos.campania = Number(form.campania)
    }

    setGuardando(true)
    try {
      const guardada = await guardarIncidencia(id, datos)
      avisar(esEdicion ? 'Incidencia guardada.' : 'Incidencia creada.')
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
      titulo={esEdicion ? 'Editar incidencia' : 'Registrar incidencia'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos de la incidencia</h2>
            <Campo
              id="campania"
              etiqueta="Campaña"
              error={errores.campania}
              ayuda={
                campaniaActual
                  ? `Período de la campaña: ${campaniaActual.fecha_inicio} a ${campaniaActual.fecha_fin_prevista}.`
                  : 'Solo se admiten campañas planificadas, en producción o cosechadas.'
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
              id="tipo_incidencia"
              etiqueta="Tipo de incidencia"
              error={errores.tipo_incidencia}
              ayuda="La categoría define si puedes indicar un agente (solo biológicos)."
            >
              <select
                id="tipo_incidencia"
                value={form.tipo_incidencia}
                onChange={(e) => {
                  cambiar('tipo_incidencia', e.target.value)
                  cambiar('agente', '')
                }}
              >
                <option value="">Elige un tipo</option>
                {tipos.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="fecha"
              etiqueta="Fecha"
              error={errores.fecha}
              ayuda="No puede ser futura (hora de Lima) y debe caer dentro del período de la campaña."
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
              id="severidad"
              etiqueta="Severidad"
              error={errores.severidad}
            >
              <select
                id="severidad"
                value={form.severidad}
                onChange={(e) => cambiar('severidad', e.target.value)}
              >
                <option value="">Elige la severidad</option>
                {SEVERIDADES_INCIDENCIA.map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="descripcion"
              etiqueta="Descripción"
              error={errores.descripcion}
              ayuda="Qué pasó, dónde y cómo se detectó."
            >
              <textarea
                id="descripcion"
                rows={3}
                value={form.descripcion}
                onChange={(e) => cambiar('descripcion', e.target.value)}
              />
            </Campo>
            <Campo
              id="superficie_afectada_ha"
              etiqueta="Superficie afectada (ha, opcional)"
              error={errores.superficie_afectada_ha}
              ayuda="No puede superar la superficie sembrada de la campaña."
            >
              <input
                id="superficie_afectada_ha"
                inputMode="decimal"
                placeholder="0.5"
                value={form.superficie_afectada_ha}
                onChange={(e) =>
                  cambiar('superficie_afectada_ha', e.target.value)
                }
              />
            </Campo>
          </section>

          <section className="panel">
            <h2>Agente y tratamiento</h2>
            {esBiologica ? (
              <Campo
                id="agente"
                etiqueta="Agente (opcional)"
                error={errores.agente}
                ayuda="Plaga o enfermedad detectada; solo activos del catálogo."
              >
                <select
                  id="agente"
                  value={form.agente}
                  onChange={(e) => cambiar('agente', e.target.value)}
                >
                  <option value="">Sin agente asignado</option>
                  {agentes.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.nombre}
                    </option>
                  ))}
                </select>
              </Campo>
            ) : (
              <Campo
                id="agente"
                etiqueta="Agente"
                ayuda="El agente solo puede indicarse en tipos biológicos (plaga o enfermedad)."
              >
                <select id="agente" value="" disabled>
                  <option value="">No aplica para este tipo</option>
                </select>
              </Campo>
            )}
            <Campo
              id="producto_aplicado"
              etiqueta="Producto aplicado (informativo)"
              error={errores.producto_aplicado}
              ayuda="Solo informativo (máx. 100 caracteres); no controla existencias."
            >
              <input
                id="producto_aplicado"
                maxLength={100}
                placeholder="Ej. caldo sulfocálcico"
                value={form.producto_aplicado}
                onChange={(e) => cambiar('producto_aplicado', e.target.value)}
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
                'Registrar incidencia'
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
