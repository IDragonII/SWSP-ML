import { useEffect, useState } from 'react'
import { apiCatalogo } from '../api/catalogos.js'
import { erroresDeCampo, mensajeDeError } from '../api/errores.js'
import Aviso from '../components/Aviso.jsx'
import Campo from '../components/Campo.jsx'
import Cargando from '../components/Cargando.jsx'
import Modal from '../components/Modal.jsx'
import RuedaCarga from '../components/RuedaCarga.jsx'
import { useToast } from '../context/useToast.js'

export default function CatalogoFormulario({
  catalogo,
  id,
  abierto,
  onGuardado,
  onCancelar,
}) {
  const esEdicion = Boolean(id)
  const { avisar } = useToast()

  const [form, setForm] = useState({})
  const [origenes, setOrigenes] = useState({})
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [hidratado, setHidratado] = useState(!esEdicion)
  const [guardando, setGuardando] = useState(false)

  const cargando = !hidratado

  function cambiar(clave, valor) {
    setForm((actual) => ({ ...actual, [clave]: valor }))
    setErrores((actual) => ({ ...actual, [clave]: undefined }))
  }

  useEffect(() => {
    let activo = true
    const destinos = [
      ...new Set(catalogo.campos.map((c) => c.origen).filter(Boolean)),
    ]
    destinos.forEach((destino) => {
      apiCatalogo(`/${destino}/`)
        .desplegable()
        .then((lista) => {
          if (activo) setOrigenes((prev) => ({ ...prev, [destino]: lista }))
        })
        .catch(() => {})
    })
    return () => {
      activo = false
    }
  }, [catalogo])

  useEffect(() => {
    if (!esEdicion) return undefined
    let activo = true
    apiCatalogo(catalogo.ruta)
      .obtener(id)
      .then((objeto) => {
        if (!activo) return
        const inicial = {}
        for (const campo of catalogo.campos) {
          const bruto = campo.origen
            ? objeto[campo.nombre]?.id
            : objeto[campo.nombre]
          inicial[campo.nombre] =
            bruto === null || bruto === undefined ? '' : String(bruto)
        }
        setForm(inicial)
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
  }, [id, esEdicion, catalogo])

  async function enviar(evento) {
    evento.preventDefault()
    setErrores({})

    const pendientes = {}
    for (const campo of catalogo.campos) {
      const requerido = campo.requerido !== false
      if (
        requerido &&
        campo.tipo === 'select' &&
        !String(form[campo.nombre] ?? '').trim()
      ) {
        pendientes[campo.nombre] = 'Elige una opción.'
      }
    }
    if (Object.keys(pendientes).length > 0) {
      setErrores(pendientes)
      return
    }

    const datos = {}
    for (const campo of catalogo.campos) {
      const bruto = form[campo.nombre] ?? ''
      if (campo.tipo === 'numero') {
        datos[campo.nombre] = String(bruto).trim() === '' ? '' : Number(bruto)
      } else if (campo.tipo === 'select' && campo.origen) {
        datos[campo.nombre] = Number(bruto)
      } else if (campo.tipo === 'area') {
        datos[campo.nombre] = String(bruto).trim() || null
      } else {
        datos[campo.nombre] = String(bruto).trim()
      }
    }

    setGuardando(true)
    try {
      const guardado = await apiCatalogo(catalogo.ruta).guardar(id, datos)
      avisar(esEdicion ? 'Cambios guardados.' : 'Registro creado.')
      onGuardado?.(guardado)
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

  return (
    <Modal
      abierto={abierto}
      tamano="formulario"
      titulo={esEdicion ? catalogo.tituloEdicion : catalogo.tituloAlta}
      ocupado={guardando}
      onCerrar={onCancelar}
    >
      <Aviso>{error}</Aviso>

      {cargando ? (
        <Cargando />
      ) : (
        <form onSubmit={enviar} className="formulario-pagina">
          <section className="panel">
            <h2>{catalogo.nombre}</h2>
            {catalogo.campos.map((campo) => {
              const idCampo = `cat-${campo.nombre}`
              const valor = form[campo.nombre] ?? ''
              let control
              if (campo.tipo === 'area') {
                control = (
                  <textarea
                    id={idCampo}
                    rows={3}
                    value={valor}
                    onChange={(e) => cambiar(campo.nombre, e.target.value)}
                  />
                )
              } else if (campo.tipo === 'select') {
                const opciones = campo.origen
                  ? (origenes[campo.origen] ?? []).map((o) => ({
                      valor: String(o.id),
                      etiqueta: o.nombre,
                    }))
                  : Object.entries(campo.mapa).map(([codigo, etiqueta]) => ({
                      valor: codigo,
                      etiqueta,
                    }))
                control = (
                  <select
                    id={idCampo}
                    value={valor}
                    onChange={(e) => cambiar(campo.nombre, e.target.value)}
                  >
                    <option value="">Elige una opción</option>
                    {opciones.map((op) => (
                      <option key={op.valor} value={op.valor}>
                        {op.etiqueta}
                      </option>
                    ))}
                  </select>
                )
              } else if (campo.tipo === 'numero') {
                control = (
                  <input
                    id={idCampo}
                    type="number"
                    step={campo.nombre === 'orden' ? 1 : 'any'}
                    value={valor}
                    onChange={(e) => cambiar(campo.nombre, e.target.value)}
                  />
                )
              } else {
                control = (
                  <input
                    id={idCampo}
                    value={valor}
                    onChange={(e) => cambiar(campo.nombre, e.target.value)}
                  />
                )
              }
              return (
                <Campo
                  key={campo.nombre}
                  id={idCampo}
                  etiqueta={campo.etiqueta}
                  error={errores[campo.nombre]}
                  ayuda={campo.ayuda}
                >
                  {control}
                </Campo>
              )
            })}
          </section>

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
                `Crear ${catalogo.singular}`
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
      )}
    </Modal>
  )
}
