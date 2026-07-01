import { useEffect, useRef, useState } from 'react'
import { useChat } from '../hooks/useChat'
import MessageBubble from './MessageBubble'

export default function ChatWindow() {
  const { messages, isStreaming, error, sendMessage, clearError } = useChat()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    sendMessage(text)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0 0 0 0' }}>
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #e0d8d0', background: '#fff' }}>
        <h1 style={{ fontSize: 17, fontWeight: 600, color: '#2d2d2d' }}>happy-wife-gpt</h1>
        <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Your calm, confidential marriage counselor</p>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#bbb', marginTop: 60 }}>
            <p style={{ fontSize: 32 }}>💬</p>
            <p style={{ marginTop: 8 }}>Share what's on your mind.</p>
            <p style={{ fontSize: 13, marginTop: 4 }}>Everything stays between us.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={m.id}
            message={m}
            isStreaming={isStreaming && i === messages.length - 1 && m.role === 'assistant'}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div style={{ padding: '10px 24px', background: '#fff0f0', color: '#c0392b', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#c0392b', fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} style={{ padding: '12px 24px 20px', borderTop: '1px solid #e0d8d0', background: '#fff', display: 'flex', gap: 10 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) } }}
          placeholder="What's on your mind? (Enter to send, Shift+Enter for newline)"
          rows={2}
          disabled={isStreaming}
          style={{
            flex: 1, resize: 'none', padding: '10px 14px', borderRadius: 12,
            border: '1.5px solid #e0d8d0', fontSize: 14, lineHeight: 1.4,
            outline: 'none', fontFamily: 'inherit',
            background: isStreaming ? '#faf8f5' : '#fff',
          }}
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          style={{
            padding: '0 20px', borderRadius: 12, border: 'none', cursor: isStreaming ? 'not-allowed' : 'pointer',
            background: isStreaming ? '#c5b8e8' : '#7c5cdb', color: '#fff', fontWeight: 600, fontSize: 14,
            alignSelf: 'flex-end', height: 42,
          }}
        >
          {isStreaming ? '…' : 'Send'}
        </button>
      </form>

      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </div>
  )
}
