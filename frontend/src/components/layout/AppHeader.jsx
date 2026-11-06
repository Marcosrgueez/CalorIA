import { Sun, Moon, Search } from 'lucide-react'

export default function AppHeader({
  greeting = false, userName, title, subtitle,
  theme, onToggleTheme, onSearch, rightAction,
}) {
  const hour = new Date().getHours()
  const greetText = hour < 12 ? 'Buenos días' : hour < 20 ? 'Buenas tardes' : 'Buenas noches'

  return (
    <div className="px-5 pt-11 pb-4" style={{ background: 'var(--bg)' }}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {greeting ? (
            <>
              <p className="text-[12px] font-medium mb-0.5" style={{ color: 'var(--text-3)' }}>
                {greetText} ✦
              </p>
              <h1
                className="text-[24px] font-bold tracking-[-0.03em] leading-tight"
                style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display", serif' }}
              >
                {userName ? `¡Hola, ${userName}!` : '¡Bienvenido!'}
              </h1>
              <p className="text-[14px] mt-1" style={{ color: 'var(--text-2)' }}>
                Tu nutricionista personal
              </p>
            </>
          ) : (
            <>
              <h1
                className="text-[22px] font-bold tracking-[-0.02em]"
                style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display", serif' }}
              >
                {title}
              </h1>
              {subtitle && (
                <p className="text-[13px] mt-0.5" style={{ color: 'var(--text-2)' }}>
                  {subtitle}
                </p>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0 mt-1">
          <button
            onClick={onToggleTheme}
            className="w-9 h-9 rounded-full flex items-center justify-center active:scale-[0.9] transition-transform"
            style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          {onSearch && (
            <button
              onClick={onSearch}
              className="w-9 h-9 rounded-full flex items-center justify-center active:scale-[0.9] transition-transform"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
            >
              <Search size={15} />
            </button>
          )}
          {rightAction}
        </div>
      </div>
    </div>
  )
}
