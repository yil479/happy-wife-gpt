import { useEffect, useRef, useState } from 'react'
import { deleteDocument, listDocuments, uploadDocument } from '../api/client'
import type { DocumentMeta } from '../api/client'

const ACCEPTED = '.txt,.md,.pdf'

export default function DocumentUpload() {
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
      <div>
        <h2 style={{ fontSize: 14, fontWeight: 700, color: '#555', textTransform: 'uppercase', letterSpacing: 0.5 }}>Knowledge Base</h2>
        <p style={{ fontSize: 12, color: '#aaa', marginTop: 3 }}>Upload .txt, .md, or .pdf files</p>
      </div>

      {/* Collection selector */}
      <div style={{ display: 'flex', gap: 6 }}>
        {(['advice', 'experiences'] as const).map((c) => (
          <button
            key={c}
            onClick={() => setCollection(c)}
            style={{
              flex: 1, padding: '6px 0', borderRadius: 8, border: '1.5px solid',
              borderColor: collection === c ? '#7c5cdb' : '#e0d8d0',
              background: collection === c ? '#f0ecfb' : '#fff',
              color: collection === c ? '#7c5cdb' : '#888',
              fontWeight: collection === c ? 600 : 400,
              fontSize: 12, cursor: 'pointer',
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* File picker */}
      <label style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 8, padding: '10px 0', borderRadius: 10,
        border: '1.5px dashed #c5b8e8', background: '#faf8ff',
        cursor: uploading ? 'not-allowed' : 'pointer', fontSize: 13, color: '#7c5cdb',
      }}>
        {uploading ? 'Uploading…' : '＋ Choose file'}
        <input ref={fileRef} type="file" accept={ACCEPTED} onChange={handleUpload} disabled={uploading} style={{ display: 'none' }} />
      </label>

      {/* Feedback */}
      {feedback && (
        <div style={{
          fontSize: 12, padding: '8px 10px', borderRadius: 8,
          background: feedback.kind === 'ok' ? '#f0faf0' : '#fff0f0',
          color: feedback.kind === 'ok' ? '#2e7d32' : '#c0392b',
        }}>
          {feedback.msg}
        </div>
      )}

      {/* Document list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {docs.length === 0 && (
          <p style={{ fontSize: 12, color: '#ccc', textAlign: 'center', marginTop: 24 }}>No documents yet</p>
        )}
        {docs.map((doc) => (
          <div key={doc.doc_id} style={{
            padding: '10px 12px', borderRadius: 10, background: '#fff',
            border: '1px solid #e0d8d0', fontSize: 12,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 600, color: '#2d2d2d', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</p>
                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  <span style={{ background: '#f0ecfb', color: '#7c5cdb', borderRadius: 4, padding: '1px 6px' }}>{doc.collection}</span>
                  <span style={{ color: '#aaa' }}>{doc.chunk_count} chunks</span>
                  <span style={{ color: '#aaa' }}>{new Date(doc.ingested_at).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc)}
                style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: '#ccc', fontSize: 16, lineHeight: 1, flexShrink: 0 }}
                title="Delete"
              >✕</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
