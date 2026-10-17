import { useEffect, useState } from 'react'
import { obtenerUsuario, guardarUsuario, listarRoles } from '../api/usuarios.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  telefono: '',
  rol: '',
  password: '',
}

export default function UsuarioFormulario({
  id,
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(VACIO)
  const [roles, setRoles] = useState([])
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !listo || !hidratado

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    listarRoles()
      .then((lista) => activo && setRoles(lista))
      .catch(() => activo && setRoles([]))
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerUsuario(id)
      .then((usuario) => {
        if (!activo) return
        setForm({
          username: usuario.username,
          first_name: usuario.first_name ?? '',
          last_name: usuario.last_name ?? '',
          email: usuario.email ?? '',
          telefono: usuario.telefono ?? '',
          rol: usuario.rol ? String(usuario.rol.id) : '',
          password: '',
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
    if (!esEdicion && !form.username.trim()) {
      fallos.username = 'El nombre de usuario es obligatorio.'
    }
    if (!form.first_name.trim()) {
      fallos.first_name = 'Los nombres son obligatorios.'
    }
    if (!form.last_name.trim()) {
      fallos.last_name = 'Los apellidos son obligatorios.'
    }
    if (!form.rol) {
      fallos.rol = 'El rol es obligatorio.'
    }
    if (!esEdicion) {
      if (!form.password) {
        fallos.password = 'La contraseña es obligatoria.'
      } else if (form.password.length < 8) {
        fallos.password = 'La contraseña debe tener al menos 8 caracteres.'
      } else if (
        form.password.toLowerCase().includes(form.username.trim().toLowerCase()) &&
        form.username.trim()
      ) {
        fallos.password =
          'La contraseña no puede contener el nombre de usuario.'
      } else if (/^\d+$/.test(form.password)) {
        fallos.password = 'La contraseña no puede ser solo numérica.'
      }
    }
    if (form.email.trim() && !form.email.includes('@')) {
      fallos.email = 'El correo no es válido.'
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
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      telefono: form.telefono.trim(),
      rol: Number(form.rol),
    }
    if (!esEdicion) {
      datos.username = form.username.trim()
      datos.password = form.password
    }

    setGuardando(true)
    try {
      const guardado = await guardarUsuario(id, datos)
      avisar(esEdicion ? 'Usuario actualizado.' : 'Usuario creado.')
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
      titulo={esEdicion ? 'Editar usuario' : 'Nuevo usuario'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Identidad</h2>
            <Campo
              id="username"
              etiqueta="Nombre de usuario"
              error={errores.username}
              ayuda={
                esEdicion
                  ? 'El nombre de usuario no se puede modificar.'
                  : 'Se usa para entrar al sistema; no se puede cambiar después.'
              }
            >
              <input
                id="username"
                value={form.username}
                disabled={esEdicion}
                autoComplete="username"
                onChange={(e) => cambiar('username', e.target.value)}
              />
            </Campo>
            <Campo
              id="first_name"
              etiqueta="Nombres"
              error={errores.first_name}
            >
              <input
                id="first_name"
                value={form.first_name}
                onChange={(e) => cambiar('first_name', e.target.value)}
              />
            </Campo>
            <Campo
              id="last_name"
              etiqueta="Apellidos"
              error={errores.last_name}
            >
              <input
                id="last_name"
                value={form.last_name}
                onChange={(e) => cambiar('last_name', e.target.value)}
              />
            </Campo>
          </section>

          <section className="panel">
            <h2>Contacto y rol</h2>
            <Campo id="email" etiqueta="Correo (opcional)" error={errores.email}>
              <input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => cambiar('email', e.target.value)}
              />
            </Campo>
            <Campo
              id="telefono"
              etiqueta="Teléfono (opcional)"
              error={errores.telefono}
            >
              <input
                id="telefono"
                value={form.telefono}
                onChange={(e) => cambiar('telefono', e.target.value)}
              />
            </Campo>
            <Campo
              id="rol"
              etiqueta="Rol"
              error={errores.rol}
              ayuda="El rol define los permisos del usuario dentro del sistema."
            >
              <select
                id="rol"
                value={form.rol}
                onChange={(e) => cambiar('rol', e.target.value)}
              >
                <option value="">Elige un rol</option>
                {roles.map((rol) => (
                  <option key={rol.id} value={rol.id}>
                    {rol.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            {!esEdicion && (
              <Campo
                id="password"
                etiqueta="Contraseña"
                error={errores.password}
                ayuda="Mínimo 8 caracteres, sin ser solo números ni repetir el nombre de usuario."
              >
                <input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(e) => cambiar('password', e.target.value)}
                />
              </Campo>
            )}
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
                'Crear usuario'
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
