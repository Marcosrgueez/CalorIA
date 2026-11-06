import { Home, UtensilsCrossed, Camera, BarChart2, MessageCircle, User } from 'lucide-react'

const TABS = [
  { id: 'inicio',  Icon: Home,            label: 'Inicio' },
  { id: 'plan',    Icon: UtensilsCrossed, label: 'Plan'   },
  { id: 'camara',  Icon: Camera,          label: 'Cámara' },
  { id: 'stats',   Icon: BarChart2,       label: 'Stats'  },
  { id: 'chat',    Icon: MessageCircle,   label: 'Chat'   },
  { id: 'perfil',  Icon: User,            label: 'Perfil' },
]

export default function BottomNav({ active, onChange }) {
  return (
    <nav
      className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] z-50 px-3 pb-3 pt-4"
      style={{ background: 'linear-gradient(to top, var(--bg) 20%, transparent)' }}
    >
      <div
        className="flex items-center justify-around px-1 py-1.5 rounded-2xl"
        style={{
          background: 'var(--nav-glass)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          boxShadow: '0 0 0 1px var(--nav-border)',
          border: '1px solid var(--nav-border)',
        }}
      >
        {TABS.map(({ id, Icon, label }) => {
          const isActive = active === id
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              className="relative flex flex-col items-center gap-[3px] px-2.5 py-2 rounded-xl transition-all duration-150 active:scale-[0.88]"
              style={{
                background: isActive ? 'var(--cta-soft)' : 'transparent',
                minWidth: '48px',
                opacity: isActive ? 1 : 0.45,
              }}
            >
              <Icon
                size={20}
                strokeWidth={isActive ? 2.5 : 1.8}
                style={{ color: isActive ? 'var(--cta)' : 'var(--text-1)' }}
              />
              <span
                className="text-[10px] font-semibold leading-none"
                style={{ color: isActive ? 'var(--cta)' : 'var(--text-1)' }}
              >
                {label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
