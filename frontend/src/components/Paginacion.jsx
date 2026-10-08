export default function Paginacion({ conteo, pagina, porPagina, onCambio }) {
  const total = Math.max(1, Math.ceil((conteo ?? 0) / porPagina))
  if (total <= 1) return null
  return (
    <nav className="paginacion" aria-label="Paginación">
      <button
        type="button"
        className="boton-secundario"
        disabled={pagina <= 1}
        onClick={() => onCambio(pagina - 1)}
      >
        Anterior
      </button>
      <span className="paginacion-info">
        Página {pagina} de {total}
      </span>
      <button
        type="button"
        className="boton-secundario"
        disabled={pagina >= total}
        onClick={() => onCambio(pagina + 1)}
      >
        Siguiente
      </button>
    </nav>
  )
}
