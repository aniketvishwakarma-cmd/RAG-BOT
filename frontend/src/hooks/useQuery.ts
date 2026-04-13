import { useMutation } from '@tanstack/react-query'
import { queryApi, type QueryRequest } from '../api/queryApi'

export function useQueryMutation() {
  return useMutation({
    mutationFn: (req: QueryRequest) => queryApi.submit(req)
  })
}

