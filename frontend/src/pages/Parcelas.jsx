import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listarTodo } from '../api/catalogos.js'
import { mensajeDeError } from '../api/errores.js'
import { listarParcelas } from '../api/parcelas.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'
import { useSesion } from '../context/useSesion.js'
import ParcelaFicha from './ParcelaFicha.jsx'
import ParcelaFormulario from './ParcelaFormulario.jsx'
import ProductorFicha from './ProductorFicha.jsx'

export default function Parcelas() {
  const { tienePermiso } = useSesion()
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const estado = params.get('estado') ?? ''
  const comunidad = params.get('comunidad') ?? ''
  const pagina = Number(params.get('page') ?? 1)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${estado}|${comunidad}|${pagina}|${recarga}`

  const [texto, setTexto] = useState(busqueda)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [comunidades, setComunidades] = useState([])
  const [error, setError] = useState(null)
  const [edicionId, setEdicionId] = useState(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [fichaId, setFichaId] = useState(null)
  const [parcelaFichaId, setParcelaFichaId] = useState(null)
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
    for (const [clave, valor] of Object.entries(cambios)) {
      if (valor === null || valor === undefined || valor === '') nuevo.delete(clave)
      else nuevo.set(clave, String(valor))
    }
    setParams(nuevo)
  }

  useEffect(() => {
    let activo = true
    listarTodo('/ubicaciones/comunidades/', { activo: 'true' })
      .then((lista) => {
        if (activo) setComunidades(lista)
      })
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    let activo = true
    const filtros = {}
    if (busqueda) filtros.busqueda = busqueda
    if (estado) filtros.estado = estado
    if (comunidad) filtros.comunidad = comunidad
    if (pagina > 1) filtros.page = pagina
    listarParcelas(filtros)
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
  }, [busqueda, estado, comunidad, pagina, clave])

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Parcelas</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
        {tienePermiso('parcelas.crear') && (
          <button
            className="boton-primario"
            type="button"
            onClick={() => setAltaAbierta(true)}
          >
            Nueva parcela
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
            placeholder="Código, productor o referencia"
            onChange={(event) => setTexto(event.target.value)}
          />
        </Campo>
        <Campo id="filtro-estado" etiqueta="Estado">
          <select
            id="filtro-estado"
            value={estado}
            onChange={(event) => cambiar({ estado: event.target.value, page: null })}
          >
            <option value="">Todas</option>
            <option value="ACTIVA">Activas</option>
            <option value="INACTIVA">Inactivas</option>
          </select>
        </Campo>
        <Campo id="filtro-comunidad" etiqueta="Comunidad">
          <select
            id="filtro-comunidad"
            value={comunidad}
            onChange={(event) => cambiar({ comunidad: event.target.value, page: null })}
          >
            <option value="">Todas</option>
            {comunidades.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Buscar
          </button>
          {(busqueda || estado || comunidad) && (
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
          <p>No hay parcelas que coincidan con la búsqueda.</p>
          <p className="nota">
            Prueba a limpiar los filtros o registra una parcela nueva.
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            refrescando={refrescando}
            filas={datos.results}
            columnas={[
              {
                clave: 'codigo',
                etiqueta: 'Código',
                celda: (fila) => (
                  <span className="chip-codigo">{fila.codigo}</span>
                ),
              },
              {
                clave: 'productor',
                etiqueta: 'Productor',
                celda: (fila) => (
                  <button
                    type="button"
                    className="boton-texto"
                    onClick={() => setFichaId(fila.productor.id)}
                  >
                    {fila.productor.nombre_completo}
                  </button>
                ),
              },
              {
                clave: 'comunidad',
                etiqueta: 'Comunidad',
                celda: (fila) => fila.comunidad.nombre,
              },
              {
                clave: 'superficie',
                etiqueta: 'Superficie',
                celda: (fila) => `${fila.superficie_ha} ha`,
              },
              {
                clave: 'estado',
                etiqueta: 'Estado',
                celda: (fila) => <Chip>{fila.estado}</Chip>,
              },
              {
                clave: 'acciones',
                etiqueta: 'Acciones',
                acciones: true,
                celda: (fila) =>
                  tienePermiso('parcelas.editar') ? (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setEdicionId(fila.id)}
                    >
                      Editar
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="boton-texto"
                      onClick={() => setParcelaFichaId(fila.id)}
                    >
                      Ver ficha
                    </button>
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

      {edicionId !== null && (
        <ParcelaFormulario
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
        <ParcelaFormulario
          abierto
          onGuardado={() => {
            setAltaAbierta(false)
            refrescar()
          }}
          onCancelar={() => setAltaAbierta(false)}
        />
      )}

      {fichaId !== null && (
        <ProductorFicha
          id={fichaId}
          abierto
          onCerrar={() => {
            setFichaId(null)
            refrescar()
          }}
        />
      )}

      {parcelaFichaId !== null && (
        <ParcelaFicha
          id={parcelaFichaId}
          abierto
          onCerrar={() => {
            setParcelaFichaId(null)
            refrescar()
          }}
        />
      )}
    </>
  )
}
