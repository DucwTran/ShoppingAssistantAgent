export function LoadingIndicator() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      <p className="text-sm text-gray-600 dark:text-gray-300">Đang xử lý…</p>
    </div>
  )
}
