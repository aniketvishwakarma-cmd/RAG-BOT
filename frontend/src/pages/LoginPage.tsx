import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [username, setUsername] = useState('auditor')

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-6">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">CIBIL-RegBot</div>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">Sign in</h1>
          <p className="mt-2 text-sm text-slate-500">Use the demo login to enter the regulatory workspace.</p>
        </div>
        <div className="space-y-4">
          <input value={username} onChange={(event) => setUsername(event.target.value)} className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm" />
          <button
            onClick={() => {
              login(username, 'demo-token')
              navigate('/query')
            }}
            className="w-full rounded-md bg-slate-900 px-4 py-3 text-sm font-semibold text-white"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}
