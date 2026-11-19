import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Chip from './Chip.jsx'
import Tabla from './Tabla.jsx'

// Colores por algoritmo: el mismo par orden que la tabla de métricas
const COLOR = {
  REGRESION_LINEAL: 'var(--helecho)',
  RANDOM_FOREST: 'var(--bosque)',
  GRADIENT_BOOSTING: 'var(--marigold)',
  LINEA_BASE: 'var(--apagado)',
}

function num(valor) {
  if (valor === null || valor === undefined || valor === '') return null
  const n = Number(valor)
  return Number.isFinite(n) ? n : null
}

function cifra(valor, decimales = 2) {
  const n = num(valor)
  return n === null
    ? '—'
    : n.toLocaleString('es-PE', { maximumFractionDigits: decimales })
}

function etiquetaAlgoritmo(nombre) {
  return String(nombre).replaceAll('_', ' ').toLowerCase()
}

function formatearTooltip(valor) {
  return valor === null || valor === undefined
    ? '—'
    : Number(valor).toLocaleString('es-PE', { maximumFractionDigits: 2 })
}

function GraficoBarras({ titulo, aria, filas, series, dominio }) {
  return (
    <figure className="grafico-bloque">
      <figcaption>{titulo}</figcaption>
      <div className="grafico-envoltura" role="img" aria-label={aria}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filas} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--linea)" />
            <XAxis
              dataKey="etiqueta"
              tick={{ fontSize: 12, fill: 'var(--tinta)' }}
              stroke="var(--apagado)"
            />
            <YAxis
              domain={dominio}
              tick={{ fontSize: 12, fill: 'var(--tinta)' }}
              stroke="var(--apagado)"
              width={48}
            />
            <Tooltip formatter={formatearTooltip} />
            <Legend />
            {series.map((serie) => (
              <Bar
                key={serie.clave}
                dataKey={serie.clave}
                name={serie.nombre}
                fill={serie.color}
              >
                {filas.map((fila) => (
                  <Cell
                    key={fila.clave}
                    fill={fila.clave === 'base' ? 'var(--apagado)' : serie.color}
                  />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

/**
 * Panel de diagnóstico de «Resultados del entrenamiento» (S24):
 * veredicto, RMSE/MAE vs línea base, RMSE por pliegue, estabilidad,
 * R², MAPE, error por cultivo del elegido, tabla de holdout, variables
 * usadas/descartadas y rangos vistos. Todo sale del payload de
 * /resultados/; sin `linea_base` (entrenamiento viejo) muestra la nota.
 */
export default function GraficosEntrenamiento({ resultado }) {
  if (!resultado?.linea_base) {
    return (
      <div className="diagnostico-seccion">
        <h3>Diagnóstico del entrenamiento</h3>
        <p className="conteo">
          Este entrenamiento no guardó el diagnóstico: reentrena con la
          versión actual del sistema para ver los gráficos de validación.
        </p>
      </div>
    )
  }

  const base = resultado.linea_base
  const modelos = resultado.modelos || []
  const criterio = resultado.criterio || {}
  const elegido = criterio.elegido
  const modeloElegido =
    modelos.find((m) => m.algoritmo === elegido) || null

  // --- 1-2) RMSE y MAE de los modelos contra la línea base -----------
  const filasMetricas = [
    ...modelos.map((m) => ({
      clave: m.algoritmo,
      etiqueta: etiquetaAlgoritmo(m.algoritmo),
      rmse: num(m.rmse),
      mae: num(m.mae),
    })),
    {
      clave: 'base',
      etiqueta: 'línea base',
      rmse: num(base.rmse),
      mae: num(base.mae),
    },
  ]

  // --- 3) RMSE por pliegue: una serie por algoritmo + la base --------
  const seriesPliegues = [
    ...modelos.map((m) => ({
      nombre: etiquetaAlgoritmo(m.algoritmo),
      color: COLOR[m.algoritmo] || 'var(--apagado)',
      puntos: (m.hiperparametros?.validacion?.rmse_pliegues || []).map(
        (v, i) => ({ pliegue: i + 1, rmse: num(v) }),
      ),
    })),
    {
      nombre: 'línea base',
      color: COLOR.LINEA_BASE,
      puntos: (base.rmse_pliegues || []).map((v, i) => ({
        pliegue: i + 1,
        rmse: num(v),
      })),
    },
  ].filter((s) => s.puntos.length > 0)

  // --- 4) Estabilidad: desvío del RMSE entre pliegues ----------------
  const filasEstabilidad = [
    ...modelos
      .map((m) => ({
        clave: m.algoritmo,
        etiqueta: etiquetaAlgoritmo(m.algoritmo),
        desvio: num(m.hiperparametros?.validacion?.desvio_rmse),
      }))
      .filter((f) => f.desvio !== null),
    {
      clave: 'base',
      etiqueta: 'línea base',
      desvio: num(base.desvio_rmse),
    },
  ].filter((f) => f.desvio !== null)

  // --- 5) R² de ajuste ----------------------------------------------
  const filasR2 = [
    ...modelos.map((m) => ({
      clave: m.algoritmo,
      etiqueta: etiquetaAlgoritmo(m.algoritmo),
      r2: num(m.r2),
    })),
    { clave: 'base', etiqueta: 'línea base', r2: num(base.r2) },
  ].filter((f) => f.r2 !== null)

  // --- 6) MAPE (puede ser null si algún real era 0) -------------------
  const filasMape = [
    ...modelos
      .map((m) => ({
        clave: m.algoritmo,
        etiqueta: etiquetaAlgoritmo(m.algoritmo),
        mape: num(m.hiperparametros?.validacion?.mape),
      }))
      .filter((f) => f.mape !== null),
    {
      clave: 'base',
      etiqueta: 'línea base',
      mape: num(base.mape),
    },
  ].filter((f) => f.mape !== null)

  // --- 7) Error por cultivo del elegido (top 12 por RMSE) -------------
  const porCultivo = modeloElegido?.hiperparametros?.validacion?.por_cultivo
  const filasCultivos = porCultivo
    ? Object.entries(porCultivo)
        .map(([cultivo, m]) => ({
          id: cultivo,
          etiqueta: cultivo,
          rmse: num(m.rmse),
          mae: num(m.mae),
          filas: m.filas,
        }))
        .filter((f) => f.rmse !== null)
        .sort((a, b) => b.rmse - a.rmse)
        .slice(0, 12)
    : []

  // --- 8) Holdout 20 % (solo con n >= 100) ---------------------------
  const holdout = resultado.prueba_final
    ? Object.entries(resultado.prueba_final).map(([algoritmo, m]) => ({
        id: algoritmo,
        algoritmo,
        mae: m.mae,
        rmse: m.rmse,
        filas: m.filas,
      }))
    : null

  // --- 9) Variables usadas y descartadas por faltantes ---------------
  const usadas = resultado.variables_usadas || {}
  const listaVariables = Array.isArray(usadas.variables)
    ? usadas.variables
    : []
  const fuera = Object.entries(usadas.fuera || {})

  // --- 10) Rangos vistos en el entrenamiento (.joblib) ---------------
  const rangos = modeloElegido?.hiperparametros?.rangos || {}
  const filasRangos = Object.entries(rangos).map(([variable, r], i) => ({
    id: `${variable}-${i}`,
    variable,
    min: r?.min,
    max: r?.max,
  }))

  return (
    <div className="diagnostico-seccion">
      <h3>Diagnóstico del entrenamiento</h3>
      <p className="texto-intro">
        <Chip>{elegido ? etiquetaAlgoritmo(elegido) : 'sin elegido'}</Chip>{' '}
        {criterio.motivo || 'sin veredicto registrado'}
        {num(criterio.sigma) !== null && (
          <> · σ = {cifra(criterio.sigma)}</>
        )}
      </p>

      <div className="graficos-rejilla">
        <GraficoBarras
          titulo="RMSE y MAE de los modelos vs línea base (kg/ha)"
          aria-label="Barras comparando RMSE y MAE de los tres modelos contra la línea base"
          filas={filasMetricas}
          series={[
            { clave: 'rmse', nombre: 'RMSE', color: 'var(--helecho)' },
            { clave: 'mae', nombre: 'MAE', color: 'var(--marigold)' },
          ]}
        />

        {seriesPliegues.length > 0 && (
          <figure className="grafico-bloque">
            <figcaption>RMSE por pliegue de validación (kg/ha)</figcaption>
            <div
              className="grafico-envoltura"
              role="img"
              aria-label="Dispersión del RMSE en cada pliegue, una serie por algoritmo y para la línea base"
            >
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart
                  margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--linea)" />
                  <XAxis
                    type="number"
                    dataKey="pliegue"
                    name="Pliegue"
                    domain={[1, 'dataMax']}
                    tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                    stroke="var(--apagado)"
                    tickFormatter={(v) => (Number.isInteger(v) ? v : '')}
                  />
                  <YAxis
                    dataKey="rmse"
                    name="RMSE"
                    tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                    stroke="var(--apagado)"
                    width={48}
                  />
                  <Tooltip
                    formatter={(valor, nombre) => [
                      formatearTooltip(valor),
                      nombre,
                    ]}
                  />
                  <Legend />
                  {seriesPliegues.map((serie) => (
                    <Scatter
                      key={serie.nombre}
                      name={serie.nombre}
                      data={serie.puntos}
                      fill={serie.color}
                      stroke={serie.color}
                    />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </figure>
        )}

        {filasEstabilidad.length > 1 && (
          <GraficoBarras
            titulo="Desvío del RMSE entre pliegues (estabilidad, kg/ha)"
            aria-label="Barras del desvío estándar del RMSE entre pliegues por algoritmo y línea base"
            filas={filasEstabilidad}
            series={[
              {
                clave: 'desvio',
                nombre: 'Desvío RMSE',
                color: 'var(--helecho)',
              },
            ]}
          />
        )}

        {filasR2.length > 1 && (
          <GraficoBarras
            titulo="R² de ajuste (más cerca de 1, mejor)"
            aria-label="Barras del coeficiente R cuadrado por algoritmo y línea base"
            filas={filasR2}
            series={[{ clave: 'r2', nombre: 'R²', color: 'var(--bosque)' }]}
          />
        )}

        {filasMape.length > 1 && (
          <GraficoBarras
            titulo="MAPE — error porcentual medio (%)"
            aria-label="Barras del error porcentual medio por algoritmo y línea base"
            filas={filasMape}
            series={[
              { clave: 'mape', nombre: 'MAPE (%)', color: 'var(--marigold)' },
            ]}
          />
        )}

        {filasCultivos.length > 0 && (
          <GraficoBarras
            titulo={`Error por cultivo — ${etiquetaAlgoritmo(elegido || '')} (kg/ha, top ${filasCultivos.length})`}
            aria-label="Barras del RMSE y MAE por cultivo para el algoritmo elegido"
            filas={filasCultivos}
            series={[
              { clave: 'rmse', nombre: 'RMSE', color: 'var(--helecho)' },
              { clave: 'mae', nombre: 'MAE', color: 'var(--apagado)' },
            ]}
          />
        )}
      </div>

      <div className="diagnostico-seccion">
        <h4>Holdout 20 % (prueba final)</h4>
        {holdout ? (
          <Tabla
            filas={holdout}
            columnas={[
              {
                clave: 'algoritmo',
                etiqueta: 'Algoritmo',
                celda: (fila) => etiquetaAlgoritmo(fila.algoritmo),
              },
              { clave: 'mae', etiqueta: 'MAE', celda: (fila) => cifra(fila.mae) },
              {
                clave: 'rmse',
                etiqueta: 'RMSE',
                celda: (fila) => cifra(fila.rmse),
              },
              {
                clave: 'filas',
                etiqueta: 'Filas',
                celda: (fila) =>
                  fila.filas === null || fila.filas === undefined
                    ? '—'
                    : String(fila.filas),
              },
            ]}
          />
        ) : (
          <p className="conteo">
            Sin holdout: este entrenamiento usó solo validación cruzada
            (menos de 100 campañas).
          </p>
        )}
      </div>

      <div className="diagnostico-seccion">
        <h4>Variables del modelo</h4>
        {listaVariables.length > 0 ? (
          <div className="diagnostico-chips">
            {listaVariables.map((variable) => (
              <Chip key={variable}>{variable}</Chip>
            ))}
          </div>
        ) : (
          <p className="conteo">Sin lista de variables registrada.</p>
        )}
        <h4>Descartadas por faltantes</h4>
        {fuera.length > 0 ? (
          <div className="diagnostico-chips">
            {fuera.map(([columna, fraccion]) => (
              <Chip key={columna}>
                {columna} · {cifra(Number(fraccion) * 100, 0)} % sin dato
              </Chip>
            ))}
          </div>
        ) : (
          <p className="conteo">
            Ninguna variable numérica se descartó por faltantes.
          </p>
        )}
      </div>

      <div className="diagnostico-seccion">
        <h4>Rangos vistos en el entrenamiento</h4>
        {filasRangos.length > 0 ? (
          <Tabla
            filas={filasRangos}
            columnas={[
              {
                clave: 'variable',
                etiqueta: 'Variable',
                celda: (fila) => fila.variable,
              },
              {
                clave: 'min',
                etiqueta: 'Mínimo',
                celda: (fila) => cifra(fila.min),
              },
              {
                clave: 'max',
                etiqueta: 'Máximo',
                celda: (fila) => cifra(fila.max),
              },
            ]}
          />
        ) : (
          <p className="conteo">
            Sin rangos registrados en el artefacto de este entrenamiento.
          </p>
        )}
      </div>
    </div>
  )
}
