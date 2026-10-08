import { useEffect, useState } from 'react'
import { cliente } from '../api/cliente.js'
import {
  listarTodo,
  obtenerComunidades,
  obtenerDistritos,
  obtenerProvincias,
} from '../api/catalogos.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import {
  DISPONIBILIDADES_AGUA,
  PENDIENTES,
  SISTEMAS_RIEGO,
  TIPOS_SUELO,
  estadoParcela,
  guardarParcela,
  obtenerParcela,
} from '../api/parcelas.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

const VACIO = {
  productor: '',
  provincia: '',
  distrito: '',
  comunidad: '',
  superficie_ha: '',
  altitud_msnm: '',
  latitud: '',
  longitud: '',
  tipo_suelo: '',
  pendiente: '',
  disponibilidad_agua: '',
  sistema_riego: '',
  referencia_ubicacion: '',
}

async function ubicacionDeComunidad(comunidadId) {
  const { data } = await cliente.get(`/ubicaciones/comunidades/${comunidadId}/`)
  return {
    provincia: String(data.distrito.provincia.id),
    distrito: String(data.distrito.id),
    comunidad: String(data.id),
  }
}

export default function ParcelaFormulario({
  id,
  productorInicial = '',
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState(() => ({
    ...VACIO,
    productor: productorInicial,
  }))
  const [productores, setProductores] = useState([])
  const [provincias, setProvincias] = useState([])
  const [distritosCargados, setDistritosCargados] = useState({
    provincia: null,
    lista: [],
  })
  const [comunidadesCargadas, setComunidadesCargadas] = useState({
    distrito: null,
    lista: [],
  })
  const [estado, setEstado] = useState(null)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [catalogosListos, setCatalogosListos] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)
  const [confirmacion, setConfirmacion] = useState(null)

  const distritos =
    form.provincia && distritosCargados.provincia === form.provincia
      ? distritosCargados.lista
      : []
  const comunidades =
    form.distrito && comunidadesCargadas.distrito === form.distrito
      ? comunidadesCargadas.lista
      : []
  const cargando = !catalogosListos || !hidratado

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  async function alElegirProductor(valor) {
    cambiar('productor', valor)
    if (!valor) return
    try {
      const { data: productor } = await cliente.get(`/productores/${valor}/`)
      const ubicacion = await ubicacionDeComunidad(productor.comunidad)
      setForm((actual) => ({ ...actual, productor: valor, ...ubicacion }))
    } catch {
      // Se conserva la comunidad elegida a mano
    }
  }

  useEffect(() => {
    let activo = true
    Promise.all([
      listarTodo('/productores/'),
      obtenerProvincias(),
    ])
      .then(([listaProductores, listaProvincias]) => {
        if (!activo) return
        setProductores(listaProductores)
        setProvincias(listaProvincias)
      })
      .catch(() => {})
      .finally(() => activo && setCatalogosListos(true))
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    if (!form.provincia) return undefined
    let activo = true
    obtenerDistritos(form.provincia)
      .then((lista) =>
        activo && setDistritosCargados({ provincia: form.provincia, lista }),
      )
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [form.provincia])

  useEffect(() => {
    if (!form.distrito) return undefined
    let activo = true
    obtenerComunidades(form.distrito)
      .then((lista) =>
        activo && setComunidadesCargadas({ distrito: form.distrito, lista }),
      )
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [form.distrito])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerParcela(id)
      .then(async (parcela) => {
        if (!activo) return
        const ubicacion = await ubicacionDeComunidad(parcela.comunidad.id)
        if (!activo) return
        setForm({
          productor: String(parcela.productor.id),
          ...ubicacion,
          superficie_ha: parcela.superficie_ha,
          altitud_msnm: String(parcela.altitud_msnm),
          latitud: parcela.latitud ?? '',
          longitud: parcela.longitud ?? '',
          tipo_suelo: parcela.tipo_suelo ?? '',
          pendiente: parcela.pendiente ?? '',
          disponibilidad_agua: parcela.disponibilidad_agua ?? '',
          sistema_riego: parcela.sistema_riego ?? '',
          referencia_ubicacion: parcela.referencia_ubicacion ?? '',
        })
        setEstado(parcela.estado)
        setError(null)
        setHidratado(true)
      })
      .catch((e) => {
        if (!activo) return
        setError(mensajeDeError(e))
        setHidratado(true)
      })
    return () => {
      activo = false
    }
  }, [id, esEdicion])

  useEffect(() => {
    if (esEdicion || !productorInicial) return undefined
    let activo = true
    cliente
      .get(`/productores/${productorInicial}/`)
      .then(({ data: productor }) => ubicacionDeComunidad(productor.comunidad))
      .then((ubicacion) => {
        if (activo) {
          setForm((actual) => ({
            ...actual,
            productor: productorInicial,
            ...ubicacion,
          }))
        }
      })
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [esEdicion, productorInicial])

  async function enviar(event) {
    event.preventDefault()
    setErrores({})
    setError(null)

    if (!form.productor) {
      setErrores({ productor: 'El productor es obligatorio.' })
      return
    }
    if (!form.comunidad) {
      setErrores({ comunidad: 'La comunidad es obligatoria.' })
      return
    }
    const conLatitud = form.latitud.trim() !== ''
    const conLongitud = form.longitud.trim() !== ''
    if (conLatitud !== conLongitud) {
      setError('Las coordenadas deben ir las dos o ninguna.')
      return
    }

    const datos = {
      comunidad: Number(form.comunidad),
      superficie_ha: form.superficie_ha.trim(),
      altitud_msnm: form.altitud_msnm.trim(),
      latitud: conLatitud ? form.latitud.trim() : null,
      longitud: conLongitud ? form.longitud.trim() : null,
      tipo_suelo: form.tipo_suelo || null,
      pendiente: form.pendiente || null,
      disponibilidad_agua: form.disponibilidad_agua || null,
      sistema_riego: form.sistema_riego || null,
      referencia_ubicacion: form.referencia_ubicacion.trim() || null,
    }
    if (!esEdicion) datos.productor = Number(form.productor)

    setGuardando(true)
    try {
      const guardada = await guardarParcela(id, datos)
      avisar(esEdicion ? 'Parcela guardada.' : 'Parcela creada.')
      onGuardado?.(guardada)
    } catch (e) {
      if (e.response?.status === 400) {
        const campos = erroresDeCampo(e.response.data)
        setErrores(campos)
        // Con errores de campo ya se ven junto al campo: no se duplican.
        if (Object.keys(campos).length > 0) return
      }
      avisar(mensajeDeError(e), 'error')
    } finally {
      setGuardando(false)
    }
  }

  function pedirCambioEstado() {
    const nuevo = estado === 'ACTIVA' ? 'INACTIVA' : 'ACTIVA'
    setConfirmacion({
      titulo: nuevo === 'INACTIVA' ? 'Desactivar parcela' : 'Reactivar parcela',
      texto:
        nuevo === 'INACTIVA'
          ? '¿Desactivar esta parcela? El registro se conserva.'
          : '¿Reactivar esta parcela?',
      confirmar: nuevo === 'INACTIVA' ? 'Desactivar' : 'Reactivar',
      nivel: nuevo === 'INACTIVA' ? 'peligro' : 'primario',
      accion: () => alternarEstado(nuevo),
    })
  }

  async function alternarEstado(nuevo) {
    setGuardando(true)
    try {
      const actualizada = await estadoParcela(id, nuevo)
      setEstado(actualizada.estado)
      avisar(nuevo === 'INACTIVA' ? 'Parcela desactivada.' : 'Parcela reactivada.')
    } catch (e) {
      avisar(mensajeDeError(e), 'error')
    } finally {
      setGuardando(false)
    }
  }

  async function ejecutarConfirmacion() {
    if (!confirmacion) return
    await confirmacion.accion()
    setConfirmacion(null)
  }

  const productorActual = productores.find(
    (p) => String(p.id) === String(form.productor),
  )

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo={esEdicion ? 'Editar parcela' : 'Nueva parcela'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {esEdicion && estado && (
        <div className="pagina-cabecera">
          <div className="ficha-acciones">
            <Chip>{estado}</Chip>
            <button
              type="button"
              className={estado === 'ACTIVA' ? 'boton-peligro' : 'boton-primario'}
              disabled={guardando}
              onClick={pedirCambioEstado}
            >
              {estado === 'ACTIVA' ? 'Desactivar' : 'Reactivar'}
            </button>
          </div>
        </div>
      )}

      {cargando ? <Cargando /> : (
      <form onSubmit={enviar} className="formulario-pagina">
        <section className="panel">
          <h2>Asignación</h2>
          <Campo
            id="productor"
            etiqueta="Productor"
            error={errores.productor}
            ayuda={
              esEdicion
                ? 'El productor de una parcela no se puede cambiar.'
                : undefined
            }
          >
            {esEdicion ? (
              <input
                id="productor"
                value={
                  productorActual
                    ? `${productorActual.nombre_completo} (${productorActual.codigo})`
                    : form.productor
                }
                disabled
              />
            ) : (
              <select
                id="productor"
                value={form.productor}
                onChange={(e) => alElegirProductor(e.target.value)}
              >
                <option value="">Elige un productor</option>
                {productores.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre_completo} ({p.codigo})
                  </option>
                ))}
              </select>
            )}
          </Campo>
        </section>

        <section className="panel">
          <h2>Datos de la parcela</h2>
          <Campo
            id="superficie_ha"
            etiqueta="Superficie (ha)"
            error={errores.superficie_ha}
            ayuda="Mayor que 0, hasta 2 decimales."
          >
            <input
              id="superficie_ha"
              inputMode="decimal"
              value={form.superficie_ha}
              onChange={(e) => cambiar('superficie_ha', e.target.value)}
            />
          </Campo>
          <Campo
            id="altitud_msnm"
            etiqueta="Altitud (msnm)"
            error={errores.altitud_msnm}
            ayuda="Entre 0 y 6500."
          >
            <input
              id="altitud_msnm"
              inputMode="numeric"
              value={form.altitud_msnm}
              onChange={(e) => cambiar('altitud_msnm', e.target.value)}
            />
          </Campo>
          <Campo
            id="latitud"
            etiqueta="Latitud"
            error={errores.latitud}
            ayuda="Opcional, pero con longitud (las dos o ninguna)."
          >
            <input
              id="latitud"
              inputMode="decimal"
              placeholder="-15.123456"
              value={form.latitud}
              onChange={(e) => cambiar('latitud', e.target.value)}
            />
          </Campo>
          <Campo
            id="longitud"
            etiqueta="Longitud"
            error={errores.longitud}
            ayuda="Opcional, pero con latitud (las dos o ninguna)."
          >
            <input
              id="longitud"
              inputMode="decimal"
              placeholder="-70.987654"
              value={form.longitud}
              onChange={(e) => cambiar('longitud', e.target.value)}
            />
          </Campo>
          <Campo id="tipo_suelo" etiqueta="Tipo de suelo" error={errores.tipo_suelo}>
            <select
              id="tipo_suelo"
              value={form.tipo_suelo}
              onChange={(e) => cambiar('tipo_suelo', e.target.value)}
            >
              <option value="">Sin especificar</option>
              {TIPOS_SUELO.map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </Campo>
          <Campo id="pendiente" etiqueta="Pendiente" error={errores.pendiente}>
            <select
              id="pendiente"
              value={form.pendiente}
              onChange={(e) => cambiar('pendiente', e.target.value)}
            >
              <option value="">Sin especificar</option>
              {PENDIENTES.map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </Campo>
          <Campo
            id="disponibilidad_agua"
            etiqueta="Disponibilidad de agua"
            error={errores.disponibilidad_agua}
          >
            <select
              id="disponibilidad_agua"
              value={form.disponibilidad_agua}
              onChange={(e) => cambiar('disponibilidad_agua', e.target.value)}
            >
              <option value="">Sin especificar</option>
              {DISPONIBILIDADES_AGUA.map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </Campo>
          <Campo
            id="sistema_riego"
            etiqueta="Sistema de riego"
            error={errores.sistema_riego}
          >
            <select
              id="sistema_riego"
              value={form.sistema_riego}
              onChange={(e) => cambiar('sistema_riego', e.target.value)}
            >
              <option value="">Sin especificar</option>
              {SISTEMAS_RIEGO.map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </Campo>
          <Campo
            id="referencia_ubicacion"
            etiqueta="Referencia de ubicación"
            error={errores.referencia_ubicacion}
          >
            <input
              id="referencia_ubicacion"
              value={form.referencia_ubicacion}
              onChange={(e) => cambiar('referencia_ubicacion', e.target.value)}
            />
          </Campo>
        </section>

        <section className="panel">
          <h2>Ubicación (comunidad)</h2>
          <Campo id="provincia" etiqueta="Provincia">
            <select
              id="provincia"
              value={form.provincia}
              onChange={(e) =>
                setForm((actual) => ({
                  ...actual,
                  provincia: e.target.value,
                  distrito: '',
                  comunidad: '',
                }))
              }
            >
              <option value="">Elige una provincia</option>
              {provincias.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </Campo>
          <Campo id="distrito" etiqueta="Distrito">
            <select
              id="distrito"
              value={form.distrito}
              disabled={!form.provincia}
              onChange={(e) =>
                setForm((actual) => ({
                  ...actual,
                  distrito: e.target.value,
                  comunidad: '',
                }))
              }
            >
              <option value="">
                {form.provincia ? 'Elige un distrito' : 'Primero la provincia'}
              </option>
              {distritos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nombre}
                </option>
              ))}
            </select>
          </Campo>
          <Campo id="comunidad" etiqueta="Comunidad" error={errores.comunidad}>
            <select
              id="comunidad"
              value={form.comunidad}
              disabled={!form.distrito}
              onChange={(e) => cambiar('comunidad', e.target.value)}
            >
              <option value="">
                {form.distrito ? 'Elige una comunidad' : 'Primero el distrito'}
              </option>
              {comunidades.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Campo>
        </section>

        <div className="formulario-acciones">
          <button className="boton-primario" type="submit" disabled={guardando}>
            {guardando ? (
              <>
                <RuedaCarga etiqueta="Guardando…" />
                Guardando…
              </>
            ) : esEdicion ? (
              'Guardar cambios'
            ) : (
              'Crear parcela'
            )}
          </button>
          <button className="boton-secundario" type="button" onClick={onCancelar}>
            Cancelar
          </button>
        </div>
      </form>
      )}

      <Modal
        abierto={confirmacion !== null}
        titulo={confirmacion?.titulo}
        texto={confirmacion?.texto}
        confirmar={confirmacion?.confirmar}
        nivel={confirmacion?.nivel}
        ocupado={guardando}
        onConfirmar={ejecutarConfirmacion}
        onCerrar={() => setConfirmacion(null)}
      />
    </Modal>
  )
}
