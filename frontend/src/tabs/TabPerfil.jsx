import { useState } from 'react'
import { User, Sun, Moon, Trash2, ChevronRight, LogOut, LogIn, Crown, Info, Scale } from 'lucide-react'
import AppHeader from '../components/layout/AppHeader'
import AuthModal from '../components/auth/AuthModal'
import PricingModal from '../components/auth/PricingModal'
import LegalModal from '../components/legal/LegalModal'
import { ACTIVITY_LEVELS, GOALS } from '../utils/tdee'

const ACTIVITY_LABEL = {
  sedentary:  'Sedentario',
  light:      'Ligero',
  moderate:   'Moderado',
  active:     'Activo',
  very_active:'Muy activo',
}

export default function TabPerfil({ theme, toggleTheme, profileState, authState }) {
  const { profile, updateProfile, resetProfile, kcal, macros, goalLabel } = profileState
  const { auth, isPremium, logout } = authState
  const [showAuth, setShowAuth] = useState(false)
  const [showPricing, setShowPricing] = useState(false)
  const [showLegal, setShowLegal] = useState(null)
  const [confirmReset, setConfirmReset] = useState(false)

  const goalColor = profile.goal === 'cut' ? '#0ea5e9' : profile.goal === 'bulk' ? '#4a7c59' : '#7c5cbf'

  return (
    <div className="tab-enter pb-6">
      <AppHeader title="Perfil" subtitle="Tu cuenta y ajustes" theme={theme} onToggleTheme={toggleTheme} />

      <div className="px-4 space-y-4">

        {/* Profile hero */}
        <div className="card p-5 relative overflow-hidden"
          style={{ background: 'linear-gradient(135deg, var(--bg-surface) 0%, var(--cta-soft) 100%)' }}>
          {/* Dot pattern */}
          <div className="absolute inset-0 pointer-events-none"
            style={{
              backgroundImage: 'radial-gradient(circle, var(--border-strong) 1px, transparent 1px)',
              backgroundSize: '18px 18px',
              opacity: 0.5,
            }} />
          <div className="flex items-center gap-4 relative">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-[24px] font-bold text-white flex-shrink-0"
              style={{ background: `linear-gradient(135deg, var(--cta), var(--accent))` }}>
              {profile.name ? profile.name[0].toUpperCase() : <User size={28} />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[18px] font-bold truncate" style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
                {profile.name || 'Usuario'}
              </p>
              {auth?.email && (
                <p className="text-[12px] truncate mt-0.5" style={{ color: 'var(--text-3)' }}>{auth.username}</p>
              )}
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                  style={{ background: isPremium ? '#fef3ef' : 'var(--bg-surface2)', color: isPremium ? 'var(--cta)' : 'var(--text-3)' }}>
                  {isPremium ? '✦ Premium' : 'Gratis'}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                  style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                  {goalLabel}
                </span>
              </div>
            </div>
          </div>

          {/* Macro summary */}
          <div className="relative grid grid-cols-4 gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
            {[
              { label: 'Kcal', value: kcal?.toLocaleString('es'), color: 'var(--cta)' },
              { label: 'Prot', value: `${macros?.prot}g`, color: '#4a7c59' },
              { label: 'Grasa', value: `${macros?.fat}g`, color: '#f59e0b' },
              { label: 'Carbs', value: `${macros?.carbsMin}g`, color: '#e8603c' },
            ].map(m => (
              <div key={m.label} className="text-center">
                <p className="text-[15px] font-bold tabular-nums" style={{ color: m.color }}>{m.value}</p>
                <p className="text-[10px] font-medium mt-0.5" style={{ color: 'var(--text-3)' }}>{m.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Body stats */}
        <div className="card p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-3" style={{ color: 'var(--text-3)' }}>Datos corporales</p>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Edad', value: profile.age, unit: 'años', key: 'age', min: 16, max: 80 },
              { label: 'Peso', value: profile.weight, unit: 'kg', key: 'weight', min: 40, max: 200, step: 0.5 },
              { label: 'Altura', value: profile.height, unit: 'cm', key: 'height', min: 140, max: 220 },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-[10px] font-medium mb-1" style={{ color: 'var(--text-3)' }}>{f.label}</label>
                <div className="flex items-baseline gap-1">
                  <input
                    type="number"
                    value={f.value}
                    min={f.min}
                    max={f.max}
                    step={f.step || 1}
                    onChange={e => updateProfile(f.key, parseFloat(e.target.value) || f.value)}
                    className="w-full rounded-xl px-2.5 py-2 text-[14px] font-bold outline-none text-center"
                    style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}
                  />
                </div>
                <p className="text-center text-[10px] mt-0.5" style={{ color: 'var(--text-3)' }}>{f.unit}</p>
              </div>
            ))}
          </div>

          {/* Sex + Activity */}
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <p className="text-[10px] font-medium mb-1.5" style={{ color: 'var(--text-3)' }}>Sexo</p>
              <div className="flex gap-1.5">
                {[{ v: 'm', l: 'Hombre' }, { v: 'f', l: 'Mujer' }].map(s => (
                  <button key={s.v} onClick={() => updateProfile('sex', s.v)}
                    className="flex-1 py-2 rounded-xl text-[12px] font-semibold active:scale-[0.96] transition-transform"
                    style={{
                      background: profile.sex === s.v ? 'var(--cta)' : 'var(--bg-surface2)',
                      color: profile.sex === s.v ? '#fff' : 'var(--text-2)',
                    }}>
                    {s.l}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-medium mb-1.5" style={{ color: 'var(--text-3)' }}>Objetivo</p>
              <div className="flex gap-1">
                {[{ v: 'cut', l: '↓ Perder' }, { v: 'maintain', l: '= Mant.' }, { v: 'bulk', l: '↑ Ganar' }].map(g => (
                  <button key={g.v} onClick={() => updateProfile('goal', g.v)}
                    className="flex-1 py-2 rounded-xl text-[10px] font-semibold active:scale-[0.96] transition-transform"
                    style={{
                      background: profile.goal === g.v ? goalColor : 'var(--bg-surface2)',
                      color: profile.goal === g.v ? '#fff' : 'var(--text-2)',
                    }}>
                    {g.l}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-3">
            <p className="text-[10px] font-medium mb-1.5" style={{ color: 'var(--text-3)' }}>Actividad física</p>
            <div className="flex gap-1.5 flex-wrap">
              {Object.entries(ACTIVITY_LABEL).map(([v, l]) => (
                <button key={v} onClick={() => updateProfile('activity', v)}
                  className="px-3 py-1.5 rounded-full text-[11px] font-semibold active:scale-[0.95] transition-transform"
                  style={{
                    background: profile.activity === v ? 'var(--accent)' : 'var(--bg-surface2)',
                    color: profile.activity === v ? '#fff' : 'var(--text-2)',
                  }}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Settings */}
        <div className="card overflow-hidden">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] px-4 pt-4 pb-2" style={{ color: 'var(--text-3)' }}>Ajustes</p>

          {[
            {
              Icon: theme === 'dark' ? Sun : Moon,
              label: theme === 'dark' ? 'Modo claro' : 'Modo oscuro',
              sub: 'Cambia la apariencia de la app',
              action: toggleTheme,
              color: '#f59e0b',
            },
            {
              Icon: Crown,
              label: isPremium ? 'Plan Premium activo' : 'Actualizar a Premium',
              sub: isPremium ? 'Dietas ilimitadas y funciones avanzadas' : 'Desbloquea todas las funciones',
              action: () => setShowPricing(true),
              color: '#e8603c',
            },
            {
              Icon: Scale,
              label: 'Información legal',
              sub: 'Términos, privacidad y aviso legal',
              action: () => setShowLegal('terminos'),
              color: '#6b7280',
            },
          ].map((item, i) => (
            <button key={i} onClick={item.action}
              className="w-full flex items-center gap-3 px-4 py-3.5 active:scale-[0.99] transition-transform"
              style={{ borderTop: i === 0 ? '1px solid var(--border)' : '1px solid var(--border)' }}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: `${item.color}18` }}>
                <item.Icon size={16} style={{ color: item.color }} />
              </div>
              <div className="flex-1 text-left">
                <p className="text-[13px] font-semibold" style={{ color: 'var(--text-1)' }}>{item.label}</p>
                <p className="text-[11px]" style={{ color: 'var(--text-3)' }}>{item.sub}</p>
              </div>
              <ChevronRight size={14} style={{ color: 'var(--text-3)' }} />
            </button>
          ))}
        </div>

        {/* Account */}
        <div className="card overflow-hidden">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] px-4 pt-4 pb-2" style={{ color: 'var(--text-3)' }}>Cuenta</p>

          {auth ? (
            <button onClick={logout}
              className="w-full flex items-center gap-3 px-4 py-3.5 active:scale-[0.99] transition-transform"
              style={{ borderTop: '1px solid var(--border)' }}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: '#f4433618' }}>
                <LogOut size={16} style={{ color: '#f44336' }} />
              </div>
              <div className="flex-1 text-left">
                <p className="text-[13px] font-semibold" style={{ color: '#f44336' }}>Cerrar sesión</p>
                <p className="text-[11px]" style={{ color: 'var(--text-3)' }}>{auth.username}</p>
              </div>
            </button>
          ) : (
            <button onClick={() => setShowAuth(true)}
              className="w-full flex items-center gap-3 px-4 py-3.5 active:scale-[0.99] transition-transform"
              style={{ borderTop: '1px solid var(--border)' }}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: 'var(--accent-soft)' }}>
                <LogIn size={16} style={{ color: 'var(--accent)' }} />
              </div>
              <div className="flex-1 text-left">
                <p className="text-[13px] font-semibold" style={{ color: 'var(--text-1)' }}>Iniciar sesión</p>
                <p className="text-[11px]" style={{ color: 'var(--text-3)' }}>Guarda tu progreso en la nube</p>
              </div>
              <ChevronRight size={14} style={{ color: 'var(--text-3)' }} />
            </button>
          )}

          {/* Danger zone */}
          {!confirmReset ? (
            <button onClick={() => setConfirmReset(true)}
              className="w-full flex items-center gap-3 px-4 py-3.5 active:scale-[0.99] transition-transform"
              style={{ borderTop: '1px solid var(--border)' }}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: '#f4433614' }}>
                <Trash2 size={16} style={{ color: '#f44336' }} />
              </div>
              <div className="flex-1 text-left">
                <p className="text-[13px] font-semibold" style={{ color: 'var(--text-1)' }}>Borrar datos locales</p>
                <p className="text-[11px]" style={{ color: 'var(--text-3)' }}>Restablece el perfil y el historial</p>
              </div>
            </button>
          ) : (
            <div className="px-4 py-3.5 flex items-center gap-3" style={{ borderTop: '1px solid var(--border)', background: '#f4433608' }}>
              <p className="text-[13px] flex-1" style={{ color: 'var(--text-2)' }}>¿Confirmar borrado?</p>
              <button onClick={() => { resetProfile(); setConfirmReset(false) }}
                className="px-3 py-1.5 rounded-xl text-[12px] font-bold text-white active:scale-[0.95] transition-transform"
                style={{ background: '#f44336' }}>
                Borrar
              </button>
              <button onClick={() => setConfirmReset(false)}
                className="px-3 py-1.5 rounded-xl text-[12px] font-semibold active:scale-[0.95] transition-transform"
                style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}>
                Cancelar
              </button>
            </div>
          )}
        </div>

        {/* App info */}
        <div className="text-center pt-2 pb-2">
          <p className="text-[11px]" style={{ color: 'var(--text-3)' }}>CalorIA v1.0 · Tu nutricionista con IA</p>
          <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-3)' }}>Hecho con ♥ para comer mejor y gastar menos</p>
        </div>
      </div>

      <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} authState={authState} />
      <PricingModal isOpen={showPricing} onClose={() => setShowPricing(false)} onOpenAuth={() => { setShowPricing(false); setShowAuth(true) }} />
      {showLegal && <LegalModal onClose={() => setShowLegal(null)} initialTab={showLegal} />}
    </div>
  )
}
