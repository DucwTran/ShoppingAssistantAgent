export type ConversationStatus = "pending_approval" | "done" | "rejected"

export interface Recommendation {
  product_name: string
  price: number | null
  currency: string | null
  url: string | null
  why_it_fits: string[]
  tradeoffs: string[]
  alternative: string | null
  confidence: number
}

export interface ShoppingResultData {
  recommendation: Recommendation | null
  general_reply: string | null
}

export interface ShoppingResponse {
  thread_id: string
  status: ConversationStatus
  data: ShoppingResultData
}

export interface QueryRequest {
  query: string
  /** A finished conversation to continue with a follow-up question; omitted, a new one starts. */
  thread_id?: string | null
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

/**
 * The streaming endpoints' `error` frame: the envelope, the status the JSON endpoint would have returned,
 * and the conversation to pass to the retry endpoint.
 */
export interface StreamErrorFrame extends ErrorEnvelope {
  status: number
  thread_id: string
}

/** One `progress` frame from the streaming endpoints; extra fields depend on the event. */
export interface ProgressEvent {
  event: string
  node: string
  status: "info" | "warning"
  message: string
  tool?: string
  args?: { query?: string }
}
