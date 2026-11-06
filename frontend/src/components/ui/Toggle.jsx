export default function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      {label && (
        <span className="text-[13px] font-medium flex-1" style={{ color: 'var(--text-2)' }}>
          {label}
        </span>
      )}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className="relative w-11 h-6 rounded-full flex-shrink-0 transition-colors duration-200"
        style={{ background: checked ? 'var(--cta)' : 'var(--border-strong)' }}
      >
        <span
          className="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
          style={{ left: checked ? '22px' : '2px' }}
        />
      </button>
    </label>
  )
}
