import { Link } from 'react-router-dom'
import { useSesion } from '../context/useSesion.js'
import { opcionesMenu } from '../routes/opcionesMenu.js'

function saludoPorHora() {
  const hora = new Date().getHours()
  if (hora < 13) return 'Buenos días'
  if (hora < 20) return 'Buenas tardes'
  return 'Buenas noches'
}

export default function Inicio() {
  const { usuario, tienePermiso } = useSesion()
  const modulos = opcionesMenu.filter(
    (opcion) => opcion.ruta !== '/' && (!opcion.permiso || tienePermiso(opcion.permiso)),
  )
  const nombre = usuario.nombre_completo || usuario.username

  return (
    <>
      <h1>
        {saludoPorHora()}, {nombre}
      </h1>
      <p className="texto-intro">
        Has iniciado sesión con el rol <strong>{usuario.rol?.nombre}</strong>. Este menú
        se arma según tus permisos; el backend vuelve a comprobar cada permiso en cada
        petición.
      </p>

      <section className="panel">
        <h2>Tus módulos</h2>
        {modulos.length > 0 ? (
          <ul className="enlaces-modulos">
            {modulos.map((opcion) => (
              <li key={opcion.ruta}>
                <Link to={opcion.ruta}>{opcion.nombre}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>Solo tienes acceso al inicio. Pide los permisos que necesites al administrador.</p>
        )}
        <p className="nota">
          Los módulos listados se irán habilitando en los próximos sprints; el resto se
          muestra según el rol.
        </p>
      </section>
    </>
  )
}
