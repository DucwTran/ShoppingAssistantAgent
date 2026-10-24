import { useState } from "react"
import type { ShoppingResultData } from "../types/shopping"
import { RecommendationCard } from "./RecommendationCard"

interface PendingApprovalMessageProps {
  data: ShoppingResultData
  onApprove: () => void
  onReject: (feedback: string) => void
  busy: boolean
}

export function PendingApprovalMessage({ data, onApprove, onReject, busy }: PendingApprovalMessageProps) {
  const [showFeedbackInput, setShowFeedbackInput] = useState(false)
  const [feedback, setFeedback] = useState("")

  if (!data.recommendation) return null

  return (
    <div className="max-w-[80%] space-y-3">
      <RecommendationCard recommendation={data.recommendation} />

      {!showFeedbackInput ? (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onApprove}
            disabled={busy}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => setShowFeedbackInput(true)}
            disabled={busy}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            Reject
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What should change?"
            disabled={busy}
            className="w-full rounded-lg border border-gray-300 p-2 text-sm dark:border-gray-600 dark:bg-gray-900"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onReject(feedback)}
              disabled={busy || feedback.trim().length === 0}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Confirm reject
            </button>
            <button
              type="button"
              onClick={() => setShowFeedbackInput(false)}
              disabled={busy}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
