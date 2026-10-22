// Chequeo automático: cada entrada del menú (opcionesMenu.js) debe tener
// ruta con pantalla real en App.jsx (rutasConPantalla + <Route> declarado).
// Si una entrada cae en el marcador «en preparación», el lint falla.
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const menu = readFileSync(join(raiz, 'src', 'routes', 'opcionesMenu.js'), 'utf8')
const app = readFileSync(join(raiz, 'src', 'App.jsx'), 'utf8')

// Excepciones a propósito: rutas del menú que SÍ son marcador. Vacío hoy;
// solo se permite añadir una entrada aquí con acuerdo del responsable.
const EXCEPCIONES = []

const rutasMenu = [...menu.matchAll(/ruta:\s*'([^']+)'/g)].map((m) => m[1])

const bloque = app.match(/rutasConPantalla = new Set\(\[([\s\S]*?)\]\)/)
if (!bloque) {
  console.error('No se encontró rutasConPantalla en App.jsx.')
  process.exit(1)
}
const rutasConPantalla = new Set(
  [...bloque[1].matchAll(/'([^']+)'/g)].map((m) => m[1]),
)

const declaradas = new Set(
  [...app.matchAll(/path="([^"]+)"/g)].map((m) => m[1]),
)
if (/<Route\s+index/.test(app)) declaradas.add('/')

const fallos = []
for (const ruta of rutasMenu) {
  if (EXCEPCIONES.includes(ruta)) continue
  if (!rutasConPantalla.has(ruta)) {
    fallos.push(
      `${ruta}: no está en rutasConPantalla (mostraría el marcador «en preparación»).`,
    )
  }
  if (!declaradas.has(ruta)) {
    fallos.push(`${ruta}: no tiene <Route> declarado en App.jsx.`)
  }
}

if (fallos.length > 0) {
  console.error('El menú tiene entradas sin pantalla real:')
  for (const fallo of fallos) console.error(`  - ${fallo}`)
  process.exit(1)
}

console.log(
  `Menú verificado: ${rutasMenu.length} entradas con pantalla real (excepciones: ${EXCEPCIONES.length}).`,
)
