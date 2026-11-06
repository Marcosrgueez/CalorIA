import { useState } from 'react'
import { Heart, MessageCircle, X, Plus } from 'lucide-react'
import Modal from '../ui/Modal'

const FILTERS = ['Todo', 'Éxito', 'Consejos', 'Preguntas']

const MOCK_POSTS = [
  {
    id: 1, user: 'María G.', avatar: 'M', category: 'Éxito',
    content: '¡Llevo 4 semanas usando CalorIA y ya perdí 3kg! Las recetas son deliciosas y el presupuesto se cumple siempre.',
    likes: 47, comments: 8, time: '2h',
    tags: ['pérdida de peso', 'resultado'],
  },
  {
    id: 2, user: 'Carlos M.', avatar: 'C', category: 'Consejos',
    content: 'Tip: si compras en Mercadona con la lista generada por la app, puedes ahorrar hasta un 30% comparando por peso. El comparador de precios es increíble.',
    likes: 31, comments: 5, time: '4h',
    tags: ['ahorro', 'compra'],
  },
  {
    id: 3, user: 'Ana L.', avatar: 'A', category: 'Éxito',
    content: 'El escáner de nevera me cambió la vida. Tenía solo huevos, tomate y queso y me generó 3 recetas distintas. ¡Mágico!',
    likes: 62, comments: 12, time: '6h',
    tags: ['nevera', 'recetas'],
  },
  {
    id: 4, user: 'Javier P.', avatar: 'J', category: 'Preguntas',
    content: '¿Alguien sabe si se puede ajustar el plan para ganar músculo sin aumentar mucho el gasto? Estoy en modo bulk pero con presupuesto ajustado.',
    likes: 14, comments: 19, time: '8h',
    tags: ['bulk', 'presupuesto'],
  },
  {
    id: 5, user: 'Laura S.', avatar: 'L', category: 'Consejos',
    content: 'Para los que empiezan: ponéos el objetivo de "Mantener" el primer mes. Os acostumbráis a las recetas y luego es más fácil ajustar a déficit.',
    likes: 28, comments: 4, time: '1d',
    tags: ['principiantes', 'hábitos'],
  },
]

const AVATAR_COLORS = ['#4a7c59', '#e8603c', '#7c5cbf', '#0ea5e9', '#f59e0b']

export default function ComunidadModal({ isOpen, onClose }) {
  const [filter, setFilter] = useState('Todo')
  const [liked, setLiked] = useState(new Set())

  const filtered = filter === 'Todo' ? MOCK_POSTS : MOCK_POSTS.filter(p => p.category === filter)

  function toggleLike(id) {
    setLiked(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Comunidad" fullScreen>
      <div className="flex-1">
        {/* Filter pills */}
        <div className="flex gap-2 px-5 py-3 overflow-x-auto no-scrollbar" style={{ borderBottom: '1px solid var(--border)' }}>
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="flex-shrink-0 px-3.5 py-1.5 rounded-full text-[12px] font-semibold active:scale-[0.95] transition-all"
              style={{
                background: filter === f ? 'var(--cta)' : 'var(--bg-surface2)',
                color: filter === f ? '#fff' : 'var(--text-2)',
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Posts */}
        <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
          {filtered.map((post, idx) => (
            <div key={post.id} className="px-5 py-4 space-y-3">
              <div className="flex items-start gap-3">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-white text-[13px] font-bold flex-shrink-0"
                  style={{ background: AVATAR_COLORS[idx % AVATAR_COLORS.length] }}
                >
                  {post.avatar}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-bold" style={{ color: 'var(--text-1)' }}>{post.user}</span>
                    <span
                      className="text-[10px] px-2 py-0.5 rounded-full font-semibold"
                      style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}
                    >
                      {post.category}
                    </span>
                    <span className="text-[11px] ml-auto flex-shrink-0" style={{ color: 'var(--text-3)' }}>{post.time}</span>
                  </div>
                  <p className="text-[13px] leading-relaxed mt-1.5" style={{ color: 'var(--text-2)' }}>
                    {post.content}
                  </p>
                  {post.tags?.length > 0 && (
                    <div className="flex gap-1.5 mt-2 flex-wrap">
                      {post.tags.map(t => (
                        <span key={t} className="text-[11px] px-2 py-0.5 rounded-full"
                          style={{ background: 'var(--bg-surface2)', color: 'var(--text-3)' }}>
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-4 pl-12">
                <button
                  onClick={() => toggleLike(post.id)}
                  className="flex items-center gap-1.5 text-[12px] font-medium active:scale-[0.9] transition-transform"
                  style={{ color: liked.has(post.id) ? '#f43f5e' : 'var(--text-3)' }}
                >
                  <Heart size={15} fill={liked.has(post.id) ? '#f43f5e' : 'none'} />
                  {post.likes + (liked.has(post.id) ? 1 : 0)}
                </button>
                <button
                  className="flex items-center gap-1.5 text-[12px] font-medium active:scale-[0.9] transition-transform"
                  style={{ color: 'var(--text-3)' }}
                >
                  <MessageCircle size={15} />
                  {post.comments}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Compose FAB */}
        <div className="sticky bottom-0 flex justify-end px-5 py-4" style={{ background: 'var(--bg-surface)' }}>
          <button
            className="flex items-center gap-2 px-4 py-3 rounded-xl text-white font-semibold text-[14px] active:scale-[0.95] transition-transform"
            style={{ background: 'var(--cta)', boxShadow: '0 4px 16px var(--cta-shadow)' }}
          >
            <Plus size={18} />
            Publicar
          </button>
        </div>
      </div>
    </Modal>
  )
}
