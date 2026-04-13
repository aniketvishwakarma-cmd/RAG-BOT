interface Props {
  message: string
  tone?: 'success' | 'error'
}

export function Toast({ message, tone = 'success' }: Props) {
  return (
    <div className={tone === 'success' ? 'rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700' : 'rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700'}>
      {message}
    </div>
  )
}

