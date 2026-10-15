import type {
  ErrorEnvelope,
  ProgressEvent,
  QueryRequest,
  ResumeRequest,
  ShoppingResponse,
  StreamErrorFrame,
} from "../types/shopping"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"

export class ApiError extends Error {
  status: number
  code: string
  /** Set when a run failed on the server: the conversation can be continued with streamRetry. */
  threadId: string | null

  constructor(status: number, code: string, message: string, threadId: string | null = null) {
    super(message)
    this.status = status
    this.code = code
    this.threadId = threadId
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

function parseFrame(raw: string): { event: string; data: unknown } {
  let event = "message"
  const dataLines: string[] = []
  for (const line of raw.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7)
    else if (line.startsWith("data: ")) dataLines.push(line.slice(6))
  }
  return { event, data: JSON.parse(dataLines.join("\n")) }
}

/**
 * POST to a streaming endpoint and read its server-sent events: `progress` frames go to onProgress,
 * the `result` frame resolves the promise, an `error` frame rejects it. EventSource can't be used
 * because it only supports GET.
 */
async function postStream(
  path: string,
  body: unknown,
  onProgress: (event: ProgressEvent) => void,
): Promise<ShoppingResponse> {
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

  if (!response.ok) throw await parseErrorResponse(response)
  if (!response.body) throw new ApiError(0, "network_error", "The server sent no response body.")

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ""
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value.replaceAll("\r\n", "\n")

      let separator: number
      while ((separator = buffer.indexOf("\n\n")) !== -1) {
        const frame = parseFrame(buffer.slice(0, separator))
        buffer = buffer.slice(separator + 2)

        if (frame.event === "progress") onProgress(frame.data as ProgressEvent)
        else if (frame.event === "result") return frame.data as ShoppingResponse
        else if (frame.event === "error") {
          const { status, thread_id, error } = frame.data as StreamErrorFrame
          throw new ApiError(status ?? 500, error.code, error.message, thread_id ?? null)
        }
      }
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, "network_error", "The connection was interrupted.")
  } finally {
    reader.releaseLock()
  }
  throw new ApiError(0, "stream_incomplete", "The connection closed before a result arrived.")
}

export function streamQuery(query: string, onProgress: (event: ProgressEvent) => void): Promise<ShoppingResponse> {
  const body: QueryRequest = { query }
  return postStream("/api/v1/shopping/query/stream", body, onProgress)
}

export function streamResume(
  threadId: string,
  approved: boolean,
  feedback: string | null,
  onProgress: (event: ProgressEvent) => void,
): Promise<ShoppingResponse> {
  const body: ResumeRequest = { approved, feedback }
  return postStream(`/api/v1/shopping/resume/${threadId}/stream`, body, onProgress)
}

/** Continues a conversation whose last run failed, from the step that failed. */
export function streamRetry(threadId: string, onProgress: (event: ProgressEvent) => void): Promise<ShoppingResponse> {
  return postStream(`/api/v1/shopping/retry/${threadId}/stream`, undefined, onProgress)
}
