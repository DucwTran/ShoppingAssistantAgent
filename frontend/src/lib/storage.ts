const STORAGE_KEY = "shopping-assistant.conversation"

export interface StoredConversation<TMessage> {
  threadId: string | null
  messages: TMessage[]
}

export function loadConversation<TMessage>(): StoredConversation<TMessage> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null

    const parsed = JSON.parse(raw) as unknown
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("messages" in parsed) ||
      !Array.isArray((parsed as { messages: unknown }).messages)
    ) {
      return null
    }

    const candidate = parsed as StoredConversation<TMessage>
    return {
      threadId: typeof candidate.threadId === "string" ? candidate.threadId : null,
      messages: candidate.messages,
    }
  } catch {
    return null
  }
}

export function saveConversation<TMessage>(state: StoredConversation<TMessage>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // localStorage can throw in private browsing or when quota is exceeded — losing persistence is acceptable, crashing the app is not
  }
}

export function clearConversation(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // see saveConversation
  }
}
