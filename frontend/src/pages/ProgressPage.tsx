import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { fetchAssessment, fetchProgress } from '../api/client'
import type { LearnerProgress, ConceptProgress } from '../types'

export default function ProgressPage() {
  const navigate = useNavigate()
  const [progress, setProgress] = useState<LearnerProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const assessment = await fetchAssessment()
        if (!assessment) {
          navigate('/assess')
          return
        }
        const p = await fetchProgress(assessment.field)
        setProgress(p)
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [navigate])

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
        {error}
      </div>
    )
  }

  if (!progress) return null

  const completionPct = Math.round(progress.completion_rate * 100)

  // Build chart data from concept quiz scores
  const chartData = buildChartData(progress.concept_progress)

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-1">学习进度</h1>
      <p className="text-sm text-slate-400 mb-6">领域: {progress.field}</p>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <SummaryCard label="完成率" value={`${completionPct}%`} />
        <SummaryCard
          label="已完成"
          value={`${progress.completed_concepts} / ${progress.total_concepts}`}
        />
        <SummaryCard label="连续天数" value={`${progress.streak_days} 天`} />
        <SummaryCard
          label="总学习时间"
          value={`${totalMinutes(progress.concept_progress)} 分钟`}
        />
      </div>

      {/* Completion donut */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-6 flex flex-col items-center justify-center">
          <div className="relative w-36 h-36">
            <svg viewBox="0 0 36 36" className="w-full h-full">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e2e8f0"
                strokeWidth="3"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="3"
                strokeDasharray={`${completionPct}, 100`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-slate-800">
                {completionPct}%
              </span>
            </div>
          </div>
          <p className="text-sm text-slate-500 mt-3">总完成率</p>
        </div>

        {/* Quiz scores chart */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">
            测验成绩趋势
          </h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center pt-12">
              暂无测验数据
            </p>
          )}
        </div>
      </div>

      {/* Per-concept table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-8">
        <h3 className="text-sm font-semibold text-slate-700 px-4 py-3 border-b border-slate-100">
          概念详情
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-slate-600">
                  概念
                </th>
                <th className="text-left px-4 py-2 font-medium text-slate-600">
                  状态
                </th>
                <th className="text-left px-4 py-2 font-medium text-slate-600">
                  掌握度
                </th>
                <th className="text-left px-4 py-2 font-medium text-slate-600">
                  测验分数
                </th>
                <th className="text-left px-4 py-2 font-medium text-slate-600">
                  学习时间
                </th>
              </tr>
            </thead>
            <tbody>
              {progress.concept_progress.map((cp) => (
                <tr
                  key={cp.concept_id}
                  className="border-t border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-4 py-2.5 font-medium text-slate-700">
                    {cp.concept_name}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={cp.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <MasteryBar level={cp.mastery_level} />
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">
                    {cp.quiz_scores.length > 0
                      ? cp.quiz_scores
                          .map((s) => `${Math.round(s)}%`)
                          .join(', ')
                      : '-'}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500">
                    {cp.time_spent_minutes} 分钟
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Weekly Report */}
      {progress.weekly_report && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            周报
          </h3>
          <div className="prose prose-sm prose-slate max-w-none">
            <ReactMarkdown>{progress.weekly_report}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-lg font-bold text-slate-800">{value}</p>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-slate-100 text-slate-500',
    in_progress: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-green-100 text-green-700',
  }
  const labels: Record<string, string> = {
    pending: '待学习',
    in_progress: '学习中',
    completed: '已完成',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${styles[status] ?? ''}`}>
      {labels[status] ?? status}
    </span>
  )
}

function MasteryBar({ level }: { level: number }) {
  const pct = Math.round(level * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-slate-200 rounded-full h-1.5">
        <div
          className="bg-blue-500 h-1.5 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-500">{pct}%</span>
    </div>
  )
}

function totalMinutes(concepts: ConceptProgress[]): number {
  return concepts.reduce((sum, c) => sum + c.time_spent_minutes, 0)
}

function buildChartData(
  concepts: ConceptProgress[]
): { name: string; score: number }[] {
  const data: { name: string; score: number }[] = []
  for (const cp of concepts) {
    for (const score of cp.quiz_scores) {
      data.push({
        name: cp.concept_name.slice(0, 6),
        score: Math.round(score),
      })
    }
  }
  return data
}
