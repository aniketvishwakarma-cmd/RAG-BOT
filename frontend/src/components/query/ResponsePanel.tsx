interface Props {
  answer: string
  keyFacts: string[]
  insufficientEvidence: boolean
}

export function ResponsePanel({ answer, keyFacts, insufficientEvidence }: Props) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Answer</h2>
        {insufficientEvidence && <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700">Refusal</span>}
      </div>
      <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{answer}</p>
      {keyFacts.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Key facts</div>
          <ul className="space-y-2 text-sm text-slate-700">
            {keyFacts.map((fact) => (
              <li key={fact} className="rounded-md bg-slate-50 px-3 py-2">
                {fact}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

