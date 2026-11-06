import { useState } from 'react'
import { ChevronDown, Zap, Calendar, RefreshCw, AlertCircle, Refrigerator, ShoppingCart, Info, TrendingDown, TrendingUp, Minus } from 'lucide-react'
import AppHeader from '../components/layout/AppHeader'
import MealCard from '../components/results/MealCard'
import MacrosCard from '../components/results/MacrosCard'
import SliderField from '../components/ui/SliderField'
import Toggle from '../components/ui/Toggle'
import Spinner from '../components/ui/Spinner'
import { useDiet } from '../hooks/useDiet'
import { DietPageSkeleton } from '../components/ui/Skeleton'
import { ACTIVITY_LEVELS, GOALS } from '../utils/tdee'

const SM_OPTIONS = [
  { val: 'mercadona', label: 'Mercadona', initial: 'M',  color: '#007bc4', bg: '#e8f4fd' },
  { val: 'carrefour', label: 'Carrefour', initial: 'C',  color: '#004f9f', bg: '#e8eef8' },
  { val: 'gadis',     label: 'Gadis',     initial: 'G',  color: '#e30613', bg: '#fdeaea' },
  { val: 'consum',    label: 'Consum',    initial: 'Co', color: '#e30613', bg: '#fdeaea' },
  { val: 'todos',     label: 'Todos',     initial: 'T',  color: '#4a7c59', bg: '#eef5f0' },
]

const FRIDGE_QUICK = ['pollo','huevo','arroz','pasta','atún','tomate','cebolla','lentejas','brócoli','salmón','carne','queso']

const GOAL_STYLES = {
  cut:      { color: '#0ea5e9', bg: '#f0f9ff', Icon: TrendingDown },
  maintain: { color: '#7c5cbf', bg: '#f3f0fb', Icon: Minus },
  bulk:     { color: '#4a7c59', bg: '#eef5f0', Icon: TrendingUp },
}

// ── Section header — consistent accent bar pattern ─────────────────────────
function SectionHeader({ label, color }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-0.5 h-4 rounded-full" style={{ background: color || 'var(--cta)' }} />
      <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text-3)' }}>{label}</p>
    </div>
  )
}

// ── Generate view ──────────────────────────────────────────────────────────
function PlanGenerateView({ profileState, onGenerate, onGenerateWeek, loading, error, onGenerateFridge }) {
  const { profile, updateProfile, macros, kcal } = profileState
  const [macrosOpen, setMacrosOpen] = useState(false)
  const [fridgeMode, setFridgeMode] = useState(false)
  const [selectedFridge, setSelectedFridge] = useState(new Set())
  const [customFridge, setCustomFridge] = useState('')

  function toggleFridge(id) {
    setSelectedFridge(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  function handleFridgeGenerate() {
    const custom = customFridge.split(',').map(s => s.trim()).filter(Boolean)
    const all = [...new Set([...selectedFridge, ...custom])]
    if (all.length === 0) return
    onGenerateFridge({ name: profile.name || 'Usuario', ingredients: all, kcal_target: kcal, budget_eur: profile.budget })
  }

  return (
    <div className="px-5 space-y-4 pb-8">
      {/* Error */}
      {error && (
        <div className="rounded-2xl p-4 flex gap-3" style={{ background: 'var(--cta-soft)', border: '1px solid var(--cta)' }}>
          <AlertCircle size={18} style={{ color: 'var(--cta)', flexShrink: 0, marginTop: 1 }} />
          <div>
            <p className="text-[13px] font-semibold" style={{ color: 'var(--cta)' }}>{error.message}</p>
            {error.suggestions?.length > 0 && (
              <ul className="mt-1.5 space-y-0.5">
                {error.suggestions.map(s => (
                  <li key={s} className="text-[12px]" style={{ color: 'var(--text-2)' }}>· {s}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Datos personales */}
      <div className="card p-4">
        <SectionHeader label="Datos personales" />
        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium mb-1.5" style={{ color: 'var(--text-2)' }}>Nombre</label>
            <input
              value={profile.name}
              onChange={e => updateProfile('name', e.target.value)}
              placeholder="Tu nombre"
              className="w-full rounded-xl px-4 py-2.5 text-[14px] outline-none"
              style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[12px] font-medium mb-1.5" style={{ color: 'var(--text-2)' }}>Sexo</label>
              <select value={profile.sex} onChange={e => updateProfile('sex', e.target.value)}
                className="w-full rounded-xl px-3 py-2.5 text-[13px] outline-none appearance-none"
                style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}>
                <option value="m">Hombre</option>
                <option value="f">Mujer</option>
              </select>
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5" style={{ color: 'var(--text-2)' }}>Actividad</label>
              <select value={profile.activity} onChange={e => updateProfile('activity', parseFloat(e.target.value))}
                className="w-full rounded-xl px-3 py-2.5 text-[13px] outline-none appearance-none"
                style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}>
                {ACTIVITY_LEVELS.map(a => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </div>
          </div>
          <SliderField label="Edad"   id="age"    value={profile.age}    min={16}  max={80}  unit=" años" onChange={v => updateProfile('age', v)} />
          <SliderField label="Peso"   id="weight" value={profile.weight} min={40}  max={180} step={0.5} unit=" kg" onChange={v => updateProfile('weight', v)} />
          <SliderField label="Altura" id="height" value={profile.height} min={140} max={220} unit=" cm" onChange={v => updateProfile('height', v)} />
        </div>
      </div>

      {/* Objetivo */}
      <div className="card p-4">
        <SectionHeader label="Objetivo" />
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(GOALS).map(([key, g]) => {
            const gs = GOAL_STYLES[key] || {}
            const isActive = profile.goal === key
            return (
              <button key={key} onClick={() => updateProfile('goal', key)}
                className="flex flex-col items-center gap-1.5 py-3.5 rounded-xl text-[12px] font-semibold transition-all active:scale-[0.95]"
                style={{
                  background: isActive ? gs.bg : 'var(--bg-surface2)',
                  color: isActive ? gs.color : 'var(--text-2)',
                  border: `1.5px solid ${isActive ? gs.color : 'var(--border)'}`,
                  boxShadow: isActive ? `0 2px 12px ${gs.color}30` : 'none',
                }}>
                {gs.Icon && <gs.Icon size={16} style={{ color: isActive ? gs.color : 'var(--text-3)' }} />}
                {g.label}
              </button>
            )
          })}
        </div>

        {/* Kcal hero card */}
        <div className="mt-3 relative overflow-hidden rounded-2xl px-4 py-4"
          style={{ background: 'linear-gradient(135deg, var(--cta-soft) 0%, var(--accent-soft) 100%)', border: '1px solid var(--border)' }}>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ opacity: 0.07 }}>
            <Zap size={64} style={{ color: 'var(--cta)' }} />
          </div>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-1" style={{ color: 'var(--text-3)' }}>
            Tu objetivo diario
          </p>
          <div className="flex items-baseline gap-1.5 mb-3">
            <span className="tabular-nums font-bold leading-none"
              style={{ fontSize: '34px', color: 'var(--cta)', fontFamily: '"Playfair Display",serif' }}>
              {kcal.toLocaleString('es')}
            </span>
            <span className="text-[14px] font-semibold" style={{ color: 'var(--text-3)' }}>kcal / día</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {[
              { label: 'Proteína', val: `${macros.prot}g`,     color: '#4a7c59' },
              { label: 'Grasa',    val: `${macros.fat}g`,      color: '#f59e0b' },
              { label: 'Carbos',   val: `${macros.carbsMin}g`, color: '#e8603c' },
            ].map(m => (
              <div key={m.label} className="flex items-center gap-1 px-2.5 py-1 rounded-full"
                style={{ background: m.color + '18' }}>
                <span className="text-[12px] font-bold" style={{ color: m.color }}>{m.val}</span>
                <span className="text-[10px] font-medium" style={{ color: m.color + 'aa' }}>{m.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Compra */}
      <div className="card p-4">
        <SectionHeader label="Compra" color="var(--accent)" />
        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium mb-2" style={{ color: 'var(--text-2)' }}>Supermercado</label>
            <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
              {SM_OPTIONS.map(s => {
                const active = profile.supermarket === s.val
                return (
                  <button key={s.val} onClick={() => updateProfile('supermarket', s.val)}
                    className="flex-shrink-0 flex flex-col items-center gap-2 p-3 rounded-2xl w-[72px] transition-all duration-150 active:scale-[0.95]"
                    style={{
                      background: active ? s.bg : 'var(--bg-surface2)',
                      border: `2px solid ${active ? s.color : 'transparent'}`,
                      boxShadow: active ? `0 2px 12px ${s.color}30` : 'none',
                    }}>
                    <div className="w-11 h-11 rounded-xl flex items-center justify-center font-bold text-[15px]"
                      style={{ background: active ? s.color : s.bg, color: active ? '#fff' : s.color }}>
                      {s.initial}
                    </div>
                    <span className="text-[10px] font-semibold text-center leading-tight"
                      style={{ color: active ? s.color : 'var(--text-2)' }}>
                      {s.label}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
          <SliderField label="Presupuesto diario" id="budget" value={profile.budget} min={2} max={20} step={0.5} unit="€" onChange={v => updateProfile('budget', v)} />
        </div>
      </div>

      {/* Macros avanzados */}
      <div className="card overflow-hidden">
        <button onClick={() => setMacrosOpen(o => !o)}
          className="w-full flex items-center justify-between px-4 py-3.5 text-[13px] font-medium active:opacity-70 transition-opacity"
          style={{ color: 'var(--text-2)' }}>
          <span>Macros avanzados</span>
          <ChevronDown size={16}
            className={`transition-transform duration-200 ${macrosOpen ? 'rotate-180' : ''}`}
            style={{ color: 'var(--text-3)' }} />
        </button>
        {macrosOpen && (
          <div className="px-4 pb-4 space-y-4" style={{ borderTop: '1px solid var(--border)' }}>
            <div className="pt-3 grid grid-cols-2 gap-3 text-center">
              {[
                { label: 'Proteína mín.', val: macros.prot,     unit: 'g', color: '#4a7c59' },
                { label: 'Grasa máx.',    val: macros.fat,      unit: 'g', color: '#f59e0b' },
                { label: 'Carbos mín.',   val: macros.carbsMin, unit: 'g', color: '#e8603c' },
                { label: 'Carbos máx.',   val: macros.carbsMax, unit: 'g', color: '#7c5cbf' },
              ].map(m => (
                <div key={m.label} className="rounded-xl py-3" style={{ background: 'var(--bg-surface2)' }}>
                  <p className="text-[20px] font-bold tabular-nums" style={{ color: m.color, fontFamily: '"Playfair Display",serif' }}>{m.val}</p>
                  <p className="text-[10px] font-medium mt-0.5" style={{ color: 'var(--text-3)' }}>{m.unit} · {m.label}</p>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-center" style={{ color: 'var(--text-3)' }}>
              Calculados automáticamente según tu objetivo
            </p>
          </div>
        )}
      </div>

      {/* Nevera vacía */}
      <div className="card p-4 overflow-hidden"
        style={fridgeMode ? { border: '1.5px solid var(--accent)', background: 'linear-gradient(135deg, var(--bg-surface) 60%, var(--accent-soft) 100%)' } : {}}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: fridgeMode ? 'var(--accent-soft)' : 'var(--bg-surface2)' }}>
              <Refrigerator size={16} style={{ color: fridgeMode ? 'var(--accent)' : 'var(--text-3)' }} />
            </div>
            <div>
              <p className="text-[13px] font-semibold" style={{ color: 'var(--text-1)' }}>Modo nevera vacía</p>
              {!fridgeMode && <p className="text-[11px]" style={{ color: 'var(--text-3)' }}>Genera recetas con lo que tienes</p>}
            </div>
          </div>
          <Toggle checked={fridgeMode} onChange={setFridgeMode} />
        </div>
        {fridgeMode && (
          <div className="space-y-3 mt-1">
            <p className="text-[12px]" style={{ color: 'var(--text-2)' }}>Selecciona los ingredientes disponibles:</p>
            <div className="flex flex-wrap gap-2">
              {FRIDGE_QUICK.map(item => (
                <button key={item} onClick={() => toggleFridge(item)}
                  className="px-3 py-1.5 rounded-lg text-[12px] font-medium capitalize transition-all active:scale-[0.95]"
                  style={{
                    background: selectedFridge.has(item) ? 'var(--accent-soft)' : 'var(--bg-surface2)',
                    color: selectedFridge.has(item) ? 'var(--accent)' : 'var(--text-2)',
                    border: `1px solid ${selectedFridge.has(item) ? 'var(--accent)' : 'var(--border)'}`,
                  }}>
                  {item}
                </button>
              ))}
            </div>
            <input value={customFridge} onChange={e => setCustomFridge(e.target.value)}
              placeholder="Otros ingredientes separados por comas…"
              className="w-full rounded-xl px-3.5 py-2.5 text-[13px] outline-none"
              style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }} />
            <button onClick={handleFridgeGenerate}
              disabled={loading.fridge || (selectedFridge.size === 0 && !customFridge.trim())}
              className="w-full h-12 rounded-xl text-white font-bold text-[14px] flex items-center justify-center gap-2 active:scale-[0.97] transition-transform disabled:opacity-50"
              style={{ background: 'var(--accent)', boxShadow: '0 4px 16px rgba(74,124,89,0.3)' }}>
              {loading.fridge ? <Spinner size={18} color="#fff" /> : <Refrigerator size={18} />}
              Generar con lo que tengo
            </button>
          </div>
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

      {/* CTAs */}
      {!fridgeMode && (
        <div className="rounded-2xl p-4 space-y-3"
          style={{ background: 'linear-gradient(135deg, var(--cta-soft) 0%, var(--accent-soft) 100%)', border: '1px solid var(--border)' }}>
          <p className="text-[11px] text-center font-semibold" style={{ color: 'var(--text-3)' }}>
            ¿Listo? La IA generará tu menú en segundos
          </p>
          <button onClick={onGenerate}
            disabled={loading.today}
            className="w-full h-14 rounded-2xl text-white font-bold text-[15px] flex items-center justify-center gap-2.5 active:scale-[0.97] transition-transform disabled:opacity-60 cta-pulse"
            style={{ background: 'var(--cta)' }}>
            {loading.today ? <Spinner size={20} color="#fff" /> : <Zap size={20} />}
            Generar Dieta de Hoy
          </button>
          <button onClick={onGenerateWeek}
            disabled={loading.week}
            className="w-full h-12 rounded-2xl font-semibold text-[14px] flex items-center justify-center gap-2 active:scale-[0.97] transition-transform disabled:opacity-60"
            style={{ background: 'var(--bg-surface)', color: 'var(--text-1)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            {loading.week ? <Spinner size={18} /> : <Calendar size={18} style={{ color: 'var(--accent)' }} />}
            Plan Semanal — 7 días
          </button>
        </div>
      )}
    </div>
  )
}

// ── Results view ───────────────────────────────────────────────────────────
function PlanResultsView({ diet, onSwap }) {
  const mealCount = diet.meals?.length ?? 0
  return (
    <div className="pb-6">
      <div className="px-5 mb-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text-3)' }}>
          {mealCount} comida{mealCount !== 1 ? 's' : ''} · dieta de hoy
        </p>
      </div>
      <MacrosCard macros={diet.macros} />
      {diet.meals?.map((meal, i) => (
        <MealCard
          key={i}
          meal={meal}
          dietId={diet.diet_id}
          onSwap={onSwap ? (mealName) => onSwap(diet.diet_id, mealName) : undefined}
        />
      ))}
    </div>
  )
}

// ── Week view ──────────────────────────────────────────────────────────────
function PlanWeekView({ weekPlan, onGenerateWeek, loading }) {
  const [dayIdx, setDayIdx] = useState(0)
  const days = weekPlan?.days ?? []
  const selected = days[dayIdx]

  return (
    <div className="pb-6">
      {/* Day pills with kcal */}
      <div className="flex gap-2 px-5 mb-4 overflow-x-auto no-scrollbar">
        {days.map((d, i) => (
          <button key={d.day} onClick={() => setDayIdx(i)}
            className="flex-shrink-0 flex flex-col items-center px-3 py-2.5 rounded-xl transition-all active:scale-[0.95]"
            style={{
              background: i === dayIdx ? 'var(--cta)' : 'var(--bg-surface2)',
              color: i === dayIdx ? '#fff' : 'var(--text-2)',
              minWidth: '52px',
            }}>
            <span className="text-[12px] font-bold">{d.day.slice(0, 3)}</span>
            <span className="text-[9px] tabular-nums mt-0.5" style={{ opacity: 0.75 }}>
              {Math.round(d.diet?.macros?.kcal ?? 0)} kcal
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <>
          <div className="px-5 mb-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text-3)' }}>
              MENÚ DEL DÍA
            </p>
            <p className="text-[20px] font-bold tracking-[-0.01em]"
              style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
              {selected.day}
            </p>
          </div>
          <MacrosCard macros={selected.diet.macros} />
          {selected.diet.meals?.map((meal, i) => (
            <MealCard key={i} meal={meal} dietId={selected.diet.diet_id} />
          ))}
        </>
      )}

      <div className="px-5 mt-4">
        <button onClick={onGenerateWeek} disabled={loading}
          className="w-full h-12 rounded-xl font-semibold text-[14px] flex items-center justify-center gap-2 active:scale-[0.97] transition-transform disabled:opacity-60"
          style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)', border: '1px solid var(--border)' }}>
          {loading ? <Spinner size={18} /> : <RefreshCw size={16} />}
          Regenerar semana con IA
        </button>
      </div>
    </div>
  )
}

// ── Shopping view ──────────────────────────────────────────────────────────
function PlanShoppingView({ shoppingData, onGenerateShopping, loading }) {
  if (!shoppingData) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
        <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 relative overflow-hidden"
          style={{ background: 'linear-gradient(135deg, var(--accent-soft) 0%, var(--cta-soft) 100%)', border: '1px solid var(--border)' }}>
          <ShoppingCart size={32} style={{ color: 'var(--accent)' }} />
        </div>
        <p className="text-[20px] font-bold mb-2 tracking-[-0.01em]"
          style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
          Lista de la compra
        </p>
        <p className="text-[13px] mb-6 leading-relaxed" style={{ color: 'var(--text-2)' }}>
          Genera primero el plan semanal para obtener tu lista optimizada de ingredientes
        </p>
        <button onClick={onGenerateShopping} disabled={!onGenerateShopping || loading}
          className="h-12 px-8 rounded-xl font-bold text-[14px] text-white flex items-center justify-center gap-2 active:scale-[0.97] transition-transform disabled:opacity-60"
          style={{ background: 'var(--cta)', boxShadow: '0 4px 16px var(--cta-shadow)' }}>
          {loading ? <Spinner size={18} color="#fff" /> : 'Generar lista semanal'}
        </button>
      </div>
    )
  }

  const categories = Object.entries(shoppingData.items_by_category ?? {})

  return (
    <div className="px-5 pb-6 space-y-4">
      {/* Total — gradient hero card */}
      <div className="relative overflow-hidden rounded-2xl p-5"
        style={{ background: 'linear-gradient(135deg, var(--accent-soft) 0%, var(--cta-soft) 100%)', border: '1px solid var(--border)' }}>
        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none" style={{ opacity: 0.07 }}>
          <ShoppingCart size={64} style={{ color: 'var(--accent)' }} />
        </div>
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-1" style={{ color: 'var(--text-3)' }}>
          Total estimado · 7 días
        </p>
        <p className="font-bold tabular-nums leading-none"
          style={{ fontSize: '36px', color: 'var(--accent)', fontFamily: '"Playfair Display",serif' }}>
          {shoppingData.total_cost_eur?.toFixed(2)}€
        </p>
        <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-3)' }}>
          Dieta personalizada con IA · precios orientativos
        </p>
      </div>

      {/* Categories */}
      {categories.map(([cat, items]) => (
        <div key={cat} className="card overflow-hidden">
          {/* Accent bar header */}
          <div className="px-4 py-2.5 flex items-center gap-2"
            style={{ background: 'var(--bg-surface2)', borderBottom: '1px solid var(--border)' }}>
            <div className="w-0.5 h-3.5 rounded-full" style={{ background: 'var(--accent)' }} />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em] capitalize"
              style={{ color: 'var(--text-3)' }}>{cat}</span>
          </div>
          {items.map((item, i) => (
            <div key={item.product_name}
              className="flex items-center px-4 py-3 gap-3 text-[13px]"
              style={{ borderBottom: i < items.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <span className="flex-1 font-medium" style={{ color: 'var(--text-1)' }}>{item.product_name}</span>
              <span className="tabular-nums" style={{ color: 'var(--text-3)' }}>{Math.round(item.total_grams_needed)}g</span>
              <span className="font-bold tabular-nums"
                style={{ color: item.cost_is_estimated ? 'var(--text-2)' : 'var(--text-1)' }}>
                {item.total_cost_eur?.toFixed(2)}€
                {item.cost_is_estimated && <span className="text-[10px] ml-0.5 font-normal">~</span>}
              </span>
            </div>
          ))}
        </div>
      ))}

      <p className="text-[10px] text-center leading-relaxed" style={{ color: 'var(--text-3)' }}>
        * Precios orientativos obtenidos de fuentes públicas. Pueden variar.
        Consulta el precio exacto en la web del supermercado.
      </p>
    </div>
  )
}

// ── Main tab ───────────────────────────────────────────────────────────────
export default function TabPlan({ theme, toggleTheme, profileState, authState }) {
  const { buildPayload } = profileState
  const [view, setView] = useState('generate')
  const [shoppingData, setShoppingData] = useState(null)

  const { diet, weekPlan, loading, error, generateToday, generateWeek, generateFridge, generateShopping, swapMeal, setDiet, clearError } = useDiet()

  async function handleGenerate() {
    clearError()
    try { const d = await generateToday(buildPayload()); if (d) setView('results') } catch {}
  }
  async function handleGenerateWeek() {
    clearError()
    try { const w = await generateWeek(buildPayload()); if (w) setView('week') } catch {}
  }
  async function handleGenerateFridge(payload) {
    clearError()
    try { const d = await generateFridge(payload); if (d) setView('results') } catch {}
  }
  async function handleGenerateShopping() {
    if (!weekPlan) return
    const data = await generateShopping(weekPlan)
    if (data) setShoppingData(data)
  }

  async function handleSwapMeal(dietId, mealName) {
    const newMeal = await swapMeal(dietId, mealName, buildPayload())
    if (newMeal) {
      setDiet(prev => ({
        ...prev,
        meals: prev.meals.map(m => m.name === mealName ? newMeal : m),
      }))
    }
  }

  const VIEWS = [
    { id: 'generate', label: 'Configurar' },
    { id: 'results',  label: 'Mi Dieta'   },
    { id: 'week',     label: 'Semana'     },
    { id: 'shopping', label: 'Compra'     },
  ]

  const anyLoading = loading.today || loading.week || loading.fridge
  // Regenerating while a result is already shown → use skeleton instead of full spinner
  const showResultSkeleton = loading.today && !!diet && view === 'results'
  const showFullSpinner = anyLoading && !showResultSkeleton

  return (
    <div className="tab-enter">
      <AppHeader title="Tu Plan" subtitle="Dieta personalizada con IA" theme={theme} onToggleTheme={toggleTheme} />

      {/* View switcher */}
      <div className="px-5 mb-4">
        <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--bg-surface2)' }}>
          {VIEWS.map(v => {
            const active = view === v.id
            const hasContent =
              (v.id === 'results' && !!diet) ||
              (v.id === 'week' && !!weekPlan) ||
              (v.id === 'shopping' && !!shoppingData)
            return (
              <button key={v.id}
                onClick={() => setView(v.id)}
                className="flex-1 py-2 rounded-lg text-[12px] font-semibold transition-all relative"
                style={{
                  background: active ? 'var(--bg-surface)' : 'transparent',
                  color: active ? 'var(--text-1)' : 'var(--text-2)',
                  boxShadow: active ? 'var(--shadow-sm)' : 'none',
                }}>
                {v.label}
                {hasContent && !active && (
                  <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full"
                    style={{ background: 'var(--cta)', display: 'block' }} />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Full-page spinner (first generation / week / fridge) */}
      {showFullSpinner && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="relative">
            <Spinner size={36} />
            <div className="absolute inset-0 rounded-full pulse-ring pointer-events-none"
              style={{ border: '2px solid var(--cta)', opacity: 0.25 }} />
          </div>
          <p className="text-[17px] font-bold tracking-[-0.01em]"
            style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
            {loading.week ? 'Creando tu semana perfecta…' : loading.fridge ? 'Cocinando con tu nevera…' : 'Diseñando tu dieta ideal…'}
          </p>
          <p className="text-[12px]" style={{ color: 'var(--text-3)' }}>La IA está optimizando tu menú</p>
        </div>
      )}

      {/* Skeleton while regenerating existing diet */}
      {showResultSkeleton && <DietPageSkeleton />}

      {/* Views */}
      {!anyLoading && view === 'generate' && (
        <PlanGenerateView
          profileState={profileState}
          onGenerate={handleGenerate}
          onGenerateWeek={handleGenerateWeek}
          onGenerateFridge={handleGenerateFridge}
          loading={loading}
          error={error}
        />
      )}

      {!anyLoading && view === 'results' && (
        diet ? <PlanResultsView diet={diet} onSwap={handleSwapMeal} /> : (
          <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
            <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 relative overflow-hidden"
              style={{ background: 'linear-gradient(135deg, var(--cta-soft) 0%, #ffe8e0 100%)', border: '1px solid var(--border)' }}>
              <Zap size={32} style={{ color: 'var(--cta)' }} />
            </div>
            <p className="text-[20px] font-bold mb-2 tracking-[-0.01em]"
              style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
              Sin dieta generada
            </p>
            <p className="text-[13px] mb-6 leading-relaxed" style={{ color: 'var(--text-2)' }}>
              Configura tu perfil y genera tu primera dieta personalizada con IA
            </p>
            <button onClick={() => setView('generate')}
              className="h-12 px-8 rounded-xl font-bold text-[14px] text-white active:scale-[0.97] transition-transform"
              style={{ background: 'var(--cta)', boxShadow: '0 4px 16px var(--cta-shadow)' }}>
              Configurar y generar
            </button>
          </div>
        )
      )}

      {!anyLoading && view === 'week' && (
        weekPlan ? (
          <PlanWeekView weekPlan={weekPlan} onGenerateWeek={handleGenerateWeek} loading={loading.week} />
        ) : (
          <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
            <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 relative overflow-hidden"
              style={{ background: 'linear-gradient(135deg, var(--accent-soft) 0%, #d4f0e0 100%)', border: '1px solid var(--border)' }}>
              <Calendar size={32} style={{ color: 'var(--accent)' }} />
            </div>
            <p className="text-[20px] font-bold mb-2 tracking-[-0.01em]"
              style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
              Plan semanal
            </p>
            <p className="text-[13px] mb-6 leading-relaxed" style={{ color: 'var(--text-2)' }}>
              Genera tu menú de 7 días personalizado con IA y precios reales
            </p>
            <button onClick={handleGenerateWeek} disabled={loading.week}
              className="h-12 px-8 rounded-xl font-bold text-[14px] text-white active:scale-[0.97] transition-transform disabled:opacity-60"
              style={{ background: 'var(--accent)', boxShadow: '0 4px 16px rgba(74,124,89,0.25)' }}>
              {loading.week ? <Spinner size={18} color="#fff" /> : 'Generar plan semanal'}
            </button>
          </div>
        )
      )}

      {!anyLoading && view === 'shopping' && (
        <PlanShoppingView
          shoppingData={shoppingData}
          onGenerateShopping={handleGenerateShopping}
          loading={loading.shopping}
        />
      )}
    </div>
  )
}
