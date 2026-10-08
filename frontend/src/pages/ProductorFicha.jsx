import { useCallback, useEffect, useState } from 'react'
import { cliente } from '../api/cliente.js'
import { tecnicosDisponibles } from '../api/catalogos.js'
import { mensajeDeError } from '../api/errores.js'
import {
  asignarTecnico,
  estadoAsignacion,
  estadoProductor,
  listarAsignaciones,
  obtenerProductor,
} from '../api/productores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import ParcelaFormulario from './ParcelaFormulario.jsx'
import ProductorFormulario from './ProductorFormulario.jsx'

function fechaLarga(valor) {
  if (!valor) return '—'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return valor
  return fecha.toLocaleString('es-PE', { dateStyle: 'long', timeStyle: 'short' })
}

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function ProductorFicha({ id, abierto, onCerrar }) {
  const { tienePermiso } = useSesion()
  const [ficha, setFicha] = useState(null)
  const [comunidad, setComunidad] = useState(null)
  const [asignaciones, setAsignaciones] = useState([])
  const [tecnicos, setTecnicos] = useState([])
  const [tecnicoElegido, setTecnicoElegido] = useState('')
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [recarga, setRecarga] = useState(0)
  const [confirmacion, setConfirmacion] = useState(null)
  const [editando, setEditando] = useState(false)
  const [nuevaParcela, setNuevaParcela] = useState(false)
  const [parcelaEditando, setParcelaEditando] = useState(null)

  const gestionaAsignaciones = tienePermiso('asignaciones.gestionar')
  const puedeEditar = tienePermiso('productores.editar')
  const puedeDesactivar = tienePermiso('productores.desactivar')

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  useEffect(() => {
    let activo = true
    obtenerProductor(id)
      .then((datos) => {
        if (!activo) return
        setError(null)
        setFicha(datos)
        if (datos.comunidad) {
          cliente
            .get(`/ubicaciones/comunidades/${datos.comunidad}/`)
            .then((r) => activo && setComunidad(r.data))
            .catch(() => activo && setComunidad(null))
        }
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [id, recarga])

  useEffect(() => {
    if (!gestionaAsignaciones) return undefined
    let activo = true
    listarAsignaciones(id)
      .then((datos) => activo && setAsignaciones(datos.results))
      .catch(() => {})
    tecnicosDisponibles()
      .then((lista) => activo && setTecnicos(lista))
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [id, gestionaAsignaciones, recarga])

  function pedirCambioProductor() {
    const nuevo = ficha.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO'
    setConfirmacion({
      titulo: nuevo === 'INACTIVO' ? 'Desactivar productor' : 'Reactivar productor',
      texto:
        nuevo === 'INACTIVO'
          ? '¿Desactivar este productor? Conservará sus parcelas como historial.'
          : '¿Reactivar este productor?',
      confirmar: nuevo === 'INACTIVO' ? 'Desactivar' : 'Reactivar',
      nivel: nuevo === 'INACTIVO' ? 'peligro' : 'primario',
      accion: () => cambiarEstadoProductor(nuevo),
    })
  }

  async function cambiarEstadoProductor(nuevo) {
    setOcupado(true)
    setError(null)
    setAviso(null)
    try {
      await estadoProductor(id, nuevo)
      setAviso(nuevo === 'INACTIVO' ? 'Productor desactivado.' : 'Productor reactivado.')
      recargar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  async function asignar(event) {
    event.preventDefault()
    if (!tecnicoElegido) return
    setOcupado(true)
    setError(null)
    setAviso(null)
    try {
      await asignarTecnico({ tecnico: Number(tecnicoElegido), productor: Number(id) })
      setAviso('Técnico asignado.')
      setTecnicoElegido('')
      recargar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  function pedirAlternarAsignacion(asignacion) {
    setConfirmacion({
      titulo: asignacion.activo ? 'Quitar técnico' : 'Reactivar asignación',
      texto: asignacion.activo
        ? `¿Quitar a ${asignacion.tecnico.nombre_completo} de este productor? El registro se conserva sin efecto.`
        : `¿Reactivar la asignación de ${asignacion.tecnico.nombre_completo}?`,
      confirmar: asignacion.activo ? 'Quitar' : 'Reactivar',
      nivel: asignacion.activo ? 'peligro' : 'primario',
      accion: () => alternarAsignacion(asignacion),
    })
  }

  async function alternarAsignacion(asignacion) {
    setOcupado(true)
    setError(null)
    setAviso(null)
    try {
      await estadoAsignacion(asignacion.id, !asignacion.activo)
      setAviso(asignacion.activo ? 'Asignación desactivada.' : 'Asignación reactivada.')
      recargar()
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setOcupado(false)
    }
  }

  async function ejecutarConfirmacion() {
    if (!confirmacion) return
    await confirmacion.accion()
    setConfirmacion(null)
  }

  const { resumen, parcelas, tecnicos_asignados: asignadosEnFicha } = ficha ?? {}

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `${ficha.apellidos}, ${ficha.nombres}` : 'Productor'}
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
          {puedeEditar && (
            <button
              type="button"
              className="boton-secundario"
              onClick={() => setEditando(true)}
            >
              Editar
            </button>
          )}
          {tienePermiso('parcelas.crear') && (
            <button
              type="button"
              className="boton-secundario"
              onClick={() => setNuevaParcela(true)}
            >
              Nueva parcela
            </button>
          )}
          {puedeDesactivar && (
            <button
              type="button"
              className={ficha.estado === 'ACTIVO' ? 'boton-peligro' : 'boton-primario'}
              disabled={ocupado}
              onClick={pedirCambioProductor}
            >
              {ficha.estado === 'ACTIVO' ? 'Desactivar' : 'Reactivar'}
            </button>
          )}
        </div>
      </div>

      <Aviso nivel="ok">{aviso}</Aviso>
      <Aviso>{error}</Aviso>

      <section className="panel">
        <h2>Datos del productor</h2>
        <dl className="datos-rejilla">
          <Dato rotulo="DNI" valor={ficha.dni} />
          <Dato rotulo="Teléfono" valor={ficha.telefono} />
          <Dato rotulo="Fecha de incorporación" valor={ficha.fecha_incorporacion} />
          <Dato rotulo="Creado por" valor={ficha.creado_por} />
          <Dato rotulo="Creado" valor={fechaLarga(ficha.creado_en)} />
          <Dato rotulo="Última edición" valor={fechaLarga(ficha.actualizado_en)} />
        </dl>
      </section>

      <section className="panel">
        <h2>Ubicación</h2>
        <dl className="datos-rejilla">
          <Dato
            rotulo="Comunidad"
            valor={
              comunidad
                ? `${comunidad.nombre} · ${comunidad.distrito.nombre} · ${comunidad.distrito.provincia.nombre}`
                : '—'
            }
          />
          <Dato rotulo="Referencia" valor={ficha.referencia_ubicacion} />
        </dl>
      </section>

      <section className="panel">
        <h2>Parcelas</h2>
        <ul className="resumen-lista">
          <li>
            <strong>{resumen?.parcelas_activas ?? 0}</strong> activas de{' '}
            {parcelas?.length ?? 0}
          </li>
          <li>
            <strong>{resumen?.superficie_total_ha ?? 0}</strong> ha en total
          </li>
        </ul>
        {parcelas && parcelas.length > 0 ? (
          <Tabla
            filas={parcelas}
            columnas={[
              {
                clave: 'codigo',
                etiqueta: 'Código',
                celda: (parcela) => (
                  <span className="chip-codigo">{parcela.codigo}</span>
                ),
              },
              {
                clave: 'superficie',
                etiqueta: 'Superficie',
                celda: (parcela) => `${parcela.superficie_ha} ha`,
              },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (parcela) => <Chip>{parcela.estado}</Chip>,
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (parcela) =>
                  tienePermiso('parcelas.editar') ? (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setParcelaEditando(parcela.id)}
                    >
                      Editar
                    </button>
                  ) : null,
              },
            ]}
          />
        ) : (
          <p className="nota">
            Este productor todavía no tiene parcelas registradas.
          </p>
        )}
      </section>

      {asignadosEnFicha !== undefined && (
        <section className="panel">
          <h2>Técnicos asignados</h2>
          {asignadosEnFicha.length > 0 ? (
            <ul className="asignaciones-lista">
              {asignadosEnFicha.map((asignado) => (
                <li key={asignado.id}>
                  <span>{asignado.nombre_completo}</span>
                  <span className="nota">
                    desde {asignado.fecha_asignacion}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="nota">Sin técnicos asignados.</p>
          )}

          {gestionaAsignaciones && (
            <>
              <form className="asignar-form" onSubmit={asignar}>
                <Campo id="asignar-tecnico" etiqueta="Asignar un técnico">
                  <select
                    id="asignar-tecnico"
                    value={tecnicoElegido}
                    onChange={(event) => setTecnicoElegido(event.target.value)}
                  >
                    <option value="">Elige un técnico</option>
                    {tecnicos.map((tecnico) => (
                      <option key={tecnico.id} value={tecnico.id}>
                        {tecnico.nombre_completo} ({tecnico.username})
                      </option>
                    ))}
                  </select>
                </Campo>
                <button
                  className="boton-primario"
                  type="submit"
                  disabled={ocupado || !tecnicoElegido}
                >
                  Asignar
                </button>
              </form>

              {asignaciones.length > 0 && (
                <Tabla
                  filas={asignaciones}
                  columnas={[
                    {
                      clave: 'tecnico',
                      etiqueta: 'Técnico',
                      celda: (asignacion) =>
                        asignacion.tecnico.nombre_completo,
                    },
                    {
                      clave: 'desde',
                      etiqueta: 'Desde',
                      celda: (asignacion) => asignacion.fecha_asignacion,
                    },
                    {
                      clave: 'estado',
                      etiqueta: 'Estado',
                      celda: (asignacion) => (
                        <Chip>
                          {asignacion.activo ? 'ACTIVA' : 'INACTIVA'}
                        </Chip>
                      ),
                    },
                    {
                      clave: 'acciones',
                      etiqueta: 'Acciones',
                      acciones: true,
                      celda: (asignacion) => (
                        <button
                          type="button"
                          className="boton-texto"
                          disabled={ocupado}
                          onClick={() => pedirAlternarAsignacion(asignacion)}
                        >
                          {asignacion.activo ? 'Desactivar' : 'Reactivar'}
                        </button>
                      ),
                    },
                  ]}
                />
              )}
            </>
          )}
        </section>
      )}
      </>
      )}

      {editando && (
        <ProductorFormulario
          id={id}
          abierto
          onGuardado={() => {
            setEditando(false)
            recargar()
          }}
          onCancelar={() => setEditando(false)}
        />
      )}

      {nuevaParcela && ficha && (
        <ParcelaFormulario
          productorInicial={ficha.id}
          abierto
          onGuardado={() => {
            setNuevaParcela(false)
            recargar()
          }}
          onCancelar={() => setNuevaParcela(false)}
        />
      )}

      {parcelaEditando !== null && (
        <ParcelaFormulario
          id={parcelaEditando}
          abierto
          onGuardado={() => {
            setParcelaEditando(null)
            recargar()
          }}
          onCancelar={() => {
            setParcelaEditando(null)
            recargar()
          }}
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
