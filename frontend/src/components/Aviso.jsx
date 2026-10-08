export default function Aviso({ nivel = 'error', children }) {
  if (!children) return null
  return (
    <p
      className={nivel === 'ok' ? 'aviso aviso-ok' : 'aviso error'}
      role={nivel === 'ok' ? 'status' : 'alert'}
    >
      {children}
    </p>
  )
}
