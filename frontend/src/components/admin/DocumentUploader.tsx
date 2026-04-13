import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { documentApi } from '../../api/documentApi'

interface Props {
  onUploaded: () => void
}

export function DocumentUploader({ onUploaded }: Props) {
  const [layer, setLayer] = useState('RBI_CIRCULAR')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [status, setStatus] = useState<string>('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)

  const { getRootProps, getInputProps } = useDropzone({
    onDrop: async (acceptedFiles) => {
      if (!acceptedFiles.length || isUploading) return

      setIsUploading(true)
      setUploadProgress(0)
      setStatus(`Uploading ${acceptedFiles.length} file${acceptedFiles.length > 1 ? 's' : ''}...`)

      try {
        await documentApi.upload(acceptedFiles, layer, effectiveDate || undefined, {
          onProgress: (percent) => {
            setUploadProgress(percent)
            setStatus(percent >= 100 ? 'Upload complete. Processing document...' : `Uploading... ${percent}%`)
          }
        })
        setUploadProgress(100)
        setStatus('Document processed successfully.')
        onUploaded()
      } catch (error) {
        console.error(error)
        setStatus('Upload failed. Please try again.')
        setUploadProgress(0)
      } finally {
        setIsUploading(false)
      }
    }
  })

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap gap-3">
        <select value={layer} onChange={(event) => setLayer(event.target.value)} disabled={isUploading} className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-100">
          <option value="RBI_MASTER">RBI_MASTER</option>
          <option value="CICRA">CICRA</option>
          <option value="RBI_CIRCULAR">RBI_CIRCULAR</option>
          <option value="SOP">SOP</option>
        </select>
        <input value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} disabled={isUploading} type="date" className="rounded-md border border-slate-200 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-100" />
      </div>
      <div
        {...getRootProps()}
        className={`rounded-lg border border-dashed px-4 py-10 text-center text-sm text-slate-600 ${isUploading ? 'cursor-progress border-emerald-300 bg-emerald-50' : 'border-slate-300 bg-slate-50'}`}
      >
        <input {...getInputProps()} />
        {isUploading ? 'Uploading is in progress. Please wait.' : 'Drag and drop regulatory files here, or click to select documents.'}
      </div>
      {status && (
        <div className="mt-3 space-y-2 text-sm text-slate-600">
          <div className="flex items-center justify-between gap-4">
            <span>{status}</span>
            {isUploading && <span className="tabular-nums text-slate-500">{uploadProgress}%</span>}
          </div>
          {(isUploading || uploadProgress === 100) && (
            <div className="h-2 overflow-hidden rounded-full bg-slate-200">
              <div
                className={`h-full rounded-full transition-all duration-300 ${uploadProgress >= 100 && isUploading ? 'animate-pulse bg-emerald-500' : 'bg-emerald-600'}`}
                style={{ width: `${Math.max(uploadProgress, 6)}%` }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
