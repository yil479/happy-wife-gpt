import { useEffect, useRef, useState } from 'react'
import { useChat } from '../hooks/useChat'
import MessageBubble from './MessageBubble'

interface Props {
  panelOpen: boolean
  onOpenPanel: () => void
}

export default function ChatWindow({ panelOpen, onOpenPanel }: Props) {
  const { messages, isStreaming, error, sendMessage, clearError, startNewConversation } = useChat()
  const [input, setInput] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    sendMessage(text)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px', borderBottom: '1px solid #f5e0ec', background: '#fffdfc',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <h1 style={{ fontSize: 19, fontWeight: 700, color: '#7c3f9e' }}>💌 happy wife gpt</h1>
          <p style={{ fontSize: 12, color: '#b79ac2', marginTop: 2 }}>Your calm, confidential marriage counselor</p>
        </div>

        <div ref={menuRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setMenuOpen((o) => !o)}
            title="Menu"
            style={{
              width: 38, height: 38, borderRadius: '50%', border: '1.5px solid #f0d9f5',
              background: menuOpen ? '#fbeafc' : '#fff', cursor: 'pointer',
              fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 2px 6px rgba(219, 92, 197, 0.12)', transition: 'transform 0.15s ease, background 0.15s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.08)')}
            onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          >
            ⋯
          </button>

          {menuOpen && (
            <div style={{
              position: 'absolute', top: 46, right: 0, minWidth: 190,
              background: '#fff', borderRadius: 16, border: '1px solid #f5e0ec',
              boxShadow: '0 8px 24px rgba(180, 90, 170, 0.18)', padding: 8, zIndex: 10,
            }}>
              <button
                onClick={() => { onOpenPanel(); setMenuOpen(false) }}
                style={{
                  width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 12px', borderRadius: 10, border: 'none', cursor: 'pointer',
                  background: panelOpen ? '#fbeafc' : 'transparent', color: '#7c3f9e',
                  fontSize: 13.5, fontWeight: 600, fontFamily: 'inherit',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#fbeafc')}
                onMouseLeave={(e) => (e.currentTarget.style.background = panelOpen ? '#fbeafc' : 'transparent')}
              >
                📤 Upload Document
              </button>
              <button
                onClick={() => { startNewConversation(); setMenuOpen(false) }}
                style={{
                  width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 12px', borderRadius: 10, border: 'none', cursor: 'pointer',
                  background: 'transparent', color: '#7c3f9e',
                  fontSize: 13.5, fontWeight: 600, fontFamily: 'inherit',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#fbeafc')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                🆕 New Conversation
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#d9b8e0', marginTop: 60 }}>
            <p style={{ fontSize: 36 }}>🌸</p>
            <p style={{ marginTop: 8, color: '#b98fc7', fontWeight: 600 }}>Share what's on your mind.</p>
            <p style={{ fontSize: 13, marginTop: 4, color: '#d9b8e0' }}>Everything stays between us.</p>
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
        <div style={{
          margin: '0 24px 8px', padding: '10px 16px', borderRadius: 14,
          background: '#fff0f0', color: '#c0392b', fontSize: 13,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>{error}</span>
          <button onClick={clearError} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#c0392b', fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} style={{ padding: '12px 24px 20px', borderTop: '1px solid #f5e0ec', background: '#fffdfc', display: 'flex', gap: 10 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) } }}
          placeholder="What's on your mind? (Enter to send, Shift+Enter for newline)"
          rows={2}
          disabled={isStreaming}
          style={{
            flex: 1, resize: 'none', padding: '10px 16px', borderRadius: 18,
            border: '1.5px solid #f0d9f5', fontSize: 14, lineHeight: 1.4,
            outline: 'none', fontFamily: 'inherit',
            background: isStreaming ? '#fdf6fa' : '#fff',
          }}
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          style={{
            padding: '0 22px', borderRadius: 18, border: 'none', cursor: isStreaming ? 'not-allowed' : 'pointer',
            background: isStreaming ? '#f0cbe6' : 'linear-gradient(135deg, #ff8fc0, #b983ff)',
            color: '#fff', fontWeight: 700, fontSize: 14,
            alignSelf: 'flex-end', height: 44, fontFamily: 'inherit',
            boxShadow: isStreaming ? 'none' : '0 3px 10px rgba(185, 100, 220, 0.35)',
            transition: 'transform 0.12s ease',
          }}
          onMouseEnter={(e) => { if (!isStreaming) e.currentTarget.style.transform = 'scale(1.04)' }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)' }}
        >
          {isStreaming ? '…' : 'Send 💜'}
        </button>
      </form>

      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </div>
  )
}
