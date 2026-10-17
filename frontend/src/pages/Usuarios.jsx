import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { mensajeDeError } from '../api/errores.js'
import {
  desactivarUsuario,
  listarUsuarios,
  reactivarUsuario,
} from '../api/usuarios.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import UsuarioFicha from './UsuarioFicha.jsx'
import UsuarioFormulario from './UsuarioFormulario.jsx'

export default function Usuarios() {
  const { usuario: sesion, tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [error, setError] = useState(null)
  const [fichaId, setFichaId] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [ocupadoId, setOcupadoId] = useState(null)
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
    if (pagina > 1) filtros.page = pagina
    listarUsuarios(filtros)
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
  }, [busqueda, pagina, clave])

  function cambiarEstado(fila) {
    const esDesactivar = fila.is_active
    setOcupadoId(fila.id)
    const peticion = esDesactivar
      ? desactivarUsuario(fila.id)
      : reactivarUsuario(fila.id)
    peticion
      .then(() => {
        avisar(esDesactivar ? 'Usuario desactivado.' : 'Usuario reactivado.')
        refrescar()
        if (fichaId === fila.id) setRecarga((n) => n + 1)
      })
      .catch((e) => avisar(mensajeDeError(e), 'error'))
      .finally(() => setOcupadoId(null))
  }

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Usuarios</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        {tienePermiso('usuarios.crear') && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            Nuevo usuario
          </button>
        )}
      </div>

      <form
        className="filtros"
        onSubmit={(event) => {
          event.preventDefault()
          cambiar({ busqueda: texto.trim(), page: null })
        }}
      >
        <Campo id="filtro-busqueda" etiqueta="Buscar">
          <input
            id="filtro-busqueda"
            type="search"
            value={texto}
            placeholder="Usuario, nombre o correo"
            onChange={(event) => setTexto(event.target.value)}
          />
        </Campo>
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {busqueda && (
            <button
              className="boton-secundario"
              type="button"
              onClick={() => setParams({})}
            >
              Limpiar
            </button>
          )}
        </div>
      </form>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay usuarios que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o crea un usuario nuevo.
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
                    {fila.nombre_completo}
                  </button>
                ),
              },
              {
                clave: 'username',
                etiqueta: 'Usuario',
                celda: (fila) => <span className="chip-codigo">{fila.username}</span>,
              },
              {
                clave: 'email',
                etiqueta: 'Correo',
                celda: (fila) => fila.email || '—',
              },
              {
                clave: 'rol',
                etiqueta: 'Rol',
                celda: (fila) => fila.rol?.nombre ?? '—',
              },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => (
                  <>
                    <Chip>{fila.is_active ? 'ACTIVO' : 'INACTIVO'}</Chip>{' '}
                    {fila.bloqueado && <Chip>BLOQUEADO</Chip>}
                  </>
                ),
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) => (
                  <>
                    {tienePermiso('usuarios.editar') && (
                      <button
                        type="button"
                        className="boton-texto"
                        onClick={() => setEdicionId(fila.id)}
                      >
                        Editar
                      </button>
                    )}
                    {tienePermiso('usuarios.desactivar') &&
                      fila.id !== sesion?.id && (
                        <button
                          type="button"
                          className="boton-texto"
                          disabled={ocupadoId === fila.id}
                          onClick={() => cambiarEstado(fila)}
                        >
                          {ocupadoId === fila.id
                            ? 'Procesando…'
                            : fila.is_active
                              ? 'Desactivar'
                              : 'Reactivar'}
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

      {fichaId !== null && (
        <UsuarioFicha
          id={fichaId}
          abierto
          onCambio={refrescar}
          onCerrar={() => {
            setFichaId(null)
            refrescar()
          }}
        />
      )}

      {edicionId !== null && (
        <UsuarioFormulario
          id={edicionId}
          abierto
          onGuardado={() => {
            setEdicionId(null)
            refrescar()
          }}
          onCancelar={() => {
            setEdicionId(null)
            refrescar()
          }}
        />
      )}

      {altaAbierta && (
        <UsuarioFormulario
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
