// Mini-gráfico SVG sem dependências externas
export default function Sparkline({
  data,
  width = 520,
  height = 120,
  color = 'var(--info)',
}: {
  data: number[]
  width?: number
  height?: number
  color?: string
}) {
  if (data.length < 2) {
    return <p className="muted">Aguardando leituras…</p>
  }
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pad = 8
  const pts = data.map((v, i) => {
    const x = pad + (i * (width - 2 * pad)) / (data.length - 1)
    const y = height - pad - ((v - min) * (height - 2 * pad)) / range
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto' }}>
      <polyline
        points={pts.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {pts.map((p, i) => {
        const [x, y] = p.split(',')
        return <circle key={i} cx={x} cy={y} r="3" fill={color} />
      })}
    </svg>
  )
}
