import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import { obtenerClima } from '../api/clima.js'
import Aviso from '../components/Aviso.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import { useSesion } from '../context/useSesion.js'
import ClimaFormulario from './ClimaFormulario.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function ClimaFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const [ficha, setFicha] = useState(null)
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)

  const puedeEditar = tienePermiso('clima.editar')

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerClima(id)
      .then((datos) => {
        if (!activo) return
        setError(null)
        setFicha(datos)
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [id, recarga])

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `Clima del ${ficha.fecha}` : 'Registro de clima'}
      onCerrar={onCerrar}
    >
      {error && !ficha ? (
        <Aviso>{error}</Aviso>
      ) : !ficha ? (
        <Cargando />
      ) : (
        <>
          <div className="ficha-cabecera">
            <p className="ficha-estado">
              {ficha.parcela.codigo}{' '}
              <Chip>{ficha.fuente === 'API' ? 'API' : 'MANUAL'}</Chip>{' '}
              {ficha.helada && <Chip>HELADA</Chip>}
            </p>
            <div className="ficha-acciones">
              {puedeEditar && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setEditando(true)}
                >
                  Editar
                </button>
              )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          <section className="panel">
            <h2>Días del registro</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Fecha" valor={ficha.fecha} />
              <Dato rotulo="Parcela" valor={ficha.parcela.codigo} />
              <Dato
                rotulo="Productor"
                valor={ficha.parcela.productor.nombre_completo}
              />
              <Dato rotulo="Comunidad" valor={ficha.parcela.comunidad.nombre} />
            </dl>
          </section>

          <section className="panel">
            <h2>Medidas del día</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Temperatura mínima" valor={ficha.temp_min && `${ficha.temp_min} °C`} />
              <Dato rotulo="Temperatura máxima" valor={ficha.temp_max && `${ficha.temp_max} °C`} />
              <Dato
                rotulo="Temperatura promedio"
                valor={
                  ficha.temp_prom
                    ? `${ficha.temp_prom} °C${ficha.temp_prom_calculado ? ' (punto medio calculado)' : ''}`
                    : null
                }
              />
              <Dato
                rotulo="Precipitación"
                valor={ficha.precipitacion_mm && `${ficha.precipitacion_mm} mm`}
              />
              <Dato
                rotulo="Humedad"
                valor={ficha.humedad_pct && `${ficha.humedad_pct} %`}
              />
              <Dato
                rotulo="Viento máximo"
                valor={ficha.viento_ms && `${ficha.viento_ms} m/s`}
              />
              <Dato
                rotulo="Radiación"
                valor={ficha.radiacion_mj && `${ficha.radiacion_mj} MJ/m²`}
              />
              <Dato
                rotulo="Helada"
                valor={
                  ficha.helada
                    ? ficha.helada_calculada
                      ? 'Sí (derivada del umbral)'
                      : 'Sí'
                    : 'No'
                }
              />
            </dl>
          </section>

          <section className="panel">
            <h2>Trazabilidad</h2>
            <dl className="datos-rejilla">
              <Dato
                rotulo="Fuente"
                valor={ficha.fuente === 'API' ? 'API meteorológica' : 'Manual'}
              />
              {ficha.registrado_por !== undefined && (
                <Dato rotulo="Registrado por" valor={ficha.registrado_por} />
              )}
              <Dato rotulo="Creado" valor={ficha.creado_en} />
              <Dato rotulo="Última edición" valor={ficha.actualizado_en} />
            </dl>
          </section>
        </>
      )}

      {editando && (
        <ClimaFormulario
          id={id}
          abierto
          onGuardado={() => {
            setEditando(false)
            recargar()
          }}
          onCancelar={() => setEditando(false)}
        />
      )}
    </Modal>
  )
}
