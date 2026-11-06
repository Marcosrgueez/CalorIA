export default function Spinner({ size = 20, color = 'var(--cta)' }) {
  return (
    <div
      className="rounded-full border-2 border-transparent animate-spin flex-shrink-0"
      style={{
        width: size,
        height: size,
        borderTopColor: color,
        borderRightColor: color + '33',
        borderBottomColor: 'transparent',
        borderLeftColor: 'transparent',
      }}
    />
  )
}
