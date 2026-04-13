import { create } from 'zustand'

interface AuthState {
  token: string | null
  username: string | null
  login: (username: string, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  username: localStorage.getItem('username'),
  login: (username, token) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('username', username)
    set({ username, token })
  },
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
    set({ username: null, token: null })
  }
}))

