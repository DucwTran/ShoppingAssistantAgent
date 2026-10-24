import type { ShoppingResultData } from "../types/shopping"
import { RecommendationCard } from "./RecommendationCard"

interface FinalRecommendationMessageProps {
  data: ShoppingResultData
  rejected: boolean
}

export function FinalRecommendationMessage({ data, rejected }: FinalRecommendationMessageProps) {
  if (!data.recommendation) return null

  return (
    <div className="max-w-[80%] space-y-2">
      <span className="text-xs font-medium tracking-wide text-gray-400 uppercase">
        {rejected ? "Rejection limit reached — not approved" : "Final"}
      </span>
      <div className={rejected ? "opacity-60" : undefined}>
        <RecommendationCard recommendation={data.recommendation} />
      </div>
    </div>
  )
}
