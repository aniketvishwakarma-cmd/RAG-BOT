import { formatCurrency } from '../../utils/formatters'

interface Props {
  title: string
  ciDays: number
  cicDays: number
}

export function DisputeCard({ title, ciDays, cicDays }: Props) {
  const totalDelay = Math.max(0, ciDays + cicDays - 30)

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">{title}</div>
      <div className="mt-2 grid grid-cols-3 gap-3 text-sm text-slate-600">
        <div>CI: {ciDays} days</div>
        <div>CIC: {cicDays} days</div>
        <div>Total delay: {totalDelay} days</div>
      </div>
      <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">Consumer compensation: {formatCurrency(totalDelay * 100)}</div>
    </div>
  )
}

