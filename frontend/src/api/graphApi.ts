import client from './client'

export const graphApi = {
  relations: async (limit = 500) => {
    const { data } = await client.get(`/graph/relations?limit=${limit}`)
    return data
  },
  lineage: async (documentId: string) => {
    const { data } = await client.get(`/graph/lineage/${documentId}`)
    return data
  }
}
