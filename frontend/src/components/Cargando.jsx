export default function Cargando({ texto = 'Cargando…' }) {
  return (
    <div className="cargando" role="status">
      <div className="cargando-anillo" />
      <p>{texto}</p>
    </div>
  )
}
