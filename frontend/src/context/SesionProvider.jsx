import { useCallback, useEffect, useMemo, useState } from 'react'
import { cerrarSesion, iniciarSesion, obtenerSesion } from '../api/auth.js'
import { alDenegarPermiso, alExpirarSesion } from '../api/cliente.js'
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
    // Semana 14: ante un 403 se relee /auth/me y los permisos del menú,
    // las rutas y los botones se recalculan sin recargar la página
    const cancelarPermiso = alDenegarPermiso(() => {
      obtenerSesion()
        .then((datos) => {
          if (activo) setUsuario(datos)
        })
        .catch(() => {})
    })
    return () => {
      activo = false
      cancelar()
      cancelarPermiso()
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

  // Semana 13 (HU-113): el cambio de contraseña devuelve el usuario con
  // la marca debe_cambiar_clave ya baja; se aplica sin recargar
  const actualizar = useCallback((datos) => setUsuario(datos), [])

  const valor = useMemo(
    () => ({
      usuario,
      cargando,
      iniciarSesion: entrar,
      cerrarSesion: salir,
      actualizarUsuario: actualizar,
      permisos: usuario?.permisos ?? [],
      tienePermiso: (codigo) => (usuario?.permisos ?? []).includes(codigo),
    }),
    [usuario, cargando, entrar, salir, actualizar],
  )

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>
}
