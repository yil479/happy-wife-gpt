import { useEffect, useRef, useState } from 'react'
import { deleteDocument, listDocuments, uploadDocument } from '../api/client'
import type { DocumentMeta } from '../api/client'

const ACCEPTED = '.txt,.md,.pdf'

interface Props {
  onClose?: () => void
}

export default function DocumentUpload({ onClose }: Props) {
  const [docs, setDocs] = useState<DocumentMeta[]>([])
  const [collection, setCollection] = useState<'experiences' | 'advice'>('advice')
  const [uploading, setUploading] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function fetchDocs() {
    try {
      const res = await listDocuments('both')
      setDocs(res.documents)
    } catch { /* silently ignore on sidebar */ }
  }

  useEffect(() => { fetchDocs() }, [])

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setFeedback(null)
    try {
      const res = await uploadDocument(file, collection)
      setFeedback({ kind: 'ok', msg: `✓ ${res.filename} — ${res.chunks_stored} chunks indexed` })
      await fetchDocs()
    } catch (err) {
      setFeedback({ kind: 'err', msg: err instanceof Error ? err.message : 'Upload failed' })
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleDelete(doc: DocumentMeta) {
    if (!confirm(`Delete "${doc.filename}"?`)) return
    try {
      await deleteDocument(doc.doc_id, doc.collection as 'experiences' | 'advice')
      setDocs((prev) => prev.filter((d) => d.doc_id !== doc.doc_id))
    } catch (err) {
      setFeedback({ kind: 'err', msg: err instanceof Error ? err.message : 'Delete failed' })
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: '#7c3f9e' }}>📚 Knowledge Base</h2>
          <p style={{ fontSize: 12, color: '#c9a8d1', marginTop: 3 }}>Upload .txt, .md, or .pdf files</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            title="Close"
            style={{
              background: '#fdf6fa', border: '1px solid #f5e0ec', borderRadius: '50%',
              width: 26, height: 26, cursor: 'pointer', color: '#c295cf', fontSize: 13,
              flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >✕</button>
        )}
      </div>

      {/* Collection selector */}
      <div style={{ display: 'flex', gap: 6 }}>
        {(['advice', 'experiences'] as const).map((c) => (
          <button
            key={c}
            onClick={() => setCollection(c)}
            style={{
              flex: 1, padding: '7px 0', borderRadius: 12, border: '1.5px solid',
              borderColor: collection === c ? '#e0a0e8' : '#f5e0ec',
              background: collection === c ? 'linear-gradient(135deg, #ffe3f2, #f0e3ff)' : '#fff',
              color: collection === c ? '#a44fc0' : '#c9a8d1',
              fontWeight: collection === c ? 700 : 500,
              fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* File picker */}
      <label style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 8, padding: '12px 0', borderRadius: 14,
        border: '1.5px dashed #e0a0e8', background: '#fdf6fa',
        cursor: uploading ? 'not-allowed' : 'pointer', fontSize: 13, color: '#a44fc0', fontWeight: 600,
      }}>
        {uploading ? 'Uploading…' : '💗 Choose file'}
        <input ref={fileRef} type="file" accept={ACCEPTED} onChange={handleUpload} disabled={uploading} style={{ display: 'none' }} />
      </label>

      {/* Feedback */}
      {feedback && (
        <div style={{
          fontSize: 12, padding: '8px 10px', borderRadius: 12,
          background: feedback.kind === 'ok' ? '#f0faf0' : '#fff0f0',
          color: feedback.kind === 'ok' ? '#2e7d32' : '#c0392b',
        }}>
          {feedback.msg}
        </div>
      )}

      {/* Document list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {docs.length === 0 && (
          <p style={{ fontSize: 12, color: '#e2c5e8', textAlign: 'center', marginTop: 24 }}>No documents yet 🌷</p>
        )}
        {docs.map((doc) => (
          <div key={doc.doc_id} style={{
            padding: '10px 12px', borderRadius: 14, background: '#fff',
            border: '1px solid #f5e0ec', fontSize: 12,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 700, color: '#4a3b52', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</p>
                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  <span style={{ background: '#f0ecfb', color: '#7c5cdb', borderRadius: 6, padding: '1px 6px' }}>{doc.collection}</span>
                  <span style={{ color: '#c9a8d1' }}>{doc.chunk_count} chunks</span>
                  <span style={{ color: '#c9a8d1' }}>{new Date(doc.ingested_at).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc)}
                style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: '#e2c5e8', fontSize: 16, lineHeight: 1, flexShrink: 0 }}
                title="Delete"
              >✕</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
