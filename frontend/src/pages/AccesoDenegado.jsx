import { Link } from 'react-router-dom'

export default function AccesoDenegado() {
  return (
    <>
      <h1>No tienes acceso a esta sección</h1>
      <p className="texto-intro">
        Tu rol no incluye el permiso que esta página necesita. Si requieres acceso,
        pídeselo al administrador del sistema.
      </p>
      <p className="pagina-accion">
        <Link to="/">Volver al inicio</Link>
      </p>
    </>
  )
}
