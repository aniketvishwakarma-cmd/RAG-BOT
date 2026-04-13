import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { queryApi, type QueryRequest, type QueryResponse } from '../api/queryApi'
import { SearchBar } from '../components/query/SearchBar'
import { LayerFilter } from '../components/query/LayerFilter'
import { ResponsePanel } from '../components/query/ResponsePanel'
import { CitationList } from '../components/query/CitationList'
import { ConfidenceMeter } from '../components/query/ConfidenceMeter'
import { ConflictAlert } from '../components/query/ConflictAlert'
import { QueryHistory } from '../components/query/QueryHistory'
import { useQueryStore } from '../store/useQueryStore'

const layers = ['RBI_MASTER', 'CICRA', 'RBI_CIRCULAR', 'SOP']

export default function QueryPage() {
  const [query, setQuery] = useState('')
  const [selectedLayers, setSelectedLayers] = useState<string[]>([])
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const addHistory = useQueryStore((state) => state.addHistory)
  const setLatest = useQueryStore((state) => state.setLatest)

  const mutation = useMutation({
    mutationFn: (req: QueryRequest) => queryApi.submit(req),
    onSuccess: (data) => {
      setResponse(data)
      setLatest(data)
      addHistory(data.query)
    }
  })

  const handleSubmit = () => {
    if (!query.trim()) return
    mutation.mutate({
      query: query.trim(),
      layer_filter: selectedLayers.length > 0 ? selectedLayers : undefined,
      include_graph_context: true
    })
  }

  return (
    <div className="flex h-full gap-6">
      <aside className="w-80 flex-shrink-0">
        <QueryHistory onSelect={setQuery} />
      </aside>
      <main className="flex-1 space-y-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <SearchBar value={query} onChange={setQuery} onSubmit={handleSubmit} isLoading={mutation.isPending} />
          <LayerFilter layers={layers} selected={selectedLayers} onChange={setSelectedLayers} />
        </div>

        {mutation.isError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            Error: {(mutation.error as Error).message}
          </div>
        )}

        {response && (
          <>
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <ConfidenceMeter confidence={response.confidence} />
                <div className="flex gap-2 text-xs text-slate-500">
                  <span>{response.latency_ms}ms</span>
                  <span>{response.citations.length} citations</span>
                  <span>{response.layer_sources_used.join(', ')}</span>
                </div>
              </div>
              {response.requires_human_review && (
                <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                  Low confidence. Auditor review is recommended before operational use.
                </div>
              )}
              {response.resolution_note && <ConflictAlert note={response.resolution_note} />}
            </div>
            <ResponsePanel answer={response.answer} keyFacts={response.key_facts} insufficientEvidence={response.insufficient_evidence} />
            {response.citations.length > 0 && <CitationList citations={response.citations} />}
          </>
        )}
      </main>
    </div>
  )
}

