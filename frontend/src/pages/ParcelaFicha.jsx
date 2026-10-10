import { useCallback, useEffect, useState } from 'react'
import { mensajeDeError } from '../api/errores.js'
import { cliente } from '../api/cliente.js'
import { estadoParcela, obtenerParcela } from '../api/parcelas.js'
import Aviso from '../components/Aviso.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import CampaniaFormulario from './CampaniaFormulario.jsx'
import ParcelaFormulario from './ParcelaFormulario.jsx'
import ProductorFicha from './ProductorFicha.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function ParcelaFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [ficha, setFicha] = useState(null)
  const [comunidad, setComunidad] = useState(null)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(false)
  const [nuevaCampania, setNuevaCampania] = useState(false)
  const [campaniaEditando, setCampaniaEditando] = useState(null)
  const [productorFicha, setProductorFicha] = useState(false)
  const [confirmacion, setConfirmacion] = useState(null)

  const puedeEditar = tienePermiso('parcelas.editar')
  const puedeDesactivar = tienePermiso('parcelas.desactivar')
  const puedeCrearCampania = tienePermiso('campanias.crear')
  const puedeEditarCampania = tienePermiso('campanias.editar')

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerParcela(id)
      .then((datos) => {
        if (!activo) return
        setError(null)
        setFicha(datos)
        if (datos.comunidad) {
          cliente
            .get(`/ubicaciones/comunidades/${datos.comunidad.id}/`)
            .then((r) => activo && setComunidad(r.data))
            .catch(() => activo && setComunidad(null))
        }
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [id, recarga])

  function pedirCambioEstado() {
    const nuevo = ficha.estado === 'ACTIVA' ? 'INACTIVA' : 'ACTIVA'
    setConfirmacion({
      titulo: nuevo === 'INACTIVA' ? 'Desactivar parcela' : 'Reactivar parcela',
      texto:
        nuevo === 'INACTIVA'
          ? '¿Desactivar esta parcela? El registro se conserva.'
          : '¿Reactivar esta parcela?',
      confirmar: nuevo === 'INACTIVA' ? 'Desactivar' : 'Reactivar',
      nivel: nuevo === 'INACTIVA' ? 'peligro' : 'primario',
      accion: async () => {
        setOcupado(true)
        try {
          await estadoParcela(id, nuevo)
          avisar(
            nuevo === 'INACTIVA'
              ? 'Parcela desactivada.'
              : 'Parcela reactivada.',
          )
          recargar()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    })
  }

  async function ejecutarConfirmacion() {
    if (!confirmacion) return
    await confirmacion.accion()
    setConfirmacion(null)
  }

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `Parcela ${ficha.codigo}` : 'Parcela'}
      ocupado={ocupado}
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
              <span className="chip-codigo">{ficha.codigo}</span>{' '}
              <Chip>{ficha.estado}</Chip>
            </p>
            <div className="ficha-acciones">
              <button
                type="button"
                className="boton-secundario"
                onClick={() => setProductorFicha(true)}
              >
                Ver productor
              </button>
              {puedeCrearCampania && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setNuevaCampania(true)}
                >
                  Nueva campaña
                </button>
              )}
              {puedeEditar && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => setEditando(true)}
                >
                  Editar
                </button>
              )}
              {puedeDesactivar && (
                <button
                  type="button"
                  className={
                    ficha.estado === 'ACTIVA' ? 'boton-peligro' : 'boton-primario'
                  }
                  disabled={ocupado}
                  onClick={pedirCambioEstado}
                >
                  {ficha.estado === 'ACTIVA' ? 'Desactivar' : 'Reactivar'}
                </button>
              )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          <section className="panel">
            <h2>Datos de la parcela</h2>
            <dl className="datos-rejilla">
              <Dato
                rotulo="Productor"
                valor={ficha.productor.nombre_completo}
              />
              <Dato rotulo="Comunidad" valor={comunidad?.nombre} />
              <Dato
                rotulo="Distrito"
                valor={comunidad?.distrito?.nombre}
              />
              <Dato
                rotulo="Provincia"
                valor={comunidad?.distrito?.provincia?.nombre}
              />
              <Dato rotulo="Superficie" valor={`${ficha.superficie_ha} ha`} />
              <Dato rotulo="Altitud" valor={ficha.altitud_msnm} />
              <Dato rotulo="Referencia" valor={ficha.referencia_ubicacion} />
              <Dato rotulo="Creado por" valor={ficha.creado_por} />
            </dl>
          </section>

          <section className="panel">
            <h2>Campañas</h2>
            {ficha.campanias.length > 0 ? (
              <Tabla
                filas={ficha.campanias}
                columnas={[
                  {
                    clave: 'periodo',
                    etiqueta: 'Período',
                    celda: (campania) => campania.periodo,
                  },
                  {
                    clave: 'cultivo',
                    etiqueta: 'Cultivo',
                    celda: (campania) => campania.cultivo.nombre,
                  },
                  {
                    clave: 'variedad',
                    etiqueta: 'Variedad',
                    celda: (campania) => campania.variedad.nombre,
                  },
                  {
                    clave: 'fechas',
                    etiqueta: 'Ciclo',
                    celda: (campania) =>
                      `${campania.fecha_inicio} → ${campania.fecha_fin_prevista}`,
                  },
                  {
                    clave: 'superficie',
                    etiqueta: 'Sembrada',
                    celda: (campania) => `${campania.superficie_sembrada_ha} ha`,
                  },
                  {
                    clave: 'estado',
                    etiqueta: 'Estado',
                    celda: (campania) => <Chip>{campania.estado}</Chip>,
                  },
                  {
                    clave: 'acciones',
                    etiqueta: 'Acciones',
                    acciones: true,
                    celda: (campania) =>
                      puedeEditarCampania ? (
                        <button
                          type="button"
                          className="boton-texto"
                          onClick={() => setCampaniaEditando(campania.id)}
                        >
                          Editar
                        </button>
                      ) : null,
                  },
                ]}
              />
            ) : (
              <p className="nota">Esta parcela todavía no tiene campañas.</p>
            )}
          </section>
        </>
      )}

      {editando && (
        <ParcelaFormulario
          id={id}
          abierto
          onGuardado={() => {
            setEditando(false)
            recargar()
          }}
          onCancelar={() => setEditando(false)}
        />
      )}

      {nuevaCampania && ficha && (
        <CampaniaFormulario
          parcelaInicial={ficha.id}
          productorInicial={ficha.productor.id}
          abierto
          onGuardado={() => {
            setNuevaCampania(false)
            recargar()
          }}
          onCancelar={() => setNuevaCampania(false)}
        />
      )}

      {campaniaEditando !== null && (
        <CampaniaFormulario
          id={campaniaEditando}
          abierto
          onGuardado={() => {
            setCampaniaEditando(null)
            recargar()
          }}
          onCancelar={() => {
            setCampaniaEditando(null)
            recargar()
          }}
        />
      )}

      {productorFicha && ficha && (
        <ProductorFicha
          id={ficha.productor.id}
          abierto
          onCerrar={() => setProductorFicha(false)}
        />
      )}

      <Modal
        abierto={confirmacion !== null}
        titulo={confirmacion?.titulo}
        texto={confirmacion?.texto}
        confirmar={confirmacion?.confirmar}
        nivel={confirmacion?.nivel}
        ocupado={ocupado}
        onConfirmar={ejecutarConfirmacion}
        onCerrar={() => setConfirmacion(null)}
      />
    </Modal>
  )
}
