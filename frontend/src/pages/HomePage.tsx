import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchStatus } from '../api/client'

interface StatusData {
  has_assessment: boolean
  field?: string
  completion_rate?: number
  due_reviews?: number
  total_concepts?: number
  completed_concepts?: number
}

export default function HomePage() {
  const [status, setStatus] = useState<StatusData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStatus()
      .then((data) => setStatus(data as unknown as StatusData))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        加载中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
        加载失败: {error}
      </div>
    )
  }

  if (!status?.has_assessment) {
    return <WelcomeView />
  }

  return <DashboardView status={status} />
}

function WelcomeView() {
  return (
    <div className="max-w-2xl mx-auto pt-16 text-center">
      <h1 className="text-3xl font-bold text-slate-800 mb-4">
        欢迎使用 NewLearner
      </h1>
      <p className="text-slate-500 mb-2 leading-relaxed">
        AI 驱动的研究领域深度学习系统
      </p>
      <p className="text-slate-400 text-sm mb-8">
        通过三层内容体系 (直觉 / 机制 / 实践) 帮助你系统掌握前沿研究方向
      </p>

      <Link
        to="/assess"
        className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
      >
        开始能力评估
      </Link>

      <div className="mt-16 grid grid-cols-3 gap-6 text-left">
        <FeatureCard
          title="知识图谱"
          desc="自动构建领域知识结构，规划最优学习路径"
        />
        <FeatureCard
          title="深度内容"
          desc="三层教学内容：直觉理解 → 数学机制 → 实践应用"
        />
        <FeatureCard
          title="间隔复习"
          desc="基于 SM-2 算法的闪卡系统，科学巩固记忆"
        />
      </div>
    </div>
  )
}

function FeatureCard({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-slate-700 mb-2">{title}</h3>
      <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
    </div>
  )
}

function DashboardView({ status }: { status: StatusData }) {
  const completionPct = Math.round((status.completion_rate ?? 0) * 100)

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-1">学习面板</h1>
      <p className="text-sm text-slate-400 mb-6">
        当前领域: {status.field}
      </p>

      {/* Stats cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="完成率" value={`${completionPct}%`} color="blue" />
        <StatCard
          label="已学概念"
          value={`${status.completed_concepts ?? 0} / ${status.total_concepts ?? 0}`}
          color="green"
        />
        <StatCard
          label="待复习"
          value={`${status.due_reviews ?? 0} 张卡片`}
          color="amber"
        />
      </div>

      {/* Quick links */}
      <h2 className="text-sm font-semibold text-slate-600 mb-3">快捷入口</h2>
      <div className="grid grid-cols-2 gap-3">
        <QuickLink to="/graph" label="查看知识图谱" sub="继续学习下一个概念" />
        <QuickLink to="/review" label="开始复习" sub="复习到期的闪卡" />
        <QuickLink to="/progress" label="学习进度" sub="查看详细统计数据" />
        <QuickLink to="/export" label="导出资料" sub="导出为 Obsidian / Anki" />
      </div>
    </div>
  )
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: string
}) {
  const colors: Record<string, string> = {
    blue: 'border-blue-200 bg-blue-50',
    green: 'border-green-200 bg-green-50',
    amber: 'border-amber-200 bg-amber-50',
  }
  return (
    <div
      className={`rounded-lg border p-4 ${colors[color] ?? 'border-slate-200 bg-white'}`}
    >
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-slate-800">{value}</p>
    </div>
  )
}

function QuickLink({
  to,
  label,
  sub,
}: {
  to: string
  label: string
  sub: string
}) {
  return (
    <Link
      to={to}
      className="flex flex-col rounded-lg border border-slate-200 bg-white p-4 hover:border-blue-300 hover:bg-blue-50/30 transition-colors"
    >
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <span className="text-xs text-slate-400 mt-1">{sub}</span>
    </Link>
  )
}
