import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  desactivarUsuario,
  desbloquearUsuario,
  obtenerUsuario,
  reactivarUsuario,
  restablecerClave,
} from '../api/usuarios.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function UsuarioFicha({ id, abierto, onCerrar, onCambio }) {
  const { usuario: sesion, tienePermiso } = useSesion()
  const { avisar } = useToast()
  const navegar = useNavigate()
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [confirmacion, setConfirmacion] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [claveAbierta, setClaveAbierta] = useState(false)

  const puedeGestionarEstado = tienePermiso('usuarios.desactivar')
  const puedeEditar = tienePermiso('usuarios.editar')
  const esPropio = sesion?.id === ficha?.id

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerUsuario(id)
      .then((datos) => {
        if (!activo) return
        setError(null)
        setFicha(datos)
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [id, recarga])

  function pedir(titulo, texto, confirmar, nivel, accion) {
    setConfirmacion({ titulo, texto, confirmar, nivel, accion })
  }

  function ejecutarConfirmacion() {
    if (!confirmacion) return
    const { accion } = confirmacion
    setConfirmacion(null)
    accion()
  }

  function desactivar() {
    pedir(
      'Desactivar usuario',
      `¿Desactivar a ${ficha.nombre_completo}? No podrá iniciar sesión y sus sesiones abiertas quedarán invalidadas.`,
      'Desactivar',
      'peligro',
      async () => {
        setOcupado(true)
        try {
          await desactivarUsuario(id)
          avisar('Usuario desactivado.')
          recargar()
          onCambio?.()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    )
  }

  function reactivar() {
    pedir(
      'Reactivar usuario',
      `¿Reactivar la cuenta de ${ficha.nombre_completo}? Volverá a poder iniciar sesión.`,
      'Reactivar',
      'primario',
      async () => {
        setOcupado(true)
        try {
          await reactivarUsuario(id)
          avisar('Usuario reactivado.')
          recargar()
          onCambio?.()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    )
  }

  function desbloquear() {
    pedir(
      'Desbloquear acceso',
      `¿Limpiar el bloqueo por intentos fallidos de ${ficha.username}?`,
      'Desbloquear',
      'primario',
      async () => {
        setOcupado(true)
        try {
          const respuesta = await desbloquearUsuario(id)
          avisar(respuesta.detail)
          recargar()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    )
  }

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `Usuario ${ficha.username}` : 'Usuario'}
      onCerrar={onCerrar}
    >
      {error && !ficha ? (
        <Aviso>{error}</Aviso>
      ) : !ficha ? (
        <Cargando />
      ) : (
        <>
          <div className="ficha-cabecera">
            <p className="ficha-estado">
              <Chip>{ficha.is_active ? 'ACTIVO' : 'INACTIVO'}</Chip>{' '}
              {ficha.bloqueado && <Chip>BLOQUEADO</Chip>}{' '}
              <span className="nota">Rol: {ficha.rol?.nombre ?? '—'}</span>
            </p>
            <div className="ficha-acciones">
              {tienePermiso('auditoria.ver') && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() =>
                    navegar(`/auditoria?tabla=usuarios&registro=${ficha.id}`)
                  }
                >
                  Ver historial
                </button>
              )}
              {puedeEditar && !esPropio && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setClaveAbierta(true)}
                >
                  Restablecer contraseña
                </button>
              )}
              {puedeEditar && ficha.bloqueado && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={desbloquear}
                >
                  Desbloquear acceso
                </button>
              )}
              {puedeGestionarEstado && !esPropio && ficha.is_active && (
                <button
                  type="button"
                  className="boton-peligro"
                  onClick={desactivar}
                >
                  Desactivar
                </button>
              )}
              {puedeGestionarEstado && !ficha.is_active && (
                <button
                  type="button"
                  className="boton-primario"
                  onClick={reactivar}
                >
                  Reactivar
                </button>
              )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          <section className="panel">
            <h2>Datos de la cuenta</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Nombre completo" valor={ficha.nombre_completo} />
              <Dato rotulo="Usuario" valor={ficha.username} />
              <Dato rotulo="Correo" valor={ficha.email} />
              <Dato rotulo="Teléfono" valor={ficha.telefono} />
              <Dato rotulo="Rol" valor={ficha.rol?.nombre} />
              <Dato
                rotulo="Bloqueo"
                valor={
                  ficha.bloqueado
                    ? `Bloqueado (${ficha.bloqueado_segundos} s restantes)`
                    : 'Sin bloqueo'
                }
              />
              <Dato
                rotulo="Creado"
                valor={(ficha.date_joined ?? '').slice(0, 10)}
              />
              <Dato
                rotulo="Último acceso"
                valor={
                  ficha.last_login
                    ? new Date(ficha.last_login).toLocaleString('es-PE')
                    : 'Nunca'
                }
              />
            </dl>
            {ficha.permisos?.length > 0 && (
              <p className="nota">
                El rol {ficha.rol?.nombre} otorga {ficha.permisos.length}{' '}
                permiso(s): {ficha.permisos.join(', ')}.
              </p>
            )}
          </section>

          {claveAbierta && (
            <FormularioClave
              usuario={ficha}
              onGuardado={() => {
                setClaveAbierta(false)
                recargar()
                onCambio?.()
              }}
              onCancelar={() => setClaveAbierta(false)}
            />
          )}
        </>
      )}

      <Modal
        abierto={confirmacion !== null}
        titulo={confirmacion?.titulo}
        texto={confirmacion?.texto}
        confirmar={confirmacion?.confirmar}
        nivel={confirmacion?.nivel}
        ocupado={ocupado}
        onConfirmar={ejecutarConfirmacion}
        onCerrar={() => !ocupado && setConfirmacion(null)}
      />
    </Modal>
  )
}

function FormularioClave({ usuario, onGuardado, onCancelar }) {
  const { avisar } = useToast()
  const [password, setPassword] = useState('')
  const [errorCampo, setErrorCampo] = useState(null)
  const [error, setError] = useState(null)
  const [guardando, setGuardando] = useState(false)

  async function enviar(event) {
    event.preventDefault()
    setError(null)
    setErrorCampo(null)
    if (!password) {
      setErrorCampo('La contraseña es obligatoria.')
      return
    }
    if (password.length < 8) {
      setErrorCampo('La contraseña debe tener al menos 8 caracteres.')
      return
    }
    setGuardando(true)
    try {
      await restablecerClave(usuario.id, password)
      avisar('Contraseña restablecida. Las sesiones abiertas quedan cerradas.')
      onGuardado?.()
    } catch (e) {
      if (e.response?.status === 400) {
        const campos = erroresDeCampo(e.response.data)
        if (campos.password) {
          setErrorCampo(campos.password)
          setGuardando(false)
          return
        }
      }
      setError(mensajeDeError(e))
      setGuardando(false)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal
      abierto
      tamano="formulario"
      titulo={`Restablecer contraseña de ${usuario.username}`}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>
      <form onSubmit={enviar} className="formulario-pagina">
        <section className="panel">
          <Campo
            id="clave-nueva"
            etiqueta="Contraseña nueva"
            error={errorCampo}
            ayuda="Mínimo 8 caracteres; no repitas contraseñas comunes ni el nombre de usuario. Las sesiones abiertas de esta cuenta se cierran."
          >
            <input
              id="clave-nueva"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
            ) : (
              'Restablecer contraseña'
            )}
          </button>
          <button
            className="boton-secundario"
            type="button"
            onClick={onCancelar}
          >
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  )
}
