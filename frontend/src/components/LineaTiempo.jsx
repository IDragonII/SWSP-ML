import Chip from './Chip.jsx'

const TIPOS = {
  ETAPA: 'Etapa',
  ACTIVIDAD: 'Actividad',
  INCIDENCIA: 'Incidencia',
  PRODUCCION: 'Cosecha',
}

const ESTADOS = {
  EN_CURSO: 'EN CURSO',
  REGISTRADA: 'REGISTRADA',
  PENDIENTE: 'PENDIENTE',
}

function Elemento({ elemento }) {
  return (
    <li className={`linea-tiempo-item linea-tiempo-item--${elemento.tipo.toLowerCase()}`}>
      <p className="linea-tiempo-fecha">
        {elemento.fecha ?? 'Sin fecha'}
        {elemento.fecha_fin ? ` → ${elemento.fecha_fin}` : ''}
      </p>
      <div className="linea-tiempo-cuerpo">
        <p className="linea-tiempo-titulo">
          <span className="nota">{TIPOS[elemento.tipo]}</span> {elemento.titulo}{' '}
          <Chip>{ESTADOS[elemento.estado] ?? elemento.estado}</Chip>
          {elemento.severidad && <Chip>{elemento.severidad.toUpperCase()}</Chip>}
        </p>
        {elemento.detalle && (
          <p className="linea-tiempo-detalle">{elemento.detalle}</p>
        )}
      </div>
    </li>
  )
}

export default function LineaTiempo({ datos }) {
  if (!datos) return null
  const { etapa_actual, etapas_definidas, elementos, total_elementos, truncado } =
    datos

  return (
    <div className="linea-tiempo">
      <p className="linea-tiempo-actual">
        {etapa_actual ? (
          <>
            Etapa actual:{' '}
            <Chip>{etapa_actual.en_curso ? 'EN CURSO' : 'REGISTRADA'}</Chip>{' '}
            <strong>{etapa_actual.nombre}</strong>{' '}
            <span className="nota">
              desde {etapa_actual.fecha_inicio}
              {etapa_actual.fecha_fin ? ` hasta ${etapa_actual.fecha_fin}` : ''}
            </span>
          </>
        ) : (
          <span className="nota">
            La campaña todavía no tiene etapas registradas.
          </span>
        )}
      </p>

      <ol className="linea-tiempo-progreso">
        {etapas_definidas.map((etapa) => (
          <li
            key={etapa.id}
            className={
              etapa.registrada
                ? etapa.fecha_fin
                  ? 'linea-tiempo-paso completada'
                  : 'linea-tiempo-paso activa'
                : 'linea-tiempo-paso'
            }
          >
            <span className="linea-tiempo-paso-nombre">{etapa.nombre}</span>
            <span className="nota">
              {etapa.fecha_inicio ?? 'Pendiente'}
              {etapa.fecha_fin ? ` → ${etapa.fecha_fin}` : ''}
            </span>
          </li>
        ))}
      </ol>

      {elementos.length > 0 ? (
        <ol className="linea-tiempo-lista">
          {elementos.map((elemento, indice) => (
            <Elemento
              key={`${elemento.tipo}-${elemento.fecha ?? 'p'}-${indice}`}
              elemento={elemento}
            />
          ))}
        </ol>
      ) : (
        <p className="nota">
          Todavía no hay actividades, incidencias ni etapas registradas.
        </p>
      )}

      {truncado && (
        <p className="nota">
          Cronología truncada: se muestran los primeros{' '}
          {elementos.length} de {total_elementos} elementos.
        </p>
      )}
    </div>
  )
}
