import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ''
})

export interface TenderListItem {
  id: number
  title: string
  announcement_type?: string
  purchase_category?: string
  company_name?: string
  publish_date?: string
  source_list_order?: number
  project_code?: string
  project_name?: string
  buyer?: string
  agency?: string
  source_url?: string
  requirement_count: number
  block_count: number
}

export interface DocumentBlock {
  id: number
  block_order: number
  block_type: string
  heading_level?: number
  section_no?: string
  title?: string
  text_content?: string
  table_json?: unknown
  block_json?: unknown
}

export interface TenderRequirement {
  id: number
  requirement_order: number
  requirement_type?: string
  requirement_title?: string
  requirement_text?: string
}

export interface TenderDetail {
  document: TenderListItem & {
    source_list_url?: string
    raw_text?: string
    document_json?: Record<string, unknown>
    last_seen_at?: string
  }
  blocks: DocumentBlock[]
  requirements: TenderRequirement[]
  packages: unknown[]
}

export async function fetchTenders(params: { q?: string; limit?: number; offset?: number }) {
  const { data } = await http.get<{ total: number; items: TenderListItem[]; limit: number; offset: number }>(
    '/api/southern-grid/tenders',
    { params }
  )
  return data
}

export async function fetchTenderDetail(id: number) {
  const { data } = await http.get<TenderDetail>(`/api/southern-grid/tenders/${id}`)
  return data
}

