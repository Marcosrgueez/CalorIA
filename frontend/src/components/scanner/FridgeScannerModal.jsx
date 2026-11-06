import { useState, useRef } from 'react'
import { Upload, Clock } from 'lucide-react'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import * as api from '../../api/client'

const DIFF_COLORS = { fácil: '#4a7c59', media: '#f59e0b', difícil: '#e8603c' }

export default function FridgeScannerModal({ onClose }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [activeRecipe, setActiveRecipe] = useState(0)
  const fileRef = useRef()

  async function handleFile(file) {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await api.scanFridge(form)
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'No se detectaron ingredientes')
    } finally {
      setLoading(false)
    }
  }

  const recipes = result?.recipes ?? []
  const recipe = recipes[activeRecipe]

  return (
    <Modal isOpen title="Escanear Nevera" onClose={onClose}>
      <div className="p-5 space-y-4">
        {!result && !loading && (
          <>
            <p className="text-[13px]" style={{ color: 'var(--text-2)' }}>
              Fotografía tu nevera o despensa y la IA detectará los ingredientes y sugerirá recetas.
            </p>
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full h-36 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-3 active:scale-[0.98] transition-transform"
              style={{ borderColor: 'var(--border-strong)', color: 'var(--text-3)' }}
            >
              <Upload size={28} />
              <span className="text-[13px] font-medium">Foto de nevera o despensa</span>
            </button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden"
              onChange={e => handleFile(e.target.files[0])} />
          </>
        )}

        {loading && (
          <div className="flex flex-col items-center py-10 gap-4">
            <Spinner size={32} />
            <p className="text-[13px]" style={{ color: 'var(--text-2)' }}>Analizando tu nevera…</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl p-4 text-[13px]" style={{ background: 'var(--cta-soft)', color: 'var(--cta)' }}>
            {typeof error === 'string' ? error : 'No se detectaron ingredientes.'}
          </div>
        )}

        {result && (
          <div className="space-y-4 slide-up">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--text-3)' }}>
                Ingredientes detectados
              </p>
              <div className="flex flex-wrap gap-1.5">
                {result.ingredients_detected?.map(ing => (
                  <span key={ing} className="text-[12px] px-2.5 py-1 rounded-full font-medium capitalize"
                    style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                    {ing}
                  </span>
                ))}
              </div>
            </div>

            {recipes.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--text-3)' }}>
                  Recetas sugeridas
                </p>
                <div className="flex gap-2 mb-3 overflow-x-auto no-scrollbar">
                  {recipes.map((r, i) => (
                    <button key={i} onClick={() => setActiveRecipe(i)}
                      className="flex-shrink-0 px-3 py-1.5 rounded-lg text-[12px] font-semibold active:scale-[0.95] transition-all"
                      style={{
                        background: i === activeRecipe ? 'var(--cta)' : 'var(--bg-surface2)',
                        color: i === activeRecipe ? '#fff' : 'var(--text-2)',
                      }}>
                      {r.name}
                    </button>
                  ))}
                </div>

                {recipe && (
                  <div className="rounded-2xl p-4 space-y-3" style={{ background: 'var(--bg-surface2)' }}>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 text-[12px]" style={{ color: 'var(--text-2)' }}>
                        <Clock size={13} />
                        {recipe.prep_time_min} min
                      </div>
                      <span
                        className="text-[11px] px-2 py-0.5 rounded-full font-semibold capitalize"
                        style={{ background: (DIFF_COLORS[recipe.difficulty] || '#999') + '18', color: DIFF_COLORS[recipe.difficulty] || '#999' }}
                      >
                        {recipe.difficulty}
                      </span>
                      <span className="text-[12px] font-semibold" style={{ color: 'var(--cta)' }}>
                        ~{recipe.estimated_kcal} kcal
                      </span>
                    </div>

                    {recipe.steps?.length > 0 && (
                      <div className="space-y-2">
                        {recipe.steps.map((step, i) => (
                          <div key={i} className="flex gap-2.5 text-[12px] leading-relaxed" style={{ color: 'var(--text-2)' }}>
                            <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white mt-0.5"
                              style={{ background: 'var(--cta)' }}>{i + 1}</span>
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <button
              onClick={() => { setResult(null); setError(null) }}
              className="w-full py-3 rounded-xl text-[13px] font-semibold active:scale-[0.97] transition-transform"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
            >
              Analizar de nuevo
            </button>
          </div>
        )}
      </div>
    </Modal>
  )
}
