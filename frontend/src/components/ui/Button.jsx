export default function Button({
  children, onClick, variant = 'primary', size = 'md',
  disabled, fullWidth, className = '', style = {},
}) {
  const base = 'inline-flex items-center justify-center gap-2 font-semibold rounded-xl active:scale-[0.97] transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none'

  const sizes = {
    sm: 'h-9 px-4 text-[13px]',
    md: 'h-12 px-5 text-[14px]',
    lg: 'h-14 px-6 text-[15px]',
  }

  const variants = {
    primary: {
      background: 'var(--cta)',
      color: '#fff',
      boxShadow: '0 4px 16px var(--cta-shadow)',
    },
    secondary: {
      background: 'var(--bg-surface2)',
      color: 'var(--text-1)',
      border: '1px solid var(--border)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--text-2)',
      border: '1px solid var(--border)',
    },
    accent: {
      background: 'var(--accent)',
      color: '#fff',
    },
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
      style={{ ...variants[variant], ...style }}
    >
      {children}
    </button>
  )
}
