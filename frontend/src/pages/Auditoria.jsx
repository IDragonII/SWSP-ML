import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ACCIONES_AUDITORIA, listarAuditoria } from '../api/auditoria.js'
import { mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Paginacion from '../components/Paginacion.jsx'
import Tabla from '../components/Tabla.jsx'

const ETIQUETAS_ACCION = {
  CREAR: 'Crear',
  MODIFICAR: 'Modificar',
  ELIMINAR: 'Eliminar',
  ACTIVAR: 'Activar',
  DESACTIVAR: 'Desactivar',
  ANULAR: 'Anular',
  REACTIVAR: 'Reactivar',
  ASIGNAR: 'Asignar',
  DESASIGNAR: 'Desasignar',
  LOGIN: 'Entrar',
  LOGOUT: 'Salir',
  BLOQUEAR: 'Bloquear',
  DESBLOQUEAR: 'Desbloquear',
  RESTABLECER_CLAVE: 'Restablecer clave',
  CAMBIAR_CLAVE: 'Cambiar clave',
}

const TABLAS_CONOCIDAS = {
  productores: 'Productor',
  parcelas: 'Parcela',
  usuarios: 'Usuario',
  cultivos: 'Cultivo',
}

export default function Auditoria() {
  const [params, setParams] = useSearchParams()

  const busqueda = params.get('busqueda') ?? ''
  const modulo = params.get('modulo') ?? ''
  const accion = params.get('accion') ?? ''
  const fechaDesde = params.get('fecha_desde') ?? ''
  const fechaHasta = params.get('fecha_hasta') ?? ''
  const tabla = params.get('tabla') ?? ''
  const registro = params.get('registro') ?? ''
  const pagina = Number(params.get('page') ?? 1)

  const [texto, setTexto] = useState(busqueda)
  const [moduloTexto, setModuloTexto] = useState(modulo)
  const [busquedaPrevia, setBusquedaPrevia] = useState(busqueda)
  const [moduloPrevio, setModuloPrevio] = useState(modulo)
  const [recarga, setRecarga] = useState(0)
  const clave = `${busqueda}|${modulo}|${accion}|${fechaDesde}|${fechaHasta}|${tabla}|${registro}|${pagina}|${recarga}`
  const [datos, setDatos] = useState(null)
  const [claveCargada, setClaveCargada] = useState(null)
  const [error, setError] = useState(null)
  const refrescando = datos !== null && claveCargada !== clave

  // Sincroniza los campos de texto cuando la URL cambia (p. ej. al
  // llegar de «Ver historial» o al Limpiar), mismo patrón que Usuarios
  if (busquedaPrevia !== busqueda) {
    setBusquedaPrevia(busqueda)
    setTexto(busqueda)
  }
  if (moduloPrevio !== modulo) {
    setModuloPrevio(modulo)
    setModuloTexto(modulo)
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
    if (modulo) filtros.modulo = modulo
    if (accion) filtros.accion = accion
    if (fechaDesde) filtros.fecha_desde = fechaDesde
    if (fechaHasta) filtros.fecha_hasta = fechaHasta
    if (tabla) filtros.tabla = tabla
    if (registro) filtros.registro = registro
    if (pagina > 1) filtros.page = pagina
    listarAuditoria(filtros)
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
  }, [busqueda, modulo, accion, fechaDesde, fechaHasta, tabla, registro, pagina, clave])

  const hayHistorial = Boolean(tabla && registro)
  const nombreTabla = TABLAS_CONOCIDAS[tabla] ?? tabla

  if (!datos && !error) return <Cargando />

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Auditoría</h1>
          <p className="conteo">
            {datos
              ? `${datos.count} evento(s) — registro inmutable de acciones`
              : 'Sin datos'}
          </p>
        </div>
        <div className="ficha-acciones">
          <button
            className="boton-secundario"
            type="button"
            onClick={() => setRecarga((n) => n + 1)}
          >
            Actualizar
          </button>
          {hayHistorial && (
            <button
              className="boton-secundario"
              type="button"
              onClick={() =>
                cambiar({ tabla: null, registro: null, page: null })
              }
            >
              Quitar historial de {nombreTabla} #{registro}
            </button>
          )}
        </div>
      </div>

      <form
        className="filtros"
        onSubmit={(evento) => {
          evento.preventDefault()
          cambiar({
            busqueda: texto.trim(),
            modulo: moduloTexto.trim(),
            page: null,
          })
        }}
      >
        <Campo id="filtro-busqueda" etiqueta="Buscar">
          <input
            id="filtro-busqueda"
            type="search"
            value={texto}
            placeholder="Módulo, acción o tabla"
            onChange={(evento) => setTexto(evento.target.value)}
          />
        </Campo>
        <Campo id="filtro-modulo" etiqueta="Módulo">
          <input
            id="filtro-modulo"
            type="text"
            value={moduloTexto}
            placeholder="p. ej. productores"
            onChange={(evento) => setModuloTexto(evento.target.value)}
          />
        </Campo>
        <Campo id="filtro-accion" etiqueta="Acción">
          <select
            id="filtro-accion"
            value={accion}
            onChange={(evento) => cambiar({ accion: evento.target.value, page: null })}
          >
            <option value="">Todas</option>
            {ACCIONES_AUDITORIA.map((opcion) => (
              <option key={opcion} value={opcion}>
                {ETIQUETAS_ACCION[opcion] ?? opcion}
              </option>
            ))}
          </select>
        </Campo>
        <Campo id="filtro-desde" etiqueta="Desde">
          <input
            id="filtro-desde"
            type="date"
            value={fechaDesde}
            onChange={(evento) =>
              cambiar({ fecha_desde: evento.target.value, page: null })
            }
          />
        </Campo>
        <Campo id="filtro-hasta" etiqueta="Hasta">
          <input
            id="filtro-hasta"
            type="date"
            value={fechaHasta}
            onChange={(evento) =>
              cambiar({ fecha_hasta: evento.target.value, page: null })
            }
          />
        </Campo>
        <div className="filtros-acciones">
          <button className="boton-primario" type="submit">
            Aplicar
          </button>
          <button
            className="boton-secundario"
            type="button"
            onClick={() => setParams(hayHistorial ? { tabla, registro } : {})}
          >
            Limpiar
          </button>
        </div>
      </form>

      <Aviso>{error}</Aviso>

      {datos && datos.results.length === 0 ? (
        <div className="panel">
          <p>No hay eventos que coincidan con los filtros.</p>
          <p className="nota">
            La auditoría solo registra acciones (escrituras y accesos); las
            lecturas no dejan eventos.
          </p>
        </div>
      ) : (
        datos && (
          <Tabla
            refrescando={refrescando}
            filas={datos.results}
            columnas={[
              {
                clave: 'fecha',
                etiqueta: 'Fecha',
                celda: (fila) =>
                  new Date(fila.fecha).toLocaleString('es-PE', {
                    dateStyle: 'short',
                    timeStyle: 'medium',
                  }),
              },
              {
                clave: 'usuario',
                etiqueta: 'Usuario',
                celda: (fila) =>
                  fila.usuario ? (
                    <span className="chip-codigo">{fila.usuario.username}</span>
                  ) : (
                    '—'
                  ),
              },
              {
                clave: 'accion',
                etiqueta: 'Acción',
                celda: (fila) => (
                  <Chip>{ETIQUETAS_ACCION[fila.accion] ?? fila.accion}</Chip>
                ),
              },
              {
                clave: 'modulo',
                etiqueta: 'Módulo',
                celda: (fila) => fila.modulo,
              },
              {
                clave: 'tabla',
                etiqueta: 'Tabla',
                celda: (fila) => fila.tabla ?? '—',
              },
              {
                clave: 'registro_id',
                etiqueta: 'Registro',
                celda: (fila) => fila.registro_id ?? '—',
              },
              {
                clave: 'detalle',
                etiqueta: 'Detalle',
                celda: (fila) =>
                  fila.detalle ? (
                    <code className="chip-codigo">
                      {JSON.stringify(fila.detalle)}
                    </code>
                  ) : (
                    '—'
                  ),
              },
              {
                clave: 'ip',
                etiqueta: 'IP',
                celda: (fila) => fila.ip ?? '—',
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
    </>
  )
}
