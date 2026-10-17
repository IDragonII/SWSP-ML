import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import {
  guardarEtapaCampania,
  obtenerEtapaCampania,
} from '../api/etapasCampania.js'
import { obtenerCampania } from '../api/campanias.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  etapa: '',
  fecha_inicio: '',
  fecha_fin: '',
  observaciones: '',
}

function hoyLima() {
  const ahora = new Date()
  const fecha = new Date(ahora.getTime() - 5 * 60 * 60 * 1000)
  return fecha.toISOString().slice(0, 10)
}

export default function EtapaFormulario({
  id,
  campaniaInicial,
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(VACIO)
  const [campania, setCampania] = useState(null)
  const [etapas, setEtapas] = useState([])
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado
  const maxFecha = hoyLima()

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    obtenerCampania(campaniaInicial)
      .then((datos) => {
        if (!activo) return
        setCampania(datos)
        return listarTodo('/etapas-fenologicas/', {
          cultivo: datos.cultivo.id,
          activo: 'true',
        })
      })
      .then((lista) => activo && setEtapas(lista ?? []))
      .catch((e) => activo && setError(mensajeDeError(e)))
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [campaniaInicial])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerEtapaCampania(id)
      .then((etapa) => {
        if (!activo) return
        setForm({
          etapa: String(etapa.etapa.id),
          fecha_inicio: etapa.fecha_inicio ?? '',
          fecha_fin: etapa.fecha_fin ?? '',
          observaciones: etapa.observaciones ?? '',
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
    if (!form.etapa) {
      fallos.etapa = 'La etapa es obligatoria.'
    }
    if (!form.fecha_inicio) {
      fallos.fecha_inicio = 'La fecha de inicio es obligatoria.'
    } else if (form.fecha_inicio > maxFecha) {
      fallos.fecha_inicio = 'La fecha de inicio no puede ser futura.'
    } else if (
      campania &&
      (form.fecha_inicio < campania.fecha_inicio ||
        form.fecha_inicio > campania.fecha_fin_prevista)
    ) {
      fallos.fecha_inicio = `La fecha de inicio debe estar dentro del período de la campaña (${campania.fecha_inicio} a ${campania.fecha_fin_prevista}).`
    }
    if (form.fecha_fin) {
      if (form.fecha_fin > maxFecha) {
        fallos.fecha_fin = 'La fecha de fin no puede ser futura.'
      } else if (form.fecha_inicio && form.fecha_fin < form.fecha_inicio) {
        fallos.fecha_fin = 'La fecha de fin no puede ser anterior a la de inicio.'
      } else if (
        campania &&
        (form.fecha_fin < campania.fecha_inicio ||
          form.fecha_fin > campania.fecha_fin_prevista)
      ) {
        fallos.fecha_fin = `La fecha de fin debe estar dentro del período de la campaña (${campania.fecha_inicio} a ${campania.fecha_fin_prevista}).`
      }
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
      fecha_inicio: form.fecha_inicio,
      fecha_fin: form.fecha_fin || null,
      observaciones: form.observaciones.trim(),
    }
    if (!esEdicion) {
      datos.campania = Number(campaniaInicial)
      datos.etapa = Number(form.etapa)
    } else {
      datos.etapa = Number(form.etapa)
    }

    setGuardando(true)
    try {
      const guardada = await guardarEtapaCampania(id, datos)
      avisar(esEdicion ? 'Etapa actualizada.' : 'Etapa registrada.')
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
      titulo={esEdicion ? 'Editar etapa de la campaña' : 'Registrar etapa'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos de la etapa</h2>
            <Campo
              id="etapa"
              etiqueta="Etapa fenológica"
              error={errores.etapa}
              ayuda={
                campania
                  ? `Solo etapas del cultivo de la campaña (${campania.cultivo.nombre}). Una etapa por campaña.`
                  : 'Solo etapas del cultivo de la campaña.'
              }
            >
              <select
                id="etapa"
                value={form.etapa}
                onChange={(e) => cambiar('etapa', e.target.value)}
              >
                <option value="">Elige una etapa</option>
                {etapas.map((etapa) => (
                  <option key={etapa.id} value={etapa.id}>
                    {etapa.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="fecha_inicio"
              etiqueta="Fecha de inicio"
              error={errores.fecha_inicio}
              ayuda={
                campania
                  ? `No puede ser futura y debe caer dentro del período (${campania.fecha_inicio} a ${campania.fecha_fin_prevista}).`
                  : 'No puede ser futura (hora de Lima).'
              }
            >
              <input
                id="fecha_inicio"
                type="date"
                max={maxFecha}
                value={form.fecha_inicio}
                onChange={(e) => cambiar('fecha_inicio', e.target.value)}
              />
            </Campo>
            <Campo
              id="fecha_fin"
              etiqueta="Fecha de fin (opcional)"
              error={errores.fecha_fin}
              ayuda="Déjala vacía si la etapa sigue en curso: al registrar la siguiente se cierra automáticamente."
            >
              <input
                id="fecha_fin"
                type="date"
                max={maxFecha}
                value={form.fecha_fin}
                onChange={(e) => cambiar('fecha_fin', e.target.value)}
              />
            </Campo>
            <Campo
              id="observaciones"
              etiqueta="Observaciones (opcional)"
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
                'Registrar etapa'
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
