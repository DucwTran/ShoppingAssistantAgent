interface ErrorBannerProps {
  message: string
  /** Shown only when sending the failed request again can succeed. */
  onRetry?: () => void
  onDismiss: () => void
}

export function ErrorBanner({ message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="max-w-[80%] rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
    >
      <p className="text-sm">{message}</p>
      <div className="mt-3 flex gap-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-amber-600 px-3 py-1.5 text-sm text-white hover:bg-amber-700"
          >
            Try again
          </button>
        )}
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-lg px-3 py-1.5 text-sm text-amber-800 hover:bg-amber-100 dark:text-amber-200 dark:hover:bg-amber-900"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
