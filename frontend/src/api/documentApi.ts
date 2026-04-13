import client from './client'

interface UploadOptions {
  onProgress?: (percent: number) => void
}

export const documentApi = {
  upload: async (files: File[], layer: string, effectiveDate?: string, options?: UploadOptions) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    form.append('source_layer', layer)
    if (effectiveDate) form.append('effective_date', effectiveDate)
    const { data } = await client.post('/ingest/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (!options?.onProgress || !progressEvent.total) return
        const percent = Math.min(100, Math.round((progressEvent.loaded * 100) / progressEvent.total))
        options.onProgress(percent)
      }
    })
    return data
  },
  ingestFilePath: async (filePath: string, title: string, layer: string, effectiveDate?: string) => {
    const form = new FormData()
    form.append('file_path', filePath)
    form.append('title', title)
    form.append('source_layer', layer)
    if (effectiveDate) form.append('effective_date', effectiveDate)
    const { data } = await client.post('/ingest/', form)
    return data
  },
  list: async () => {
    const { data } = await client.get('/documents/')
    return data
  },
  delete: async (id: string) => {
    const { data } = await client.delete(`/documents/${id}`)
    return data
  }
}
