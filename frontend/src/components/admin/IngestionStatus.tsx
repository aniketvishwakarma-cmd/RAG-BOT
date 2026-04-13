import { useWebSocket } from '../../hooks/useWebSocket'

export function IngestionStatus() {
  const { status } = useWebSocket()

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">Ingestion channel</div>
      <div className="mt-2 text-sm text-slate-600">{status === 'connected' ? 'Status stream connected.' : 'Waiting for ingestion events.'}</div>
    </div>
  )
}

