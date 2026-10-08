const ACTIVO = /^(ACTIVO|ACTIVA)/

export default function Chip({ children }) {
  const texto = String(children ?? '')
  const tono = ACTIVO.test(texto) ? 'chip-activo' : 'chip-inactivo'
  return <span className={`chip ${tono}`}>{texto}</span>
}
