import { X } from 'lucide-react'
import { useEffect } from 'react'

export default function Modal({ isOpen, onClose, title, children, fullScreen = false }) {
  useEffect(() => {
    if (isOpen) document.body.style.overflow = 'hidden'
    else document.body.style.overflow = ''
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={`relative w-full max-w-[430px] modal-enter overflow-hidden
          ${fullScreen ? 'h-[calc(100dvh-60px)] rounded-t-3xl' : 'rounded-t-3xl sm:rounded-2xl max-h-[90vh]'}`}
        style={{
          background: 'var(--bg-surface)',
          boxShadow: 'var(--shadow-modal)',
        }}
      >
        {title && (
          <div
            className="flex items-center justify-between px-5 py-4"
            style={{ borderBottom: '1px solid var(--border)' }}
          >
            <h2 className="text-[17px] font-bold" style={{ color: 'var(--text-1)' }}>
              {title}
            </h2>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full flex items-center justify-center active:scale-[0.9] transition-transform"
              style={{ background: 'var(--bg-surface2)', color: 'var(--text-2)' }}
            >
              <X size={16} />
            </button>
          </div>
        )}
        <div className="overflow-y-auto max-h-[calc(90vh-60px)]">
          {children}
        </div>
      </div>
    </div>
  )
}
