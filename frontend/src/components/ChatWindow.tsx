import { useEffect, useRef, type PropsWithChildren, Children } from "react"

export function ChatWindow({ children }: PropsWithChildren) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const count = Children.count(children)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [count])

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      {children}
      <div ref={bottomRef} />
    </div>
  )
}
