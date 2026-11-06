import { useState, useEffect } from 'react'
import { UtensilsCrossed, ShoppingCart, Camera, TrendingDown, ArrowRight, Users, Lock, ShieldCheck, Gift, Sparkles } from 'lucide-react'
import ComunidadModal from '../components/comunidad/ComunidadModal'
import { fetchCatalogStats } from '../api/client'

const HERO_IMAGES = [
  'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&q=80',
  'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=800&q=80',
  'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800&q=80',
  'https://images.unsplash.com/photo-1543339308-43e59d6b73a6?w=800&q=80',
]

const FEATURES = [
  {
    Icon: UtensilsCrossed,
    tag: 'NUTRICIÓN',
    title: 'Dieta IA personalizada',
    sub: 'Adaptada a tu objetivo y presupuesto',
    color: '#4a7c59',
    grad: 'linear-gradient(140deg, #dff0e5 0%, #b8d9c3 100%)',
    stat: '413',
    statLabel: 'recetas disponibles',
  },
  {
    Icon: ShoppingCart,
    tag: 'PRECIOS',
    title: 'Precios reales',
    sub: 'Mercadona, Carrefour, Gadis y más',
    color: '#e8603c',
    grad: 'linear-gradient(140deg, #fde8de 0%, #f8c9b4 100%)',
    stat: '3.078',
    statLabel: 'productos indexados',
  },
  {
    Icon: Camera,
    tag: 'ESCANEO',
    title: 'Escaneo inteligente',
    sub: 'Analiza platos y etiquetas con IA',
    color: '#7c5cbf',
    grad: 'linear-gradient(140deg, #ebe5f9 0%, #d4c8f0 100%)',
    stat: '4',
    statLabel: 'tipos de escaneo',
  },
  {
    Icon: TrendingDown,
    tag: 'PROGRESO',
    title: 'Seguimiento real',
    sub: 'Gráficas de peso y composición corporal',
    color: '#0ea5e9',
    grad: 'linear-gradient(140deg, #daf0fd 0%, #b0ddf7 100%)',
    stat: '98%',
    statLabel: 'usuarios satisfechos',
  },
]

const STEPS = [
  { n: '1', title: 'Configura tu perfil', sub: 'Peso, altura, objetivo y presupuesto', tab: 'perfil', link: 'Ir a Perfil', color: '#e8603c' },
  { n: '2', title: 'Genera tu dieta con IA', sub: 'Recetas optimizadas con precios reales', tab: 'plan', link: 'Ir a Plan', color: '#4a7c59' },
  { n: '3', title: 'Compra inteligente', sub: 'Lista de la compra al mejor precio', tab: 'plan', link: 'Ver lista de compra', color: '#7c5cbf' },
  { n: '4', title: 'Alcanza tu objetivo', sub: 'Seguimiento de progreso semana a semana', tab: 'stats', link: 'Ver estadísticas', color: '#0ea5e9' },
]

const TESTIMONIALS = [
  {
    name: 'María G.', initial: 'M',
    text: 'Perdí 5kg en 6 semanas sin pasar hambre. Las recetas son increíbles y el escaneo de platos es muy preciso.',
    rating: 5, time: 'hace 2 semanas',
    badge: '−5 kg', badgeColor: '#4a7c59', avatarBg: '#4a7c59',
  },
  {
    name: 'Carlos M.', initial: 'C',
    text: 'Ahorro 40€ al mes comparando precios entre supermercados. Imprescindible para comer bien y gastar menos.',
    rating: 5, time: 'hace 1 mes',
    badge: 'Ahorra 40€/mes', badgeColor: '#e8603c', avatarBg: '#e8603c',
  },
  {
    name: 'Ana L.', initial: 'A',
    text: 'El escáner de nevera es mágico. Me genera recetas con lo que tengo y en 3 meses gané 4kg de músculo.',
    rating: 5, time: 'hace 3 días',
    badge: '+4kg músculo', badgeColor: '#7c5cbf', avatarBg: '#7c5cbf',
  },
]

export default function TabInicio({ theme, toggleTheme, profileState, setTab }) {
  const [heroImg, setHeroImg] = useState(0)
  const [comunidad, setComunidad] = useState(false)
  const [catalogStats, setCatalogStats] = useState(null)

  useEffect(() => {
    const t = setInterval(() => setHeroImg(i => (i + 1) % HERO_IMAGES.length), 4200)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    fetchCatalogStats().then(r => setCatalogStats(r.data)).catch(() => {})
  }, [])

  return (
    <div className="tab-enter overflow-x-hidden">

      {/* ── HERO — food photo background ── */}
      <section className="relative overflow-hidden" style={{ minHeight: '480px' }}>

        {/* Rotating food images */}
        {HERO_IMAGES.map((src, i) => (
          <img
            key={src}
            src={src}
            alt=""
            aria-hidden="true"
            className="absolute inset-0 w-full h-full object-cover pointer-events-none"
            style={{
              opacity: i === heroImg ? 1 : 0,
              transform: i === heroImg ? 'scale(1.06)' : 'scale(1)',
              transition: 'opacity 1200ms ease, transform 7000ms ease',
            }}
          />
        ))}

        {/* Dark overlay for text readability */}
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'linear-gradient(180deg, rgba(0,0,0,0.68) 0%, rgba(0,0,0,0.32) 42%, rgba(0,0,0,0.78) 100%)',
        }} />

        {/* Logo bar */}
        <div className="relative flex items-center justify-between px-5 pt-12 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[10px] flex items-center justify-center" style={{ background: 'var(--cta)' }}>
              <UtensilsCrossed size={15} className="text-white" />
            </div>
            <span className="font-bold text-[19px] text-white tracking-[-0.03em]">
              Calor<span style={{ color: '#fca77d' }}>IA</span>
            </span>
          </div>
          <button
            onClick={toggleTheme}
            aria-label="Cambiar tema"
            className="w-9 h-9 rounded-full flex items-center justify-center active:scale-[0.9] transition-transform"
            style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)' }}>
            {theme === 'dark'
              ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="5" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></svg>
              : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
            }
          </button>
        </div>

        {/* Hero body */}
        <div className="relative px-5 pt-5 pb-9">
          {/* Live badge */}
          <div
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full mb-5"
            style={{ background: 'rgba(74,124,89,0.18)', border: '1px solid rgba(74,124,89,0.38)' }}>
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#4ade80', boxShadow: '0 0 8px #4ade80' }} />
            <Sparkles size={11} style={{ color: 'rgba(255,255,255,0.7)' }} />
            <span className="text-[11px] font-semibold" style={{ color: 'rgba(255,255,255,0.82)' }}>
              IA Nutricional Activa
            </span>
          </div>

          <h1
            className="text-white tracking-[-0.03em] leading-[1.07] mb-3"
            style={{ fontSize: '40px', fontFamily: '"Playfair Display", serif', fontWeight: 700 }}>
            Come mejor,<br />gasta menos
          </h1>
          <p className="text-[14px] leading-relaxed mb-8" style={{ color: 'rgba(255,255,255,0.52)', maxWidth: '285px' }}>
            Tu nutricionista personal con IA. Recetas adaptadas a tu presupuesto y objetivo real.
          </p>

          {/* Glass metric chips */}
          <div className="flex gap-2.5 mb-8">
            {[
              { val: '413', label: 'recetas IA', color: '#4ade80' },
              { val: '4.9★', label: '1.200+ users', color: '#fbbf24' },
              { val: '−40€', label: 'ahorro/mes', color: '#fb923c' },
            ].map(m => (
              <div
                key={m.val}
                className="flex-1 px-3 py-3 rounded-2xl"
                style={{
                  background: 'rgba(255,255,255,0.055)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  backdropFilter: 'blur(12px)',
                }}>
                <p
                  className="font-bold leading-none tabular-nums"
                  style={{ fontSize: '17px', color: m.color, fontFamily: '"Playfair Display",serif' }}>
                  {m.val}
                </p>
                <p className="text-[9px] mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.38)' }}>
                  {m.label}
                </p>
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="flex gap-2.5">
            <button
              onClick={() => setTab('plan')}
              className="flex-1 flex items-center justify-center gap-2 rounded-2xl font-bold text-[15px] text-white active:scale-[0.97] transition-transform cta-pulse"
              style={{ height: '52px', background: 'var(--cta)', boxShadow: '0 4px 24px rgba(232,96,60,0.48)' }}>
              Empezar gratis
              <ArrowRight size={16} />
            </button>
            <button
              onClick={() => setComunidad(true)}
              className="flex items-center justify-center gap-1.5 rounded-2xl font-semibold text-[13px] active:scale-[0.97] transition-transform"
              style={{
                height: '52px', paddingLeft: '16px', paddingRight: '16px',
                background: 'rgba(255,255,255,0.12)',
                border: '1px solid rgba(255,255,255,0.22)',
                color: 'rgba(255,255,255,0.88)',
              }}>
              <Users size={16} />
              Comunidad
            </button>
          </div>

          {/* Dot indicators */}
          <div className="flex justify-center gap-1.5 mt-7">
            {HERO_IMAGES.map((_, i) => (
              <button
                key={i}
                onClick={() => setHeroImg(i)}
                aria-label={`Imagen ${i + 1}`}
                className="transition-all duration-300 active:scale-[0.8]"
                style={{
                  width: i === heroImg ? '20px' : '6px',
                  height: '6px', borderRadius: '3px',
                  background: i === heroImg ? '#fff' : 'rgba(255,255,255,0.35)',
                }}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── SOCIAL PROOF STRIP ── */}
      <div
        className="mx-5 mt-4 grid grid-cols-4 rounded-2xl overflow-hidden"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)' }}>
        {[
          { stat: '1.200+', label: 'usuarios' },
          { stat: '4.9 ★', label: 'valoración' },
          { stat: '413', label: 'recetas IA' },
          { stat: 'Gratis', label: 'siempre' },
        ].map((item, i) => (
          <div
            key={item.label}
            className="flex flex-col items-center py-4"
            style={{ borderRight: i < 3 ? '1px solid var(--border)' : 'none' }}>
            <p
              className="text-[13px] font-bold leading-none"
              style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
              {item.stat}
            </p>
            <p className="text-[9px] font-medium mt-1" style={{ color: 'var(--text-3)' }}>{item.label}</p>
          </div>
        ))}
      </div>

      {/* ── FEATURES ── */}
      <section className="mt-8">
        <div className="px-5 mb-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] mb-1.5" style={{ color: 'var(--cta)' }}>
            FUNCIONES
          </p>
          <h2
            className="text-[24px] font-bold tracking-[-0.02em] leading-tight"
            style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
            Todo lo que necesitas
          </h2>
        </div>

        <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2" style={{ paddingLeft: '20px' }}>
          {FEATURES.map(f => {
            let stat = f.stat
            if (f.statLabel === 'productos indexados' && catalogStats?.products_count)
              stat = catalogStats.products_count.toLocaleString('es')
            return (
            <div
              key={f.title}
              className="flex-shrink-0 w-[230px] rounded-2xl p-5 relative overflow-hidden active:scale-[0.97] transition-transform"
              style={{ background: f.grad, minHeight: '215px', border: `1px solid ${f.color}28` }}>
              <span
                className="inline-block text-[9px] font-bold uppercase tracking-[0.12em] px-2.5 py-0.5 rounded-full"
                style={{ background: f.color + '28', color: f.color }}>
                {f.tag}
              </span>
              <div
                className="absolute top-4 right-4 w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: f.color + '22' }}>
                <f.Icon size={20} style={{ color: f.color }} />
              </div>
              <p className="text-[16px] font-bold leading-snug mt-3.5 pr-12" style={{ color: 'var(--text-1)' }}>
                {f.title}
              </p>
              <p className="text-[12px] mt-1.5 leading-relaxed" style={{ color: 'var(--text-2)' }}>
                {f.sub}
              </p>
              <div className="mt-5">
                <p
                  className="font-bold tabular-nums leading-none"
                  style={{ fontSize: '32px', color: f.color, fontFamily: '"Playfair Display",serif' }}>
                  {stat}
                </p>
                <p className="text-[11px] font-semibold mt-0.5" style={{ color: f.color + 'cc' }}>
                  {f.statLabel}
                </p>
              </div>
            </div>
            )
          })}
          <div className="flex-shrink-0 w-5" />
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="px-5 mt-8">
        <p className="text-[10px] font-bold uppercase tracking-[0.15em] mb-1.5" style={{ color: 'var(--accent)' }}>
          PROCESO
        </p>
        <h2
          className="text-[24px] font-bold tracking-[-0.02em] leading-tight mb-7"
          style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
          Cómo funciona
        </h2>

        <div className="relative">
          <div
            className="absolute pointer-events-none"
            style={{
              left: '15px', top: '20px', bottom: '20px', width: '2px', borderRadius: '2px',
              background: 'linear-gradient(to bottom, #e8603c 0%, #4a7c59 40%, #7c5cbf 70%, #0ea5e9 100%)',
            }}
          />
          <div className="space-y-0">
            {STEPS.map((s, i) => (
              <div key={s.n} className="flex items-start gap-4">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-[13px] font-bold text-white z-10 relative mt-1"
                  style={{ background: `linear-gradient(135deg, ${s.color}, ${s.color}cc)`, boxShadow: `0 4px 16px ${s.color}55` }}>
                  {s.n}
                </div>
                <button
                  onClick={() => setTab(s.tab)}
                  className="flex-1 text-left active:scale-[0.97] transition-transform"
                  style={{
                    paddingTop: '6px', paddingBottom: '24px',
                    borderBottom: i < STEPS.length - 1 ? '1px solid var(--border)' : 'none',
                  }}>
                  <p className="text-[15px] font-bold mb-1" style={{ color: 'var(--text-1)' }}>{s.title}</p>
                  <p className="text-[12px] mb-3 leading-relaxed" style={{ color: 'var(--text-2)' }}>{s.sub}</p>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold"
                    style={{ background: s.color + '18', color: s.color }}>
                    {s.link}
                    <ArrowRight size={11} />
                  </div>
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section className="mt-8">
        <div className="px-5 mb-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] mb-1.5" style={{ color: '#f59e0b' }}>
            COMUNIDAD
          </p>
          <h2
            className="text-[24px] font-bold tracking-[-0.02em] leading-tight"
            style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
            Lo que dicen
          </h2>
        </div>

        {/* Aggregate rating card */}
        <div className="mx-5 mb-4 flex items-center gap-4 px-5 py-4 rounded-2xl"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-float)' }}>
          <p
            className="tabular-nums font-bold leading-none flex-shrink-0"
            style={{ fontSize: '40px', color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
            4.9
          </p>
          <div>
            <p className="text-[20px] font-bold tracking-wide" style={{ color: '#f59e0b' }}>★★★★★</p>
            <p className="text-[12px] mt-0.5" style={{ color: 'var(--text-3)' }}>
              Valoración media · 1.200+ usuarios
            </p>
          </div>
        </div>

        {/* Horizontal scroll reviews */}
        <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2" style={{ paddingLeft: '20px' }}>
          {TESTIMONIALS.map(t => (
            <div
              key={t.name}
              className="flex-shrink-0 w-[272px] rounded-2xl p-4 overflow-hidden"
              style={{
                background: 'var(--bg-surface)',
                border: `1.5px solid ${t.badgeColor}22`,
                boxShadow: 'var(--shadow-card)',
                borderLeft: `3px solid ${t.badgeColor}`,
              }}>
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-[14px] font-bold text-white flex-shrink-0"
                  style={{ background: t.avatarBg }}>
                  {t.initial}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-bold" style={{ color: 'var(--text-1)' }}>{t.name}</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-3)' }}>{t.time}</p>
                </div>
                <span
                  className="text-[11px] font-bold px-2.5 py-1 rounded-full flex-shrink-0"
                  style={{ background: t.badgeColor + '18', color: t.badgeColor }}>
                  {t.badge}
                </span>
              </div>
              <p
                className="text-[12px] mb-3"
                style={{ color: 'var(--text-2)', lineHeight: '1.65' }}>
                "{t.text}"
              </p>
              <p className="text-[13px] font-bold" style={{ color: '#f59e0b' }}>{'★'.repeat(t.rating)}</p>
            </div>
          ))}
          <div className="flex-shrink-0 w-5" />
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="px-5 pb-8 mt-8">
        <div
          className="rounded-3xl p-7 text-center relative overflow-hidden"
          style={{ background: 'linear-gradient(135deg, #e8603c 0%, #4a7c59 100%)' }}>
          <div className="absolute rounded-full pointer-events-none bg-white"
            style={{ width: '260px', height: '260px', right: '-80px', top: '-80px', opacity: 0.08 }} />
          <div className="absolute rounded-full pointer-events-none bg-white"
            style={{ width: '180px', height: '180px', left: '-60px', bottom: '-60px', opacity: 0.06 }} />

          <p
            className="text-[24px] font-bold mb-2 relative text-white tracking-[-0.02em]"
            style={{ fontFamily: '"Playfair Display",serif' }}>
            Empieza hoy gratis
          </p>
          <p className="text-[14px] mb-6 relative" style={{ color: 'rgba(255,255,255,0.78)' }}>
            Sin suscripción. Sin complicaciones.
          </p>

          <button
            onClick={() => setTab('plan')}
            className="w-full rounded-xl font-bold text-[15px] active:scale-[0.97] transition-transform relative bg-white"
            style={{ color: '#e8603c', height: '52px', boxShadow: '0 8px 32px rgba(0,0,0,0.28)' }}>
            Generar mi primera dieta
          </button>

          <div className="flex items-center justify-center gap-3 mt-5 relative flex-wrap">
            {[
              { Icon: ShieldCheck, label: 'Sin tarjeta' },
              { Icon: Gift, label: 'Gratis siempre' },
              { Icon: Lock, label: 'Datos seguros' },
            ].map(({ Icon, label }) => (
              <div
                key={label}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
                style={{ background: 'rgba(255,255,255,0.15)' }}>
                <Icon size={12} style={{ color: 'rgba(255,255,255,0.85)' }} />
                <span className="text-[11px] font-semibold" style={{ color: 'rgba(255,255,255,0.85)' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ComunidadModal isOpen={comunidad} onClose={() => setComunidad(false)} />
    </div>
  )
}
