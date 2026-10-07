import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useSesion } from '../context/useSesion.js'
import { opcionesMenu } from '../routes/opcionesMenu.js'
import Marca from './Marca.jsx'

export default function Layout() {
  const { usuario, cerrarSesion, tienePermiso } = useSesion()
  const [menuAbierto, setMenuAbierto] = useState(false)

  const visibles = opcionesMenu.filter(
    (opcion) => !opcion.permiso || tienePermiso(opcion.permiso),
  )

  return (
    <div className="app">
      <button
        type="button"
        className="boton-menu-movil"
        onClick={() => setMenuAbierto((abierto) => !abierto)}
        aria-expanded={menuAbierto}
        aria-controls="menu-principal"
      >
        <Marca width="20" height="20" />
        SIGPA-GA · Menú
      </button>

      {menuAbierto && (
        <button
          type="button"
          className="fondo-menu"
          aria-label="Cerrar menú"
          onClick={() => setMenuAbierto(false)}
        />
      )}

      <aside
        id="menu-principal"
        className={menuAbierto ? 'barra-lateral abierta' : 'barra-lateral'}
      >
        <div className="marca">
          <Marca />
          <span className="marca-nombre">SIGPA-GA</span>
        </div>

        <nav className="menu" aria-label="Principal">
          {visibles.map((opcion) => (
            <NavLink
              key={opcion.ruta}
              to={opcion.ruta}
              end={opcion.ruta === '/'}
              className={({ isActive }) => (isActive ? 'enlace activo' : 'enlace')}
              onClick={() => setMenuAbierto(false)}
            >
              {opcion.nombre}
            </NavLink>
          ))}
        </nav>

        <p className="pie-menu">
          Proyecto de Mejora Agroproductiva de Granos Andinos
          <br />
          Puno · 2025
        </p>
      </aside>

      <div className="zona">
        <header className="cabecera">
          <p className="situacion">
            <strong>{usuario.nombre_completo || usuario.username}</strong>
            {' · '}
            {usuario.rol?.nombre}
          </p>
          <button type="button" className="boton-salir" onClick={() => cerrarSesion()}>
            Cerrar sesión
          </button>
        </header>

        <main className="contenido">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
