import type { ShoppingResultData } from "../types/shopping"
import { RecommendationCard } from "./RecommendationCard"

interface FinalRecommendationMessageProps {
  data: ShoppingResultData
}

export function FinalRecommendationMessage({ data }: FinalRecommendationMessageProps) {
  if (!data.recommendation) return null

  return (
    <div className="max-w-[80%] space-y-2">
      <span className="text-xs font-medium tracking-wide text-gray-400 uppercase">Final</span>
      <RecommendationCard recommendation={data.recommendation} />
      {data.quality_score !== null && (
        <p className="text-sm text-gray-500">Quality score: {Math.round(data.quality_score * 100)}%</p>
      )}
    </div>
  )
}
