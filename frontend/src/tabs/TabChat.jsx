import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, RefreshCw } from 'lucide-react'
import AppHeader from '../components/layout/AppHeader'
import { sendChat } from '../api/client'

const QUICK = [
  'Me salté la dieta hoy',
  'Tengo ansiedad por dulce',
  'No tengo tiempo para cocinar',
  'Hazme algo con pollo y arroz',
  'Quiero una cena barata',
  '¿Cuánta proteína necesito?',
]

const WELCOME = {
  id: 'welcome',
  role: 'assistant',
  text: '¡Hola! Soy tu asistente nutricional IA. Puedo ayudarte a adaptar tu dieta, resolver dudas de nutrición, generarte recetas con lo que tienes o simplemente motivarte. ¿En qué te ayudo hoy?',
}

export default function TabChat({ theme, toggleTheme, profileState, dietState }) {
  const { profile, kcal, macros } = profileState
  const { diet } = dietState || {}
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(text) {
    const msg = (text || input).trim()
    if (!msg || loading) return
    setInput('')
    setMessages(m => [...m, { id: Date.now(), role: 'user', text: msg }])
    setLoading(true)
    try {
      const userCtx = {
        name: profile.name || 'Usuario',
        age: profile.age,
        sex: profile.sex,
        weight: profile.weight,
        height: profile.height,
        goal: profile.goal,
        activity: profile.activity,
        kcal_target: kcal,
        protein_g: macros?.prot,
        fat_g: macros?.fat,
        carbs_g: macros?.carbsMin,
        current_diet: diet ?? null,
      }
      // Build history excluding welcome message, add current user message
      const history = messages
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role, content: m.text }))
      history.push({ role: 'user', content: msg })
      const res = await sendChat({ messages: history, user_context: userCtx })
      const reply = res.data?.reply || res.data?.message || 'No entendí tu mensaje. Intenta reformularlo.'
      setMessages(m => [...m, { id: Date.now() + 1, role: 'assistant', text: reply }])
    } catch {
      setMessages(m => [...m, {
        id: Date.now() + 1,
        role: 'assistant',
        text: 'Lo siento, tuve un problema conectando. Revisa tu conexión e inténtalo de nuevo.',
        error: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setMessages([WELCOME])
    setInput('')
  }

  return (
    <div className="tab-enter flex flex-col h-full">
      <AppHeader
        title="Chat IA"
        subtitle="Tu asistente nutricional personal"
        theme={theme}
        onToggleTheme={toggleTheme}
        rightAction={
          <button onClick={reset}
            className="w-8 h-8 rounded-full flex items-center justify-center active:scale-[0.9] transition-transform"
            style={{ background: 'var(--bg-surface2)' }}>
            <RefreshCw size={14} style={{ color: 'var(--text-3)' }} />
          </button>
        }
      />

      {/* Welcome screen or messages */}
      {messages.length === 1 ? (
        <div className="flex-1 overflow-y-auto no-scrollbar px-5 py-4">
          {/* Centered logo with pulse ring */}
          <div className="flex flex-col items-center text-center pt-6 pb-4">
            <div className="relative mb-5">
              <div className="absolute inset-0 rounded-2xl pulse-ring pointer-events-none"
                style={{ background: 'var(--accent)', transform: 'scale(1.5)', opacity: 0.12 }} />
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center relative"
                style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
                <Sparkles size={28} style={{ color: 'var(--accent)' }} />
              </div>
            </div>
            <h2 className="text-[22px] font-bold mb-2 tracking-[-0.02em]"
              style={{ color: 'var(--text-1)', fontFamily: '"Playfair Display",serif' }}>
              ¿En qué te ayudo hoy?
            </h2>
            <p className="text-[13px] mb-6" style={{ color: 'var(--text-2)' }}>
              Tu nutricionista personal con IA, siempre disponible
            </p>
          </div>
          {/* Vertical full-width suggestion buttons */}
          <div className="space-y-2">
            {QUICK.map((q, i) => (
              <button key={q} onClick={() => send(q)}
                className="fade-up w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl text-[13px] font-medium text-left active:scale-[0.98] transition-transform"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-1)',
                  boxShadow: 'var(--shadow-card)',
                  animationDelay: `${i * 45}ms`,
                }}>
                <div className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: 'var(--accent-soft)' }}>
                  <Sparkles size={12} style={{ color: 'var(--accent)' }} />
                </div>
                {q}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 no-scrollbar">
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`}>
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mb-0.5"
                  style={{ background: 'var(--accent-soft)' }}>
                  <Sparkles size={13} style={{ color: 'var(--accent)' }} />
                </div>
              )}
              <div
                className="max-w-[80%] px-4 py-3 text-[13px] leading-relaxed"
                style={{
                  background: msg.role === 'user' ? 'var(--cta)' : msg.error ? 'var(--bg-surface2)' : 'var(--bg-surface)',
                  color: msg.role === 'user' ? '#fff' : msg.error ? 'var(--text-3)' : 'var(--text-1)',
                  borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                {msg.text}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start items-end gap-2">
              <div className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center"
                style={{ background: 'var(--accent-soft)' }}>
                <Sparkles size={13} style={{ color: 'var(--accent)' }} />
              </div>
              <div className="px-4 py-3" style={{ background: 'var(--bg-surface)', boxShadow: 'var(--shadow-card)', borderRadius: '18px 18px 18px 4px' }}>
                <div className="flex gap-1 items-center h-4">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-1.5 h-1.5 rounded-full"
                      style={{
                        background: 'var(--text-3)',
                        animation: 'breathe 1.2s ease-in-out infinite',
                        animationDelay: `${i * 0.2}s`,
                      }} />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}

      {/* Input bar */}
      <div className="px-4 pb-4 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Escribe tu mensaje..."
            rows={1}
            className="flex-1 resize-none rounded-2xl px-4 py-3 text-[14px] outline-none no-scrollbar"
            style={{
              background: 'var(--bg-surface2)',
              border: '1px solid var(--border)',
              color: 'var(--text-1)',
              maxHeight: '96px',
              lineHeight: '1.4',
            }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 96) + 'px'
            }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 active:scale-[0.9] transition-transform"
            style={{
              background: input.trim() && !loading ? 'var(--cta)' : 'var(--bg-surface2)',
              boxShadow: input.trim() && !loading ? '0 4px 16px var(--cta-shadow)' : 'none',
            }}>
            <Send size={16} style={{ color: input.trim() && !loading ? '#fff' : 'var(--text-3)' }} />
          </button>
        </div>
      </div>
    </div>
  )
}
