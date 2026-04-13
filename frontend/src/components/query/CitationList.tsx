import type { CitationCard as CitationCardType } from '../../api/queryApi'
import { CitationCard } from './CitationCard'

interface Props {
  citations: CitationCardType[]
}

export function CitationList({ citations }: Props) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">Citations</h2>
      {citations.map((citation, index) => (
        <CitationCard key={`${citation.source_name}-${index}`} citation={citation} index={index} />
      ))}
    </section>
  )
}

