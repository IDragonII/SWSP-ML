import { useEffect, useState } from 'react'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import {
  crearRol,
  editarRol,
  listarTodosLosRoles,
  obtenerCatalogoPermisos,
  obtenerRol,
} from '../api/roles.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'
import RolMatriz from './RolMatriz.jsx'

const VACIO = { nombre: '', descripcion: '', limita: false }

export default function RolFormulario({ id, abierto, onGuardado, onCancelar }) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(VACIO)
  const [roles, setRoles] = useState([])
  const [catalogo, setCatalogo] = useState(null)
  const [ficha, setFicha] = useState(null)

  const [basadoEn, setBasadoEn] = useState('')
  const [seleccion, setSeleccion] = useState(new Set())
  const [matrizTocada, setMatrizTocada] = useState(false)

  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado
  const esSistema = ficha?.es_sistema === true
  const conUsuarios = (ficha?.usuarios_activos ?? 0) > 0

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    Promise.all([
      esEdicion ? Promise.resolve(null) : listarTodosLosRoles(),
      obtenerCatalogoPermisos(),
    ])
      .then(([lista, cat]) => {
        if (!activo) return
        if (lista) setRoles(lista)
        setCatalogo(cat)
        setError(null)
        setListo(true)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setListo(true)
      })
    return () => {
      activo = false
    }
  }, [esEdicion])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerRol(id)
      .then((rol) => {
        if (!activo) return
        setFicha(rol)
        setForm({
          nombre: rol.nombre,
          descripcion: rol.descripcion ?? '',
          limita: rol.limita_a_asignados,
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

  async function elegirBase(valor) {
    setBasadoEn(valor)
    setErrores((actual) => ({ ...actual, permisos: undefined }))
    if (!valor) {
      setSeleccion(new Set())
      setMatrizTocada(false)
      return
    }
    try {
      const base = await obtenerRol(Number(valor))
      setSeleccion(new Set(base.permisos))
      setMatrizTocada(false)
    } catch (e) {
      avisar(mensajeDeError(e), 'error')
      setBasadoEn('')
    }
  }

  function alternar(codigo) {
    setMatrizTocada(true)
    setSeleccion((actual) => {
      const siguiente = new Set(actual)
      if (siguiente.has(codigo)) siguiente.delete(codigo)
      else siguiente.add(codigo)
      return siguiente
    })
  }

  function validarCliente() {
    const fallos = {}
    if (!esEdicion && form.nombre.trim().length < 3) {
      fallos.nombre = 'El nombre del rol debe tener al menos 3 caracteres.'
    }
    if (esEdicion && !esSistema && form.nombre.trim().length < 3) {
      fallos.nombre = 'El nombre del rol debe tener al menos 3 caracteres.'
    }
    return fallos
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErrores({})
    setError(null)

    const fallos = validarCliente()
    if (Object.keys(fallos).length > 0) {
      setErrores(fallos)
      return
    }

    let cuerpo
    if (esEdicion) {
      cuerpo = { descripcion: form.descripcion.trim() }
      if (!esSistema) {
        cuerpo.nombre = form.nombre.trim()
        if (!conUsuarios) cuerpo.limita_a_asignados = form.limita
      }
    } else {
      cuerpo = {
        nombre: form.nombre.trim(),
        descripcion: form.descripcion.trim(),
        limita_a_asignados: form.limita,
      }
      if (basadoEn && !matrizTocada) {
        cuerpo.basado_en = Number(basadoEn)
      } else {
        cuerpo.permisos = [...seleccion].sort()
      }
    }

    setGuardando(true)
    try {
      if (esEdicion) await editarRol(id, cuerpo)
      else await crearRol(cuerpo)
      avisar(esEdicion ? 'Rol actualizado.' : 'Rol creado.')
      onGuardado?.()
    } catch (e) {
      if (e.response?.status === 400) {
        const campos = erroresDeCampo(e.response.data)
        setErrores(campos)
        const mensajes = e.response.data?.permisos
        if (Array.isArray(mensajes) && mensajes.length > 0) {
          setErrores((actual) => ({ ...actual, permisos: mensajes.join(' ') }))
          return
        }
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
      titulo={esEdicion ? 'Editar rol' : 'Nuevo rol'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando texto="Cargando el catálogo de permisos…" />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Datos del rol</h2>
            <Campo
              id="rol-nombre"
              etiqueta="Nombre"
              error={errores.nombre}
              ayuda={
                esSistema
                  ? 'El nombre de un rol del sistema no se modifica.'
                  : 'Debe ser único (no distingue mayúsculas). Mínimo 3 caracteres.'
              }
            >
              <input
                id="rol-nombre"
                value={form.nombre}
                disabled={esEdicion && esSistema}
                onChange={(e) => cambiar('nombre', e.target.value)}
              />
            </Campo>
            <Campo
              id="rol-descripcion"
              etiqueta="Descripción (opcional)"
              error={errores.descripcion}
              ayuda="Para qué sirve el rol: se ve en el listado y en la ficha."
            >
              <input
                id="rol-descripcion"
                value={form.descripcion}
                maxLength={200}
                onChange={(e) => cambiar('descripcion', e.target.value)}
              />
            </Campo>
            {!esEdicion && (
              <Campo
                id="rol-basado"
                etiqueta="Basado en (opcional)"
                ayuda="Copia los permisos de otro rol y podrás ajustarlos antes de guardar. Solo envía «basado en» si no tocas la matriz."
              >
                <select
                  id="rol-basado"
                  value={basadoEn}
                  onChange={(e) => elegirBase(e.target.value)}
                >
                  <option value="">Sin base (empieza vacío o elige a mano)</option>
                  {roles.map((rol) => (
                    <option key={rol.id} value={rol.id}>
                      {rol.nombre}
                      {rol.es_sistema ? ' (sistema)' : ''}
                    </option>
                  ))}
                </select>
              </Campo>
            )}
            <Campo
              id="rol-limita"
              etiqueta="Alcance"
              error={errores.limita_a_asignados}
              ayuda={
                esSistema
                  ? 'Los roles del sistema no cambian su alcance.'
                  : conUsuarios
                    ? 'No se puede cambiar: el rol ya tiene usuarios.'
                    : 'Actívalo si este rol solo debe ver sus productores asignados.'
              }
            >
              <label className="casilla-linea">
                <input
                  id="rol-limita"
                  type="checkbox"
                  checked={form.limita}
                  disabled={esEdicion && (esSistema || conUsuarios)}
                  onChange={(e) => cambiar('limita', e.target.checked)}
                />
                Limitar a productores asignados
              </label>
            </Campo>
          </section>

          {!esEdicion && (
            <>
              <div className="matriz-cabecera">
                <h2>Permisos ({seleccion.size} seleccionados)</h2>
              </div>
              <p className="nota">
                Elige qué hace este rol. Algunos permisos dependen de otros
                (p. ej. «atender alertas» exige «ver alertas»): si falta una
                dependencia, el servidor la indicará al guardar y podrás
                marcarla. Un rol vacío no ve nada.
              </p>
              <Aviso>{errores.permisos}</Aviso>
              <RolMatriz
                catalogo={catalogo}
                seleccion={seleccion}
                editar
                onAlternar={alternar}
              />
            </>
          )}

          {esEdicion && (
            <p className="nota">
              Los permisos no se cambian aquí: ábrelo desde la ficha del rol
              («Editar permisos») para ver la matriz y el resumen de cambios.
            </p>
          )}

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
                'Crear rol'
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
