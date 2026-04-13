import type { CitationCard as CitationCardType } from '../../api/queryApi'
import { layerColors } from '../../utils/layerColors'

interface Props {
  citation: CitationCardType
  index: number
}

const layerLabels: Record<string, string> = {
  RBI_MASTER: 'RBI Master Direction',
  CICRA: 'CICRA / Statutory Act',
  RBI_CIRCULAR: 'RBI Circular',
  SOP: 'Internal SOP'
}

export function CitationCard({ citation, index }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-slate-400">#{index + 1}</span>
          <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${layerColors[citation.source_layer] || 'border-slate-200 bg-slate-100 text-slate-700'}`}>
            Layer {citation.layer_priority}: {layerLabels[citation.source_layer] || citation.source_layer}
          </span>
          <span className="text-xs font-medium text-slate-500">{citation.source_name}</span>
        </div>
        <span className="text-xs text-slate-400">{(citation.relevance_score * 100).toFixed(0)}% relevant</span>
      </div>
      <div className="mb-3 flex flex-wrap gap-2 font-mono text-xs text-slate-600">
        {citation.section_no && <span className="rounded-md bg-slate-50 px-2 py-1">Section: {citation.section_no}</span>}
        {citation.clause_no && <span className="rounded-md bg-slate-50 px-2 py-1">Clause: {citation.clause_no}</span>}
        {citation.paragraph_no && <span className="rounded-md bg-slate-50 px-2 py-1">Para: {citation.paragraph_no}</span>}
        {citation.page_no && <span className="rounded-md bg-slate-50 px-2 py-1">Page: {citation.page_no}</span>}
      </div>
      <blockquote className="border-l-2 border-slate-300 pl-3 text-sm italic leading-7 text-slate-700">"{citation.excerpt}"</blockquote>
    </div>
  )
}

