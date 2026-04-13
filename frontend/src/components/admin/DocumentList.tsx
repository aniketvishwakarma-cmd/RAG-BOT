import { formatDate } from '../../utils/formatters'

interface Props {
  documents: Array<Record<string, unknown>>
  onDelete: (id: string) => void
}

export function DocumentList({ documents, onDelete }: Props) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">Layer</th>
            <th className="px-4 py-3">Version</th>
            <th className="px-4 py-3">Effective</th>
            <th className="px-4 py-3">Chunks</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 text-sm text-slate-700">
          {documents.map((document) => (
            <tr key={String(document.id)}>
              <td className="px-4 py-3">{String(document.title)}</td>
              <td className="px-4 py-3">{String(document.source_layer)}</td>
              <td className="px-4 py-3">{String(document.version ?? '1.0')}</td>
              <td className="px-4 py-3">{formatDate((document.effective_date as string | undefined) ?? null)}</td>
              <td className="px-4 py-3">{String(document.chunk_count ?? 0)}</td>
              <td className="px-4 py-3">
                <button onClick={() => onDelete(String(document.id))} className="rounded-md border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700">
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

