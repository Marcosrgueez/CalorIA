import { useState, useEffect } from 'react'
import { TrendingDown, TrendingUp, Minus, Droplets, Activity, Info, Flame, Dumbbell, Moon, Heart, Timer, Zap } from 'lucide-react'
import AppHeader from '../components/layout/AppHeader'
import { calcBMR, GOALS } from '../utils/tdee'

function calcStreak(log) {
  if (!log.length) return 0
  const days = [...new Set(log.map(e => {
    const d = new Date(e.ts); d.setHours(0, 0, 0, 0); return d.getTime()
  }))].sort((a, b) => b - a)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  let streak = 0
  let expected = today.getTime()
  for (const day of days) {
    if (day === expected) { streak++; expected -= 86400000 }
    else if (day < expected) break
  }
  return streak
}

function WeightChart({ log }) {
  const entries = [...log].reverse().slice(-20)
  if (entries.length < 2) return null
  const weights = entries.map(e => e.weight)
  const minW = Math.min(...weights) - 0.5
  const maxW = Math.max(...weights) + 0.5
  const range = maxW - minW || 1
  const W = 280, H = 64, PX = 8, PY = 8
  const toX = i => PX + (i / (entries.length - 1)) * (W - PX * 2)
  const toY = w => H - PY - ((w - minW) / range) * (H - PY * 2)
  const pts = entries.map((e, i) => ({ x: toX(i), y: toY(e.weight), w: e.weight }))
  const line = pts.map(p => `${p.x},${p.y}`).join(' ')
  const area = `${pts[0].x},${H} ${line} ${pts[pts.length - 1].x},${H}`
  const last = pts[pts.length - 1]
  return (
    <div className="mt-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: '72px' }}>
        <defs>
          <linearGradient id="wg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--cta)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--cta)" stopOpacity="0.01" />
          </linearGradient>
        </defs>
        <polygon points={area} fill="url(#wg)" />
        <polyline points={line} fill="none" stroke="var(--cta)" strokeWidth="1.8"
          strokeLinecap="round" strokeLinejoin="round" />
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y}
            r={i === pts.length - 1 ? 4 : 2.5}
            fill={i === pts.length - 1 ? 'var(--cta)' : 'var(--bg-surface)'}
            stroke="var(--cta)" strokeWidth="1.8" />
        ))}
        <text x={last.x} y={last.y - 7} textAnchor="middle"
          style={{ fontSize: '9px', fill: 'var(--cta)', fontWeight: 700 }}>
          {last.w} kg
        </text>
      </svg>
      <div className="flex justify-between mt-0.5">
        <span className="text-[9px]" style={{ color: 'var(--text-3)' }}>{entries[0]?.date}</span>
        <span className="text-[9px]" style={{ color: 'var(--text-3)' }}>{entries[entries.length - 1]?.date}</span>
      </div>
    </div>
  )
}

const LOG_KEY = 'mm_weight_log'
const HYDRA_KEY = 'mm_hydration'
const MESSAGES = {
  cut:  ['Estás en déficit calórico. Mantén la constancia y los resultados llegarán.', '¡Cada día cuenta! El déficit sostenido es la clave del éxito.'],
  bulk: ['Estás en superávit calórico. Combina con entrenamiento para maximizar el músculo.', '¡Construyendo músculo día a día! Sigue con la rutina de fuerza.'],
  maintain: ['Mantener el peso es un logro en sí mismo. ¡Sigue así!', '¡Equilibrio perfecto! Estás en el camino correcto.'],
}

function bmiInfo(bmi) {
  if (bmi < 18.5) return { label: 'Bajo peso',  color: '#0ea5e9' }
  if (bmi < 25)   return { label: 'Normal',      color: '#4a7c59' }
  if (bmi < 30)   return { label: 'Sobrepeso',   color: '#f59e0b' }
  return               { label: 'Obesidad',      color: '#e8603c' }
}

function navyBodyFat(sex, height, waist, neck, hip) {
  if (!waist || !neck) return null
  if (sex === 'm') {
    return Math.max(0, (495 / (1.0324 - 0.19077 * Math.log10(waist - neck) + 0.15456 * Math.log10(height))) - 450)
  }
  if (!hip) return null
  return Math.max(0, (495 / (1.29579 - 0.35004 * Math.log10(waist + hip - neck) + 0.22100 * Math.log10(height))) - 450)
}

export default function TabStats({ theme, toggleTheme, profileState }) {
  const { profile, kcal, goalLabel } = profileState
  const [newWeight, setNewWeight] = useState('')
  const [log, setLog] = useState(() => { try { return JSON.parse(localStorage.getItem(LOG_KEY)) || [] } catch { return [] } })
  const [glasses, setGlasses] = useState(() => { try { const s = JSON.parse(localStorage.getItem(HYDRA_KEY)); return s?.date === new Date().toDateString() ? s.count : 0 } catch { return 0 } })
  const [waist, setWaist] = useState('')
  const [neck, setNeck] = useState('')
  const [hip, setHip] = useState('')

  useEffect(() => { localStorage.setItem(LOG_KEY, JSON.stringify(log)) }, [log])
  useEffect(() => { localStorage.setItem(HYDRA_KEY, JSON.stringify({ date: new Date().toDateString(), count: glasses })) }, [glasses])

  function addWeight() {
    const w = parseFloat(newWeight)
    if (!w || w < 20 || w > 300) return
    const entry = { date: new Date().toLocaleDateString('es'), weight: w, ts: Date.now() }
    setLog(l => [entry, ...l].slice(0, 90))
    setNewWeight('')
  }

  const bmi = profile.weight / Math.pow(profile.height / 100, 2)
  const bmiI = bmiInfo(bmi)
  const bodyFat = navyBodyFat(profile.sex, profile.height, parseFloat(waist), parseFloat(neck), parseFloat(hip))
  const goal = GOALS[profile.goal]
  const motMsg = (MESSAGES[profile.goal] || MESSAGES.maintain)[Math.floor(Date.now() / 86400000) % 2]

  const exerciseRec = profile.goal === 'cut'
    ? { title: 'Cardio + déficit', color: '#0ea5e9', items: [
        { Icon: Flame,    name: 'Cardio moderado',  detail: '30 min por sesión',      freq: '4×/sem' },
        { Icon: Activity, name: '8.000 pasos',       detail: 'Caminar diariamente',    freq: 'Diario' },
        { Icon: Dumbbell, name: 'Fuerza',            detail: 'Preservar músculo magro', freq: '2×/sem' },
      ]}
    : profile.goal === 'bulk'
    ? { title: 'Fuerza progresiva', color: '#4a7c59', items: [
        { Icon: Dumbbell, name: 'Push/Pull/Legs',    detail: 'Progresión de carga',    freq: '4×/sem' },
        { Icon: Activity, name: 'Cardio ligero',     detail: 'Baja intensidad',        freq: '2×/sem' },
        { Icon: Moon,     name: 'Descanso',          detail: '7–9h para recuperar',   freq: 'Diario' },
      ]}
    : { title: 'Mantenimiento activo', color: '#7c5cbf', items: [
        { Icon: Activity, name: 'Mix cardio+fuerza', detail: 'Variedad equilibrada',   freq: '3–4×/sem' },
        { Icon: Heart,    name: 'Actividad diaria',  detail: 'Caminar, nadar, escalar', freq: 'Diario' },
        { Icon: Timer,    name: '150 min cardio',    detail: 'Objetivo OMS semanal',   freq: '7 días' },
      ]}

  const lastLog = log[0]
  const prevLog = log[1]
  const delta = lastLog && prevLog ? (lastLog.weight - prevLog.weight) : null
  const streak = calcStreak(log)

  return (
    <div className="tab-enter pb-6">
      <AppHeader title="Estadísticas" subtitle="Progreso y seguimiento" theme={theme} onToggleTheme={toggleTheme} />

      <div className="px-4 space-y-4">
        {/* Motivation */}
        <div className="card p-4" style={{ background: 'var(--accent-soft)' }}>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--accent)' }}>{motMsg}</p>
        </div>

        {/* Kcal + goal + streak */}
        <div className="grid grid-cols-3 gap-3">
          <div className="card p-4 text-center">
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-1" style={{ color: 'var(--text-3)' }}>Calorías</p>
            <p className="text-[24px] font-bold tabular-nums" style={{ color: 'var(--cta)', fontFamily: '"Playfair Display",serif' }}>{kcal.toLocaleString('es')}</p>
            <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-3)' }}>kcal/día</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-1" style={{ color: 'var(--text-3)' }}>Objetivo</p>
            <p className="text-[16px] font-bold leading-snug" style={{ color: 'var(--text-1)' }}>{goalLabel}</p>
            <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-3)' }}>×{goal?.factor?.toFixed(2)}</p>
          </div>
          <div className="card p-4 text-center relative overflow-hidden"
            style={streak > 0 ? { background: 'linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)', border: '1px solid #fed7aa' } : {}}>
            <div className="absolute top-1 right-2 text-[16px] pointer-events-none" style={{ opacity: streak > 0 ? 1 : 0.2 }}>🔥</div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-1" style={{ color: streak > 0 ? '#ea580c' : 'var(--text-3)' }}>Racha</p>
            <p className="text-[24px] font-bold tabular-nums" style={{ color: streak > 0 ? '#ea580c' : 'var(--text-3)', fontFamily: '"Playfair Display",serif' }}>{streak}</p>
            <p className="text-[10px] mt-0.5" style={{ color: streak > 0 ? '#ea580c99' : 'var(--text-3)' }}>días</p>
          </div>
        </div>

        {/* BMI */}
        <div className="card p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-3" style={{ color: 'var(--text-3)' }}>Índice de masa corporal</p>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-[36px] font-bold tabular-nums" style={{ color: bmiI.color, fontFamily: '"Playfair Display",serif' }}>
                {bmi.toFixed(1)}
              </p>
              <p className="text-[13px] font-semibold" style={{ color: bmiI.color }}>{bmiI.label}</p>
            </div>
            <div className="flex-1">
              <div className="h-3 rounded-full overflow-hidden relative" style={{ background: 'var(--bg-surface2)' }}>
                {[
                  { pct: 23.1, color: '#0ea5e9' },
                  { pct: 32.1, color: '#4a7c59' },
                  { pct: 12.8, color: '#f59e0b' },
                  { pct: 32,   color: '#e8603c' },
                ].reduce((acc, s, i) => {
                  const prev = acc.offset
                  acc.items.push(<div key={i} className="absolute top-0 h-full" style={{ left: `${prev}%`, width: `${s.pct}%`, background: s.color }} />)
                  acc.offset += s.pct
                  return acc
                }, { items: [], offset: 0 }).items}
                <div className="absolute top-0 h-full w-1 -ml-0.5 rounded-full bg-white shadow"
                  style={{ left: `${Math.min(98, Math.max(2, ((bmi - 15) / 25) * 100))}%` }} />
              </div>
              <div className="flex justify-between mt-1">
                {['18.5', '25', '30'].map(v => (
                  <span key={v} className="text-[9px]" style={{ color: 'var(--text-3)' }}>{v}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Weight log */}
        <div className="card p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-3" style={{ color: 'var(--text-3)' }}>Registro de peso</p>
          <div className="flex gap-2 mb-3">
            <input
              type="number" step="0.1" value={newWeight}
              onChange={e => setNewWeight(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addWeight()}
              placeholder="Ej: 72.5"
              className="flex-1 rounded-xl px-3.5 py-2.5 text-[14px] outline-none"
              style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}
            />
            <button onClick={addWeight}
              className="px-4 py-2.5 rounded-xl font-semibold text-[13px] text-white active:scale-[0.95] transition-transform"
              style={{ background: 'var(--cta)' }}>
              + Registrar
            </button>
          </div>

          {delta !== null && (
            <div className="flex items-center gap-2 mb-3 text-[13px] font-semibold"
              style={{ color: delta < 0 ? '#4a7c59' : delta > 0 ? '#e8603c' : 'var(--text-3)' }}>
              {delta < 0 ? <TrendingDown size={16} /> : delta > 0 ? <TrendingUp size={16} /> : <Minus size={16} />}
              {delta > 0 ? '+' : ''}{delta.toFixed(1)} kg vs registro anterior
            </div>
          )}

          {log.length >= 2 && <WeightChart log={log} />}

          {log.length > 0 && (
            <div className="space-y-1.5 max-h-36 overflow-y-auto mt-3">
              {log.slice(0, 10).map((entry, i) => (
                <div key={entry.ts} className="flex items-center justify-between text-[13px] px-3 py-2 rounded-xl"
                  style={{ background: i === 0 ? 'var(--cta-soft)' : 'var(--bg-surface2)' }}>
                  <span style={{ color: 'var(--text-3)' }}>{entry.date}</span>
                  <span className="font-bold tabular-nums" style={{ color: i === 0 ? 'var(--cta)' : 'var(--text-1)' }}>
                    {entry.weight} kg
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Body fat (Navy) */}
        <div className="card p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-3" style={{ color: 'var(--text-3)' }}>
            Composición corporal (fórmula Navy)
          </p>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {[
              { label: 'Cintura (cm)', val: waist, set: setWaist },
              { label: 'Cuello (cm)', val: neck, set: setNeck },
              ...(profile.sex === 'f' ? [{ label: 'Cadera (cm)', val: hip, set: setHip }] : []),
            ].map(f => (
              <div key={f.label}>
                <label className="block text-[10px] font-medium mb-1" style={{ color: 'var(--text-3)' }}>{f.label}</label>
                <input type="number" value={f.val} onChange={e => f.set(e.target.value)} placeholder="—"
                  className="w-full rounded-lg px-2.5 py-2 text-[13px] outline-none text-center"
                  style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }} />
              </div>
            ))}
          </div>
          {bodyFat !== null ? (
            <div className="text-center rounded-xl py-3" style={{ background: 'var(--bg-surface2)' }}>
              <p className="text-[28px] font-bold" style={{ color: bodyFat < 20 ? '#4a7c59' : bodyFat < 30 ? '#f59e0b' : '#e8603c', fontFamily: '"Playfair Display",serif' }}>
                {bodyFat.toFixed(1)}%
              </p>
              <p className="text-[11px] font-medium mt-0.5" style={{ color: 'var(--text-3)' }}>Grasa corporal estimada</p>
            </div>
          ) : (
            <p className="text-[12px] text-center" style={{ color: 'var(--text-3)' }}>
              Introduce las medidas para calcular
            </p>
          )}
        </div>

        {/* Medical disclaimer */}
        <div className="px-3 py-2.5 rounded-xl flex items-start gap-2"
          style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)' }}>
          <Info size={13} className="flex-shrink-0 mt-0.5" style={{ color: 'var(--text-3)' }} />
          <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-3)' }}>
            CalorIA no sustituye el consejo de un profesional de la salud o nutricionista.
            Consulta a un médico antes de realizar cambios significativos en tu dieta.
          </p>
        </div>

        {/* Exercise plan */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-0.5 h-4 rounded-full" style={{ background: exerciseRec.color }} />
            <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text-3)' }}>
              Rutina recomendada — {exerciseRec.title}
            </p>
          </div>
          {exerciseRec.items.map(item => (
            <div key={item.name} className="card flex items-center gap-3 px-4 py-3.5">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: exerciseRec.color + '18' }}>
                <item.Icon size={18} style={{ color: exerciseRec.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-semibold" style={{ color: 'var(--text-1)' }}>{item.name}</p>
                <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-3)' }}>{item.detail}</p>
              </div>
              <span className="text-[11px] font-bold px-2.5 py-1 rounded-full flex-shrink-0"
                style={{ background: exerciseRec.color + '18', color: exerciseRec.color }}>
                {item.freq}
              </span>
            </div>
          ))}
        </div>

        {/* Hydration */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Droplets size={16} style={{ color: '#0ea5e9' }} />
            <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text-3)' }}>
              Hidratación — {glasses}/8 vasos
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            {Array.from({ length: 8 }, (_, i) => (
              <button key={i} onClick={() => setGlasses(i + 1)}
                className="w-10 h-10 rounded-xl flex items-center justify-center text-[16px] active:scale-[0.9] transition-transform"
                style={{ background: i < glasses ? '#0ea5e9' : 'var(--bg-surface2)', border: '1px solid var(--border)' }}>
                <Droplets size={16} style={{ color: i < glasses ? '#fff' : 'var(--text-3)' }} />
              </button>
            ))}
          </div>
          {glasses >= 8 && (
            <p className="mt-2 text-[12px] font-semibold" style={{ color: '#0ea5e9' }}>
              ¡Objetivo de hidratación alcanzado!
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
