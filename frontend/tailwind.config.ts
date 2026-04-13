import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#172033',
        mist: '#eef4fb',
        signal: '#0f766e',
        alert: '#c2410c'
      }
    }
  },
  plugins: []
} satisfies Config

