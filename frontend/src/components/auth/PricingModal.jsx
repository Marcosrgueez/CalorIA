import { Check, X } from 'lucide-react'
import Modal from '../ui/Modal'

const FREE_FEATURES = [
  { text: '3 dietas diarias',      ok: true },
  { text: 'Recetas del día',       ok: true },
  { text: 'Escaneo con cámara',    ok: true },
  { text: 'Plan semanal 7 días',   ok: false },
  { text: 'Sin límite de dietas',  ok: false },
  { text: 'Historial completo',    ok: false },
]

const PRO_FEATURES = [
  { text: 'Dietas ilimitadas' },
  { text: 'Plan semanal completo' },
  { text: 'Historial sin límite' },
  { text: 'Comparador de precios' },
  { text: 'Soporte prioritario' },
]

export default function PricingModal({ isOpen, onClose, onOpenAuth }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Planes">
      <div className="p-5 space-y-4">
        {/* Free */}
        <div className="rounded-2xl p-4" style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[15px] font-bold" style={{ color: 'var(--text-1)' }}>Gratuito</p>
            <p className="text-[20px] font-bold" style={{ color: 'var(--text-1)' }}>0€</p>
          </div>
          <div className="space-y-2">
            {FREE_FEATURES.map(f => (
              <div key={f.text} className="flex items-center gap-2.5 text-[13px]"
                style={{ color: f.ok ? 'var(--text-2)' : 'var(--text-3)' }}>
                {f.ok
                  ? <Check size={14} style={{ color: 'var(--accent)' }} />
                  : <X size={14} />}
                <span className={f.ok ? '' : 'line-through'}>{f.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pro */}
        <div
          className="rounded-2xl p-4"
          style={{ background: 'var(--cta-soft)', border: '2px solid var(--cta)', position: 'relative', overflow: 'hidden' }}
        >
          <div
            className="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
            style={{ background: 'var(--cta)' }}
          >
            POPULAR
          </div>
          <div className="flex items-end gap-1 mb-1">
            <p className="text-[24px] font-bold" style={{ color: 'var(--text-1)' }}>4.99€</p>
            <p className="text-[13px] mb-1" style={{ color: 'var(--text-2)' }}>/mes</p>
          </div>
          <p className="text-[15px] font-bold mb-3" style={{ color: 'var(--text-1)' }}>Premium</p>
          <div className="space-y-2 mb-4">
            {PRO_FEATURES.map(f => (
              <div key={f.text} className="flex items-center gap-2.5 text-[13px]" style={{ color: 'var(--text-2)' }}>
                <Check size={14} style={{ color: 'var(--cta)' }} />
                <span>{f.text}</span>
              </div>
            ))}
          </div>
          <button
            onClick={onOpenAuth}
            className="w-full h-11 rounded-xl text-white font-bold text-[14px] active:scale-[0.97] transition-transform"
            style={{ background: 'var(--cta)', boxShadow: '0 4px 16px var(--cta-shadow)' }}
          >
            Empezar Premium
          </button>
        </div>

        <p className="text-[11px] text-center" style={{ color: 'var(--text-3)' }}>
          Cancela cuando quieras. Sin compromisos.
        </p>
      </div>
    </Modal>
  )
}
