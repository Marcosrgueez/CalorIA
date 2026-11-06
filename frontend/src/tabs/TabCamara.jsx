import { useState } from 'react'
import { Camera, ScanLine, FileText, Refrigerator, ArrowRight } from 'lucide-react'
import AppHeader from '../components/layout/AppHeader'
import PhotoScannerModal from '../components/scanner/PhotoScannerModal'
import BarcodeScannerModal from '../components/scanner/BarcodeScannerModal'
import LabelScannerModal from '../components/scanner/LabelScannerModal'
import FridgeScannerModal from '../components/scanner/FridgeScannerModal'

const SCANNERS = [
  {
    id: 'photo',
    Icon: Camera,
    title: 'Analizar Plato',
    sub: 'La IA estima calorías y macros desde una foto',
    color: '#e8603c',
    bg: '#fef3ef',
  },
  {
    id: 'barcode',
    Icon: ScanLine,
    title: 'Código de Barras',
    sub: 'Información nutricional completa del producto',
    color: '#4a7c59',
    bg: '#eef5f0',
  },
  {
    id: 'label',
    Icon: FileText,
    title: 'Etiqueta Nutricional',
    sub: 'Lee la tabla nutricional automáticamente',
    color: '#7c5cbf',
    bg: '#f3f0fb',
  },
  {
    id: 'fridge',
    Icon: Refrigerator,
    title: 'Escanear Nevera',
    sub: 'Detecta ingredientes y genera recetas',
    color: '#0ea5e9',
    bg: '#f0f9ff',
    badge: 'NUEVO',
  },
]

export default function TabCamara({ theme, toggleTheme }) {
  const [active, setActive] = useState(null)

  return (
    <div className="tab-enter">
      <AppHeader
        title="Cámara IA"
        subtitle="Analiza alimentos con inteligencia artificial"
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <section className="px-4">
        <div className="grid grid-cols-2 gap-3">
          {SCANNERS.map(({ id, Icon, title, sub, color, bg, badge }, i) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className="card p-5 text-left active:scale-[0.95] transition-all duration-150 relative overflow-hidden"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              {/* Corner gradient */}
              <div
                className="absolute top-0 right-0 w-20 h-20 opacity-20 pointer-events-none"
                style={{ background: `radial-gradient(circle at top right, ${color}, transparent)` }}
              />

              {/* Badge */}
              {badge && (
                <span
                  className="absolute top-3 right-3 text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white"
                  style={{ background: color }}>
                  {badge}
                </span>
              )}

              {/* Icon */}
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 relative"
                style={{ background: bg }}
              >
                <Icon size={26} style={{ color }} />
              </div>

              <p className="text-[14px] font-bold leading-snug mb-1" style={{ color: 'var(--text-1)' }}>
                {title}
              </p>
              <p className="text-[12px] leading-relaxed mb-3" style={{ color: 'var(--text-2)' }}>
                {sub}
              </p>

              {/* Arrow indicator */}
              <div className="flex items-center gap-1" style={{ color }}>
                <span className="text-[11px] font-semibold">Abrir</span>
                <ArrowRight size={12} />
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Tips */}
      <section className="px-4 mt-5">
        <div className="rounded-2xl p-4" style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
          <p className="text-[12px] font-bold mb-1" style={{ color: 'var(--accent)' }}>
            Consejo
          </p>
          <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-2)' }}>
            Para mejores resultados, usa fotos bien iluminadas y con el alimento centrado en la imagen.
          </p>
        </div>
      </section>

      {active === 'photo'   && <PhotoScannerModal   onClose={() => setActive(null)} />}
      {active === 'barcode' && <BarcodeScannerModal onClose={() => setActive(null)} />}
      {active === 'label'   && <LabelScannerModal   onClose={() => setActive(null)} />}
      {active === 'fridge'  && <FridgeScannerModal  onClose={() => setActive(null)} />}
    </div>
  )
}
