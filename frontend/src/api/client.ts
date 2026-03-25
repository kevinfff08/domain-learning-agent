import type {
  AssessmentRequest,
  AssessmentProfile,
  CourseEntry,
  Textbook,
  ResearchSynthesis,
  VerificationReport,
  ResourceCollection,
  QuizResult,
  FlashCard,
  LearnerProgress,
  ExportResponse,
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
    let detail: string | null = null
    try {
      const parsed = JSON.parse(body) as { detail?: string }
      detail = parsed.detail ?? null
    } catch {}
    throw new Error(detail ?? `API error ${res.status}: ${body}`)
  }
  return res.json()
}

/** Generic SSE stream helper */
function sseStream(
  url: string,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void,
): () => void {
  const evtSource = new EventSource(url)

  const namedEvents = ['step_progress', 'step_start', 'step_complete', 'chapter_complete', 'paused', 'complete', 'error']
  for (const evtName of namedEvents) {
    evtSource.addEventListener(evtName, (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data)
        onEvent({ event: evtName, data })
      } catch {
        onEvent({ event: evtName, data: { raw: (e as MessageEvent).data } })
      }
      if (evtName === 'complete' || evtName === 'paused') {
        evtSource.close()
        onDone?.()
      }
      if (evtName === 'error') {
        evtSource.close()
        onError?.(new Error(
          (JSON.parse((e as MessageEvent).data) as { message?: string }).message
            ?? 'Stream failed'
        ))
      }
    })
  }

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
    onError?.(new Error('Stream connection error'))
  }

  return () => evtSource.close()
}

// ---- Status ----
export async function fetchStatus(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>('/status')
}

export async function fetchBootTime(): Promise<number> {
  const res = await request<{ boot_time: number }>('/boot-time')
  return res.boot_time
}

// ---- Assessment ----
export async function fetchAssessment(): Promise<AssessmentProfile | null> {
  try { return await request<AssessmentProfile>('/assessment') } catch { return null }
}

export async function createAssessment(profile: AssessmentRequest): Promise<AssessmentProfile> {
  return request<AssessmentProfile>('/assessment', {
    method: 'POST',
    body: JSON.stringify(profile),
  })
}

// ---- Courses ----
export async function fetchCourses(): Promise<CourseEntry[]> {
  const res = await request<{ courses: CourseEntry[] }>('/courses')
  return res.courses
}

export async function createCourse(data: AssessmentRequest): Promise<{ course: CourseEntry; profile: AssessmentProfile }> {
  return request('/courses', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function fetchCourse(courseId: string): Promise<CourseEntry> {
  return request<CourseEntry>(`/courses/${encodeURIComponent(courseId)}`)
}

export async function deleteCourse(courseId: string): Promise<void> {
  await request(`/courses/${encodeURIComponent(courseId)}`, { method: 'DELETE' })
}

// ---- Textbook ----
export async function fetchTextbook(courseId: string): Promise<Textbook | null> {
  try {
    return await request<Textbook>(`/courses/${encodeURIComponent(courseId)}/textbook`)
  } catch { return null }
}

export function buildOutline(
  courseId: string,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void,
): () => void {
  return sseStream(`${BASE}/courses/${encodeURIComponent(courseId)}/textbook/build`, onEvent, onDone, onError)
}

export function generateAllChapters(
  courseId: string,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void,
): () => void {
  return sseStream(`${BASE}/courses/${encodeURIComponent(courseId)}/textbook/generate`, onEvent, onDone, onError)
}

export async function pauseBatchGeneration(courseId: string): Promise<void> {
  await request(`/courses/${encodeURIComponent(courseId)}/textbook/generate/pause`, {
    method: 'POST',
  })
}

// ---- Chapters ----
export async function fetchChapterContent(
  courseId: string,
  chapterId: string,
): Promise<{ synthesis: ResearchSynthesis; resources?: ResourceCollection; verification?: VerificationReport } | null> {
  try {
    return await request(`/courses/${encodeURIComponent(courseId)}/chapters/${encodeURIComponent(chapterId)}`)
  } catch { return null }
}

export async function deleteChapterContent(
  courseId: string,
  chapterId: string,
): Promise<void> {
  await request(`/courses/${encodeURIComponent(courseId)}/chapters/${encodeURIComponent(chapterId)}`, {
    method: 'DELETE',
  })
}

export function streamChapter(
  courseId: string,
  chapterId: string,
  onEvent: (event: SSEEvent) => void,
  onDone?: () => void,
  onError?: (err: Error) => void,
): () => void {
  return sseStream(
    `${BASE}/courses/${encodeURIComponent(courseId)}/chapters/${encodeURIComponent(chapterId)}/stream`,
    onEvent, onDone, onError,
  )
}

// ---- Quiz (course-scoped) ----
export async function submitQuiz(
  courseId: string,
  chapterId: string,
  answers: Record<string, string>,
): Promise<QuizResult> {
  return request<QuizResult>(
    `/courses/${encodeURIComponent(courseId)}/chapters/${encodeURIComponent(chapterId)}/quiz/submit`,
    { method: 'POST', body: JSON.stringify({ answers }) },
  )
}

// ---- Spaced Repetition (course-scoped) ----
export async function fetchDueCards(courseId: string, chapterId?: string): Promise<{ count: number; cards: FlashCard[] }> {
  let url = `/courses/${encodeURIComponent(courseId)}/review/due`
  if (chapterId) url += `?chapter_id=${encodeURIComponent(chapterId)}`
  return request(url)
}

export async function reviewCard(
  courseId: string,
  cardId: string,
  rating: number,
  chapterId: string,
): Promise<Record<string, unknown>> {
  return request(`/courses/${encodeURIComponent(courseId)}/review/${encodeURIComponent(cardId)}`, {
    method: 'POST',
    body: JSON.stringify({ rating, chapter_id: chapterId }),
  })
}

// ---- Progress (course-scoped) ----
export async function fetchProgress(courseId: string): Promise<LearnerProgress> {
  return request<LearnerProgress>(`/courses/${encodeURIComponent(courseId)}/progress`)
}

// ---- Export (course-scoped) ----
export async function exportMaterials(
  courseId: string,
  formats: string[],
): Promise<ExportResponse> {
  return request<ExportResponse>(
    `/courses/${encodeURIComponent(courseId)}/export`,
    { method: 'POST', body: JSON.stringify({ formats }) },
  )
}

// ---- Socratic dialogue ----
export async function advanceSocratic(
  courseId: string,
  chapterId: string,
  studentAnswer: string,
  currentStep: number,
  dialogue: Record<string, unknown>[],
): Promise<Record<string, unknown>> {
  return request(`/courses/${encodeURIComponent(courseId)}/chapters/${encodeURIComponent(chapterId)}/socratic`, {
    method: 'POST',
    body: JSON.stringify({ student_answer: studentAnswer, current_step: currentStep, dialogue }),
  })
}
