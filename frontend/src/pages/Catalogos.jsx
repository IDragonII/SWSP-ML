import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiCatalogo } from '../api/catalogos.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import { useToast } from '../context/useToast.js'
import { CATALOGOS } from './catalogosConfig.js'
import CatalogoFormulario from './CatalogoFormulario.jsx'

function textoCelda(columna, fila) {
  if (columna.formato) return columna.formato(fila)
  switch (columna.tipo) {
    case 'estado':
      return <Chip>{fila.activo ? 'ACTIVO' : 'INACTIVO'}</Chip>
    case 'codigo':
      return <span className="chip-codigo">{fila[columna.clave]}</span>
    case 'anidado':
      return fila[columna.clave]?.nombre ?? '—'
    case 'opciones':
      return columna.mapa[fila[columna.clave]] ?? fila[columna.clave]
    case 'numero':
      return String(Number(fila[columna.clave]))
    default:
      return fila[columna.clave] ?? '—'
  }
}

export default function Catalogos() {
  const { tienePermiso } = useSesion()
  const { avisar } = useToast()
  const [params, setParams] = useSearchParams()

  const claveCatalogo = params.get('catalogo') ?? CATALOGOS[0].clave
  const catalogo =
    CATALOGOS.find((c) => c.clave === claveCatalogo) ?? CATALOGOS[0]
  const busqueda = params.get('busqueda') ?? ''
  const estado = params.get('estado') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${catalogo.clave}|${busqueda}|${estado}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [claveCatalogoPrevia, setClaveCatalogoPrevia] = useState(catalogo.clave)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [error, setError] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [confirmacion, setConfirmacion] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const refrescando = datos !== null && claveCargada !== clave

  const puedeCrear = catalogo.alta && tienePermiso('catalogos.crear')
  const puedeEditar = tienePermiso('catalogos.editar')
  const puedeEstado = catalogo.estado && tienePermiso('catalogos.desactivar')

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
      if (valor === null || valor === undefined || valor === '')
        nuevo.delete(claveCambio)
      else nuevo.set(claveCambio, String(valor))
    }
    setParams(nuevo)
  }

  // Al cambiar de pestaña se vacían los datos: las columnas cambian.
  if (claveCatalogoPrevia !== catalogo.clave) {
    setClaveCatalogoPrevia(catalogo.clave)
    setDatos(null)
    setClaveCargada(null)
    setError(null)
  }

  useEffect(() => {
    let activo = true
    const filtros = {}
    if (busqueda) filtros.busqueda = busqueda
    if (catalogo.estado && estado) filtros.activo = estado
    if (pagina > 1) filtros.page = pagina
    apiCatalogo(catalogo.ruta)
      .listar(filtros)
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
  }, [clave, catalogo, busqueda, estado, pagina])

  function pedirEstado(fila) {
    const activar = !fila.activo
    setConfirmacion({
      titulo: `${activar ? 'Reactivar' : 'Desactivar'} ${catalogo.singular}`,
      texto: activar
        ? `¿Reactivar «${fila.nombre}»? Volverá a aparecer en los listados y desplegables.`
        : `¿Desactivar «${fila.nombre}»? Dejará de aparecer en los listados y desplegables.`,
      confirmar: activar ? 'Reactivar' : 'Desactivar',
      nivel: activar ? 'primario' : 'peligro',
      accion: () => cambiarEstado(fila, activar),
    })
  }

  async function cambiarEstado(fila, activar) {
    setOcupado(true)
    try {
      await apiCatalogo(catalogo.ruta).cambiarEstado(fila.id, activar)
      avisar(activar ? 'Registro reactivado.' : 'Registro desactivado.')
      refrescar()
    } catch (e) {
      avisar(mensajeDeError(e), 'error')
    } finally {
      setOcupado(false)
    }
  }

  async function ejecutarConfirmacion() {
    if (!confirmacion) return
    await confirmacion.accion()
    setConfirmacion(null)
  }

  if (!datos && !error) return <Cargando />

  const columnas = catalogo.columnas.map((columna) => ({
    clave: columna.clave,
    etiqueta: columna.etiqueta,
    celda: (fila) => textoCelda(columna, fila),
  }))

  if (puedeEditar || puedeEstado) {
    columnas.push({
      clave: 'acciones',
      etiqueta: 'Acciones',
      acciones: true,
      celda: (fila) => (
        <>
          {puedeEditar && (
            <button
              type="button"
              className="boton-texto"
              onClick={() => setEdicionId(fila.id)}
            >
              Editar
            </button>
          )}
          {puedeEstado && (
            <button
              type="button"
              className="boton-texto"
              onClick={() => pedirEstado(fila)}
            >
              {fila.activo ? 'Desactivar' : 'Reactivar'}
            </button>
          )}
        </>
      ),
    })
  }

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Catálogos</h1>
          <p className="conteo">
            {datos
              ? `${datos.count} ${catalogo.nombre.toLowerCase()}`
              : 'Sin datos'}
          </p>
        </div>
        {puedeCrear && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            {catalogo.tituloAlta}
          </button>
        )}
      </div>

      <div className="pestanas">
        {CATALOGOS.map((c) => (
          <button
            key={c.clave}
            type="button"
            className={`pestana${c.clave === catalogo.clave ? ' activa' : ''}`}
            aria-pressed={c.clave === catalogo.clave}
            onClick={() =>
              cambiar({ catalogo: c.clave, busqueda: null, estado: null, page: null })
            }
          >
            {c.nombre}
          </button>
        ))}
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
            placeholder={`Nombre del ${catalogo.singular}`}
            onChange={(event) => setTexto(event.target.value)}
          />
        </Campo>
        {catalogo.estado && (
          <Campo id="filtro-estado" etiqueta="Estado">
            <select
              id="filtro-estado"
              value={estado}
              onChange={(event) =>
                cambiar({ estado: event.target.value, page: null })
              }
            >
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </select>
          </Campo>
        )}
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {(busqueda || estado) && (
            <button
              className="boton-secundario"
              type="button"
              onClick={() => cambiar({ busqueda: null, estado: null, page: null })}
            >
              Limpiar
            </button>
          )}
        </div>
      </form>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay {catalogo.nombre.toLowerCase()} que coincidan con la búsqueda.</p>
          <p className="nota">
            {puedeCrear
              ? 'Prueba a limpiar los filtros o usa el botón de arriba para crear uno nuevo.'
              : 'Prueba a limpiar los filtros.'}
          </p>
        </div>
      ) : (
        datos && (
          <Tabla refrescando={refrescando} filas={datos.results} columnas={columnas} />
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
        onCerrar={() => setConfirmacion(null)}
      />

      {altaAbierta && (
        <CatalogoFormulario
          catalogo={catalogo}
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {edicionId !== null && (
        <CatalogoFormulario
          catalogo={catalogo}
          id={edicionId}
          abierto
          onGuardado={() => {
            setEdicionId(null)
            refrescar()
          }}
          onCancelar={() => setEdicionId(null)}
        />
      )}
    </>
  )
}
