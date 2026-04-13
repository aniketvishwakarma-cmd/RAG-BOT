import { useEffect, useState } from 'react'
import { queryApi } from '../../api/queryApi'

interface Props {
  onSelect: (query: string) => void
}

export function QueryHistory({ onSelect }: Props) {
  const [items, setItems] = useState<string[]>([])

  useEffect(() => {
    queryApi
      .getHistory()
      .then((data) => setItems((data.queries || []).map((item: { original_query: string }) => item.original_query)))
      .catch(() => setItems([]))
  }, [])

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Recent queries</h3>
      <div className="space-y-2">
        {items.length === 0 && <div className="text-sm text-slate-500">No queries yet.</div>}
        {items.map((item) => (
          <button key={item} onClick={() => onSelect(item)} className="w-full rounded-md bg-slate-50 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100">
            {item}
          </button>
        ))}
      </div>
    </div>
  )
}
