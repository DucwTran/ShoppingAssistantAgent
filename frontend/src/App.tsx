import { ChatWindow } from "./components/ChatWindow"
import { ErrorBanner } from "./components/ErrorBanner"
import { FinalRecommendationMessage } from "./components/FinalRecommendationMessage"
import { LoadingIndicator } from "./components/LoadingIndicator"
import { PendingApprovalMessage } from "./components/PendingApprovalMessage"
import { QueryForm } from "./components/QueryForm"
import { RecommendationCard } from "./components/RecommendationCard"
import { useShoppingConversation, type ChatTurn, type ConversationPhase } from "./hooks/useShoppingConversation"
import { UserMessage } from "./components/UserMessage"

function App() {
  const conversation = useShoppingConversation()
  const { messages, phase, busyAction } = conversation

  return (
    <div className="mx-auto flex h-svh max-w-2xl flex-col">
      <header className="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
        <h1 className="text-lg font-semibold">AI Shopping Assistant</h1>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={conversation.startNewConversation}
            disabled={phase === "loading"}
            className="text-sm text-gray-500 hover:underline disabled:opacity-50"
          >
            New chat
          </button>
        )}
      </header>

      <ChatWindow>
        {messages.map((turn, index) => (
          <TurnView key={turn.id} turn={turn} isLatest={index === messages.length - 1} phase={phase} conversation={conversation} />
        ))}

        {phase === "loading" && busyAction && <LoadingIndicator action={busyAction} />}
      </ChatWindow>

      <footer className="border-t border-gray-200 p-4 dark:border-gray-700">
        <QueryForm onSubmit={conversation.submitQuery} disabled={phase !== "idle"} />
      </footer>
    </div>
  )
}

interface TurnViewProps {
  turn: ChatTurn
  isLatest: boolean
  phase: ConversationPhase
  conversation: ReturnType<typeof useShoppingConversation>
}

function TurnView({ turn, isLatest, phase, conversation }: TurnViewProps) {
  switch (turn.kind) {
    case "user_query":
      return <UserMessage text={turn.text} />

    case "user_decision":
      return (
        <div className="flex justify-end">
          <p className="max-w-[80%] text-sm text-gray-500 italic">
            {turn.approved ? "You approved this recommendation." : `You rejected: "${turn.feedback}"`}
          </p>
        </div>
      )

    case "error":
      if (isLatest && conversation.lastError) {
        return (
          <ErrorBanner
            status={conversation.lastError.status}
            code={conversation.lastError.code}
            message={conversation.lastError.message}
            onRetry={conversation.lastError.retryable ? conversation.retry : undefined}
            onDismiss={conversation.dismissError}
          />
        )
      }
      return <p className="text-sm text-red-400 italic">Error: {turn.message}</p>

    case "agent_result":
      if (turn.status === "done") {
        return <FinalRecommendationMessage data={turn.data} />
      }
      if (isLatest && (phase === "pending_approval" || phase === "loading")) {
        return (
          <PendingApprovalMessage
            data={turn.data}
            onApprove={conversation.approve}
            onReject={conversation.reject}
            busy={phase === "loading"}
          />
        )
      }
      // a pending_approval recommendation that was since rejected and replaced — read-only
      return turn.data.recommendation ? (
        <div className="max-w-[80%] opacity-60">
          <RecommendationCard recommendation={turn.data.recommendation} />
        </div>
      ) : null
  }
}

export default App
