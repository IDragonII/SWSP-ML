export default function Tabla({ columnas, filas, refrescando = false }) {
  return (
    <div className={`tabla-envoltura${refrescando ? ' refrescando' : ''}`}>
      <table className="tabla">
        <thead>
          <tr>
            {columnas.map((columna) => (
              <th key={columna.clave} scope="col">
                {columna.acciones ? (
                  <span className="visualmente-oculto">{columna.etiqueta}</span>
                ) : (
                  columna.etiqueta
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={fila.id}>
              {columnas.map((columna) => (
                <td
                  key={columna.clave}
                  data-rotulo={columna.acciones ? undefined : columna.etiqueta}
                  className={columna.acciones ? 'celda-acciones' : undefined}
                >
                  {columna.celda(fila)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
