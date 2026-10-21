export const opcionesMenu = [
  { ruta: '/', nombre: 'Inicio' },
  { ruta: '/productores', nombre: 'Productores', permiso: 'productores.ver' },
  { ruta: '/parcelas', nombre: 'Parcelas', permiso: 'parcelas.ver' },
  { ruta: '/catalogos', nombre: 'Catálogos', permiso: 'catalogos.editar' },
  { ruta: '/parametros', nombre: 'Parámetros', permiso: 'parametros.gestionar' },
  { ruta: '/campanias', nombre: 'Campañas', permiso: 'campanias.ver' },
  { ruta: '/actividades', nombre: 'Actividades', permiso: 'actividades.ver' },
  { ruta: '/produccion', nombre: 'Producción', permiso: 'produccion.ver' },
  { ruta: '/recursos', nombre: 'Recursos', permiso: 'recursos.ver' },
  { ruta: '/clima', nombre: 'Clima', permiso: 'clima.ver' },
  { ruta: '/incidencias', nombre: 'Incidencias', permiso: 'incidencias.ver' },
  { ruta: '/alertas', nombre: 'Alertas', permiso: 'alertas.ver' },
  {
    ruta: '/productores-riesgo',
    nombre: 'Productores en riesgo',
    permiso: 'alertas.ver',
  },
  { ruta: '/prediccion', nombre: 'Predicción', permiso: 'ml.ver_predicciones' },
  {
    ruta: '/predicciones',
    nombre: 'Historial de predicciones',
    permiso: 'ml.ver_predicciones',
  },
  { ruta: '/modelos', nombre: 'Modelos ML', permiso: 'ml.ver_modelos' },
  { ruta: '/entrenar', nombre: 'Entrenar', permiso: 'ml.entrenar' },
  { ruta: '/reportes', nombre: 'Reportes', permiso: 'reportes.ver' },
  { ruta: '/usuarios', nombre: 'Usuarios', permiso: 'usuarios.ver' },
  { ruta: '/roles', nombre: 'Roles y permisos', permiso: 'roles.gestionar' },
  { ruta: '/auditoria', nombre: 'Auditoría', permiso: 'auditoria.ver' },
]

// Agrupación del menú lateral (Layout.jsx). Reutiliza los mismos objetos
// de `opcionesMenu`; los grupos sin ninguna opción visible se omiten.
const porRuta = Object.fromEntries(
  opcionesMenu.map((opcion) => [opcion.ruta, opcion]),
)

const rutas = (...rutasGrupo) => rutasGrupo.map((ruta) => porRuta[ruta])

export const gruposMenu = [
  { titulo: 'General', opciones: rutas('/') },
  {
    titulo: 'Productores y parcelas',
    opciones: rutas('/productores', '/parcelas'),
  },
  {
    titulo: 'Campañas',
    opciones: rutas(
      '/campanias',
      '/actividades',
      '/produccion',
      '/recursos',
      '/clima',
      '/incidencias',
    ),
  },
  { titulo: 'Alertas', opciones: rutas('/alertas', '/productores-riesgo') },
  {
    titulo: 'Predicción',
    opciones: rutas('/prediccion', '/predicciones', '/modelos', '/entrenar'),
  },
  {
    titulo: 'Administración',
    opciones: rutas(
      '/catalogos',
      '/parametros',
      '/reportes',
      '/usuarios',
      '/roles',
      '/auditoria',
    ),
  },
]
