import { formatConfidence, formatPrice } from "../lib/format"
import type { Recommendation } from "../types/shopping"

interface RecommendationCardProps {
  recommendation: Recommendation
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { product_name, price, why_it_fits, tradeoffs, alternative, confidence } = recommendation
  const heading = product_name === "N/A" ? "General guidance" : product_name

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-lg font-semibold">{heading}</h3>
        <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
          {formatConfidence(confidence)} confidence
        </span>
      </div>

      {product_name !== "N/A" && <p className="mt-1 text-sm text-gray-500">{formatPrice(price)}</p>}

      {why_it_fits.length > 0 && (
        <div className="mt-3">
          <h4 className="text-sm font-medium">Why it fits</h4>
          <ul className="mt-1 list-inside list-disc text-sm text-gray-700 dark:text-gray-300">
            {why_it_fits.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      {tradeoffs.length > 0 && (
        <div className="mt-3">
          <h4 className="text-sm font-medium">Tradeoffs</h4>
          <ul className="mt-1 list-inside list-disc text-sm text-gray-700 dark:text-gray-300">
            {tradeoffs.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      {alternative !== null && (
        <div className="mt-3">
          <h4 className="text-sm font-medium">Alternative</h4>
          <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{alternative}</p>
        </div>
      )}
    </div>
  )
}
