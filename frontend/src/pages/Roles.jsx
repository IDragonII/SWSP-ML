import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { mensajeDeError } from '../api/errores.js'
import {
  desactivarRol,
  listarRolesAdmin,
  reactivarRol,
} from '../api/roles.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import RolFicha from './RolFicha.jsx'
import RolFormulario from './RolFormulario.jsx'

export default function Roles() {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const estado = params.get('estado') ?? ''
  const tipo = params.get('tipo') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${estado}|${tipo}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [error, setError] = useState(null)
  const [fichaId, setFichaId] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [confirmacion, setConfirmacion] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const refrescando = datos !== null && claveCargada !== clave

  function refrescar() {
    setRecarga((n) => n + 1)
  }

  if (busquedaPrevia !== busqueda) {
    setBusquedaPrevia(busqueda)
    setTexto(busqueda)
  }

  function cambiar(cambios) {
    const nuevo = new URLSearchParams(params)
    for (const [claveCambio, valor] of Object.entries(cambios)) {
      if (valor === null || valor === undefined || valor === '') {
        nuevo.delete(claveCambio)
      } else {
        nuevo.set(claveCambio, String(valor))
      }
    }
    setParams(nuevo)
  }

  useEffect(() => {
    let activo = true
    const filtros = {}
    if (busqueda) filtros.busqueda = busqueda
    if (estado) filtros.estado = estado
    if (tipo) filtros.tipo = tipo
    if (pagina > 1) filtros.page = pagina
    listarRolesAdmin(filtros)
      .then((respuesta) => {
        if (!activo) return
        setError(null)
        setDatos(respuesta)
        setClaveCargada(clave)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setClaveCargada(clave)
      })
    return () => {
      activo = false
    }
  }, [busqueda, estado, tipo, pagina, clave])

  function pedirConfirmacion(fila, esDesactivar) {
    setConfirmacion({
      titulo: esDesactivar ? 'Desactivar rol' : 'Reactivar rol',
      texto: esDesactivar
        ? `¿Desactivar el rol «${fila.nombre}»? Si tiene usuarios activos el ` +
          'servidor lo impedirá; el historial se conserva y podrás reactivarlo.'
        : `¿Reactivar el rol «${fila.nombre}»? Volverá a poder asignarse a usuarios.`,
      confirmar: esDesactivar ? 'Desactivar' : 'Reactivar',
      nivel: esDesactivar ? 'peligro' : 'primario',
      accion: async () => {
        setOcupado(true)
        try {
          if (esDesactivar) await desactivarRol(fila.id)
          else await reactivarRol(fila.id)
          avisar(esDesactivar ? 'Rol desactivado.' : 'Rol reactivado.')
          refrescar()
          if (fichaId === fila.id) setRecarga((n) => n + 1)
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setOcupado(false)
        }
      },
    })
  }

  function ejecutarConfirmacion() {
    if (!confirmacion) return
    const { accion } = confirmacion
    setConfirmacion(null)
    accion()
  }

  if (!datos && !error) return <Cargando texto="Cargando roles…" />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Roles y permisos</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        {tienePermiso('roles.gestionar') && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            Nuevo rol
          </button>
        )}
      </div>

      <form
        className="filtros"
        onSubmit={(evento) => {
          evento.preventDefault()
          cambiar({ busqueda: texto.trim(), page: null })
        }}
      >
        <Campo id="filtro-busqueda" etiqueta="Buscar">
          <input
            id="filtro-busqueda"
            type="search"
            value={texto}
            placeholder="Nombre del rol"
            onChange={(evento) => setTexto(evento.target.value)}
          />
        </Campo>
        <Campo id="filtro-estado" etiqueta="Estado">
          <select
            id="filtro-estado"
            value={estado}
            onChange={(evento) => cambiar({ estado: evento.target.value, page: null })}
          >
            <option value="">Todos</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </select>
        </Campo>
        <Campo id="filtro-tipo" etiqueta="Tipo">
          <select
            id="filtro-tipo"
            value={tipo}
            onChange={(evento) => cambiar({ tipo: evento.target.value, page: null })}
          >
            <option value="">Todos</option>
            <option value="sistema">Del sistema</option>
            <option value="personalizado">Personalizado</option>
          </select>
        </Campo>
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {busqueda || estado || tipo || pagina > 1 ? (
            <button
              className="boton-secundario"
              type="button"
              onClick={() => setParams({})}
            >
              Limpiar
            </button>
          ) : null}
        </div>
      </form>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay roles que coincidan con los filtros.</p>
          <p className="nota">
            Limpia los filtros o crea un rol nuevo con «Nuevo rol».
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            refrescando={refrescando}
            filas={datos.results}
            columnas={[
              {
                clave: 'nombre',
                etiqueta: 'Nombre',
                celda: (fila) => (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => setFichaId(fila.id)}
                  >
                    {fila.nombre}
                  </button>
                ),
              },
              {
                clave: 'descripcion',
                etiqueta: 'Descripción',
                celda: (fila) => fila.descripcion || '—',
              },
              {
                clave: 'tipo',
                etiqueta: 'Tipo',
                celda: (fila) => (
                  <Chip>{fila.es_sistema ? 'SISTEMA' : 'PERSONALIZADO'}</Chip>
                ),
              },
              {
                clave: 'alcance',
                etiqueta: 'Alcance',
                celda: (fila) =>
                  fila.limita_a_asignados ? 'Solo asignados' : 'Todos',
              },
              {
                clave: 'usuarios',
                etiqueta: 'Usuarios',
                celda: (fila) => fila.usuarios_activos,
              },
              {
                clave: 'permisos',
                etiqueta: 'Permisos',
                celda: (fila) => fila.total_permisos,
              },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => (
                  <Chip>{fila.activo ? 'ACTIVO' : 'INACTIVO'}</Chip>
                ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {tienePermiso('roles.gestionar') && (
                      <button
                        type="button"
                        className="boton-texto"
                        onClick={() => setEdicionId(fila.id)}
                      >
                        Editar
                      </button>
                    )}
                    {tienePermiso('roles.gestionar') && !fila.es_sistema && (
                      <button
                        type="button"
                        className="boton-texto"
                        onClick={() => pedirConfirmacion(fila, fila.activo)}
                      >
                        {fila.activo ? 'Desactivar' : 'Reactivar'}
                      </button>
                    )}
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setFichaId(fila.id)}
                    >
                      Ficha
                    </button>
                  </>
                ),
              },
            ]}
          />
        )
      )}

      {datos && (
        <Paginacion
          conteo={datos.count}
          pagina={pagina}
          porPagina={20}
          onCambio={(siguiente) => cambiar({ page: siguiente })}
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

      {fichaId !== null && (
        <RolFicha
          id={fichaId}
          abierto
          onCambio={refrescar}
          onEditar={(idRol) => setEdicionId(idRol)}
          onCerrar={() => {
            setFichaId(null)
            refrescar()
          }}
        />
      )}

      {edicionId !== null && (
        <RolFormulario
          id={edicionId}
          abierto
          onGuardado={() => {
            setEdicionId(null)
            refrescar()
            if (fichaId !== null) setRecarga((n) => n + 1)
          }}
          onCancelar={() => {
            setEdicionId(null)
            refrescar()
          }}
        />
      )}

      {altaAbierta && (
        <RolFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}
    </>
  )
}
