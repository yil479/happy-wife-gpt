import { useCallback, useEffect, useRef, useState } from 'react'
import { createSession, getSessionHistory, streamChat } from '../api/client'
import type { Collection, SourceChunk } from '../api/client'

const SESSION_STORAGE_KEY = 'hwg-session-id'

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
  startNewConversation: () => Promise<void>
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const initializedRef = useRef(false)

  const beginFreshSession = useCallback(async () => {
    const res = await createSession()
    sessionIdRef.current = res.session_id
    localStorage.setItem(SESSION_STORAGE_KEY, res.session_id)
    setMessages([])
  }, [])

  useEffect(() => {
    // Guard against React StrictMode's double-invoke in dev, which would
    // otherwise fire two concurrent session-init calls on first mount.
    if (initializedRef.current) return
    initializedRef.current = true

    const storedId = localStorage.getItem(SESSION_STORAGE_KEY)

    if (!storedId) {
      beginFreshSession().catch(() => setError('Could not start session. Is the backend running?'))
      return
    }

    getSessionHistory(storedId)
      .then((res) => {
        sessionIdRef.current = storedId
        setMessages(res.messages.map((m) => ({
          id: crypto.randomUUID(),
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content,
        })))
      })
      .catch(() => beginFreshSession())
      .catch(() => setError('Could not start session. Is the backend running?'))
  }, [beginFreshSession])

  const startNewConversation = useCallback(async () => {
    try {
      await beginFreshSession()
      setError(null)
    } catch {
      setError('Could not start a new conversation. Is the backend running?')
    }
  }, [beginFreshSession])

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

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearError: () => setError(null),
    startNewConversation,
  }
}
