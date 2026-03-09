import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { fetchAssessment } from '../api/client'

interface NavItem {
  to: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { to: '/', label: '首页', icon: '🏠' },
  { to: '/assess', label: '能力评估', icon: '📋' },
  { to: '/graph', label: '知识图谱', icon: '🔗' },
  { to: '/progress', label: '学习进度', icon: '📊' },
  { to: '/review', label: '间隔复习', icon: '🔄' },
  { to: '/export', label: '导出资料', icon: '📦' },
]

export default function Sidebar() {
  const [fieldName, setFieldName] = useState<string | null>(null)

  useEffect(() => {
    fetchAssessment().then((a) => {
      if (a) setFieldName(a.field)
    })
  }, [])

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-slate-900 text-slate-100 flex flex-col z-50">
      <div className="px-4 py-5 border-b border-slate-700">
        <h1 className="text-lg font-bold tracking-wide">NewLearner</h1>
        {fieldName && (
          <p className="text-xs text-slate-400 mt-1 truncate">
            领域: {fieldName}
          </p>
        )}
      </div>

      <nav className="flex-1 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white font-medium'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-slate-700 text-xs text-slate-500">
        AI 研究学习助手
      </div>
    </aside>
  )
}
