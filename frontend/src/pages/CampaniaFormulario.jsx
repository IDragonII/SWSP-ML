import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import {
  cancelarCampania,
  guardarCampania,
  iniciarCampania,
  obtenerCampania,
} from '../api/campanias.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Chip from '../components/Chip.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'
import { useSesion } from '../context/useSesion.js'

const VACIO = {
  periodo: '',
  parcela: '',
  cultivo: '',
  variedad: '',
  fecha_inicio: '',
  fecha_fin_prevista: '',
  superficie_sembrada_ha: '',
  observaciones: '',
}

// Campos que la API bloquea al iniciar la campaña (y que en cancelada
// quedan solo lectura): definen la fila del dataset y las etapas.
const BLOQUEADOS_EN_PRODUCCION = [
  'parcela',
  'cultivo',
  'variedad',
  'periodo',
  'fecha_inicio',
]

function validarPeriodo(periodo) {
  if (!/^\d{4}-\d{4}$/.test(periodo)) {
    return 'El período debe tener el formato AAAA-AAAA (por ejemplo 2025-2026).'
  }
  const anio1 = Number(periodo.slice(0, 4))
  const anio2 = Number(periodo.slice(5))
  if (anio2 !== anio1 + 1) {
    return 'El segundo año del período debe ser uno más que el primero (por ejemplo 2025-2026).'
  }
  return null
}

export default function CampaniaFormulario({
  id,
  parcelaInicial = '',
  productorInicial = '',
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()
  const { tienePermiso } = useSesion()

  const [form, setForm] = useState(() => ({
    ...VACIO,
    parcela: parcelaInicial,
  }))
  const [parcelas, setParcelas] = useState([])
  const [cultivos, setCultivos] = useState([])
  const [variedades, setVariedades] = useState({ cultivo: null, lista: [] })
  const [estado, setEstado] = useState(null)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [listo, setListo] = useState(false)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [confirmacion, setConfirmacion] = useState(null)

  const esCancelada = estado === 'CANCELADA'
  const enProduccion = estado === 'EN_PRODUCCION'
  const soloLectura = esCancelada
  const cargando = !listo || !hidratado
  const listaVariedades =
    variedades.cultivo === form.cultivo ? variedades.lista : []

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    const filtrosParcelas = { desplegable: 1 }
    if (productorInicial) filtrosParcelas.productor = productorInicial
    Promise.all([
      listarTodo('/parcelas/', filtrosParcelas),
      listarTodo('/cultivos/', { activo: 'true' }),
    ])
      .then(([listaParcelas, listaCultivos]) => {
        if (!activo) return
        setParcelas(listaParcelas)
        setCultivos(listaCultivos)
      })
      .catch(() => {})
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [productorInicial])

  useEffect(() => {
    if (!form.cultivo) return undefined
    let activo = true
    listarTodo('/variedades/', { activo: 'true', cultivo: form.cultivo })
      .then((lista) =>
        activo && setVariedades({ cultivo: form.cultivo, lista }),
      )
      .catch(() => {})
    return () => {
      activo = false
    }
  }, [form.cultivo])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    obtenerCampania(id)
      .then((campania) => {
        if (!activo) return
        setForm({
          periodo: campania.periodo,
          parcela: String(campania.parcela.id),
          cultivo: String(campania.cultivo.id),
          variedad: String(campania.variedad.id),
          fecha_inicio: campania.fecha_inicio,
          fecha_fin_prevista: campania.fecha_fin_prevista,
          superficie_sembrada_ha: String(campania.superficie_sembrada_ha),
          observaciones: campania.observaciones ?? '',
        })
        setEstado(campania.estado)
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

  async function alElegirCultivo(valor) {
    cambiar('cultivo', valor)
    cambiar('variedad', '')
  }

  function validarCliente() {
    const fallos = {}
    if (!form.periodo.trim()) fallos.periodo = 'El período es obligatorio.'
    else {
      const periodoError = validarPeriodo(form.periodo.trim())
      if (periodoError) fallos.periodo = periodoError
    }
    if (!form.parcela) fallos.parcela = 'La parcela es obligatoria.'
    if (!form.cultivo) fallos.cultivo = 'El cultivo es obligatorio.'
    if (!form.variedad) fallos.variedad = 'La variedad es obligatoria.'
    if (!form.fecha_inicio) {
      fallos.fecha_inicio = 'La fecha de inicio es obligatoria.'
    }
    if (!form.fecha_fin_prevista) {
      fallos.fecha_fin_prevista = 'La fecha de fin prevista es obligatoria.'
    } else if (
      form.fecha_inicio &&
      form.fecha_fin_prevista < form.fecha_inicio
    ) {
      fallos.fecha_fin_prevista =
        'La fecha de fin prevista no puede ser anterior a la de inicio.'
    }
    if (form.superficie_sembrada_ha.trim()) {
      const valor = Number(form.superficie_sembrada_ha.trim())
      if (Number.isNaN(valor) || valor <= 0) {
        fallos.superficie_sembrada_ha =
          'La superficie sembrada debe ser mayor que 0.'
      }
    }
    return fallos
  }

  async function enviar(event) {
    event.preventDefault()
    setErrores({})
    setError(null)

    const fallos = validarCliente()
    if (Object.keys(fallos).length > 0) {
      setErrores(fallos)
      return
    }

    const datos = {
      periodo: form.periodo.trim(),
      parcela: Number(form.parcela),
      cultivo: Number(form.cultivo),
      variedad: Number(form.variedad),
      fecha_inicio: form.fecha_inicio,
      fecha_fin_prevista: form.fecha_fin_prevista,
      observaciones: form.observaciones.trim(),
    }
    if (form.superficie_sembrada_ha.trim()) {
      datos.superficie_sembrada_ha = form.superficie_sembrada_ha.trim()
    }
    // En producción los campos bloqueados no viajan: la API los rechaza
    // aunque el valor sea el mismo.
    if (esEdicion && enProduccion) {
      for (const campo of BLOQUEADOS_EN_PRODUCCION) delete datos[campo]
    }

    setGuardando(true)
    try {
      const guardada = await guardarCampania(id, datos)
      avisar(esEdicion ? 'Campaña guardada.' : 'Campaña creada.')
      onGuardado?.(guardada)
    } catch (e) {
      if (e.response?.status === 400) {
        const campos = erroresDeCampo(e.response.data)
        setErrores(campos)
        if (Object.keys(campos).length > 0) return
      }
      avisar(mensajeDeError(e), 'error')
    } finally {
      setGuardando(false)
    }
  }

  function pedirInicio() {
    setConfirmacion({
      titulo: 'Iniciar campaña',
      texto: '¿Iniciar esta campaña? Pasará a EN_PRODUCCION y sus campos de identidad (parcela, cultivo, variedad, período y fecha de inicio) quedarán bloqueados.',
      confirmar: 'Iniciar',
      accion: async () => {
        setGuardando(true)
        try {
          await iniciarCampania(id)
          avisar('Campaña iniciada.')
          onGuardado?.()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setGuardando(false)
        }
      },
    })
  }

  function pedirCancelacion() {
    const limpio = motivo.trim()
    if (!limpio) return
    setConfirmacion({
      titulo: 'Cancelar campaña',
      texto: `¿Cancelar esta campaña? El motivo quedará en las observaciones: «${limpio}». Una cancelada no admite cambios.`,
      confirmar: 'Cancelar campaña',
      nivel: 'peligro',
      accion: async () => {
        setGuardando(true)
        try {
          await cancelarCampania(id, limpio)
          avisar('Campaña cancelada.')
          onGuardado?.()
        } catch (e) {
          avisar(mensajeDeError(e), 'error')
        } finally {
          setGuardando(false)
        }
      },
    })
  }

  async function ejecutarConfirmacion() {
    if (!confirmacion) return
    await confirmacion.accion()
    setConfirmacion(null)
  }

  const parcelaActual = parcelas.find(
    (p) => String(p.id) === String(form.parcela),
  )

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo={esEdicion ? 'Editar campaña' : 'Nueva campaña'}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {esEdicion && estado && (
        <div className="pagina-cabecera">
          <div className="ficha-acciones">
            <Chip>{estado}</Chip>
            {estado === 'PLANIFICADA' && (
              <button
                type="button"
                className="boton-primario"
                disabled={guardando}
                onClick={pedirInicio}
              >
                Iniciar campaña
              </button>
            )}
          </div>
        </div>
      )}

      {esCancelada && (
        <p className="nota">
          Esta campaña está cancelada: es de solo lectura y no admite cambios.
        </p>
      )}

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Identidad de la campaña</h2>
            <Campo
              id="periodo"
              etiqueta="Período"
              error={errores.periodo}
              ayuda="Formato AAAA-AAAA; el segundo año es uno más (2025-2026)."
            >
              <input
                id="periodo"
                placeholder="2025-2026"
                value={form.periodo}
                disabled={soloLectura || enProduccion}
                onChange={(e) => cambiar('periodo', e.target.value)}
              />
            </Campo>
            <Campo
              id="parcela"
              etiqueta="Parcela"
              error={errores.parcela}
              ayuda={
                esEdicion && !soloLectura && !enProduccion
                  ? 'Se usa para fijar el cultivo de la campaña.'
                  : undefined
              }
            >
              <select
                id="parcela"
                value={form.parcela}
                disabled={soloLectura || enProduccion}
                onChange={(e) => cambiar('parcela', e.target.value)}
              >
                <option value="">Elige una parcela</option>
                {parcelas.map((parcela) => (
                  <option key={parcela.id} value={parcela.id}>
                    {parcela.codigo} — {parcela.productor.nombre_completo}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo id="cultivo" etiqueta="Cultivo" error={errores.cultivo}>
              <select
                id="cultivo"
                value={form.cultivo}
                disabled={soloLectura || enProduccion}
                onChange={(e) => alElegirCultivo(e.target.value)}
              >
                <option value="">Elige un cultivo</option>
                {cultivos.map((cultivo) => (
                  <option key={cultivo.id} value={cultivo.id}>
                    {cultivo.nombre}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="variedad"
              etiqueta="Variedad"
              error={errores.variedad}
              ayuda="Solo las variedades del cultivo elegido."
            >
              <select
                id="variedad"
                value={form.variedad}
                disabled={soloLectura || enProduccion || !form.cultivo}
                onChange={(e) => cambiar('variedad', e.target.value)}
              >
                <option value="">
                  {form.cultivo
                    ? 'Elige una variedad'
                    : 'Primero el cultivo'}
                </option>
                {listaVariedades.map((variedad) => (
                  <option key={variedad.id} value={variedad.id}>
                    {variedad.nombre}
                  </option>
                ))}
              </select>
            </Campo>
          </section>

          <section className="panel">
            <h2>Ciclo y superficie</h2>
            <Campo
              id="fecha_inicio"
              etiqueta="Fecha de inicio"
              error={errores.fecha_inicio}
            >
              <input
                id="fecha_inicio"
                type="date"
                value={form.fecha_inicio}
                disabled={soloLectura || enProduccion}
                onChange={(e) => cambiar('fecha_inicio', e.target.value)}
              />
            </Campo>
            <Campo
              id="fecha_fin_prevista"
              etiqueta="Fecha de fin prevista"
              error={errores.fecha_fin_prevista}
            >
              <input
                id="fecha_fin_prevista"
                type="date"
                value={form.fecha_fin_prevista}
                disabled={soloLectura}
                onChange={(e) => cambiar('fecha_fin_prevista', e.target.value)}
              />
            </Campo>
            <Campo
              id="superficie_sembrada_ha"
              etiqueta="Superficie sembrada (ha)"
              error={errores.superficie_sembrada_ha}
              ayuda={
                parcelaActual
                  ? `En blanco se usa la de la parcela (${parcelaActual.superficie_ha} ha).`
                  : 'En blanco se usa la superficie de la parcela.'
              }
            >
              <input
                id="superficie_sembrada_ha"
                inputMode="decimal"
                placeholder={parcelaActual?.superficie_ha ?? ''}
                value={form.superficie_sembrada_ha}
                disabled={soloLectura}
                onChange={(e) =>
                  cambiar('superficie_sembrada_ha', e.target.value)
                }
              />
            </Campo>
            <Campo
              id="observaciones"
              etiqueta="Observaciones"
              error={errores.observaciones}
            >
              <textarea
                id="observaciones"
                rows={3}
                value={form.observaciones}
                disabled={soloLectura}
                onChange={(e) => cambiar('observaciones', e.target.value)}
              />
            </Campo>
          </section>

          {esEdicion && !esCancelada && tienePermiso('campanias.desactivar') && (
            <section className="panel">
              <h2>Cancelar campaña</h2>
              <Campo
                id="motivo"
                etiqueta="Motivo de la cancelación"
                ayuda="Obligatorio: quedará en las observaciones de la campaña."
              >
                <input
                  id="motivo"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </Campo>
              <button
                type="button"
                className="boton-peligro"
                disabled={guardando || !motivo.trim()}
                onClick={pedirCancelacion}
              >
                {guardando ? (
                  <>
                    <RuedaCarga etiqueta="Procesando…" />
                    Procesando…
                  </>
                ) : (
                  'Cancelar campaña'
                )}
              </button>
            </section>
          )}

          {!soloLectura && (
            <div className="formulario-acciones">
              <button
                className="boton-primario"
                type="submit"
                disabled={guardando}
              >
                {guardando ? (
                  <>
                    <RuedaCarga etiqueta="Guardando…" />
                    Guardando…
                  </>
                ) : esEdicion ? (
                  'Guardar cambios'
                ) : (
                  'Crear campaña'
                )}
              </button>
              <button
                className="boton-secundario"
                type="button"
                onClick={onCancelar}
              >
                {esEdicion ? 'Cerrar' : 'Cancelar'}
              </button>
            </div>
          )}
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
