import type {
  ErrorEnvelope,
  QueryRequest,
  ResumeRequest,
  ShoppingResponse,
} from "../types/shopping"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ErrorEnvelope
    return new ApiError(response.status, body.error.code, body.error.message)
  } catch {
    return new ApiError(response.status, "unknown_error", response.statusText || "Request failed")
  }
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the server.")
  }

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  return (await response.json()) as TResponse
}

export function postQuery(query: string): Promise<ShoppingResponse> {
  const body: QueryRequest = { query }
  return postJson<ShoppingResponse>("/api/v1/shopping/query", body)
}

export function postResume(
  threadId: string,
  approved: boolean,
  feedback: string | null,
): Promise<ShoppingResponse> {
  const body: ResumeRequest = { approved, feedback }
  return postJson<ShoppingResponse>(`/api/v1/shopping/resume/${threadId}`, body)
}
