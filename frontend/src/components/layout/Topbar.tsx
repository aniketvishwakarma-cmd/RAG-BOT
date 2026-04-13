import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'

export default function Topbar() {
  const navigate = useNavigate()
  const username = useAuthStore((state) => state.username)
  const logout = useAuthStore((state) => state.logout)

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <div className="text-sm font-semibold text-slate-900">Audit-proof regulatory RAG</div>
        <div className="text-xs text-slate-500">RBI hierarchy enforced across retrieval, answer generation, and review.</div>
      </div>
      <div className="flex items-center gap-3">
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">{username ?? 'auditor'}</div>
        <button
          onClick={() => {
            logout()
            navigate('/login')
          }}
          className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}

