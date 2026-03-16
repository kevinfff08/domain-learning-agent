import { NavLink, Outlet, Link } from 'react-router-dom'
import { CourseProvider, useCourse } from '../contexts/CourseContext'

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-slate-300',
    generating: 'bg-amber-400 animate-pulse',
    interrupted: 'bg-orange-400',
    ready: 'bg-blue-400',
    in_progress: 'bg-yellow-400',
    completed: 'bg-green-400',
  }
  return <span className={`w-2 h-2 rounded-full flex-shrink-0 ${colors[status] ?? 'bg-slate-300'}`} />
}

function CourseSidebar() {
  const { courseId, course, textbook, loading } = useCourse()

  if (loading) {
    return (
      <aside className="fixed left-0 top-0 h-screen w-56 bg-slate-900 text-slate-100 flex flex-col z-50">
        <div className="px-4 py-5 border-b border-slate-700">
          <h1 className="text-lg font-bold tracking-wide">NewLearner</h1>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <span className="text-sm text-slate-500">加载中...</span>
        </div>
      </aside>
    )
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-slate-900 text-slate-100 flex flex-col z-50">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-700">
        <Link to="/" className="text-lg font-bold tracking-wide hover:text-blue-300 transition-colors">
          NewLearner
        </Link>
        {course && (
          <p className="text-xs text-slate-400 mt-1 truncate" title={course.title}>
            {course.title || course.description}
          </p>
        )}
      </div>

      {/* Chapter list */}
      <div className="flex-1 overflow-y-auto py-3">
        {textbook && textbook.chapters.length > 0 ? (
          <div>
            <p className="px-4 text-xs text-slate-500 uppercase tracking-wider mb-2">
              章节
            </p>
            <nav className="space-y-0.5">
              {textbook.chapters.map((ch) => (
                <NavLink
                  key={ch.id}
                  to={`/courses/${courseId}/chapters/${ch.id}`}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 text-xs transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  <StatusDot status={ch.status} />
                  <span className="text-slate-500 w-5 text-right flex-shrink-0">
                    {ch.chapter_number}
                  </span>
                  <span className="truncate">{ch.title}</span>
                </NavLink>
              ))}
            </nav>
          </div>
        ) : (
          <div className="px-4 py-6 text-center">
            <p className="text-xs text-slate-500">尚未构建大纲</p>
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="border-t border-slate-700 py-3 space-y-0.5">
        <NavLink
          to={`/courses/${courseId}`}
          end
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white font-medium'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`
          }
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <span>教材总览</span>
        </NavLink>
        <NavLink
          to={`/courses/${courseId}/review`}
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white font-medium'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`
          }
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>间隔复习</span>
        </NavLink>
        <NavLink
          to={`/courses/${courseId}/progress`}
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white font-medium'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`
          }
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span>学习进度</span>
        </NavLink>
        <NavLink
          to={`/courses/${courseId}/export`}
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-blue-600 text-white font-medium'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`
          }
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>导出资料</span>
        </NavLink>
      </div>

      {/* Back to courses */}
      <div className="px-4 py-3 border-t border-slate-700">
        <Link
          to="/"
          className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          返回课程列表
        </Link>
      </div>
    </aside>
  )
}

export default function CourseLayout() {
  return (
    <CourseProvider>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <CourseSidebar />
        <main className="ml-56 min-h-screen p-8">
          <Outlet />
        </main>
      </div>
    </CourseProvider>
  )
}
