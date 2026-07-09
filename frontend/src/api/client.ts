const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'
const API_KEY = (import.meta.env.VITE_API_KEY as string) || ''

// ---- Types (mirroring backend Pydantic schemas) ----

export type Collection = 'experiences' | 'advice' | 'both'

export interface SessionResponse {
  session_id: string
}

export interface SourceChunk {
  text: string
  score: number
  source: string
  collection: string
}

export interface ChatResponse {
  session_id: string
  answer: string
  sources: SourceChunk[]
}

export interface ChatHistoryMessage {
  role: string
  content: string
  created_at: string
  sources?: SourceChunk[]
}

export interface SessionHistoryResponse {
  messages: ChatHistoryMessage[]
}

export interface ChatRequest {
  session_id: string
  message: string
  collection?: Collection
  stream?: boolean
}

export interface IngestResponse {
  status: string
  doc_id: string
  filename: string
  collection: string
  chunks_stored: number
}

export interface DocumentMeta {
  doc_id: string
  filename: string
  collection: string
  ingested_at: string
  chunk_count: number
}

export interface DocumentListResponse {
  documents: DocumentMeta[]
}

// ---- Helpers ----

function authHeaders(): Record<string, string> {
  const h: Record<string, string> = {}
  if (API_KEY) h['X-API-Key'] = API_KEY
  return h
}

async function checkResponse(res: Response): Promise<void> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json() as { detail?: string }
      if (body.detail) detail = body.detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }
}

// ---- API functions ----

export async function createSession(): Promise<SessionResponse> {
  const res = await fetch(`${BASE_URL}/sessions`, {
    method: 'POST',
    headers: authHeaders(),
  })
  await checkResponse(res)
  return res.json() as Promise<SessionResponse>
}

export async function getSessionHistory(sessionId: string): Promise<SessionHistoryResponse> {
  const res = await fetch(`${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/history`, {
    headers: authHeaders(),
  })
  await checkResponse(res)
  return res.json() as Promise<SessionHistoryResponse>
}

export async function streamChat(
  req: ChatRequest,
  onToken: (token: string) => void,
): Promise<SourceChunk[]> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ ...req, stream: true }),
  })
  await checkResponse(res)

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let sources: SourceChunk[] = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()
      if (data === '[DONE]') return sources
      try {
        const parsed = JSON.parse(data) as { token?: string; sources?: SourceChunk[] }
        if (parsed.sources) {
          sources = parsed.sources
        } else if (typeof parsed.token === 'string') {
          onToken(parsed.token)
        }
      } catch { /* ignore malformed lines */ }
    }
  }
  return sources
}

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ ...req, stream: false }),
  })
  await checkResponse(res)
  return res.json() as Promise<ChatResponse>
}

export async function uploadDocument(
  file: File,
  collection: 'experiences' | 'advice',
): Promise<IngestResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/ingest?collection=${collection}`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  await checkResponse(res)
  return res.json() as Promise<IngestResponse>
}

export async function listDocuments(
  collection: Collection = 'both',
): Promise<DocumentListResponse> {
  const res = await fetch(`${BASE_URL}/documents?collection=${collection}`, {
    headers: authHeaders(),
  })
  await checkResponse(res)
  return res.json() as Promise<DocumentListResponse>
}

export async function deleteDocument(
  docId: string,
  collection: 'experiences' | 'advice',
): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/documents/${encodeURIComponent(docId)}?collection=${collection}`,
    { method: 'DELETE', headers: authHeaders() },
  )
  await checkResponse(res)
}
