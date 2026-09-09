import { useEffect, useMemo, useState } from "react"
import { ApiError, postQuery, postResume } from "../api/shoppingClient"
import { clearConversation, loadConversation, saveConversation, type StoredConversation } from "../lib/storage"
import type { ConversationStatus, ShoppingResultData, ShoppingResponse } from "../types/shopping"

export type ChatTurn =
  | { kind: "user_query"; id: string; text: string }
  | { kind: "user_decision"; id: string; approved: boolean; feedback: string | null }
  | { kind: "agent_result"; id: string; threadId: string; status: ConversationStatus; data: ShoppingResultData }
  | { kind: "error"; id: string; status: number; code: string; message: string }

export type ConversationPhase = "idle" | "loading" | "pending_approval"
export type BusyAction = "query" | "approve" | "reject"

interface ActiveThread {
  threadId: string
  data: ShoppingResultData
}

interface LastError {
  status: number
  code: string
  message: string
  retryable: boolean
}

function newId(): string {
  return crypto.randomUUID()
}

function restoreActiveThread(stored: StoredConversation<ChatTurn> | null): ActiveThread | null {
  if (!stored?.threadId) return null
  const lastResult = [...stored.messages].reverse().find((m) => m.kind === "agent_result")
  if (!lastResult || lastResult.kind !== "agent_result") return null
  if (lastResult.threadId !== stored.threadId || lastResult.status !== "pending_approval") return null
  return { threadId: lastResult.threadId, data: lastResult.data }
}

export function useShoppingConversation() {
  const [messages, setMessages] = useState<ChatTurn[]>(() => loadConversation<ChatTurn>()?.messages ?? [])
  const [activeThread, setActiveThread] = useState<ActiveThread | null>(() =>
    restoreActiveThread(loadConversation<ChatTurn>()),
  )
  const [isLoading, setIsLoading] = useState(false)
  const [busyAction, setBusyAction] = useState<BusyAction | null>(null)
  const [lastError, setLastError] = useState<LastError | null>(null)
  const [retryAction, setRetryAction] = useState<(() => void) | null>(null)

  useEffect(() => {
    saveConversation({ threadId: activeThread?.threadId ?? null, messages })
  }, [activeThread, messages])

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

  function applyFailure(error: unknown, retryFn: () => void, invalidatesThread: boolean) {
    const apiError =
      error instanceof ApiError ? error : new ApiError(0, "unknown_error", "Something went wrong.")

    appendTurn({ kind: "error", id: newId(), status: apiError.status, code: apiError.code, message: apiError.message })

    const isClientRejection = apiError.status === 400 || apiError.status === 404 || apiError.status === 409
    if (invalidatesThread && (apiError.status === 404 || apiError.status === 409)) {
      setActiveThread(null)
    }
    setLastError({ status: apiError.status, code: apiError.code, message: apiError.message, retryable: !isClientRejection })
    setRetryAction(isClientRejection ? null : () => retryFn)
  }

  function runQuery(text: string) {
    setIsLoading(true)
    setBusyAction("query")
    setLastError(null)
    setRetryAction(null)

    const attempt = () => {
      setIsLoading(true)
      postQuery(text)
        .then((response) => {
          applyResponse(response)
          setIsLoading(false)
        })
        .catch((error: unknown) => {
          setIsLoading(false)
          applyFailure(error, attempt, false)
        })
    }
    attempt()
  }

  function runResume(approved: boolean, feedback: string | null) {
    if (!activeThread) return
    const threadId = activeThread.threadId

    setIsLoading(true)
    setBusyAction(approved ? "approve" : "reject")
    setLastError(null)
    setRetryAction(null)

    const attempt = () => {
      setIsLoading(true)
      postResume(threadId, approved, feedback)
        .then((response) => {
          applyResponse(response)
          setIsLoading(false)
        })
        .catch((error: unknown) => {
          setIsLoading(false)
          applyFailure(error, attempt, true)
        })
    }
    attempt()
  }

  function submitQuery(text: string) {
    if (phase !== "idle") return
    appendTurn({ kind: "user_query", id: newId(), text })
    runQuery(text)
  }

  function approve() {
    if (phase !== "pending_approval") return
    appendTurn({ kind: "user_decision", id: newId(), approved: true, feedback: null })
    runResume(true, null)
  }

  function reject(feedback: string) {
    if (phase !== "pending_approval") return
    appendTurn({ kind: "user_decision", id: newId(), approved: false, feedback })
    runResume(false, feedback)
  }

  function dismissError() {
    setLastError(null)
    setRetryAction(null)
  }

  function retry() {
    retryAction?.()
  }

  function startNewConversation() {
    if (phase === "loading") return
    clearConversation()
    setMessages([])
    setActiveThread(null)
    setLastError(null)
    setRetryAction(null)
  }

  return useMemo(
    () => ({ messages, phase, busyAction, lastError, submitQuery, approve, reject, dismissError, retry, startNewConversation }),
    [messages, phase, busyAction, lastError],
  )
}
