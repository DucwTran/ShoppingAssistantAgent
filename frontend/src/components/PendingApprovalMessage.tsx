import { useState } from "react"
import { QUALITY_WARNING_THRESHOLD } from "../lib/format"
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

  const isLowQuality = data.quality_score !== null && data.quality_score < QUALITY_WARNING_THRESHOLD

  return (
    <div className="max-w-[80%] space-y-3">
      <RecommendationCard recommendation={data.recommendation} />

      <div
        className={
          isLowQuality
            ? "rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
            : "rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
        }
      >
        {data.quality_score !== null && <p>Quality score: {Math.round(data.quality_score * 100)}%</p>}
        {isLowQuality && data.evaluation_feedback && <p className="mt-1">{data.evaluation_feedback}</p>}
      </div>

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
