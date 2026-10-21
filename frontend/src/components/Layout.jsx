import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { resumenAlertas } from '../api/alertas.js'
import { useSesion } from '../context/useSesion.js'
import { gruposMenu } from '../routes/opcionesMenu.js'
import Marca from './Marca.jsx'

function IconoMenu() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}

function FlechaGrupo() {
  return (
    <svg
      className="flecha"
      viewBox="0 0 24 24"
      width="14"
      height="14"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M9 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  )
}

function grupoContieneRuta(grupo, pathname) {
  return grupo.opciones.some(
    (opcion) =>
      pathname === opcion.ruta ||
      (opcion.ruta !== '/' && pathname.startsWith(`${opcion.ruta}/`)),
  )
}

export default function Layout() {
  const { usuario, cerrarSesion, tienePermiso } = useSesion()
  const [menuAbierto, setMenuAbierto] = useState(false)
  // Acordeón del menú: decisiones explícitas del usuario; los grupos sin
  // decisión quedan abiertos si contienen la ruta activa (se deriva en
  // el render, sin efectos)
  const [desplegues, setDesplegues] = useState({})
  const [pendientes, setPendientes] = useState(null)
  const ubicacion = useLocation()

  // Semana 15 (HU-127): insignia con el número de alertas pendientes;
  // se relee en cada cambio de ruta para reflejar atenciones y cierres
  useEffect(() => {
    if (!tienePermiso('alertas.ver')) return undefined
    let activo = true
    resumenAlertas()
      .then((datos) => activo && setPendientes(datos.pendientes))
      .catch(() => activo && setPendientes(null))
    return () => { activo = false }
  }, [tienePermiso, ubicacion.pathname])

  // Drawer móvil: Escape lo cierra (el clic en el fondo también)
  useEffect(() => {
    if (!menuAbierto) return undefined
    const alPulsar = (evento) => {
      if (evento.key === 'Escape') setMenuAbierto(false)
    }
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [menuAbierto])

  // Menú agrupado: los grupos sin ninguna opción visible se omiten
  const grupos = gruposMenu
    .map((grupo) => ({
      ...grupo,
      opciones: grupo.opciones.filter(
        (opcion) => !opcion.permiso || tienePermiso(opcion.permiso),
      ),
    }))
    .filter((grupo) => grupo.opciones.length > 0)

  return (
    <div className="app">
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
          {grupos.map((grupo, indice) => {
            const desplegado =
              grupo.titulo in desplegues
                ? desplegues[grupo.titulo]
                : grupoContieneRuta(grupo, ubicacion.pathname)
            const conInsignia =
              !desplegado &&
              pendientes > 0 &&
              grupo.opciones.some((opcion) => opcion.ruta === '/alertas')
            return (
              <div
                key={grupo.titulo}
                className="menu-grupo"
                role="group"
                aria-labelledby={`menu-titulo-${indice}`}
              >
                <button
                  type="button"
                  className="menu-titulo"
                  id={`menu-titulo-${indice}`}
                  aria-expanded={desplegado}
                  aria-controls={`menu-lista-${indice}`}
                  onClick={() =>
                    setDesplegues((anteriores) => ({
                      ...anteriores,
                      [grupo.titulo]: !desplegado,
                    }))
                  }
                >
                  <span>{grupo.titulo}</span>
                  {conInsignia && (
                    <span className="insignia" aria-label={`${pendientes} alertas pendientes`}>
                      {pendientes}
                    </span>
                  )}
                  <FlechaGrupo />
                </button>
                <div id={`menu-lista-${indice}`} className="menu-lista" hidden={!desplegado}>
                  {desplegado &&
                    grupo.opciones.map((opcion) => (
                      <NavLink
                        key={opcion.ruta}
                        to={opcion.ruta}
                        end={opcion.ruta === '/'}
                        className={({ isActive }) =>
                          isActive ? 'enlace activo' : 'enlace'
                        }
                        onClick={() => setMenuAbierto(false)}
                      >
                        {opcion.nombre}
                        {opcion.ruta === '/alertas' && pendientes > 0 && (
                          <span
                            className="insignia"
                            aria-label={`${pendientes} alertas pendientes`}
                          >
                            {pendientes}
                          </span>
                        )}
                      </NavLink>
                    ))}
                </div>
              </div>
            )
          })}
        </nav>

        <p className="pie-menu">
          Proyecto de Mejora Agroproductiva de Granos Andinos
          <br />
          Puno · 2025
        </p>
      </aside>

      <div className="zona">
        <header className="cabecera">
          <button
            type="button"
            className="boton-menu-movil"
            onClick={() => setMenuAbierto((abierto) => !abierto)}
            aria-expanded={menuAbierto}
            aria-controls="menu-principal"
            aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
          >
            <IconoMenu />
          </button>
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
