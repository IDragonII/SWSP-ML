import { Link } from 'react-router-dom'

export default function NoEncontrado() {
  return (
    <>
      <h1>Página no encontrada</h1>
      <p className="texto-intro">
        La dirección que buscas no existe. Puede que el enlace esté desactualizado.
      </p>
      <p className="pagina-accion">
        <Link to="/">Volver al inicio</Link>
      </p>
    </>
  )
}
