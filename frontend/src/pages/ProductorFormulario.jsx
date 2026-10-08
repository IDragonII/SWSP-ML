import { useEffect, useState } from 'react'
import { cliente } from '../api/cliente.js'
import {
  obtenerComunidades,
  obtenerDistritos,
  obtenerProvincias,
} from '../api/catalogos.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import { guardarProductor, obtenerProductor } from '../api/productores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'

const VACIO = {
  nombres: '',
  apellidos: '',
  dni: '',
  telefono: '',
  fecha_incorporacion: '',
  provincia: '',
  distrito: '',
  comunidad: '',
  referencia_ubicacion: '',
}

export default function ProductorFormulario({ id, abierto, onGuardado, onCancelar }) {
  const esEdicion = Boolean(id)

  const [form, setForm] = useState(VACIO)
  const [provincias, setProvincias] = useState([])
  const [distritosCargados, setDistritosCargados] = useState({
    provincia: null,
    lista: [],
  })
  const [comunidadesCargadas, setComunidadesCargadas] = useState({
    distrito: null,
    lista: [],
  })
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const distritos =
    form.provincia && distritosCargados.provincia === form.provincia
      ? distritosCargados.lista
      : []
  const comunidades =
    form.distrito && comunidadesCargadas.distrito === form.distrito
      ? comunidadesCargadas.lista
      : []
  const cargando = !hidratado

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    obtenerProvincias()
      .then((lista) => activo && setProvincias(lista))
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    if (!form.provincia) return undefined
    let activo = true
    obtenerDistritos(form.provincia)
      .then((lista) =>
        activo && setDistritosCargados({ provincia: form.provincia, lista }),
      )
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [form.provincia])

  useEffect(() => {
    if (!form.distrito) return undefined
    let activo = true
    obtenerComunidades(form.distrito)
      .then((lista) =>
        activo && setComunidadesCargadas({ distrito: form.distrito, lista }),
      )
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [form.distrito])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerProductor(id)
      .then(async (productor) => {
        if (!activo) return
        const { data: ubicacion } = await cliente.get(
          `/ubicaciones/comunidades/${productor.comunidad}/`,
        )
        if (!activo) return
        setForm({
          nombres: productor.nombres,
          apellidos: productor.apellidos,
          dni: productor.dni,
          telefono: productor.telefono ?? '',
          fecha_incorporacion: productor.fecha_incorporacion ?? '',
          provincia: String(ubicacion.distrito.provincia.id),
          distrito: String(ubicacion.distrito.id),
          comunidad: String(ubicacion.id),
          referencia_ubicacion: productor.referencia_ubicacion ?? '',
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

  async function enviar(event) {
    event.preventDefault()
    setErrores({})
    setError(null)
    if (!form.comunidad) {
      setErrores({ comunidad: 'La comunidad es obligatoria.' })
      return
    }
    const datos = {
      nombres: form.nombres.trim(),
      apellidos: form.apellidos.trim(),
      dni: form.dni.trim(),
      telefono: form.telefono.trim() || null,
      comunidad: Number(form.comunidad),
      referencia_ubicacion: form.referencia_ubicacion.trim() || null,
    }
    if (form.fecha_incorporacion) datos.fecha_incorporacion = form.fecha_incorporacion

    setGuardando(true)
    try {
      const guardado = await guardarProductor(id, datos)
      onGuardado?.(guardado)
    } catch (e) {
      if (e.response?.status === 400) {
        setErrores(erroresDeCampo(e.response.data))
      }
      setError(mensajeDeError(e))
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo={esEdicion ? 'Editar productor' : 'Nuevo productor'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? <Cargando /> : (
      <form onSubmit={enviar} className="formulario-pagina">
        <section className="panel">
          <h2>Datos personales</h2>
          <Campo id="nombres" etiqueta="Nombres" error={errores.nombres}>
            <input
              id="nombres"
              value={form.nombres}
              autoComplete="given-name"
              onChange={(e) => cambiar('nombres', e.target.value)}
            />
          </Campo>
          <Campo id="apellidos" etiqueta="Apellidos" error={errores.apellidos}>
            <input
              id="apellidos"
              value={form.apellidos}
              autoComplete="family-name"
              onChange={(e) => cambiar('apellidos', e.target.value)}
            />
          </Campo>
          <Campo
            id="dni"
            etiqueta="DNI"
            error={errores.dni}
            ayuda="Exactamente 8 dígitos."
          >
            <input
              id="dni"
              inputMode="numeric"
              maxLength={8}
              value={form.dni}
              onChange={(e) => cambiar('dni', e.target.value)}
            />
          </Campo>
          <Campo
            id="telefono"
            etiqueta="Teléfono"
            error={errores.telefono}
            ayuda="Opcional."
          >
            <input
              id="telefono"
              inputMode="tel"
              value={form.telefono}
              onChange={(e) => cambiar('telefono', e.target.value)}
            />
          </Campo>
          <Campo
            id="fecha_incorporacion"
            etiqueta="Fecha de incorporación"
            error={errores.fecha_incorporacion}
            ayuda="Opcional. Si se deja vacía, es la fecha de hoy."
          >
            <input
              id="fecha_incorporacion"
              type="date"
              value={form.fecha_incorporacion}
              onChange={(e) => cambiar('fecha_incorporacion', e.target.value)}
            />
          </Campo>
        </section>

        <section className="panel">
          <h2>Ubicación</h2>
          <Campo id="provincia" etiqueta="Provincia">
            <select
              id="provincia"
              value={form.provincia}
              onChange={(e) =>
                setForm((actual) => ({
                  ...actual,
                  provincia: e.target.value,
                  distrito: '',
                  comunidad: '',
                }))
              }
            >
              <option value="">Elige una provincia</option>
              {provincias.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </Campo>
          <Campo id="distrito" etiqueta="Distrito">
            <select
              id="distrito"
              value={form.distrito}
              disabled={!form.provincia}
              onChange={(e) =>
                setForm((actual) => ({
                  ...actual,
                  distrito: e.target.value,
                  comunidad: '',
                }))
              }
            >
              <option value="">
                {form.provincia ? 'Elige un distrito' : 'Primero la provincia'}
              </option>
              {distritos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nombre}
                </option>
              ))}
            </select>
          </Campo>
          <Campo
            id="comunidad"
            etiqueta="Comunidad"
            error={errores.comunidad}
          >
            <select
              id="comunidad"
              value={form.comunidad}
              disabled={!form.distrito}
              onChange={(e) => cambiar('comunidad', e.target.value)}
            >
              <option value="">
                {form.distrito ? 'Elige una comunidad' : 'Primero el distrito'}
              </option>
              {comunidades.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Campo>
          <Campo
            id="referencia_ubicacion"
            etiqueta="Referencia de ubicación"
            error={errores.referencia_ubicacion}
            ayuda="Opcional. Ejemplo: al costado de la escuela."
          >
            <input
              id="referencia_ubicacion"
              value={form.referencia_ubicacion}
              onChange={(e) => cambiar('referencia_ubicacion', e.target.value)}
            />
          </Campo>
        </section>

        <div className="formulario-acciones">
          <button className="boton-primario" type="submit" disabled={guardando}>
            {guardando
              ? 'Guardando…'
              : esEdicion
                ? 'Guardar cambios'
                : 'Crear productor'}
          </button>
          <button className="boton-secundario" type="button" onClick={onCancelar}>
            Cancelar
          </button>
        </div>
      </form>
      )}
    </Modal>
  )
}
