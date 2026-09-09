interface ErrorBannerProps {
  status: number
  code: string
  message: string
  onRetry?: () => void
  onDismiss: () => void
}

export function ErrorBanner({ status, code, message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium">
            {code} ({status})
          </p>
          <p className="mt-1 text-sm">{message}</p>
        </div>
        <button type="button" onClick={onDismiss} className="shrink-0 text-sm text-red-600 hover:underline dark:text-red-300">
          Dismiss
        </button>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700"
        >
          Try again
        </button>
      )}
    </div>
  )
}
