import ChatWindow from './components/ChatWindow'
import DocumentUpload from './components/DocumentUpload'

export default function App() {
  return (
    <div style={{ display: 'flex', width: '100%', height: '100dvh', background: '#f5f0eb' }}>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: '#f5f0eb' }}>
        <ChatWindow />
      </main>
      <aside style={{
        width: 300, flexShrink: 0,
        borderLeft: '1px solid #e0d8d0',
        background: '#faf8f5',
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <DocumentUpload />
      </aside>
    </div>
  )
}
