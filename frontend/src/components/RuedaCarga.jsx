export default function RuedaCarga({ etiqueta = 'Cargando…' }) {
  return (
    <span className="rueda" role="status" aria-label={etiqueta} />
  )
}
