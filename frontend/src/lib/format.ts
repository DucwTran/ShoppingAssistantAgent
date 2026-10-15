export function formatPrice(price: number | null, currency: string | null): string {
  if (price === null) return "Price unknown"
  return `${new Intl.NumberFormat("vi-VN").format(price)} ${currency ?? "VND"}`
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}
