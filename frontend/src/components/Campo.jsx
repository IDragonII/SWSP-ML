export default function Campo({ id, etiqueta, error, ayuda, children }) {
  return (
    <div className="campo">
      <label htmlFor={id}>{etiqueta}</label>
      {children}
      {error ? (
        <p className="campo-error" role="alert">
          {error}
        </p>
      ) : (
        ayuda && <p className="campo-ayuda">{ayuda}</p>
      )}
    </div>
  )
}
