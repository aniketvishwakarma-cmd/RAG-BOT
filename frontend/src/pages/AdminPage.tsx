import { useEffect, useState } from 'react'
import { auditApi } from '../api/auditApi'
import { documentApi } from '../api/documentApi'
import { DocumentList } from '../components/admin/DocumentList'
import { DocumentUploader } from '../components/admin/DocumentUploader'
import { HITLReviewer } from '../components/admin/HITLReviewer'
import { IngestionStatus } from '../components/admin/IngestionStatus'

export default function AdminPage() {
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([])
  const [reviewItems, setReviewItems] = useState<Array<Record<string, unknown>>>([])

  const refresh = async () => {
    const docs = await documentApi.list()
    setDocuments(docs.documents || [])
  }

  useEffect(() => {
    refresh().catch(() => setDocuments([]))
    auditApi.list().then(() => setReviewItems([])).catch(() => setReviewItems([]))
  }, [])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Document administration</h1>
        <p className="text-sm text-slate-500">Upload source material, inspect versions, and review low-confidence answers.</p>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="space-y-5">
          <DocumentUploader onUploaded={() => refresh()} />
          <DocumentList
            documents={documents}
            onDelete={async (id) => {
              await documentApi.delete(id)
              await refresh()
            }}
          />
        </div>
        <div className="space-y-5">
          <IngestionStatus />
          <HITLReviewer
            items={reviewItems}
            onValidate={async (queryId, status) => {
              await auditApi.validate(queryId, status)
            }}
          />
        </div>
      </div>
    </div>
  )
}

