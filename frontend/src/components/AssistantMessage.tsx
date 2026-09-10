interface AssistantMessageProps {
  text: string
}

export function AssistantMessage({ text }: AssistantMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2 text-gray-900 whitespace-pre-wrap dark:bg-gray-800 dark:text-gray-100">
        {text}
      </div>
    </div>
  )
}
