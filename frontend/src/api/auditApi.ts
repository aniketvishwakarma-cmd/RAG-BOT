import client from './client'

export const auditApi = {
  list: async (page = 1, limit = 50) => {
    const { data } = await client.get(`/audit/?page=${page}&limit=${limit}`)
    return data
  },
  validate: async (queryId: string, status: 'approved' | 'rejected', notes?: string) => {
    const { data } = await client.post('/audit/validate', { query_id: queryId, status, notes })
    return data
  }
}

