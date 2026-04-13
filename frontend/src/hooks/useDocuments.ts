import { useQuery } from '@tanstack/react-query'
import { documentApi } from '../api/documentApi'

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: () => documentApi.list()
  })
}

