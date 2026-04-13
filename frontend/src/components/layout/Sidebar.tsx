import { Link, useLocation } from 'react-router-dom'

const items = [
  { to: '/query', label: 'Query' },
  { to: '/audit', label: 'Audit' },
  { to: '/admin', label: 'Admin' },
  { to: '/tracker', label: 'TAT Tracker' },
  { to: '/graph', label: 'Graph' }
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="flex w-64 flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">CIBIL-RegBot</div>
        <div className="mt-1 text-lg font-semibold text-slate-900">Regulatory cockpit</div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {items.map((item) => {
          const active = location.pathname === item.to
          return (
            <Link
              key={item.to}
              to={item.to}
              className={active ? 'block rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white' : 'block rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100'}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

