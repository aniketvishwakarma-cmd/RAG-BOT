import { useEffect, useState } from 'react'
import { auditApi } from '../api/auditApi'

export default function AuditPage() {
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([])

  useEffect(() => {
    auditApi.list().then((data) => setLogs(data.logs || [])).catch(() => setLogs([]))
  }, [])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Audit trail</h1>
        <p className="text-sm text-slate-500">Every request, validation decision, and ingestion action is preserved here.</p>
      </div>
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-sm text-slate-700">
            {logs.map((log) => (
              <tr key={String(log.id)}>
                <td className="px-4 py-3">{String(log.action)}</td>
                <td className="px-4 py-3">{String(log.entity_type)} / {String(log.entity_id)}</td>
                <td className="px-4 py-3">{String(log.status)}</td>
                <td className="px-4 py-3">{new Date(String(log.created_at)).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

