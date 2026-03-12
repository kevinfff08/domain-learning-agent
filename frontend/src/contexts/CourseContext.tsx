import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import type { Textbook, CourseEntry } from '../types'
import { fetchTextbook, fetchCourse } from '../api/client'

interface CourseContextType {
  courseId: string
  course: CourseEntry | null
  textbook: Textbook | null
  loading: boolean
  refreshTextbook: () => Promise<void>
  refreshCourse: () => Promise<void>
}

const CourseContext = createContext<CourseContextType | null>(null)

export function CourseProvider({ children }: { children: ReactNode }) {
  const { courseId } = useParams<{ courseId: string }>()
  const [course, setCourse] = useState<CourseEntry | null>(null)
  const [textbook, setTextbook] = useState<Textbook | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshTextbook = async () => {
    if (!courseId) return
    const tb = await fetchTextbook(courseId)
    setTextbook(tb)
  }

  const refreshCourse = async () => {
    if (!courseId) return
    try {
      const c = await fetchCourse(courseId)
      setCourse(c)
    } catch { /* ignore */ }
  }

  useEffect(() => {
    if (!courseId) return
    setLoading(true)
    Promise.all([refreshCourse(), refreshTextbook()]).finally(() => setLoading(false))
  }, [courseId])

  return (
    <CourseContext.Provider value={{ courseId: courseId || '', course, textbook, loading, refreshTextbook, refreshCourse }}>
      {children}
    </CourseContext.Provider>
  )
}

export function useCourse() {
  const ctx = useContext(CourseContext)
  if (!ctx) throw new Error('useCourse must be inside CourseProvider')
  return ctx
}
