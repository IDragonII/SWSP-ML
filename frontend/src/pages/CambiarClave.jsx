import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cambiarClave } from '../api/auth.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Marca from '../components/Marca.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'

// Semana 13 (HU-105 a HU-113): cambio de la propia contraseña. Con la
// marca debe_cambiar_clave el backend cierra el resto de la API (403),
// así que RutaProtegida redirige aquí y solo esta pantalla —y las
// rutas de sesión— quedan disponibles hasta cambiarla.
export default function CambiarClave() {
  const { usuario, actualizarUsuario } = useSesion()
  const { avisar } = useToast()
  const navegar = useNavigate()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [errorActual, setErrorActual] = useState(null)
  const [errorNueva, setErrorNueva] = useState(null)
  const [errorConfirmacion, setErrorConfirmacion] = useState(null)
  const [error, setError] = useState(null)
  const [guardando, setGuardando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setError(null)
    setErrorActual(null)
    setErrorNueva(null)
    setErrorConfirmacion(null)
    if (nueva !== confirmar) {
      setErrorConfirmacion('Las dos contraseñas nuevas no coinciden.')
      return
    }
    setGuardando(true)
    try {
      const respuesta = await cambiarClave(actual, nueva)
      actualizarUsuario(respuesta.usuario)
      avisar('Contraseña actualizada. Tus sesiones anteriores quedaron cerradas.')
      navegar('/', { replace: true })
    } catch (err) {
      if (err.response?.status === 400) {
        const campos = erroresDeCampo(err.response.data)
        if (campos.password_actual) {
          setErrorActual(campos.password_actual)
        }
        if (campos.password_nueva) {
          setErrorNueva(campos.password_nueva)
        }
        if (campos.password_actual || campos.password_nueva) {
          setGuardando(false)
          return
        }
      }
      setError(mensajeDeError(err))
      setGuardando(false)
    }
  }

  return (
    <div className="login">
      <aside className="login-marca">
        <Marca className="marca-agua" width="100%" height="100%" />
        <div>
          <h1>SIGPA-GA</h1>
          <p className="login-lema">
            {usuario?.debe_cambiar_clave
              ? 'Tu cuenta tiene una contraseña provisional: cambia antes de continuar usando el sistema.'
              : 'Actualiza tu contraseña para seguir trabajando con seguridad.'}
          </p>
        </div>
        <p className="login-pie">Puno · 2026</p>
      </aside>

      <main className="login-panel">
        <form className="formulario" onSubmit={enviar}>
          <h2>Cambiar contraseña</h2>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          <div className="campo">
            <label htmlFor="clave-actual">Contraseña actual</label>
            <input
              id="clave-actual"
              type="password"
              autoComplete="current-password"
              required
              value={actual}
              onChange={(evento) => setActual(evento.target.value)}
            />
            {errorActual && (
              <p className="campo-error" role="alert">
                {errorActual}
              </p>
            )}
          </div>

          <div className="campo">
            <label htmlFor="clave-nueva">Contraseña nueva</label>
            <input
              id="clave-nueva"
              type="password"
              autoComplete="new-password"
              required
              value={nueva}
              onChange={(evento) => setNueva(evento.target.value)}
            />
            <p className="campo-ayuda">
              Mínimo 8 caracteres; no repitas contraseñas comunes ni tu nombre
              de usuario.
            </p>
            {errorNueva && (
              <p className="campo-error" role="alert">
                {errorNueva}
              </p>
            )}
          </div>

          <div className="campo">
            <label htmlFor="clave-confirmar">Repetir contraseña nueva</label>
            <input
              id="clave-confirmar"
              type="password"
              autoComplete="new-password"
              required
              value={confirmar}
              onChange={(evento) => setConfirmar(evento.target.value)}
            />
            {errorConfirmacion && (
              <p className="campo-error" role="alert">
                {errorConfirmacion}
              </p>
            )}
          </div>

          <button type="submit" className="boton-entrar" disabled={guardando}>
            {guardando ? (
              <>
                <RuedaCarga etiqueta="Guardando…" />
                Guardando…
              </>
            ) : (
              'Guardar contraseña'
            )}
          </button>
        </form>
      </main>
    </div>
  )
}
