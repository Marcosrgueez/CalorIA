import { useState } from 'react'
import { UtensilsCrossed, Check } from 'lucide-react'
import LegalModal from './LegalModal'

const CHECKS = [
  {
    key: 'terms',
    label: 'Acepto los ',
    link: 'Términos y Condiciones',
    tab: 'terminos',
  },
  {
    key: 'privacy',
    label: 'Acepto la ',
    link: 'Política de Privacidad',
    tab: 'privacidad',
  },
  {
    key: 'medical',
    label: 'Entiendo que CalorIA no sustituye el consejo de un médico o nutricionista profesional',
    link: null,
    tab: null,
  },
  {
    key: 'age',
    label: 'Confirmo que tengo 16 años o más',
    link: null,
    tab: null,
  },
]

export default function OnboardingConsent({ onAccept }) {
  const [checked, setChecked] = useState({ terms: false, privacy: false, medical: false, age: false })
  const [showLegal, setShowLegal] = useState(null)

  const allChecked = Object.values(checked).every(Boolean)

  function toggle(key) {
    setChecked(c => ({ ...c, [key]: !c[key] }))
  }

  if (showLegal) {
    return <LegalModal onClose={() => setShowLegal(null)} initialTab={showLegal} />
  }

  return (
    <div className="fixed inset-0 z-[200] flex flex-col items-center justify-end"
      style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }}>

      <div className="w-full max-w-[430px] rounded-t-3xl p-6 modal-enter"
        style={{ background: 'var(--bg-surface)' }}>

        {/* Logo + title */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-3 flex items-center justify-center"
            style={{ background: 'var(--cta)' }}>
            <UtensilsCrossed size={28} className="text-white" />
          </div>
          <h2 className="text-[20px] font-bold tracking-[-0.02em]"
            style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display", serif' }}>
            Bienvenido a CalorIA
          </h2>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-2)' }}>
            Antes de continuar, revisa y acepta los siguientes puntos
          </p>
        </div>

        {/* Notice */}
        <div className="rounded-xl px-3.5 py-3 mb-5"
          style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)' }}>
          <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-3)' }}>
            CalorIA utiliza inteligencia artificial para generar recomendaciones nutricionales.
            La IA puede cometer errores. Los planes generados son orientativos y no sustituyen
            el consejo de un profesional de la salud.
          </p>
        </div>

        {/* Checkboxes */}
        <div className="space-y-3 mb-6">
          {CHECKS.map(item => (
            <button key={item.key} onClick={() => toggle(item.key)}
              className="w-full flex items-start gap-3 text-left active:opacity-70 transition-opacity">
              <div className="flex-shrink-0 w-5 h-5 rounded-md mt-0.5 flex items-center justify-center transition-colors"
                style={{
                  background: checked[item.key] ? 'var(--cta)' : 'var(--bg-surface2)',
                  border: `1.5px solid ${checked[item.key] ? 'var(--cta)' : 'var(--border)'}`,
                }}>
                {checked[item.key] && <Check size={12} className="text-white" strokeWidth={3} />}
              </div>
              <p className="text-[13px] leading-snug flex-1" style={{ color: 'var(--text-1)' }}>
                {item.label}
                {item.link && (
                  <span
                    onClick={e => { e.stopPropagation(); setShowLegal(item.tab) }}
                    className="underline"
                    style={{ color: 'var(--cta)' }}>
                    {item.link}
                  </span>
                )}
              </p>
            </button>
          ))}
        </div>

        {/* CTA */}
        <button
          onClick={() => { if (allChecked) onAccept() }}
          disabled={!allChecked}
          className="w-full h-13 py-3.5 rounded-2xl font-bold text-[15px] text-white transition-all active:scale-[0.97] disabled:opacity-40"
          style={{
            background: 'var(--cta)',
            boxShadow: allChecked ? '0 6px 20px var(--cta-shadow)' : 'none',
          }}>
          Continuar
        </button>

        <p className="text-center text-[11px] mt-3" style={{ color: 'var(--text-3)' }}>
          Al continuar aceptas el uso de almacenamiento local para guardar tu perfil
        </p>
      </div>
    </div>
  )
}
