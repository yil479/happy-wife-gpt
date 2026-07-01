import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import DocumentUpload from './components/DocumentUpload'

export default function App() {
  const [panelOpen, setPanelOpen] = useState(false)

  return (
    <div style={{ display: 'flex', width: '100%', height: '100dvh' }}>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <ChatWindow panelOpen={panelOpen} onOpenPanel={() => setPanelOpen(true)} />
      </main>
      <aside style={{
        width: panelOpen ? 300 : 0,
        flexShrink: 0,
        borderLeft: panelOpen ? '1px solid #f0d9f5' : 'none',
        background: '#fffdfc',
        padding: panelOpen ? '20px' : '20px 0',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'width 0.28s cubic-bezier(0.4, 0, 0.2, 1), padding 0.28s cubic-bezier(0.4, 0, 0.2, 1)',
      }}>
        <div style={{ width: 260, opacity: panelOpen ? 1 : 0, transition: 'opacity 0.2s ease', height: '100%' }}>
          <DocumentUpload onClose={() => setPanelOpen(false)} />
        </div>
      </aside>
    </div>
  )
}
