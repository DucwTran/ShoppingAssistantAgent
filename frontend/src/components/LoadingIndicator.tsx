import type { ProgressEvent } from "../types/shopping"

const NODE_LABELS: Record<string, string> = {
  understand: "Phân tích yêu cầu",
  research_agent: "Tìm kiếm sản phẩm",
  extract_products: "Trích xuất thông tin sản phẩm",
  recommend: "Chọn sản phẩm phù hợp",
  feedback_router: "Xử lý góp ý",
}

interface LoadingIndicatorProps {
  progress: ProgressEvent[]
}

/** Pipeline steps seen so far, in order, with the tool queries the research agent ran under its step. */
function stepsFrom(progress: ProgressEvent[]): { node: string; details: string[] }[] {
  const steps: { node: string; details: string[] }[] = []
  for (const event of progress) {
    if (!(event.node in NODE_LABELS)) continue
    let step = steps.at(-1)
    if (step?.node !== event.node) {
      step = { node: event.node, details: [] }
      steps.push(step)
    }
    if (event.event === "tool_called" && event.args?.query) step.details.push(`${event.tool}: “${event.args.query}”`)
    if (event.event === "research_fallback") step.details.push("Không có kết quả, đang tìm trực tiếp…")
  }
  return steps
}

export function LoadingIndicator({ progress }: LoadingIndicatorProps) {
  const steps = stepsFrom(progress)

  return (
    <div className="space-y-2 rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
      {steps.length === 0 && <Step label="Đang xử lý…" active />}
      {steps.map((step, index) => (
        <div key={index}>
          <Step label={NODE_LABELS[step.node]} active={index === steps.length - 1} />
          {step.details.map((detail, detailIndex) => (
            <p key={detailIndex} className="ml-7 truncate text-xs text-gray-500 dark:text-gray-400">
              {detail}
            </p>
          ))}
        </div>
      ))}
    </div>
  )
}

function Step({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center gap-3">
      {active ? (
        <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      ) : (
        <span className="w-4 shrink-0 text-center text-sm text-green-600">✓</span>
      )}
      <p className={`text-sm ${active ? "text-gray-700 dark:text-gray-200" : "text-gray-500 dark:text-gray-400"}`}>
        {label}
      </p>
    </div>
  )
}
