import { create } from 'zustand'

interface DisputeCase {
  id: string
  title: string
  ciDays: number
  cicDays: number
}

interface TATState {
  disputes: DisputeCase[]
  addDispute: (dispute: DisputeCase) => void
}

export const useTATStore = create<TATState>((set) => ({
  disputes: [
    { id: 'demo-1', title: 'Consumer dispute 4832', ciDays: 23, cicDays: 10 },
    { id: 'demo-2', title: 'Consumer dispute 4833', ciDays: 20, cicDays: 8 }
  ],
  addDispute: (dispute) => set((state) => ({ disputes: [dispute, ...state.disputes] }))
}))

