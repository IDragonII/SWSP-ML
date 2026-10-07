import { Navigate, useLocation } from 'react-router-dom'
import Cargando from '../components/Cargando.jsx'
import { useSesion } from '../context/useSesion.js'

export default function RutaSoloInvitado({ children }) {
  const { usuario, cargando } = useSesion()
  const ubicacion = useLocation()

  if (cargando) return <Cargando />
  if (usuario) {
    return <Navigate to={ubicacion.state?.desde?.pathname || '/'} replace />
  }
  return children
}
