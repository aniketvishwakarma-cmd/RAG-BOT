import { create } from 'zustand'

interface DocumentStore {
  selectedLayer: string
  setSelectedLayer: (layer: string) => void
}

export const useDocumentStore = create<DocumentStore>((set) => ({
  selectedLayer: 'RBI_MASTER',
  setSelectedLayer: (selectedLayer) => set({ selectedLayer })
}))

