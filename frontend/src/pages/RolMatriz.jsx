import Chip from '../components/Chip.jsx'

// Matriz de permisos por módulo (Semana 14): la dibuja el catálogo
// de /api/permisos-catalogo/ y se usa en dos modos — solo lectura
// (ficha) y edición con casillas (alta y «Editar permisos»).

export default function RolMatriz({
  catalogo,
  seleccion,
  editar = false,
  onAlternar,
}) {
  if (!catalogo) return null

  return (
    <div className="matriz-permisos">
      {catalogo.modulos.map((grupo) => (
        <section className="panel" key={grupo.modulo}>
          <h3>{grupo.modulo}</h3>
          <ul className="matriz-lista">
            {grupo.permisos.map((permiso) => {
              const marcado = seleccion.has(permiso.codigo)
              if (!editar) {
                return (
                  <li
                    key={permiso.codigo}
                    className={marcado ? '' : 'matriz-lista__fuera'}
                  >
                    <code className="chip-codigo">{permiso.codigo}</code>
                    <span className="nota">{permiso.descripcion}</span>
                    {marcado ? <Chip>ASIGNADO</Chip> : <Chip>SIN</Chip>}
                  </li>
                )
              }
              return (
                <li key={permiso.codigo}>
                  <label className="matriz-lista__casilla">
                    <input
                      type="checkbox"
                      checked={marcado}
                      onChange={() => onAlternar(permiso.codigo)}
                    />
                    <code className="chip-codigo">{permiso.codigo}</code>
                    <span className="nota">{permiso.descripcion}</span>
                  </label>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}
