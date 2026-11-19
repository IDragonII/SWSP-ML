import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const BINS = 20
const UMBRALES = [
  ['p10', 'Dentro de ±10%', 0.1],
  ['p20', 'Dentro de ±20%', 0.2],
]

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

// % de predicciones cuyo error relativo no supera el umbral
function dentroDe(reales, predichos, umbral) {
  let cuenta = 0
  let total = 0
  for (let i = 0; i < reales.length; i += 1) {
    const real = reales[i]
    if (!real) continue
    total += 1
    if (Math.abs(predichos[i] - real) / Math.abs(real) <= umbral) {
      cuenta += 1
    }
  }
  return total ? (cuenta / total) * 100 : null
}

function histograma(residuos, cantidad = BINS) {
  let min = Infinity
  let max = -Infinity
  for (const r of residuos) {
    if (r < min) min = r
    if (r > max) max = r
  }
  const ancho = (max - min) / cantidad || 1
  const bins = Array.from({ length: cantidad }, (_, i) => ({
    inicio: min + i * ancho,
    centro: min + (i + 0.5) * ancho,
    frecuencia: 0,
  }))
  for (const r of residuos) {
    let i = Math.floor((r - min) / ancho)
    if (i >= cantidad) i = cantidad - 1
    if (i < 0) i = 0
    bins[i].frecuencia += 1
  }
  return bins.map((bin) => ({
    ...bin,
    etiqueta: bin.centro.toFixed(1),
    sobre: bin.centro >= 0,
  }))
}

function minMax(puntos, claves) {
  let min = Infinity
  let max = -Infinity
  for (const punto of puntos) {
    for (const clave of claves) {
      const v = punto[clave]
      if (v < min) min = v
      if (v > max) max = v
    }
  }
  if (!Number.isFinite(min)) return [0, 1]
  return [min, max]
}

function Grafico({ titulo, aria, children }) {
  return (
    <figure className="grafico-bloque">
      <figcaption>{titulo}</figcaption>
      <div className="grafico-envoltura" role="img" aria-label={aria}>
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
    </figure>
  )
}

/**
 * Detalle de métricas de UN modelo en el modal «Métricas» (S24), con
 * las equivalencias regresión ← clasificación: predicho vs real con
 * diagonal (matriz de confusión), residuales con signo (falsos
 * positivos/negativos), R² + % dentro de ±10/±20 % (accuracy) y curva
 * de error acumulado (ROC). MAE/RMSE ya están en la tabla y aquí.
 * Sin muestra persistida (entrenamiento viejo) solo muestra stats.
 */
export default function MetricasModelo({ modelo, muestra, lineaBase }) {
  const algoritmo = etiquetaAlgoritmo(modelo.algoritmo)
  const mape = num(modelo.hiperparametros?.validacion?.mape)
  const reales = muestra?.reales || []
  const predichos = muestra?.predichos || []
  const hayMuestra = reales.length > 0 && reales.length === predichos.length

  const stats = [
    { dt: 'MAE (kg/ha)', dd: cifra(modelo.mae) },
    { dt: 'RMSE (kg/ha)', dd: cifra(modelo.rmse) },
    { dt: 'R²', dd: cifra(modelo.r2, 4) },
    { dt: 'MAPE (%)', dd: mape === null ? '—' : cifra(mape) },
    ...(hayMuestra
      ? UMBRALES.map(([clave, etiqueta, umbral]) => ({
          dt: etiqueta,
          dd:
            dentroDe(reales, predichos, umbral) === null
              ? '—'
              : `${cifra(dentroDe(reales, predichos, umbral), 1)} %`,
          clave,
        }))
      : []),
  ]

  const residuos = hayMuestra
    ? predichos.map((p, i) => p - reales[i])
    : []
  const puntos = hayMuestra
    ? reales.map((r, i) => ({ real: r, predicho: predichos[i] }))
    : []
  const [min, max] = minMax(puntos, ['real', 'predicho'])
  const margen = (max - min) * 0.05 || 1
  const dominio = [min - margen, max + margen]
  const bins = hayMuestra ? histograma(residuos) : []
  const acumulados = [...residuos].map(Math.abs).sort((a, b) => a - b)
  const curva = acumulados.map((v, i) => ({
    error: v,
    pct: ((i + 1) / acumulados.length) * 100,
  }))

  return (
    <div>
      <p className="texto-intro">
        <strong>{algoritmo}</strong> · versión {modelo.version} — métricas
        de la validación cruzada (predicciones out-of-fold).
      </p>

      <dl className="datos-rejilla">
        {stats.map((stat) => (
          <div key={stat.dt + (stat.clave || '')}>
            <dt>{stat.dt}</dt>
            <dd>{stat.dd}</dd>
          </div>
        ))}
      </dl>

      {lineaBase && (
        <p className="conteo">
          Línea base para comparar: MAE {cifra(lineaBase.mae)} · RMSE{' '}
          {cifra(lineaBase.rmse)} · R² {cifra(lineaBase.r2, 4)}
        </p>
      )}

      {!hayMuestra ? (
        <p className="conteo">
          Este entrenamiento no guardó las predicciones fila a fila: solo
          reentrenando con la versión actual del sistema aparecen los
          gráficos de diagnóstico.
        </p>
      ) : (
        <div className="graficos-rejilla">
          <Grafico
            titulo="Predicho vs real (diagonal = acierto perfecto)"
            aria-label={`Dispersión de predicho contra real para ${algoritmo}: los puntos sobre la diagonal son aciertos`}
          >
            <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--linea)" />
              <XAxis
                type="number"
                dataKey="real"
                name="Real"
                domain={dominio}
                tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                stroke="var(--apagado)"
                width={48}
              />
              <YAxis
                type="number"
                dataKey="predicho"
                name="Predicho"
                domain={dominio}
                tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                stroke="var(--apagado)"
                width={56}
              />
              <Tooltip
                formatter={(valor, nombre) => [
                  formatearTooltip(valor),
                  nombre,
                ]}
              />
              <ReferenceLine
                segment={[
                  { x: dominio[0], y: dominio[0] },
                  { x: dominio[1], y: dominio[1] },
                ]}
                stroke="var(--apagado)"
                strokeDasharray="5 4"
              />
              <Scatter
                name="Predicciones"
                data={puntos}
                fill="var(--helecho)"
                fillOpacity={0.6}
              />
            </ScatterChart>
          </Grafico>

          <Grafico
            titulo="Residuales (predicho − real): ámbar sobreestima, verde subestima"
            aria-label={`Histograma de residuales para ${algoritmo}: residuales positivos en ámbar y negativos en verde`}
          >
            <BarChart data={bins} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--linea)" />
              <XAxis
                dataKey="etiqueta"
                tick={{ fontSize: 11, fill: 'var(--tinta)' }}
                stroke="var(--apagado)"
                interval="preserveStartEnd"
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                stroke="var(--apagado)"
                width={40}
              />
              <Tooltip
                formatter={(valor, nombre) => [formatearTooltip(valor), nombre]}
                labelFormatter={(centro) => `Residual ≈ ${centro} kg/ha`}
              />
              <Bar dataKey="frecuencia" name="Predicciones">
                {bins.map((bin) => (
                  <Cell
                    key={bin.centro}
                    fill={bin.sobre ? 'var(--marigold)' : 'var(--helecho)'}
                  />
                ))}
              </Bar>
            </BarChart>
          </Grafico>

          <Grafico
            titulo="Error acumulado: % de predicciones con |error| ≤ x kg/ha"
            aria-label={`Curva de error acumulado para ${algoritmo}: porcentaje de predicciones cuyo error absoluto no supera cada umbral`}
          >
            <LineChart data={curva} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--linea)" />
              <XAxis
                type="number"
                dataKey="error"
                domain={[0, 'dataMax']}
                tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                stroke="var(--apagado)"
                width={48}
              />
              <YAxis
                type="number"
                dataKey="pct"
                domain={[0, 100]}
                tick={{ fontSize: 12, fill: 'var(--tinta)' }}
                stroke="var(--apagado)"
                width={40}
              />
              <Tooltip
                formatter={(valor, nombre) => [
                  `${formatearTooltip(valor)}${nombre === 'pct' ? ' %' : ''}`,
                  nombre === 'pct' ? 'Predicciones' : nombre,
                ]}
                labelFormatter={(error) => `|error| ≤ ${formatearTooltip(error)} kg/ha`}
              />
              <Line
                type="monotone"
                dataKey="pct"
                name="pct"
                stroke="var(--bosque)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </Grafico>
        </div>
      )}
    </div>
  )
}
