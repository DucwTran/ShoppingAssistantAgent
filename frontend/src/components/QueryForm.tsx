import { useState, type FormEvent, type KeyboardEvent } from "react"

interface QueryFormProps {
  onSubmit: (query: string) => void
  disabled: boolean
}

export function QueryForm({ onSubmit, disabled }: QueryFormProps) {
  const [value, setValue] = useState("")

  const submit = () => {
    const trimmed = value.trim()
    if (trimmed.length === 0 || disabled) return
    onSubmit(trimmed)
    setValue("")
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Ask about a laptop…"
        rows={1}
        className="flex-1 resize-none rounded-lg border border-gray-300 p-2 text-sm disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900"
      />
      <button
        type="submit"
        disabled={disabled || value.trim().length === 0}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
      >
        Send
      </button>
    </form>
  )
}
