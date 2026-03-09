import type {
  AssessmentRequest,
  AssessmentProfile,
  KnowledgeGraph,
  ResearchSynthesis,
  VerificationReport,
  ResourceCollection,
  Quiz,
  QuizResult,
  FlashCard,
  LearnerProgress,
  SSEEvent,
} from '../types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }
  return res.json()
}

// ---- Assessment ----

export async function fetchAssessment(): Promise<AssessmentProfile | null> {
  try {
    return await request<AssessmentProfile>('/assessment')
  } catch {
    return null
  }
}

export async function createAssessment(
  profile: AssessmentRequest
): Promise<AssessmentProfile> {
  return request<AssessmentProfile>('/assessment', {
    method: 'POST',
    body: JSON.stringify(profile),
  })
}

// ---- Status ----

export async function fetchStatus(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>('/status')
}

// ---- Knowledge Graph ----

export async function fetchGraph(field: string): Promise<KnowledgeGraph | null> {
  try {
    return await request<KnowledgeGraph>(`/graph/${encodeURIComponent(field)}`)
  } catch {
    return null
  }
}

export function buildGraph(
  field: string,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void
): () => void {
  const url = `${BASE}/graph/${encodeURIComponent(field)}/build`
  const evtSource = new EventSource(url)

  // Named events from backend
  const namedEvents = ['step_progress', 'step_start', 'complete', 'error']
  for (const evtName of namedEvents) {
    evtSource.addEventListener(evtName, (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data)
        onEvent({ event: evtName, data })
      } catch {
        onEvent({ event: evtName, data: { raw: (e as MessageEvent).data } })
      }
      if (evtName === 'complete') {
        evtSource.close()
        onDone?.()
      }
      if (evtName === 'error') {
        evtSource.close()
        onError?.(new Error(
          (JSON.parse((e as MessageEvent).data) as { message?: string }).message
            ?? 'Graph build stream failed'
        ))
      }
    })
  }

  // Fallback for unnamed events
  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      onEvent({ event: 'message', data })
    } catch {
      onEvent({ event: 'message', data: { raw: e.data } })
    }
  }

  evtSource.onerror = () => {
    evtSource.close()
    onError?.(new Error('Graph build stream connection error'))
  }

  return () => evtSource.close()
}

// ---- Learning Content ----

export async function fetchContent(
  conceptId: string
): Promise<ResearchSynthesis | null> {
  try {
    return await request<ResearchSynthesis>(`/learn/${encodeURIComponent(conceptId)}/content`)
  } catch {
    return null
  }
}

export function streamLearning(
  conceptId: string,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void
): () => void {
  const url = `${BASE}/learn/${encodeURIComponent(conceptId)}/stream`
  const evtSource = new EventSource(url)

  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      onEvent({ event: e.type, data })
    } catch {
      onEvent({ event: 'message', data: { raw: e.data } })
    }
  }

  const stepEvents = [
    'step_start',
    'step_complete',
    'step_progress',
    'complete',
    'error',
  ]

  for (const evtName of stepEvents) {
    evtSource.addEventListener(evtName, (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data)
        onEvent({ event: evtName, data })
      } catch {
        onEvent({ event: evtName, data: { raw: (e as MessageEvent).data } })
      }
      if (evtName === 'complete' || evtName === 'error') {
        evtSource.close()
        if (evtName === 'complete') onDone?.()
        else onError?.(new Error('Learning stream error'))
      }
    })
  }

  evtSource.onerror = () => {
    evtSource.close()
    onError?.(new Error('Learning stream connection error'))
  }

  return () => evtSource.close()
}

// ---- Verification ----

export async function fetchVerification(
  conceptId: string
): Promise<VerificationReport | null> {
  try {
    return await request<VerificationReport>(`/learn/${encodeURIComponent(conceptId)}/verification`)
  } catch {
    return null
  }
}

// ---- Resources ----

export async function fetchResources(
  conceptId: string
): Promise<ResourceCollection | null> {
  try {
    return await request<ResourceCollection>(`/learn/${encodeURIComponent(conceptId)}/resources`)
  } catch {
    return null
  }
}

// ---- Quiz ----

export async function fetchQuiz(conceptId: string): Promise<Quiz> {
  return request<Quiz>(`/quiz/${encodeURIComponent(conceptId)}`)
}

export async function submitQuiz(
  conceptId: string,
  answers: Record<string, string>
): Promise<QuizResult> {
  return request<QuizResult>(`/quiz/${encodeURIComponent(conceptId)}/submit`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

export async function exportQuiz(conceptId: string): Promise<void> {
  const res = await fetch(
    `${BASE}/quiz/${encodeURIComponent(conceptId)}/export`
  )
  if (!res.ok) throw new Error('Export failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `quiz_${conceptId}.md`
  a.click()
  URL.revokeObjectURL(url)
}

// ---- Spaced Repetition ----

export async function fetchDueCards(): Promise<FlashCard[]> {
  return request<FlashCard[]>('/review/due')
}

export async function reviewCard(
  cardId: string,
  rating: number
): Promise<FlashCard> {
  return request<FlashCard>(`/review/${encodeURIComponent(cardId)}`, {
    method: 'POST',
    body: JSON.stringify({ rating }),
  })
}

export async function exportAnki(field: string): Promise<void> {
  const res = await fetch(`${BASE}/review/export-anki/${encodeURIComponent(field)}`)
  if (!res.ok) throw new Error('Anki export failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `anki_${field}.apkg`
  a.click()
  URL.revokeObjectURL(url)
}

// ---- Progress ----

export async function fetchProgress(field: string): Promise<LearnerProgress> {
  return request<LearnerProgress>(`/progress/${encodeURIComponent(field)}`)
}

// ---- Export ----

export async function exportMaterials(
  field: string,
  formats: string[]
): Promise<Record<string, string>> {
  return request<Record<string, string>>(
    `/export/${encodeURIComponent(field)}`,
    {
      method: 'POST',
      body: JSON.stringify({ formats }),
    }
  )
}
