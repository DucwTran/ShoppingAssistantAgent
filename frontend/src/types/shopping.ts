export type ConversationStatus = "pending_approval" | "done"

export interface Recommendation {
  product_name: string
  price: number | string
  why_it_fits: string[]
  tradeoffs: string[]
  alternative: string | null
  confidence: number
}

export interface ShoppingResultData {
  recommendation: Recommendation | null
  quality_score: number | null
  evaluation_feedback: string | null
  reflection_count: number
}

export interface ShoppingResponse {
  thread_id: string
  status: ConversationStatus
  data: ShoppingResultData
}

export interface QueryRequest {
  query: string
}

export interface ResumeRequest {
  approved: boolean
  feedback: string | null
}

export interface ErrorDetail {
  code: string
  message: string
}

export interface ErrorEnvelope {
  error: ErrorDetail
}
