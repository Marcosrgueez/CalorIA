import { useState } from 'react'
import { ScanLine, Search } from 'lucide-react'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import * as api from '../../api/client'

const NUTRI_COLORS = { A: '#2d7d46', B: '#89c12d', C: '#f9c734', D: '#f77f00', E: '#e63312' }

export default function BarcodeScannerModal({ onClose }) {
  const [barcode, setBarcode] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSearch() {
    const code = barcode.trim()
    if (!code) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.scanBarcode(code)
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Producto no encontrado')
    } finally {
      setLoading(false)
    }
  }

  const macros = result ? [
    { label: 'Calorías',  val: result.macros_per_100g?.kcal,    unit: 'kcal', color: '#e8603c' },
    { label: 'Proteína',  val: result.macros_per_100g?.protein,  unit: 'g',    color: '#4a7c59' },
    { label: 'Grasa',     val: result.macros_per_100g?.fat,      unit: 'g',    color: '#f59e0b' },
    { label: 'Carbos',    val: result.macros_per_100g?.carbs,    unit: 'g',    color: '#7c5cbf' },
    { label: 'Fibra',     val: result.macros_per_100g?.fiber,    unit: 'g',    color: '#0ea5e9' },
    { label: 'Azúcar',    val: result.macros_per_100g?.sugar,    unit: 'g',    color: '#f43f5e' },
  ] : []

  return (
    <Modal isOpen title="Código de Barras" onClose={onClose}>
      <div className="p-5 space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={barcode}
            onChange={e => setBarcode(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Introduce el código de barras…"
            className="flex-1 rounded-xl px-4 py-3 text-[14px] outline-none"
            style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}
            autoFocus
          />
          <button
            onClick={handleSearch}
            disabled={loading || !barcode.trim()}
            className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 active:scale-[0.9] transition-transform disabled:opacity-40"
            style={{ background: 'var(--cta)', color: '#fff' }}
          >
            {loading ? <Spinner size={18} color="#fff" /> : <Search size={18} />}
          </button>
        </div>

        {error && (
          <div className="rounded-xl p-3 text-[13px]" style={{ background: 'var(--cta-soft)', color: 'var(--cta)' }}>
            {typeof error === 'string' ? error : 'Producto no encontrado en la base de datos.'}
          </div>
        )}

        {result && (
          <div className="space-y-4 slide-up">
            <div className="flex items-start gap-3">
              {result.image_url && (
                <img src={result.image_url} alt={result.name} className="w-16 h-16 rounded-xl object-contain flex-shrink-0"
                  style={{ background: 'var(--bg-surface2)' }} />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-[15px] font-bold leading-snug" style={{ color: 'var(--text-1)' }}>{result.name}</p>
                <p className="text-[12px] mt-0.5" style={{ color: 'var(--text-2)' }}>{result.brand}</p>
                {result.quantity && <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-3)' }}>{result.quantity}</p>}
              </div>
              {result.nutriscore && (
                <span
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-[14px] flex-shrink-0"
                  style={{ background: NUTRI_COLORS[result.nutriscore] || '#999' }}
                >
                  {result.nutriscore}
                </span>
              )}
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--text-3)' }}>
                Por 100g
              </p>
              <div className="grid grid-cols-3 gap-2">
                {macros.map(m => (
                  <div key={m.label} className="rounded-xl p-2.5 text-center" style={{ background: 'var(--bg-surface2)' }}>
                    <p className="text-[16px] font-bold tabular-nums" style={{ color: m.color }}>{m.val}</p>
                    <p className="text-[9px] font-medium mt-0.5" style={{ color: 'var(--text-3)' }}>{m.unit} · {m.label}</p>
                  </div>
                ))}
              </div>
            </div>

            {result.allergens?.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--text-3)' }}>
                  Alérgenos
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.allergens.map(a => (
                    <span key={a} className="text-[11px] px-2 py-0.5 rounded-full font-medium capitalize"
                      style={{ background: '#fef3ef', color: '#e8603c', border: '1px solid #fca77d88' }}>
                      {a.replace('en:', '')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => { setResult(null); setBarcode(''); setError(null) }}
              className="w-full py-3 rounded-xl text-[13px] font-semibold active:scale-[0.97] transition-transform"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
            >
              Buscar otro producto
            </button>
          </div>
        )}
      </div>
    </Modal>
  )
}
