import { useEffect, useState } from 'react'

export function useWebSocket() {
  const [status, setStatus] = useState<'idle' | 'connected'>('idle')

  useEffect(() => {
    setStatus('connected')
    return () => setStatus('idle')
  }, [])

  return { status }
}

