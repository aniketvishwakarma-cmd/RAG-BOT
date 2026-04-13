interface Props {
  items: Array<Record<string, unknown>>
  onValidate: (queryId: string, status: 'approved' | 'rejected') => void
}

export function HITLReviewer({ items, onValidate }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-slate-900">Low-confidence queue</h3>
      <div className="space-y-3">
        {items.length === 0 && <div className="text-sm text-slate-500">No items need review.</div>}
        {items.map((item) => (
          <div key={String(item.id)} className="rounded-lg border border-slate-200 p-3">
            <div className="text-sm font-medium text-slate-900">{String(item.original_query)}</div>
            <div className="mt-1 text-xs text-slate-500">Confidence: {Number(item.confidence ?? 0).toFixed(2)}</div>
            <div className="mt-3 flex gap-2">
              <button onClick={() => onValidate(String(item.id), 'approved')} className="rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white">
                Approve
              </button>
              <button onClick={() => onValidate(String(item.id), 'rejected')} className="rounded-md bg-rose-600 px-3 py-2 text-xs font-semibold text-white">
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

