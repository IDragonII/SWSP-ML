import { Link } from 'react-router-dom'

export default function Modulo({ nombre }) {
  return (
    <>
      <h1>{nombre}</h1>
      <p className="texto-intro">
        Este módulo está en preparación. Su desarrollo corresponde a los próximos sprints
        del proyecto.
      </p>
      <p className="pagina-accion">
        <Link to="/">Volver al inicio</Link>
      </p>
    </>
  )
}
