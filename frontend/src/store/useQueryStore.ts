import { create } from 'zustand'
import type { QueryResponse } from '../api/queryApi'

interface QueryState {
  history: string[]
  latest: QueryResponse | null
  addHistory: (query: string) => void
  setLatest: (response: QueryResponse | null) => void
}

export const useQueryStore = create<QueryState>((set) => ({
  history: [],
  latest: null,
  addHistory: (query) =>
    set((state) => ({
      history: [query, ...state.history.filter((item) => item !== query)].slice(0, 20)
    })),
  setLatest: (response) => set({ latest: response })
}))

