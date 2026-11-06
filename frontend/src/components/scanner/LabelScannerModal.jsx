import { useState, useRef } from 'react'
import { Upload } from 'lucide-react'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import * as api from '../../api/client'

export default function LabelScannerModal({ onClose }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  async function handleFile(file) {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await api.scanLabel(form)
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'No se pudo leer la etiqueta')
    } finally {
      setLoading(false)
    }
  }

  const rows100 = result?.per_100g ? [
    { label: 'Calorías',       val: result.per_100g.kcal,          unit: 'kcal' },
    { label: 'Proteína',       val: result.per_100g.protein_g,     unit: 'g' },
    { label: 'Grasa',          val: result.per_100g.fat_g,         unit: 'g' },
    { label: 'G. saturadas',   val: result.per_100g.saturated_fat_g, unit: 'g' },
    { label: 'Carbohidratos',  val: result.per_100g.carbs_g,       unit: 'g' },
    { label: 'Azúcares',       val: result.per_100g.sugar_g,       unit: 'g' },
    { label: 'Fibra',          val: result.per_100g.fiber_g,       unit: 'g' },
    { label: 'Sal',            val: result.per_100g.salt_g,        unit: 'g' },
  ] : []

  return (
    <Modal isOpen title="Etiqueta Nutricional" onClose={onClose}>
      <div className="p-5 space-y-4">
        {!result && !loading && (
          <>
            <p className="text-[13px]" style={{ color: 'var(--text-2)' }}>
              Fotografía la tabla nutricional de cualquier producto para leer sus valores automáticamente.
            </p>
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full h-36 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-3 active:scale-[0.98] transition-transform"
              style={{ borderColor: 'var(--border-strong)', color: 'var(--text-3)' }}
            >
              <Upload size={28} />
              <span className="text-[13px] font-medium">Subir foto de etiqueta</span>
            </button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden"
              onChange={e => handleFile(e.target.files[0])} />
          </>
        )}

        {loading && (
          <div className="flex flex-col items-center py-10 gap-4">
            <Spinner size={32} />
            <p className="text-[13px]" style={{ color: 'var(--text-2)' }}>Leyendo etiqueta…</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl p-4 text-[13px]" style={{ background: 'var(--cta-soft)', color: 'var(--cta)' }}>
            {typeof error === 'string' ? error : 'No se pudo leer la etiqueta.'}
          </div>
        )}

        {result && (
          <div className="space-y-4 slide-up">
            <div>
              <h3 className="text-[16px] font-bold" style={{ color: 'var(--text-1)' }}>
                {result.product_name}
              </h3>
              {result.serving_size_g && (
                <p className="text-[12px] mt-0.5" style={{ color: 'var(--text-2)' }}>
                  Porción: {result.serving_size_g}g
                </p>
              )}
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--text-3)' }}>
                Por 100g
              </p>
              <div style={{ border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
                {rows100.filter(r => r.val != null).map((row, i) => (
                  <div
                    key={row.label}
                    className="flex items-center justify-between px-4 py-2.5 text-[13px]"
                    style={{ borderBottom: i < rows100.length - 1 ? '1px solid var(--border)' : 'none',
                             background: i % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-surface2)' }}
                  >
                    <span style={{ color: 'var(--text-2)' }}>{row.label}</span>
                    <span className="font-semibold tabular-nums" style={{ color: 'var(--text-1)' }}>
                      {row.val} {row.unit}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {result.notes && (
              <p className="text-[12px] italic" style={{ color: 'var(--text-3)' }}>{result.notes}</p>
            )}

            <button
              onClick={() => { setResult(null); setError(null) }}
              className="w-full py-3 rounded-xl text-[13px] font-semibold active:scale-[0.97] transition-transform"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
            >
              Leer otra etiqueta
            </button>
          </div>
        )}
      </div>
    </Modal>
  )
}
