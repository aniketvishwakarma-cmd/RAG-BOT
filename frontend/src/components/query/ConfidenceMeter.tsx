interface Props {
  confidence: number
}

export function ConfidenceMeter({ confidence }: Props) {
  const pct = Math.round(confidence * 100)
  const colorClass = pct >= 80 ? 'bg-emerald-500' : pct >= 65 ? 'bg-amber-500' : 'bg-rose-500'
  const label = pct >= 80 ? 'High confidence' : pct >= 65 ? 'Medium confidence - review recommended' : 'Low confidence - human review required'

  return (
    <div className="flex items-center gap-3">
      <div className="h-2 w-32 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-medium text-slate-700">{pct}%</span>
      <span className="text-xs text-slate-500">{label}</span>
    </div>
  )
}

