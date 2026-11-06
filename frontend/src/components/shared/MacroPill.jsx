const MACRO_COLORS = {
  protein: '#4a7c59',
  fat:     '#f59e0b',
  carbs:   '#e8603c',
  kcal:    '#7c5cbf',
  cost:    '#0ea5e9',
}

export default function MacroPill({ type = 'kcal', value, unit }) {
  const color = MACRO_COLORS[type] || 'var(--text-2)'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold"
      style={{ background: color + '18', color }}
    >
      <span className="tabular-nums">{value}</span>
      {unit && <span className="opacity-70">{unit}</span>}
    </span>
  )
}
