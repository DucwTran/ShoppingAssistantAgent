import { useMemo, useState } from "react"
import { ApiError, postQuery, postResume } from "../api/shoppingClient"
import type { ConversationStatus, ShoppingResultData, ShoppingResponse } from "../types/shopping"

export type ChatTurn =
  | { kind: "user_query"; id: string; text: string }
  | { kind: "user_decision"; id: string; approved: boolean; feedback: string | null }
  | { kind: "agent_result"; id: string; threadId: string; status: ConversationStatus; data: ShoppingResultData }
  | { kind: "error"; id: string; status: number; code: string; message: string }

export type ConversationPhase = "idle" | "loading" | "pending_approval"

interface ActiveThread {
  threadId: string
  data: ShoppingResultData
}

interface LastError {
  status: number
  code: string
  message: string
}

function newId(): string {
  return crypto.randomUUID()
}

export function useShoppingConversation() {
  const [messages, setMessages] = useState<ChatTurn[]>([])
  const [activeThread, setActiveThread] = useState<ActiveThread | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [lastError, setLastError] = useState<LastError | null>(null)

  const phase: ConversationPhase = isLoading ? "loading" : activeThread ? "pending_approval" : "idle"

  function appendTurn(turn: ChatTurn) {
    setMessages((prev) => [...prev, turn])
  }

  function applyResponse(response: ShoppingResponse) {
    appendTurn({
      kind: "agent_result",
      id: newId(),
      threadId: response.thread_id,
      status: response.status,
      data: response.data,
    })
    setActiveThread(response.status === "pending_approval" ? { threadId: response.thread_id, data: response.data } : null)
  }

  function applyFailure(error: unknown, invalidatesThread: boolean) {
    const apiError =
      error instanceof ApiError ? error : new ApiError(0, "unknown_error", "Something went wrong.")

    appendTurn({ kind: "error", id: newId(), status: apiError.status, code: apiError.code, message: apiError.message })

    if (invalidatesThread && (apiError.status === 404 || apiError.status === 409)) {
      setActiveThread(null)
    }
    setLastError({ status: apiError.status, code: apiError.code, message: apiError.message })
  }

  function submitQuery(text: string) {
    if (phase !== "idle") return
    appendTurn({ kind: "user_query", id: newId(), text })
    setIsLoading(true)
    setLastError(null)
    postQuery(text)
      .then(applyResponse)
      .catch((error: unknown) => applyFailure(error, false))
      .finally(() => setIsLoading(false))
  }

  function resume(approved: boolean, feedback: string | null) {
    if (phase !== "pending_approval" || !activeThread) return
    appendTurn({ kind: "user_decision", id: newId(), approved, feedback })
    setIsLoading(true)
    setLastError(null)
    postResume(activeThread.threadId, approved, feedback)
      .then(applyResponse)
      .catch((error: unknown) => applyFailure(error, true))
      .finally(() => setIsLoading(false))
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
    setActiveThread(null)
    setLastError(null)
  }

  return useMemo(
    () => ({ messages, phase, lastError, submitQuery, approve, reject, dismissError, startNewConversation }),
    [messages, phase, lastError],
  )
}
