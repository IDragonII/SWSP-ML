import { useCallback, useEffect, useMemo, useState } from 'react'
import { cerrarSesion, iniciarSesion, obtenerSesion } from '../api/auth.js'
import { alExpirarSesion } from '../api/cliente.js'
import { SesionContext } from './sesionContexto.js'

export function SesionProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let activo = true

    obtenerSesion()
      .then((datos) => {
        if (activo) setUsuario(datos)
      })
      .catch(() => {
        if (activo) setUsuario(null)
      })
      .finally(() => {
        if (activo) setCargando(false)
      })

    const cancelar = alExpirarSesion(() => setUsuario(null))
    return () => {
      activo = false
      cancelar()
    }
  }, [])

  const entrar = useCallback(async (username, password) => {
    const datos = await iniciarSesion(username, password)
    setUsuario(datos)
    return datos
  }, [])

  const salir = useCallback(async () => {
    try {
      await cerrarSesion()
    } finally {
      setUsuario(null)
    }
  }, [])

  const valor = useMemo(
    () => ({
      usuario,
      cargando,
      iniciarSesion: entrar,
      cerrarSesion: salir,
      permisos: usuario?.permisos ?? [],
      tienePermiso: (codigo) => (usuario?.permisos ?? []).includes(codigo),
    }),
    [usuario, cargando, entrar, salir],
  )

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>
}
