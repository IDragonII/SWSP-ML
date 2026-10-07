import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { mensajeDeError } from '../api/errores.js'
import Marca from '../components/Marca.jsx'
import { useSesion } from '../context/useSesion.js'

export default function Login() {
  const { iniciarSesion } = useSesion()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      await iniciarSesion(usuario, clave)
      navegar(ubicacion.state?.desde?.pathname || '/', { replace: true })
    } catch (err) {
      setError(mensajeDeError(err))
      setEnviando(false)
    }
  }

  return (
    <div className="login">
      <aside className="login-marca">
        <Marca className="marca-agua" width="100%" height="100%" />
        <div>
          <h1>SIGPA-GA</h1>
          <p className="login-lema">
            Seguimiento de productores y predicción con machine learning para el
            Proyecto de Mejora Agroproductiva de Granos Andinos.
          </p>
        </div>
        <p className="login-pie">Puno · 2025</p>
      </aside>

      <main className="login-panel">
        <form className="formulario" onSubmit={enviar}>
          <h2>Iniciar sesión</h2>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          <div className="campo">
            <label htmlFor="usuario">Usuario</label>
            <input
              id="usuario"
              name="username"
              autoComplete="username"
              required
              value={usuario}
              onChange={(evento) => setUsuario(evento.target.value)}
            />
          </div>

          <div className="campo">
            <label htmlFor="clave">Contraseña</label>
            <input
              id="clave"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={clave}
              onChange={(evento) => setClave(evento.target.value)}
            />
          </div>

          <button type="submit" className="boton-entrar" disabled={enviando}>
            {enviando ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </main>
    </div>
  )
}
