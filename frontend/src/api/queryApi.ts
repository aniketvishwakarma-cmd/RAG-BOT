import client from './client'

export interface QueryRequest {
  query: string
  layer_filter?: string[]
  bypass_cache?: boolean
  include_graph_context?: boolean
}

export interface CitationCard {
  source_id?: string
  source_name: string
  source_layer: string
  layer_priority: number
  section_no?: string
  clause_no?: string
  paragraph_no?: string
  page_no?: number
  excerpt: string
  relevance_score: number
  faithfulness_score: number
  citation_mismatch: boolean
  citation_warning?: string
}

export interface QueryResponse {
  query_id: string
  query: string
  answer: string
  key_facts: string[]
  confidence: number
  resolution_note: string
  citations: CitationCard[]
  requires_human_review: boolean
  latency_ms: number
  layer_sources_used: string[]
  insufficient_evidence: boolean
  citation_mismatch: boolean
  citation_warning?: string
  source_relevance_score?: number
  source_relevance_warning?: string
  grounding_score?: number
}

export const queryApi = {
  submit: async (req: QueryRequest): Promise<QueryResponse> => {
    const { data } = await client.post<QueryResponse>('/query/', req)
    return data
  },
  getHistory: async (page = 1, limit = 20) => {
    const { data } = await client.get(`/query/history?page=${page}&limit=${limit}`)
    return data
  },
  getById: async (id: string) => {
    const { data } = await client.get(`/query/${id}`)
    return data
  }
}

