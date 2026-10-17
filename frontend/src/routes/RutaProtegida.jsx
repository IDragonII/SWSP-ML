import { Navigate, useLocation } from 'react-router-dom'
import Cargando from '../components/Cargando.jsx'
import { useSesion } from '../context/useSesion.js'

export default function RutaProtegida({ permiso, children }) {
  const { usuario, cargando, tienePermiso } = useSesion()
  const ubicacion = useLocation()

  if (cargando) return <Cargando texto="Cargando tu sesión…" />
  if (!usuario) {
    return <Navigate to="/login" state={{ desde: ubicacion }} replace />
  }
  // Semana 13 (HU-112): con la marca de cambio obligatorio solo se usa
  // /cambiar-clave; el resto de la app espera (el backend también corta
  // la API con 403, la puerta aquí es del lado del cliente)
  if (
    usuario.debe_cambiar_clave &&
    ubicacion.pathname !== '/cambiar-clave'
  ) {
    return <Navigate to="/cambiar-clave" replace />
  }
  if (permiso && !tienePermiso(permiso)) {
    return <Navigate to="/acceso-denegado" replace />
  }
  return children
}
