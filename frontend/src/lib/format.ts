export function formatPrice(price: number | string): string {
  if (typeof price === "string") return "Price unknown"
  return `${new Intl.NumberFormat("en-US").format(price)} VND`
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}
