import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { fetchCourses, deleteCourse } from '../api/client'
import type { CourseEntry } from '../types'

const statusConfig: Record<string, { label: string; color: string }> = {
  created: { label: '已创建', color: 'bg-slate-100 text-slate-600' },
  outline_ready: { label: '大纲就绪', color: 'bg-blue-100 text-blue-700' },
  generating: { label: '生成中', color: 'bg-amber-100 text-amber-700' },
  active: { label: '学习中', color: 'bg-green-100 text-green-700' },
  completed: { label: '已完成', color: 'bg-purple-100 text-purple-700' },
}

function formatTime(isoStr: string | null): string {
  if (!isoStr) return '--'
  const d = new Date(isoStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 30) return `${diffDay} 天前`
  return d.toLocaleDateString('zh-CN')
}

export default function CoursesPage() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<CourseEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadCourses = async () => {
    try {
      const list = await fetchCourses()
      setCourses(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCourses()
  }, [])

  const handleDelete = async (e: React.MouseEvent, courseId: string) => {
    e.stopPropagation()
    e.preventDefault()
    if (!confirm('确定要删除这个课程吗？此操作不可恢复。')) return
    try {
      await deleteCourse(courseId)
      setCourses((prev) => prev.filter((c) => c.id !== courseId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        加载中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">我的课程</h1>
          <p className="text-sm text-slate-400 mt-1">
            选择一个课程继续学习，或创建新课程
          </p>
        </div>
        <Link
          to="/courses/new"
          className="bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors text-sm"
        >
          创建新课程
        </Link>
      </div>

      {courses.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-5xl mb-4 text-slate-300">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-600 mb-2">
            欢迎使用 NewLearner
          </h2>
          <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
            NewLearner 是一个 AI 驱动的研究领域学习系统，为你生成 PhD 级别的教材内容、测验和间隔复习卡片。
          </p>
          <button
            onClick={() => navigate('/courses/new')}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            创建第一个课程
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map((course) => {
            const status = statusConfig[course.status] ?? { label: course.status, color: 'bg-slate-100 text-slate-500' }
            const progress = course.total_chapters > 0
              ? Math.round((course.completed_chapters / course.total_chapters) * 100)
              : 0

            return (
              <Link
                key={course.id}
                to={`/courses/${course.id}`}
                className="block bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-md transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-base font-semibold text-slate-800 group-hover:text-blue-600 transition-colors line-clamp-2 flex-1 mr-2">
                    {course.title || course.description || '未命名课程'}
                  </h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${status.color}`}>
                    {status.label}
                  </span>
                </div>

                {course.description && course.title && (
                  <p className="text-xs text-slate-400 mb-3 line-clamp-2">
                    {course.description}
                  </p>
                )}

                {/* Progress bar */}
                {course.total_chapters > 0 && (
                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                      <span>章节进度</span>
                      <span>{course.completed_chapters} / {course.total_chapters}</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div
                        className="bg-blue-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    {formatTime(course.last_accessed || course.updated_at)}
                  </span>
                  <button
                    onClick={(e) => handleDelete(e, course.id)}
                    className="text-xs text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                    title="删除课程"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
