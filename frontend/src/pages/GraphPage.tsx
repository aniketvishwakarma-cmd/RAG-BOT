import { KnowledgeGraphViewer } from '../components/graph/KnowledgeGraphViewer'

export default function GraphPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Knowledge graph</h1>
        <p className="text-sm text-slate-500">Document lineage, clause references, and graph-augmented retrieval paths.</p>
      </div>
      <KnowledgeGraphViewer />
    </div>
  )
}
