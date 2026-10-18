import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import AccesoDenegado from './pages/AccesoDenegado.jsx'
import Actividades from './pages/Actividades.jsx'
import Alertas from './pages/Alertas.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Campanias from './pages/Campanias.jsx'
import CambiarClave from './pages/CambiarClave.jsx'
import Catalogos from './pages/Catalogos.jsx'
import Climas from './pages/Climas.jsx'
import Incidencias from './pages/Incidencias.jsx'
import Inicio from './pages/Inicio.jsx'
import Login from './pages/Login.jsx'
import Modulo from './pages/Modulo.jsx'
import NoEncontrado from './pages/NoEncontrado.jsx'
import Parametros from './pages/Parametros.jsx'
import Parcelas from './pages/Parcelas.jsx'
import Productores from './pages/Productores.jsx'
import ProductoresRiesgo from './pages/ProductoresRiesgo.jsx'
import Recursos from './pages/Recursos.jsx'
import Roles from './pages/Roles.jsx'
import Usuarios from './pages/Usuarios.jsx'
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
  '/incidencias',
  '/alertas',
  '/productores-riesgo',
  '/usuarios',
  '/roles',
  '/auditoria',
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

        {/* Sin Layout a propósito (HU-105): mientras dure la marca de
            cambio obligatorio no debe verse el menú de la app */}
        <Route
          path="/cambiar-clave"
          element={
            <RutaProtegida>
              <CambiarClave />
            </RutaProtegida>
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

          <Route
            path="/incidencias"
            element={
              <RutaProtegida permiso="incidencias.ver">
                <Incidencias />
              </RutaProtegida>
            }
          />

          <Route
            path="/alertas"
            element={
              <RutaProtegida permiso="alertas.ver">
                <Alertas />
              </RutaProtegida>
            }
          />

          <Route
            path="/productores-riesgo"
            element={
              <RutaProtegida permiso="alertas.ver">
                <ProductoresRiesgo />
              </RutaProtegida>
            }
          />

          <Route
            path="/usuarios"
            element={
              <RutaProtegida permiso="usuarios.ver">
                <Usuarios />
              </RutaProtegida>
            }
          />

          <Route
            path="/auditoria"
            element={
              <RutaProtegida permiso="auditoria.ver">
                <Auditoria />
              </RutaProtegida>
            }
          />

          <Route
            path="/roles"
            element={
              <RutaProtegida permiso="roles.gestionar">
                <Roles />
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
