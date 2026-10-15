import { useEffect, useState } from 'react'
import { listarTodo } from '../api/catalogos.js'
import { consultaApiMeteorologica } from '../api/clima.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

function hoyLima() {
  const ahora = new Date()
  const fecha = new Date(ahora.getTime() - 5 * 60 * 60 * 1000)
  return fecha.toISOString().slice(0, 10)
}

const ETIQUETAS_INFORME = [
  ['creados', 'Registros creados'],
  ['actualizados', 'Registros actualizados'],
  ['omitidos_manual', 'Omitidos (eran manuales)'],
  ['omitidos_api', 'Omitidos (sin dato nuevo)'],
  ['sin_datos', 'Días sin datos'],
  ['descartados', 'Días descartados por medidas inválidas'],
]

export default function ClimaConsulta({
  parcelaInicial = '',
  abierto,
  onGuardado,
  onCancelar,
}) {
  const { avisar } = useToast()

  const [form, setForm] = useState(() => ({
    parcela: parcelaInicial ? String(parcelaInicial) : '',
    fecha_desde: '',
    fecha_hasta: '',
  }))
  const [parcelas, setParcelas] = useState([])
  const [listo, setListo] = useState(false)
  const [errores, setErrores] = useState({})
  const [consultando, setConsultando] = useState(false)
  const [informe, setInforme] = useState(null)

  const maxFecha = hoyLima()

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    listarTodo('/parcelas/', { desplegable: 1 })
      .then((lista) => activo && setParcelas(lista))
      .catch(() => {})
      .finally(() => activo && setListo(true))
    return () => {
      activo = false
    }
  }, [])

  function validarCliente() {
    const fallos = {}
    if (!form.parcela) fallos.parcela = 'La parcela es obligatoria.'
    if (!form.fecha_desde) fallos.fecha_desde = 'La fecha inicial es obligatoria.'
    if (!form.fecha_hasta) fallos.fecha_hasta = 'La fecha final es obligatoria.'
    if (form.fecha_desde && form.fecha_hasta) {
      if (form.fecha_desde > form.fecha_hasta) {
        fallos.fecha_desde = 'La fecha inicial no puede ser posterior a la final.'
      } else if (
        (new Date(form.fecha_hasta) - new Date(form.fecha_desde)) / 86400000 + 1 >
        92
      ) {
        fallos.fecha_hasta = 'La consulta admite como máximo 92 días.'
      }
    }
    if (form.fecha_hasta > maxFecha) {
      fallos.fecha_hasta = 'La fecha final no puede ser futura.'
    }
    return fallos
  }

  async function enviar(event) {
    event.preventDefault()
    setErrores({})
    setInforme(null)

    const fallos = validarCliente()
    if (Object.keys(fallos).length > 0) {
      setErrores(fallos)
      return
    }

    setConsultando(true)
    try {
      const resultado = await consultaApiMeteorologica({
        parcela: Number(form.parcela),
        fecha_desde: form.fecha_desde,
        fecha_hasta: form.fecha_hasta,
      })
      setInforme(resultado)
      avisar('Consulta a la API meteorológica finalizada.')
      onGuardado?.()
    } catch (e) {
      if (e.response?.status === 400) {
        const campos = erroresDeCampo(e.response.data)
        setErrores(campos)
        if (Object.keys(campos).length > 0) return
      }
      avisar(mensajeDeError(e), 'error')
    } finally {
      setConsultando(false)
    }
  }

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo="Consultar API meteorológica"
      ocupado={consultando}
      onCerrar={onCancelar}
    >
      {!listo ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>Qué consultar</h2>
            <Campo
              id="consulta-parcela"
              etiqueta="Parcela"
              error={errores.parcela}
              ayuda="La parcela debe tener coordenadas registradas; solo se consultan días pasados (máx. 92)."
            >
              <select
                id="consulta-parcela"
                value={form.parcela}
                onChange={(e) => cambiar('parcela', e.target.value)}
              >
                <option value="">Elige una parcela</option>
                {parcelas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.codigo} — {p.productor.nombre_completo}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo
              id="consulta-desde"
              etiqueta="Fecha inicial"
              error={errores.fecha_desde}
            >
              <input
                id="consulta-desde"
                type="date"
                max={maxFecha}
                value={form.fecha_desde}
                onChange={(e) => cambiar('fecha_desde', e.target.value)}
              />
            </Campo>
            <Campo
              id="consulta-hasta"
              etiqueta="Fecha final"
              error={errores.fecha_hasta}
              ayuda="Los registros manuales nunca se pisan; los de la API se refrescan."
            >
              <input
                id="consulta-hasta"
                type="date"
                max={maxFecha}
                value={form.fecha_hasta}
                onChange={(e) => cambiar('fecha_hasta', e.target.value)}
              />
            </Campo>
          </section>

          {informe && (
            <section className="panel">
              <h2>Informe de la consulta</h2>
              <dl className="datos-rejilla">
                {ETIQUETAS_INFORME.map(([clave, etiqueta]) => (
                  <div key={clave}>
                    <dt>{etiqueta}</dt>
                    <dd>{informe[clave]}</dd>
                  </div>
                ))}
              </dl>
              <p className="nota">
                Consulta del {informe.consulta.fecha_desde} al{' '}
                {informe.consulta.fecha_hasta} en la parcela{' '}
                {informe.consulta.parcela} ({informe.consulta.latitud},{' '}
                {informe.consulta.longitud}).
              </p>
            </section>
          )}

          <div className="formulario-acciones">
            <button
              className="boton-primario"
              type="submit"
              disabled={consultando}
            >
              {consultando ? (
                <>
                  <RuedaCarga etiqueta="Consultando…" />
                  Consultando…
                </>
              ) : (
                'Consultar'
              )}
            </button>
            <button
              className="boton-secundario"
              type="button"
              onClick={onCancelar}
            >
              Cerrar
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}
