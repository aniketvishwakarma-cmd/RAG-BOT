import { DisputeCard } from '../components/tracker/DisputeCard'
import { PenaltyCalculator } from '../components/tracker/PenaltyCalculator'
import { TATProgress } from '../components/tracker/TATProgress'
import { useTATStore } from '../store/useTATStore'

export default function TATTrackerPage() {
  const disputes = useTATStore((state) => state.disputes)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">21 + 9 dispute tracker</h1>
        <p className="text-sm text-slate-500">Track the statutory 30-day window and map delay exposure across CI and CIC.</p>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <div className="space-y-4">
          <TATProgress ciDays={23} cicDays={10} />
          <div className="space-y-3">
            {disputes.map((dispute) => (
              <DisputeCard key={dispute.id} title={dispute.title} ciDays={dispute.ciDays} cicDays={dispute.cicDays} />
            ))}
          </div>
        </div>
        <PenaltyCalculator />
      </div>
    </div>
  )
}

