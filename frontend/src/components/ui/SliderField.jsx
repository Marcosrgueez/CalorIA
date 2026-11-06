export default function SliderField({ label, id, value, min, max, step = 1, unit = '', onChange }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label htmlFor={id} className="text-[13px] font-medium" style={{ color: 'var(--text-2)' }}>
          {label}
        </label>
        <span className="text-[14px] font-bold tabular-nums" style={{ color: 'var(--text-1)' }}>
          {value}{unit}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{ accentColor: 'var(--cta)', background: `linear-gradient(to right, var(--cta) 0%, var(--cta) ${((value - min) / (max - min)) * 100}%, var(--border-strong) ${((value - min) / (max - min)) * 100}%, var(--border-strong) 100%)` }}
      />
    </div>
  )
}
