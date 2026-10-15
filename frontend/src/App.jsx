import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import AccesoDenegado from './pages/AccesoDenegado.jsx'
import Actividades from './pages/Actividades.jsx'
import Campanias from './pages/Campanias.jsx'
import Catalogos from './pages/Catalogos.jsx'
import Climas from './pages/Climas.jsx'
import Inicio from './pages/Inicio.jsx'
import Login from './pages/Login.jsx'
import Modulo from './pages/Modulo.jsx'
import NoEncontrado from './pages/NoEncontrado.jsx'
import Parametros from './pages/Parametros.jsx'
import Parcelas from './pages/Parcelas.jsx'
import Productores from './pages/Productores.jsx'
import Recursos from './pages/Recursos.jsx'
import RutaProtegida from './routes/RutaProtegida.jsx'
import RutaSoloInvitado from './routes/RutaSoloInvitado.jsx'
import { opcionesMenu } from './routes/opcionesMenu.js'
import './App.css'

const rutasConPantalla = new Set([
  '/',
  '/productores',
  '/parcelas',
  '/catalogos',
  '/parametros',
  '/campanias',
  '/actividades',
  '/recursos',
  '/clima',
])
const modulos = opcionesMenu.filter(
  (opcion) => !rutasConPantalla.has(opcion.ruta),
)

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

          <Route
            path="/productores"
            element={
              <RutaProtegida permiso="productores.ver">
                <Productores />
              </RutaProtegida>
            }
          />

          <Route
            path="/parcelas"
            element={
              <RutaProtegida permiso="parcelas.ver">
                <Parcelas />
              </RutaProtegida>
            }
          />

          <Route
            path="/catalogos"
            element={
              <RutaProtegida permiso="catalogos.editar">
                <Catalogos />
              </RutaProtegida>
            }
          />

          <Route
            path="/parametros"
            element={
              <RutaProtegida permiso="parametros.gestionar">
                <Parametros />
              </RutaProtegida>
            }
          />

          <Route
            path="/campanias"
            element={
              <RutaProtegida permiso="campanias.ver">
                <Campanias />
              </RutaProtegida>
            }
          />

          <Route
            path="/actividades"
            element={
              <RutaProtegida permiso="actividades.ver">
                <Actividades />
              </RutaProtegida>
            }
          />

          <Route
            path="/recursos"
            element={
              <RutaProtegida permiso="recursos.ver">
                <Recursos />
              </RutaProtegida>
            }
          />

          <Route
            path="/clima"
            element={
              <RutaProtegida permiso="clima.ver">
                <Climas />
              </RutaProtegida>
            }
          />

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
