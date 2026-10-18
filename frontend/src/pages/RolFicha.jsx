import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  desactivarRol,
  obtenerCatalogoPermisos,
  obtenerRol,
  guardarPermisosRol,
  reactivarRol,
} from '../api/roles.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import RolMatriz from './RolMatriz.jsx'

function Dato({ rotulo, valor }) {
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{valor || '—'}</dd>
    </div>
  )
}

export default function RolFicha({
  id,
  abierto,
  onCerrar,
  onCambio,
  onEditar,
}) {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const navegar = useNavigate()

  const [ficha, setFicha] = useState(null)
  const [catalogo, setCatalogo] = useState(null)
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [confirmacion, setConfirmacion] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const [editandoPermisos, setEditandoPermisos] = useState(false)
  const [seleccion, setSeleccion] = useState(new Set())
  const [guardandoPermisos, setGuardandoPermisos] = useState(false)
  const [errorPermisos, setErrorPermisos] = useState(null)

  const recargar = useCallback(() => setRecarga((n) => n + 1), [])

  const esAdministrador = ficha?.nombre === 'Administrador'
  const intocable = ficha?.es_sistema || esAdministrador
  const puedeEditarPermisos =
    tienePermiso('roles.gestionar') && ficha != null && !intocable

  useEffect(() => {
    let activo = true
    obtenerRol(id)
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

  useEffect(() => {
    let activo = true
    obtenerCatalogoPermisos()
      .then((datos) => activo && setCatalogo(datos))
      .catch(() => activo && setCatalogo({ modulos: [] }))
    return () => {
      activo = false
    }
  }, [])

  // Al entrar al modo edición, la selección parte de los permisos actuales
  function empezarEdicion() {
    setSeleccion(new Set(ficha.permisos))
    setErrorPermisos(null)
    setEditandoPermisos(true)
  }

  const actuales = new Set(ficha?.permisos ?? [])
  const agregados = [...seleccion].filter((c) => !actuales.has(c)).sort()
  const quitados = [...actuales].filter((c) => !seleccion.has(c)).sort()
  const sinCambios = editandoPermisos && agregados.length === 0 && quitados.length === 0

  function alternar(codigo) {
    setSeleccion((actual) => {
      const siguiente = new Set(actual)
      if (siguiente.has(codigo)) siguiente.delete(codigo)
      else siguiente.add(codigo)
      return siguiente
    })
  }

  async function guardarPermisos() {
    setGuardandoPermisos(true)
    setErrorPermisos(null)
    try {
      const respuesta = await guardarPermisosRol(id, [...seleccion].sort())
      const cambios =
        respuesta.agregados.length === 0 && respuesta.quitados.length === 0
          ? 'Sin cambios: el rol ya tenía esos permisos.'
          : `Permisos actualizados: ${respuesta.agregados.length} agregados, ` +
            `${respuesta.quitados.length} quitados (afecta a ` +
            `${respuesta.usuarios_afectados} usuario(s) activo(s)).`
      avisar(cambios)
      setEditandoPermisos(false)
      recargar()
      onCambio?.()
    } catch (e) {
      const mensajes = e.response?.data?.permisos
      if (Array.isArray(mensajes) && mensajes.length > 0) {
        setErrorPermisos(mensajes.join(' '))
      } else {
        setErrorPermisos(mensajeDeError(e))
      }
    } finally {
      setGuardandoPermisos(false)
    }
  }

  function pedir(titulo, texto, confirmar, nivel, accion) {
    setConfirmacion({ titulo, texto, confirmar, nivel, accion })
  }

  function ejecutarConfirmacion() {
    if (!confirmacion) return
    const { accion } = confirmacion
    setConfirmacion(null)
    accion()
  }

  function desactivar() {
    pedir(
      'Desactivar rol',
      `¿Desactivar el rol «${ficha.nombre}»? Sus usuarios activos impiden ` +
        'la operación; el historial se conserva y podrás reactivarlo después.',
      'Desactivar',
      'peligro',
      async () => {
        setOcupado(true)
        try {
          await desactivarRol(id)
          avisar('Rol desactivado.')
          recargar()
          onCambio?.()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    )
  }

  function reactivar() {
    pedir(
      'Reactivar rol',
      `¿Reactivar el rol «${ficha.nombre}»? Volverá a poder asignarse a usuarios.`,
      'Reactivar',
      'primario',
      async () => {
        setOcupado(true)
        try {
          await reactivarRol(id)
          avisar('Rol reactivado.')
          recargar()
          onCambio?.()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    )
  }

  return (
    <Modal
      abierto={abierto}
      tamano="ficha"
      titulo={ficha ? `Rol ${ficha.nombre}` : 'Rol'}
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
              <Chip>{ficha.activo ? 'ACTIVO' : 'INACTIVO'}</Chip>{' '}
              <Chip>{ficha.es_sistema ? 'SISTEMA' : 'PERSONALIZADO'}</Chip>{' '}
              {ficha.limita_a_asignados && <Chip>SOLO ASIGNADOS</Chip>}{' '}
              <span className="nota">
                {ficha.usuarios_activos} usuario(s) activo(s) ·{' '}
                {ficha.total_permisos} permiso(s)
              </span>
            </p>
            <div className="ficha-acciones">
              {tienePermiso('auditoria.ver') && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() =>
                    navegar(`/auditoria?tabla=roles&registro=${ficha.id}`)
                  }
                >
                  Ver historial
                </button>
              )}
              {tienePermiso('roles.gestionar') && (
                <button
                  type="button"
                  className="boton-secundario"
                  onClick={() => onEditar?.(ficha.id)}
                >
                  Editar datos
                </button>
              )}
              {puedeEditarPermisos && !editandoPermisos && (
                <button
                  type="button"
                  className="boton-primario"
                  onClick={empezarEdicion}
                >
                  Editar permisos
                </button>
              )}
              {tienePermiso('roles.gestionar') &&
                !ficha.es_sistema &&
                ficha.activo && (
                  <button
                    type="button"
                    className="boton-peligro"
                    onClick={desactivar}
                  >
                    Desactivar
                  </button>
                )}
              {tienePermiso('roles.gestionar') &&
                !ficha.es_sistema &&
                !ficha.activo && (
                  <button
                    type="button"
                    className="boton-primario"
                    onClick={reactivar}
                  >
                    Reactivar
                  </button>
                )}
            </div>
          </div>

          <Aviso>{error}</Aviso>

          <section className="panel">
            <h2>Datos del rol</h2>
            <dl className="datos-rejilla">
              <Dato rotulo="Nombre" valor={ficha.nombre} />
              <Dato rotulo="Descripción" valor={ficha.descripcion} />
              <Dato
                rotulo="Alcance"
                valor={
                  ficha.limita_a_asignados
                    ? 'Solo productores asignados'
                    : 'Todos los productores'
                }
              />
              <Dato
                rotulo="Tipo"
                valor={ficha.es_sistema ? 'Rol del sistema' : 'Personalizado'}
              />
            </dl>
            {esAdministrador && (
              <p className="nota">
                El rol Administrador es intocable: conserva siempre los 55
                permisos del catálogo, no admite cambios de permisos ni
                desactivación.
              </p>
            )}
            {!esAdministrador && ficha.es_sistema && (
              <p className="nota">
                Es un rol del sistema: su nombre y su alcance no cambian y no
                se puede desactivar. Sus permisos tampoco se editan aquí.
              </p>
            )}
          </section>

          <div className="matriz-cabecera">
            <h2>Permisos ({ficha.permisos.length})</h2>
            {editandoPermisos && (
              <div className="ficha-acciones">
                <button
                  type="button"
                  className="boton-primario"
                  disabled={guardandoPermisos}
                  onClick={guardarPermisos}
                >
                  {guardandoPermisos ? (
                    <>
                      <RuedaCarga etiqueta="Guardando…" />
                      Guardando…
                    </>
                  ) : (
                    'Guardar permisos'
                  )}
                </button>
                <button
                  type="button"
                  className="boton-secundario"
                  disabled={guardandoPermisos}
                  onClick={() => setEditandoPermisos(false)}
                >
                  Cancelar
                </button>
              </div>
            )}
          </div>
          {editandoPermisos && (
            <p className="nota">
              {seleccion.size} seleccionado(s) ·{' '}
              <strong>{agregados.length} agregado(s)</strong>,{' '}
              <strong>{quitados.length} quitado(s)</strong>. La lista vacía
              retira todos los permisos; el reemplazo es todo-o-nada.
              {sinCambios &&
                ' Ahora mismo no hay cambios: el rol ya tenía esta combinación.'}
            </p>
          )}
          <Aviso>{errorPermisos}</Aviso>
          {!catalogo ? (
            <Cargando />
          ) : (
            <RolMatriz
              catalogo={catalogo}
              seleccion={editandoPermisos ? seleccion : actuales}
              editar={editandoPermisos}
              onAlternar={alternar}
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
            onCerrar={() => !ocupado && setConfirmacion(null)}
          />
        </>
      )}
    </Modal>
  )
}
