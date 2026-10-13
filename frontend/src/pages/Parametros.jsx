import { useEffect, useState } from 'react'
import { guardarParametro, listarParametros } from '../api/parametros.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import Tabla from '../components/Tabla.jsx'
import { useToast } from '../context/useToast.js'

const NOMBRES = {
  dias_sin_actividad: 'Días sin actividad',
  umbral_rendimiento_bajo: 'Umbral de rendimiento bajo',
  rendimiento_min_plausible: 'Rendimiento mínimo plausible',
  rendimiento_max_plausible: 'Rendimiento máximo plausible',
}

const AYUDAS = {
  dias_sin_actividad:
    'Días sin actividad registrada antes de marcar un seguimiento pendiente.',
  umbral_rendimiento_bajo:
    'Rendimiento por debajo del cual el técnico debe atender la campaña (kg/ha).',
  rendimiento_min_plausible:
    'Rendimiento por debajo del cual la producción se marca para revisión (kg/ha).',
  rendimiento_max_plausible:
    'Rendimiento por encima del cual la producción se marca para revisión (kg/ha).',
}

function ParametroFormulario({ parametro, otros, abierto, onGuardado, onCancelar }) {
  const { avisar } = useToast()
  const [valor, setValor] = useState(String(parametro.valor))
  const [error, setError] = useState(null)
  const [errores, setErrores] = useState({})
  const [guardando, setGuardando] = useState(false)

  function validarCliente() {
    const fallos = {}
    const limpio = valor.trim()
    if (!limpio) {
      fallos.valor = 'El valor es obligatorio.'
      return fallos
    }
    const numero = Number(limpio)
    if (Number.isNaN(numero) || numero <= 0) {
      fallos.valor = 'El valor debe ser un número mayor que 0.'
      return fallos
    }
    const min = otros.rendimiento_min_plausible
    const max = otros.rendimiento_max_plausible
    if (
      parametro.clave === 'rendimiento_min_plausible' &&
      max !== undefined &&
      numero >= Number(max.valor)
    ) {
      fallos.valor = 'El rendimiento mínimo debe ser menor que el máximo.'
    }
    if (
      parametro.clave === 'rendimiento_max_plausible' &&
      min !== undefined &&
      numero <= Number(min.valor)
    ) {
      fallos.valor = 'El rendimiento mínimo debe ser menor que el máximo.'
    }
    return fallos
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErrores({})
    setError(null)
    const fallos = validarCliente()
    if (Object.keys(fallos).length > 0) {
      setErrores(fallos)
      return
    }
    setGuardando(true)
    try {
      await guardarParametro(parametro.clave, valor.trim())
      avisar('Parámetro guardado.')
      onGuardado?.()
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

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo={NOMBRES[parametro.clave] ?? parametro.clave}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>
      <form onSubmit={enviar} className="formulario-pagina">
        <section className="panel">
          <Campo
            id="valor-parametro"
            etiqueta="Valor"
            error={errores.valor}
            ayuda={AYUDAS[parametro.clave]}
          >
            <input
              id="valor-parametro"
              inputMode="decimal"
              value={valor}
              onChange={(e) => {
                setValor(e.target.value)
                setErrores((actual) => ({ ...actual, valor: undefined }))
              }}
            />
          </Campo>
        </section>
        <div className="formulario-acciones">
          <button className="boton-primario" type="submit" disabled={guardando}>
            {guardando ? (
              <>
                <RuedaCarga etiqueta="Guardando…" />
                Guardando…
              </>
            ) : (
              'Guardar'
            )}
          </button>
          <button
            className="boton-secundario"
            type="button"
            onClick={onCancelar}
          >
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default function Parametros() {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [editando, setEditando] = useState(null)

  useEffect(() => {
    let activo = true
    listarParametros()
      .then((respuesta) => {
        if (!activo) return
        setError(null)
        setDatos(respuesta)
      })
      .catch((e) => activo && setError(mensajeDeError(e)))
    return () => {
      activo = false
    }
  }, [recarga])

  if (!datos && !error) return <Cargando />

  const filas = datos?.results ?? []
  const otros = Object.fromEntries(filas.map((p) => [p.clave, p]))

  return (
    <>
      <div className="pagina-cabecera">
        <div>
          <h1>Parámetros del sistema</h1>
          <p className="conteo">
            {datos ? `${datos.count} en total` : 'Sin datos'}
          </p>
        </div>
      </div>

      <p className="nota">
        Los umbrales se aplican al registrar o editar producciones: no
        reevalúan las producciones ya guardadas.
      </p>

      <Aviso>{error}</Aviso>

      {filas.length > 0 && (
        <Tabla
          filas={filas}
          columnas={[
            {
              clave: 'clave',
              etiqueta: 'Parámetro',
              celda: (fila) => NOMBRES[fila.clave] ?? fila.clave,
            },
            {
              clave: 'valor',
              etiqueta: 'Valor',
              celda: (fila) => fila.valor,
            },
            {
              clave: 'descripcion',
              etiqueta: 'Descripción',
              celda: (fila) => fila.descripcion,
            },
            {
              clave: 'actualizado_en',
              etiqueta: 'Última actualización',
              celda: (fila) =>
                fila.actualizado_en
                  ? new Date(fila.actualizado_en).toLocaleDateString('es-PE')
                  : '—',
            },
            {
              clave: 'acciones',
              etiqueta: 'Acciones',
              acciones: true,
              celda: (fila) => (
                <button
                  type="button"
                  className="boton-texto"
                  onClick={() => setEditando(fila)}
                >
                  Editar
                </button>
              ),
            },
          ]}
        />
      )}

      {editando && (
        <ParametroFormulario
          parametro={editando}
          otros={otros}
          abierto
          onGuardado={() => {
            setEditando(null)
            setRecarga((n) => n + 1)
          }}
          onCancelar={() => setEditando(null)}
        />
      )}
    </>
  )
}
