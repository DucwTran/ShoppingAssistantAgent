interface UserMessageProps {
  text: string
}

export function UserMessage({ text }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2 text-white whitespace-pre-wrap">
        {text}
      </div>
    </div>
  )
}
