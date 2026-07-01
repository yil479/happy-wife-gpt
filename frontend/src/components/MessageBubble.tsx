import { useState } from 'react'
import type { Message } from '../hooks/useChat'

interface Props {
  message: Message
  isStreaming?: boolean
}

export default function MessageBubble({ message, isStreaming }: Props) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 12,
    }}>
      <div style={{
        maxWidth: '75%',
        padding: '10px 14px',
        borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isUser ? '#7c5cdb' : '#ffffff',
        color: isUser ? '#fff' : '#2d2d2d',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        lineHeight: 1.55,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {message.content}
        {isStreaming && !isUser && (
          <span style={{ display: 'inline-block', width: 8, height: 14, background: '#7c5cdb', marginLeft: 4, borderRadius: 2, verticalAlign: 'middle', animation: 'blink 1s step-end infinite' }} />
        )}
      </div>

      {!isUser && message.sources && message.sources.length > 0 && (
        <div style={{ maxWidth: '75%', marginTop: 4 }}>
          <button
            onClick={() => setSourcesOpen((o) => !o)}
            style={{ fontSize: 12, color: '#888', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0' }}
          >
            {sourcesOpen ? '▾' : '▸'} {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
          </button>
          {sourcesOpen && (
            <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {message.sources.map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: '#666', background: '#f0ece6', padding: '6px 10px', borderRadius: 8 }}>
                  <span style={{ fontWeight: 600 }}>{s.source}</span>
                  <span style={{ marginLeft: 6, background: '#e0d8d0', borderRadius: 4, padding: '1px 5px' }}>{s.collection}</span>
                  <span style={{ marginLeft: 6, color: '#999' }}>score {s.score.toFixed(2)}</span>
                  <p style={{ marginTop: 4, color: '#555' }}>{s.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
