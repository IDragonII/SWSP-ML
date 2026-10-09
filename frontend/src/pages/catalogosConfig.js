// Configuración de la pantalla de catálogos (Semana 5): qué columnas
// muestra cada recurso, qué campos tiene su formulario y qué etiquetas
// en español llevan las listas cerradas del backend.

export const TIPOS_UNIDAD = {
  MASA: 'Masa',
  SUPERFICIE: 'Superficie',
  VOLUMEN: 'Volumen',
  LABOR: 'Labor',
  TIEMPO: 'Tiempo',
}

export const TIPOS_UNIDAD_RECURSO = {
  MASA: 'Masa',
  VOLUMEN: 'Volumen',
  LABOR: 'Labor',
  TIEMPO: 'Tiempo',
}

export const CATEGORIAS_RECURSO = {
  SEMILLA: 'Semilla',
  FERTILIZANTE: 'Fertilizante',
  ABONO: 'Abono',
  FITOSANITARIO: 'Fitosanitario',
  AGUA: 'Agua',
  MAQUINARIA: 'Maquinaria',
  MANO_OBRA: 'Mano de obra',
  COMBUSTIBLE: 'Combustible',
}

export const CATEGORIAS_INCIDENCIA = {
  CLIMATICA: 'Climática',
  BIOLOGICA: 'Biológica',
  OTRA: 'Otra',
}

export const TIPOS_AGENTE = {
  PLAGA: 'Plaga',
  ENFERMEDAD: 'Enfermedad',
}

export const CATALOGOS = [
  {
    clave: 'cultivos',
    nombre: 'Cultivos',
    singular: 'cultivo',
    ruta: '/cultivos/',
    alta: true,
    estado: true,
    tituloAlta: 'Nuevo cultivo',
    tituloEdicion: 'Editar cultivo',
    columnas: [
      { clave: 'nombre', etiqueta: 'Nombre' },
      { clave: 'descripcion', etiqueta: 'Descripción' },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' },
      {
        nombre: 'descripcion',
        etiqueta: 'Descripción',
        tipo: 'area',
        requerido: false,
        ayuda: 'Opcional.',
      },
    ],
  },
  {
    clave: 'variedades',
    nombre: 'Variedades',
    singular: 'variedad',
    ruta: '/variedades/',
    alta: true,
    estado: true,
    tituloAlta: 'Nueva variedad',
    tituloEdicion: 'Editar variedad',
    columnas: [
      { clave: 'cultivo', etiqueta: 'Cultivo', tipo: 'anidado' },
      { clave: 'nombre', etiqueta: 'Nombre' },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [
      {
        nombre: 'cultivo',
        etiqueta: 'Cultivo',
        tipo: 'select',
        origen: 'cultivos',
      },
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' },
      {
        nombre: 'descripcion',
        etiqueta: 'Descripción',
        tipo: 'area',
        requerido: false,
        ayuda: 'Opcional.',
      },
    ],
  },
  {
    clave: 'etapas',
    nombre: 'Etapas fenológicas',
    singular: 'etapa',
    ruta: '/etapas-fenologicas/',
    alta: true,
    estado: false,
    tituloAlta: 'Nueva etapa',
    tituloEdicion: 'Editar etapa',
    columnas: [
      { clave: 'cultivo', etiqueta: 'Cultivo', tipo: 'anidado' },
      { clave: 'orden', etiqueta: 'Orden' },
      { clave: 'nombre', etiqueta: 'Etapa' },
    ],
    campos: [
      {
        nombre: 'cultivo',
        etiqueta: 'Cultivo',
        tipo: 'select',
        origen: 'cultivos',
      },
      { nombre: 'nombre', etiqueta: 'Etapa', tipo: 'texto' },
      {
        nombre: 'orden',
        etiqueta: 'Orden',
        tipo: 'numero',
        ayuda: 'Entre 1 y 1000; no puede repetirse dentro del cultivo.',
      },
    ],
  },
  {
    clave: 'unidades',
    nombre: 'Unidades',
    singular: 'unidad',
    ruta: '/unidades/',
    alta: true,
    estado: true,
    tituloAlta: 'Nueva unidad',
    tituloEdicion: 'Editar unidad',
    columnas: [
      { clave: 'nombre', etiqueta: 'Nombre' },
      { clave: 'simbolo', etiqueta: 'Símbolo', tipo: 'codigo' },
      { clave: 'tipo', etiqueta: 'Tipo', tipo: 'opciones', mapa: TIPOS_UNIDAD },
      { clave: 'factor_a_base', etiqueta: 'Factor a la base', tipo: 'numero' },
      {
        clave: 'es_base',
        etiqueta: 'Unidad base',
        formato: (fila) => (fila.es_base ? 'Base' : '—'),
      },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' },
      { nombre: 'simbolo', etiqueta: 'Símbolo', tipo: 'texto' },
      {
        nombre: 'tipo',
        etiqueta: 'Tipo',
        tipo: 'select',
        mapa: TIPOS_UNIDAD,
      },
      {
        nombre: 'factor_a_base',
        etiqueta: 'Factor a la base',
        tipo: 'numero',
        ayuda: 'Mayor que 0; en la unidad base es 1.',
      },
    ],
  },
  {
    clave: 'tipos-actividad',
    nombre: 'Tipos de actividad',
    singular: 'tipo de actividad',
    ruta: '/tipos-actividad/',
    alta: false,
    estado: true,
    tituloAlta: null,
    tituloEdicion: 'Editar tipo de actividad',
    columnas: [
      { clave: 'codigo', etiqueta: 'Código', tipo: 'codigo' },
      { clave: 'nombre', etiqueta: 'Nombre' },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [{ nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' }],
  },
  {
    clave: 'recursos',
    nombre: 'Recursos',
    singular: 'recurso',
    ruta: '/recursos/',
    alta: true,
    estado: true,
    tituloAlta: 'Nuevo recurso',
    tituloEdicion: 'Editar recurso',
    columnas: [
      { clave: 'nombre', etiqueta: 'Nombre' },
      {
        clave: 'categoria',
        etiqueta: 'Categoría',
        tipo: 'opciones',
        mapa: CATEGORIAS_RECURSO,
      },
      {
        clave: 'tipo_unidad',
        etiqueta: 'Tipo de unidad',
        tipo: 'opciones',
        mapa: TIPOS_UNIDAD_RECURSO,
      },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' },
      {
        nombre: 'categoria',
        etiqueta: 'Categoría',
        tipo: 'select',
        mapa: CATEGORIAS_RECURSO,
      },
      {
        nombre: 'tipo_unidad',
        etiqueta: 'Tipo de unidad',
        tipo: 'select',
        mapa: TIPOS_UNIDAD_RECURSO,
      },
    ],
  },
  {
    clave: 'tipos-incidencia',
    nombre: 'Tipos de incidencia',
    singular: 'tipo de incidencia',
    ruta: '/tipos-incidencia/',
    alta: true,
    estado: true,
    tituloAlta: 'Nuevo tipo de incidencia',
    tituloEdicion: 'Editar tipo de incidencia',
    columnas: [
      { clave: 'nombre', etiqueta: 'Nombre' },
      {
        clave: 'categoria',
        etiqueta: 'Categoría',
        tipo: 'opciones',
        mapa: CATEGORIAS_INCIDENCIA,
      },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' },
      {
        nombre: 'categoria',
        etiqueta: 'Categoría',
        tipo: 'select',
        mapa: CATEGORIAS_INCIDENCIA,
      },
    ],
  },
  {
    clave: 'agentes',
    nombre: 'Agentes',
    singular: 'agente',
    ruta: '/agentes/',
    alta: true,
    estado: true,
    tituloAlta: 'Nuevo agente',
    tituloEdicion: 'Editar agente',
    columnas: [
      { clave: 'nombre', etiqueta: 'Nombre' },
      {
        clave: 'tipo',
        etiqueta: 'Tipo',
        tipo: 'opciones',
        mapa: TIPOS_AGENTE,
      },
      { clave: 'estado', etiqueta: 'Estado', tipo: 'estado' },
    ],
    campos: [
      { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto' },
      {
        nombre: 'tipo',
        etiqueta: 'Tipo',
        tipo: 'select',
        mapa: TIPOS_AGENTE,
      },
    ],
  },
]
