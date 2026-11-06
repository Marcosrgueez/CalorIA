import { useState } from 'react'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'

export default function AuthModal({ isOpen, onClose, authState }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const { login, register } = authState

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(username, email, password)
      }
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ha ocurrido un error')
    } finally {
      setLoading(false)
    }
  }

  function Field({ label, type, value, onChange, placeholder }) {
    return (
      <div>
        <label className="block text-[12px] font-semibold mb-1.5 uppercase tracking-[0.08em]"
          style={{ color: 'var(--text-3)' }}>{label}</label>
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          required
          className="w-full rounded-xl px-4 py-3 text-[14px] outline-none"
          style={{ background: 'var(--bg-surface2)', border: '1px solid var(--border)', color: 'var(--text-1)' }}
        />
      </div>
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={mode === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}>
      <form onSubmit={handleSubmit} className="p-5 space-y-4">
        {mode === 'register' && (
          <Field label="Nombre de usuario" type="text" value={username}
            onChange={setUsername} placeholder="tu_nombre" />
        )}
        <Field label="Email" type="email" value={email}
          onChange={setEmail} placeholder="email@ejemplo.com" />
        <Field label="Contraseña" type="password" value={password}
          onChange={setPassword} placeholder="••••••••" />

        {error && (
          <div className="rounded-xl p-3 text-[13px]" style={{ background: 'var(--cta-soft)', color: 'var(--cta)' }}>
            {typeof error === 'string' ? error : 'Error al procesar la solicitud.'}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full h-12 rounded-xl text-white font-bold text-[14px] active:scale-[0.97] transition-transform disabled:opacity-60 flex items-center justify-center gap-2"
          style={{ background: 'var(--cta)', boxShadow: '0 4px 16px var(--cta-shadow)' }}
        >
          {loading && <Spinner size={18} color="#fff" />}
          {mode === 'login' ? 'Entrar' : 'Crear cuenta'}
        </button>

        <button
          type="button"
          onClick={() => { setMode(m => m === 'login' ? 'register' : 'login'); setError(null) }}
          className="w-full text-[13px] text-center py-1 active:opacity-70 transition-opacity"
          style={{ color: 'var(--text-2)' }}
        >
          {mode === 'login' ? '¿Sin cuenta? Regístrate gratis' : '¿Ya tienes cuenta? Inicia sesión'}
        </button>
      </form>
    </Modal>
  )
}
