import { useState, useRef } from 'react'
import { Camera, Upload, X } from 'lucide-react'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import * as api from '../../api/client'

export default function PhotoScannerModal({ onClose }) {
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
      const res = await api.scanPhoto(form)
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Error analizando la imagen')
    } finally {
      setLoading(false)
    }
  }

  const macros = result ? [
    { label: 'Calorías',  val: result.calories,    unit: 'kcal', color: '#e8603c' },
    { label: 'Proteína',  val: result.protein_g,   unit: 'g',    color: '#4a7c59' },
    { label: 'Grasa',     val: result.fat_g,        unit: 'g',    color: '#f59e0b' },
    { label: 'Carbos',    val: result.carbs_g,      unit: 'g',    color: '#7c5cbf' },
  ] : []

  return (
    <Modal isOpen title="Analizar Plato" onClose={onClose}>
      <div className="p-5 space-y-4">
        {!result && !loading && (
          <>
            <p className="text-[13px]" style={{ color: 'var(--text-2)' }}>
              Sube una foto de tu plato y la IA estimará las calorías y macronutrientes.
            </p>
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full h-36 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-3 active:scale-[0.98] transition-transform"
              style={{ borderColor: 'var(--border-strong)', color: 'var(--text-3)' }}
            >
              <Upload size={28} />
              <span className="text-[13px] font-medium">Seleccionar foto</span>
            </button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden"
              onChange={e => handleFile(e.target.files[0])} />
          </>
        )}

        {loading && (
          <div className="flex flex-col items-center py-10 gap-4">
            <Spinner size={32} />
            <p className="text-[13px]" style={{ color: 'var(--text-2)' }}>Analizando imagen…</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl p-4 text-[13px]" style={{ background: 'var(--cta-soft)', color: 'var(--cta)' }}>
            {typeof error === 'string' ? error : 'No se pudo analizar la imagen.'}
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-[16px] font-bold" style={{ color: 'var(--text-1)' }}>
                {result.dish_name}
              </h3>
              <span
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full"
                style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}
              >
                Confianza {result.confidence}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {macros.map(m => (
                <div key={m.label} className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-surface2)' }}>
                  <p className="text-[22px] font-bold tabular-nums" style={{ color: m.color }}>{m.val}</p>
                  <p className="text-[10px] font-medium mt-0.5" style={{ color: 'var(--text-3)' }}>{m.unit} · {m.label}</p>
                </div>
              ))}
            </div>

            {result.ingredients_detected?.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--text-3)' }}>
                  Ingredientes detectados
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.ingredients_detected.map(ing => (
                    <span key={ing} className="text-[12px] px-2.5 py-1 rounded-full font-medium capitalize"
                      style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}>
                      {ing}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {result.notes && (
              <p className="text-[12px] italic" style={{ color: 'var(--text-3)' }}>{result.notes}</p>
            )}

            <button
              onClick={() => { setResult(null); setError(null) }}
              className="w-full py-3 rounded-xl text-[13px] font-semibold active:scale-[0.97] transition-transform"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
            >
              Analizar otra foto
            </button>
          </div>
        )}
      </div>
    </Modal>
  )
}
