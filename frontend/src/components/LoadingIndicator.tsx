import { useEffect, useState } from "react"

const PHRASES_BY_ACTION: Record<"query" | "approve" | "reject", string[]> = {
  query: [
    "Analyzing your requirements…",
    "Searching for candidates…",
    "Comparing options…",
    "Double-checking the recommendation…",
  ],
  approve: ["Finalizing…"],
  reject: [
    "Regenerating based on your feedback…",
    "Re-checking candidates…",
    "Double-checking the new recommendation…",
  ],
}

interface LoadingIndicatorProps {
  action: "query" | "approve" | "reject"
}

export function LoadingIndicator({ action }: LoadingIndicatorProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [phraseIndex, setPhraseIndex] = useState(0)
  const phrases = PHRASES_BY_ACTION[action]

  useEffect(() => {
    const timer = setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (phrases.length <= 1) return
    const timer = setInterval(() => setPhraseIndex((i) => (i + 1) % phrases.length), 5500)
    return () => clearInterval(timer)
  }, [phrases])

  return (
    <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      <div className="text-sm text-gray-600 dark:text-gray-300">
        <p>{phrases[phraseIndex]}</p>
        <p className="text-xs text-gray-400">
          {elapsedSeconds}s elapsed — this can take a few minutes.
        </p>
      </div>
    </div>
  )
}
