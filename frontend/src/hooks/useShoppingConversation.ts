import { useState } from "react"
import { ApiError, streamQuery, streamResume, streamRetry } from "../api/shoppingClient"
import type { ConversationStatus, ProgressEvent, ShoppingResultData, ShoppingResponse } from "../types/shopping"

export type ChatTurn =
  | { kind: "user_query"; id: string; text: string }
  | { kind: "user_decision"; id: string; approved: boolean; feedback: string | null }
  | { kind: "agent_result"; id: string; threadId: string; status: ConversationStatus; data: ShoppingResultData }
  | { kind: "error"; id: string; message: string }

export type ConversationPhase = "idle" | "loading" | "pending_approval"

/** A request to the backend; the failed one is kept so the user can retry it. */
type RetryableAction =
  | { kind: "query"; text: string }
  | { kind: "resume"; threadId: string; approved: boolean; feedback: string | null }
  | { kind: "continue"; threadId: string }

interface LastError {
  message: string
  /** Set when retrying can succeed: network failures and server-side outages, not rejected input. */
  retry: RetryableAction | null
}

function newId(): string {
  return crypto.randomUUID()
}

export function useShoppingConversation() {
  const [messages, setMessages] = useState<ChatTurn[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState<ProgressEvent[]>([])
  const [lastError, setLastError] = useState<LastError | null>(null)

  const phase: ConversationPhase = isLoading ? "loading" : activeThreadId ? "pending_approval" : "idle"

  function appendTurn(turn: ChatTurn) {
    setMessages((prev) => [...prev, turn])
  }

  function appendProgress(event: ProgressEvent) {
    setProgress((prev) => [...prev, event])
  }

  function applyResponse(response: ShoppingResponse) {
    appendTurn({
      kind: "agent_result",
      id: newId(),
      threadId: response.thread_id,
      status: response.status,
      data: response.data,
    })
    setActiveThreadId(response.status === "pending_approval" ? response.thread_id : null)
  }

  function applyFailure(error: unknown, action: RetryableAction) {
    const apiError =
      error instanceof ApiError ? error : new ApiError(0, "unknown_error", "Something went wrong.")
    const retryable = apiError.status === 0 || apiError.status >= 500
    // A run that failed on the server is continued from its failed step; a request that never got an
    // answer (network failure) is sent again as it was.
    const retry: RetryableAction | null = !retryable
      ? null
      : apiError.threadId
        ? { kind: "continue", threadId: apiError.threadId }
        : action

    appendTurn({ kind: "error", id: newId(), message: apiError.message })
    // Back to idle whatever failed, so the user is never left without a way forward: they can retry
    // from the error banner or ask something new.
    setActiveThreadId(null)
    setLastError({ message: apiError.message, retry })
  }

  function request(action: RetryableAction): Promise<ShoppingResponse> {
    switch (action.kind) {
      case "query":
        return streamQuery(action.text, appendProgress)
      case "resume":
        return streamResume(action.threadId, action.approved, action.feedback, appendProgress)
      case "continue":
        return streamRetry(action.threadId, appendProgress)
    }
  }

  function send(action: RetryableAction) {
    setIsLoading(true)
    setProgress([])
    setLastError(null)
    request(action)
      .then(applyResponse)
      .catch((error: unknown) => applyFailure(error, action))
      .finally(() => setIsLoading(false))
  }

  function submitQuery(text: string) {
    if (phase !== "idle") return
    appendTurn({ kind: "user_query", id: newId(), text })
    send({ kind: "query", text })
  }

  function resume(approved: boolean, feedback: string | null) {
    if (phase !== "pending_approval" || !activeThreadId) return
    appendTurn({ kind: "user_decision", id: newId(), approved, feedback })
    send({ kind: "resume", threadId: activeThreadId, approved, feedback })
  }

  function retry() {
    if (phase !== "idle" || !lastError?.retry) return
    send(lastError.retry)
  }

  function approve() {
    resume(true, null)
  }

  function reject(feedback: string) {
    resume(false, feedback)
  }

  function dismissError() {
    setLastError(null)
  }

  function startNewConversation() {
    if (phase === "loading") return
    setMessages([])
    setActiveThreadId(null)
    setProgress([])
    setLastError(null)
  }

  return { messages, phase, progress, lastError, submitQuery, approve, reject, retry, dismissError, startNewConversation }
}
