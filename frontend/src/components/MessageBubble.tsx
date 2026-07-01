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
        padding: '11px 16px',
        borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
        background: isUser ? 'linear-gradient(135deg, #ff8fc0, #b983ff)' : '#ffffff',
        color: isUser ? '#fff' : '#4a3b52',
        boxShadow: isUser ? '0 3px 10px rgba(185, 100, 220, 0.25)' : '0 2px 8px rgba(200, 150, 200, 0.12)',
        border: isUser ? 'none' : '1px solid #f5e0ec',
        lineHeight: 1.55,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {message.content}
        {isStreaming && !isUser && (
          <span style={{ display: 'inline-block', width: 8, height: 14, background: '#b983ff', marginLeft: 4, borderRadius: 2, verticalAlign: 'middle', animation: 'blink 1s step-end infinite' }} />
        )}
      </div>

      {!isUser && message.sources && message.sources.length > 0 && (
        <div style={{ maxWidth: '75%', marginTop: 4 }}>
          <button
            onClick={() => setSourcesOpen((o) => !o)}
            style={{ fontSize: 12, color: '#c295cf', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0', fontFamily: 'inherit', fontWeight: 600 }}
          >
            {sourcesOpen ? '▾' : '▸'} {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
          </button>
          {sourcesOpen && (
            <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {message.sources.map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: '#7a6482', background: '#fdf6fa', padding: '8px 12px', borderRadius: 12, border: '1px solid #f5e0ec' }}>
                  <span style={{ fontWeight: 700, color: '#7c3f9e' }}>{s.source}</span>
                  <span style={{ marginLeft: 6, background: '#f0ecfb', color: '#7c5cdb', borderRadius: 6, padding: '1px 6px' }}>{s.collection}</span>
                  <span style={{ marginLeft: 6, color: '#c9a8d1' }}>score {s.score.toFixed(2)}</span>
                  <p style={{ marginTop: 4, color: '#6d5a75' }}>{s.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
