import { useState } from 'react'
import { UtensilsCrossed, ChevronDown, ThumbsUp, ThumbsDown, RefreshCw, ChefHat, Clock } from 'lucide-react'
import * as api from '../../api/client'

const MEAL_LABELS = {
  desayuno: 'Desayuno',
  comida:   'Comida',
  cena:     'Cena',
  snack:    'Snack',
}

const MEAL_COLORS = {
  desayuno: '#f59e0b',
  comida:   '#4a7c59',
  cena:     '#7c5cbf',
  snack:    '#0ea5e9',
}

export default function MealCard({ meal, dietId, onSwap }) {
  const [expanded, setExpanded] = useState(false)
  const [tab, setTab] = useState('ingredients') // 'ingredients' | 'steps'
  const [rated, setRated] = useState(null)
  const [swapping, setSwapping] = useState(false)

  const { name, recipe_name, kcal_actual, cost_eur, items = [], instructions = [], prep_time_min, image_url } = meal
  const hasInstructions = instructions.length > 0
  const protein = items.reduce((s, it) => s + (it.protein_g ?? 0), 0)
  const accentColor = MEAL_COLORS[name] || 'var(--border)'

  async function onRate(direction) {
    const rating = direction === 'like' ? 1 : -1
    setRated(direction)
    try { if (dietId) await api.rateDiet(dietId, rating) } catch {}
  }

  async function handleSwap() {
    if (!onSwap || swapping) return
    setSwapping(true)
    try { await onSwap(name) } finally { setSwapping(false) }
  }

  return (
    <div
      className="meal-card card mx-4 mb-2 overflow-hidden"
      style={{ borderLeft: `3px solid ${accentColor}` }}
    >
      {/* ── Compact row ── */}
      <div className="flex overflow-hidden">

        {/* Foto cuadrada 96×96 */}
        <div className="relative w-24 h-24 flex-shrink-0 overflow-hidden">
          {image_url ? (
            <img src={image_url} alt={recipe_name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center"
              style={{ background: 'var(--bg-surface2)' }}>
              <UtensilsCrossed size={28} style={{ color: 'var(--text-3)' }} />
            </div>
          )}
          <div className="absolute bottom-0 left-0 right-0 px-1.5 py-1"
            style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.65), transparent)' }}>
            <span className="text-[9px] font-bold text-white uppercase tracking-wide">
              {MEAL_LABELS[name] || name}
            </span>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 px-3 py-2.5 min-w-0">
          <p className="text-[13px] font-semibold leading-snug mb-1.5 truncate"
            style={{ color: 'var(--text-1)' }}>
            {recipe_name}
          </p>
          <div className="flex flex-wrap gap-1">
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: 'var(--cta-soft)', color: 'var(--cta)' }}>
              {Math.round(kcal_actual)} kcal
            </span>
            {protein > 0 && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                {Math.round(protein)}g prot
              </span>
            )}
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}>
              {cost_eur?.toFixed(2)}€
            </span>
            {prep_time_min > 0 && (
              <span className="text-[11px] px-2 py-0.5 rounded-full"
                style={{ background: 'var(--bg-surface2)', color: 'var(--text-3)' }}>
                {prep_time_min} min
              </span>
            )}
          </div>
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(o => !o)}
          className="px-3 flex items-center self-stretch active:opacity-60 transition-opacity"
          style={{ color: 'var(--text-3)' }}>
          <ChevronDown
            size={16}
            className={`transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          />
        </button>
      </div>

      {/* ── Expanded content ── */}
      <div style={{
        maxHeight: expanded ? '900px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 380ms cubic-bezier(0.16,1,0.3,1)',
      }}>
        <div style={{ borderTop: '1px solid var(--border)' }}>

          {/* Tab bar */}
          <div className="flex" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface2)' }}>
            <button
              onClick={() => setTab('ingredients')}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-semibold transition-colors"
              style={{
                color: tab === 'ingredients' ? 'var(--cta)' : 'var(--text-3)',
                borderBottom: tab === 'ingredients' ? '2px solid var(--cta)' : '2px solid transparent',
              }}>
              <UtensilsCrossed size={12} /> Ingredientes
            </button>
            {hasInstructions && (
              <button
                onClick={() => setTab('steps')}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-semibold transition-colors"
                style={{
                  color: tab === 'steps' ? accentColor : 'var(--text-3)',
                  borderBottom: tab === 'steps' ? `2px solid ${accentColor}` : '2px solid transparent',
                }}>
                <ChefHat size={12} /> Preparación
                {prep_time_min > 0 && (
                  <span className="flex items-center gap-0.5 text-[10px]" style={{ color: 'var(--text-3)' }}>
                    <Clock size={10} />{prep_time_min}m
                  </span>
                )}
              </button>
            )}
          </div>

          {/* Ingredients tab */}
          {tab === 'ingredients' && (
            <>
              <div
                className="grid px-3 py-2 text-[10px] font-bold uppercase tracking-[0.06em]"
                style={{
                  gridTemplateColumns: '1fr 44px 52px 40px',
                  background: 'var(--bg-surface2)',
                  color: 'var(--text-3)',
                  borderBottom: '1px solid var(--border)',
                }}>
                <div>Ingrediente</div>
                <div className="text-right">g</div>
                <div className="text-right">kcal</div>
                <div className="text-right">€</div>
              </div>
              {items.map((item, i) => (
                <div
                  key={i}
                  className="ing-row grid px-3 py-2 text-[12px] items-center"
                  style={{
                    '--i': i,
                    gridTemplateColumns: '1fr 44px 52px 40px',
                    borderBottom: '1px solid var(--border)',
                    color: 'var(--text-2)',
                  }}>
                  <div className="truncate pr-2" style={{ color: 'var(--text-1)' }}>{item.product}</div>
                  <div className="text-right tabular-nums">{Math.round(item.grams)}</div>
                  <div className="text-right tabular-nums">{Math.round(item.kcal)}</div>
                  <div className="text-right tabular-nums">{item.cost_eur?.toFixed(2)}</div>
                </div>
              ))}
            </>
          )}

          {/* Steps tab */}
          {tab === 'steps' && hasInstructions && (
            <div className="px-4 py-3 space-y-3">
              {instructions.map((step, i) => (
                <div key={i} className="flex gap-3 items-start">
                  <span
                    className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white mt-0.5"
                    style={{ background: accentColor }}>
                    {i + 1}
                  </span>
                  <span className="text-[13px] leading-relaxed" style={{ color: 'var(--text-1)' }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Rating + Swap */}
          <div className="flex gap-2 px-3 py-2.5" style={{ borderTop: '1px solid var(--border)' }}>
            <button
              onClick={() => onRate('like')}
              className="flex-1 flex items-center justify-center gap-1.5 text-[12px] font-semibold py-2 rounded-xl active:scale-[0.97] transition-all duration-150"
              style={{
                background: rated === 'like' ? '#dcfce7' : 'var(--bg-surface2)',
                color: rated === 'like' ? '#16a34a' : 'var(--text-2)',
                border: `1.5px solid ${rated === 'like' ? '#86efac' : 'transparent'}`,
              }}>
              <ThumbsUp size={13} /> Me gusta
            </button>
            <button
              onClick={() => onRate('dislike')}
              className="flex-1 flex items-center justify-center gap-1.5 text-[12px] font-semibold py-2 rounded-xl active:scale-[0.97] transition-all duration-150"
              style={{
                background: rated === 'dislike' ? 'var(--cta-soft)' : 'var(--bg-surface2)',
                color: rated === 'dislike' ? 'var(--cta)' : 'var(--text-2)',
                border: `1.5px solid ${rated === 'dislike' ? 'var(--cta)' : 'transparent'}`,
              }}>
              <ThumbsDown size={13} /> Mejorar
            </button>
            {onSwap && (
              <button
                onClick={handleSwap}
                disabled={swapping}
                className="flex items-center justify-center gap-1.5 text-[12px] font-semibold px-3 py-2 rounded-xl active:scale-[0.97] transition-all duration-150 disabled:opacity-50"
                style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}>
                <RefreshCw size={13} className={swapping ? 'animate-spin' : ''} />
                {swapping ? '' : 'Cambiar'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
