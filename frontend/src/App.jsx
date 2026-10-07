import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import AccesoDenegado from './pages/AccesoDenegado.jsx'
import Inicio from './pages/Inicio.jsx'
import Login from './pages/Login.jsx'
import Modulo from './pages/Modulo.jsx'
import NoEncontrado from './pages/NoEncontrado.jsx'
import RutaProtegida from './routes/RutaProtegida.jsx'
import RutaSoloInvitado from './routes/RutaSoloInvitado.jsx'
import { opcionesMenu } from './routes/opcionesMenu.js'
import './App.css'

const modulos = opcionesMenu.filter((opcion) => opcion.ruta !== '/')

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <RutaSoloInvitado>
              <Login />
            </RutaSoloInvitado>
          }
        />

        <Route
          element={
            <RutaProtegida>
              <Layout />
            </RutaProtegida>
          }
        >
          <Route index element={<Inicio />} />
          {modulos.map((modulo) => (
            <Route
              key={modulo.ruta}
              path={modulo.ruta}
              element={
                <RutaProtegida permiso={modulo.permiso}>
                  <Modulo nombre={modulo.nombre} />
                </RutaProtegida>
              }
            />
          ))}
          <Route path="/acceso-denegado" element={<AccesoDenegado />} />
          <Route path="*" element={<NoEncontrado />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
