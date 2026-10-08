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
  if (permiso && !tienePermiso(permiso)) {
    return <Navigate to="/acceso-denegado" replace />
  }
  return children
}
