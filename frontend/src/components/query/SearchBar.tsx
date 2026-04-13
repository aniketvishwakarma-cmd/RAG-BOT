interface Props {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  isLoading?: boolean
}

export function SearchBar({ value, onChange, onSubmit, isLoading }: Props) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-semibold text-slate-900">Ask a regulatory question</label>
      <div className="flex gap-3">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="What is the penalty for a 3-day reporting delay by the CI?"
          className="min-h-[112px] flex-1 rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none ring-0"
        />
        <button
          onClick={onSubmit}
          disabled={isLoading}
          className="h-fit rounded-lg bg-slate-900 px-4 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? 'Running...' : 'Run query'}
        </button>
      </div>
    </div>
  )
}

