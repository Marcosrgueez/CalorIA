import { useEffect, useState } from 'react'

const MACROS = [
  { key: 'protein_g', label: 'Proteína', unit: 'g', color: '#4a7c59', delay: '60ms',  target: 150 },
  { key: 'fat_g',     label: 'Grasa',    unit: 'g', color: '#f59e0b', delay: '120ms', target: 80  },
  { key: 'carbs_g',   label: 'Carbos',   unit: 'g', color: '#e8603c', delay: '180ms', target: 250 },
  { key: 'cost_eur',  label: 'Coste',    unit: '€', color: '#7c5cbf', delay: '240ms', target: 10  },
]

export default function MacrosCard({ macros = {} }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => { const t = setTimeout(() => setMounted(true), 50); return () => clearTimeout(t) }, [])

  const kcal     = Math.round(macros.kcal      ?? 0)
  const protein  = Math.round(macros.protein_g ?? 0)
  const fat      = Math.round(macros.fat_g     ?? 0)
  const carbs    = Math.round(macros.carbs_g   ?? 0)
  const cost     = (macros.cost_eur ?? 0).toFixed(2)

  const values = { protein_g: protein, fat_g: fat, carbs_g: carbs, cost_eur: parseFloat(cost) }

  return (
    <div className="card mx-4 mb-3 p-4">
      {/* Hero kcal */}
      <div className="text-center pb-4 mb-4" style={{ borderBottom: '1px solid var(--border)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] mb-3" style={{ color: 'var(--text-3)' }}>
          Total del día
        </p>
        <div className="relative inline-flex items-center justify-center py-2">
          <div className="absolute w-28 h-28 rounded-full pulse-ring pointer-events-none"
            style={{ background: 'var(--cta)', opacity: 0.06 }} />
          <div className="absolute w-20 h-20 rounded-full pointer-events-none"
            style={{ background: 'var(--cta)', opacity: 0.05 }} />
          <p
            className="number-enter tabular-nums font-bold tracking-tight leading-none relative"
            style={{ fontSize: '42px', color: 'var(--text-1)', fontFamily: '"Playfair Display", serif' }}
          >
            {kcal.toLocaleString('es')}
          </p>
        </div>
        <p className="text-[13px] font-semibold mt-1" style={{ color: 'var(--cta)' }}>kcal</p>
        <div
          className="mx-auto mt-3 h-px w-24 rounded-full"
          style={{ background: 'linear-gradient(to right, transparent, var(--cta), transparent)' }}
        />
      </div>

      {/* 2×2 macro grid — coste incluido */}
      <div className="grid grid-cols-2 gap-4">
        {MACROS.map(m => {
          const val = values[m.key] ?? 0
          const pct = Math.min(100, Math.round((val / m.target) * 100))
          return (
            <div key={m.key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold uppercase tracking-[0.1em]" style={{ color: 'var(--text-3)' }}>
                  {m.label}
                </span>
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                  style={{ background: m.color + '18', color: m.color }}
                >
                  OK
                </span>
              </div>
              <div className="flex items-baseline gap-1 mb-2">
                <span
                  className="text-[22px] font-bold tabular-nums tracking-tight leading-none"
                  style={{ color: 'var(--text-1)' }}
                >
                  {m.key === 'cost_eur' ? cost : val}
                </span>
                <span className="text-[12px]" style={{ color: 'var(--text-3)' }}>{m.unit}</span>
              </div>
              <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface2)' }}>
                <div
                  className="h-full rounded-full progress-bar"
                  style={{
                    width: mounted ? `${pct}%` : '0%',
                    background: m.color,
                    transitionDelay: m.delay,
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-[10px] text-center mt-3 leading-relaxed" style={{ color: 'var(--text-3)' }}>
        * Precios orientativos obtenidos de fuentes públicas. Pueden variar.
        Consulta el precio exacto en la web del supermercado.
      </p>
    </div>
  )
}
