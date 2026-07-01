import { useCallback, useEffect, useRef, useState } from 'react'
import { createSession, streamChat } from '../api/client'
import type { Collection, SourceChunk } from '../api/client'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
}

interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  error: string | null
  sendMessage: (text: string, collection?: Collection) => Promise<void>
  clearError: () => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  useEffect(() => {
    createSession()
      .then((res) => { sessionIdRef.current = res.session_id })
      .catch(() => setError('Could not start session. Is the backend running?'))
  }, [])

  const sendMessage = useCallback(async (text: string, collection: Collection = 'both') => {
    if (!sessionIdRef.current || isStreaming) return

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text }
    const assistantId = crypto.randomUUID()
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '' }

    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setIsStreaming(true)
    setError(null)

    try {
      await streamChat(
        { session_id: sessionIdRef.current, message: text, collection },
        (token) => {
          setMessages((prev) =>
            prev.map((m) => m.id === assistantId ? { ...m, content: m.content + token } : m),
          )
        },
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
      setMessages((prev) => prev.filter((m) => m.id !== assistantId))
    } finally {
      setIsStreaming(false)
    }
  }, [isStreaming])

  return { messages, isStreaming, error, sendMessage, clearError: () => setError(null) }
}
