import { useState } from 'react'

const CI_WINDOW = 21
const CIC_WINDOW = 9
const TOTAL_WINDOW = 30
const CONSUMER_RATE = 100
const REGULATOR_RATE = 5000

export function PenaltyCalculator() {
  const [ciDays, setCiDays] = useState(21)
  const [cicDays, setCicDays] = useState(9)

  const ciDelay = Math.max(0, ciDays - CI_WINDOW)
  const totalDays = ciDays + cicDays
  const totalDelay = Math.max(0, totalDays - TOTAL_WINDOW)
  const cicDelay = Math.max(0, totalDelay - ciDelay)

  const consumerPenalty = totalDelay * CONSUMER_RATE
  const ciPenaltyShare = ciDelay * CONSUMER_RATE
  const cicPenaltyShare = cicDelay * CONSUMER_RATE

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-slate-900">Penalty calculator</h3>
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs text-slate-500">CI response days</label>
          <input type="number" min={1} max={60} value={ciDays} onChange={(event) => setCiDays(Number(event.target.value))} className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500">CIC resolution days</label>
          <input type="number" min={1} max={30} value={cicDays} onChange={(event) => setCicDays(Number(event.target.value))} className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm" />
        </div>
      </div>
      {totalDelay > 0 ? (
        <div className="space-y-3">
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">Delay of {totalDelay} days triggers consumer compensation.</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">Total to consumer: Rs.{consumerPenalty.toLocaleString()}</div>
            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">Regulator penalty: Rs.{(totalDelay * REGULATOR_RATE).toLocaleString()}</div>
          </div>
          <div className="space-y-1 text-sm text-slate-600">
            <div>CI liability: Rs.{ciPenaltyShare.toLocaleString()}</div>
            <div>CIC liability: Rs.{cicPenaltyShare.toLocaleString()}</div>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">Within the 30-day window. No consumer compensation liability.</div>
      )}
    </div>
  )
}

