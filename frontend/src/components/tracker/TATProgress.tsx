interface Props {
  ciDays: number
  cicDays: number
}

export function TATProgress({ ciDays, cicDays }: Props) {
  const total = ciDays + cicDays
  const pct = Math.min((total / 30) * 100, 100)

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between text-sm text-slate-700">
        <span>30-day statutory timeline</span>
        <span>{total}/30 days</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-100">
        <div className={pct >= 100 ? 'h-3 bg-rose-500' : 'h-3 bg-sky-500'} style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-slate-600">
        <div>CI window: {ciDays}/21 days</div>
        <div>CIC window: {cicDays}/9 days</div>
      </div>
    </div>
  )
}

