import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useCourse } from '../contexts/CourseContext'
import { buildOutline, generateAllChapters } from '../api/client'
import type { SSEEvent } from '../types'
import StepProgress from '../components/StepProgress'

const chapterStatusConfig: Record<string, { icon: string; color: string; label: string }> = {
  pending: { icon: '', color: 'text-slate-300', label: '待生成' },
  generating: { icon: '', color: 'text-amber-500', label: '生成中' },
  ready: { icon: '', color: 'text-blue-500', label: '已就绪' },
  in_progress: { icon: '', color: 'text-yellow-500', label: '学习中' },
  completed: { icon: '', color: 'text-green-500', label: '已完成' },
}

function DifficultyStars({ level }: { level: number }) {
  const full = Math.round(level)
  return (
    <span className="inline-flex gap-0.5" title={`难度 ${level}/5`}>
      {Array.from({ length: 5 }, (_, i) => (
        <svg
          key={i}
          className={`w-3 h-3 ${i < full ? 'text-amber-400' : 'text-slate-200'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </span>
  )
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'generating') {
    return (
      <svg className="w-5 h-5 text-amber-500 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    )
  }
  if (status === 'completed') {
    return (
      <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
    )
  }
  if (status === 'ready') {
    return (
      <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 11.293a1 1 0 101.414 1.414l2-2A1 1 0 0011.414 10H11V7z" clipRule="evenodd" />
      </svg>
    )
  }
  if (status === 'in_progress') {
    return (
      <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
      </svg>
    )
  }
  // pending
  return (
    <div className="w-5 h-5 rounded-full border-2 border-slate-300" />
  )
}

export default function TextbookPage() {
  const { courseId, textbook, loading, refreshTextbook, refreshCourse } = useCourse()
  const [building, setBuilding] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [messages, setMessages] = useState<string[]>([])
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const cancelRef = useRef<(() => void) | null>(null)

  const handleBuildOutline = () => {
    setBuilding(true)
    setMessages([])
    setError(null)
    setCurrentStep(0)
    setCompletedSteps([])

    const handleEvent = (event: SSEEvent) => {
      if (event.event === 'step_start') {
        const step = (event.data as { step?: number }).step ?? 0
        setCurrentStep(step)
        const msg = (event.data as { message?: string }).message
        if (msg) setMessages((prev) => [...prev, msg])
      }
      if (event.event === 'step_progress') {
        const msg = (event.data as { message?: string }).message
        if (msg) setMessages((prev) => [...prev, msg])
      }
      if (event.event === 'step_complete') {
        const step = (event.data as { step?: number }).step ?? 0
        setCompletedSteps((prev) => [...prev, step])
      }
    }

    cancelRef.current = buildOutline(
      courseId,
      handleEvent,
      async () => {
        await refreshTextbook()
        await refreshCourse()
        setBuilding(false)
      },
      (err) => {
        setError(err.message)
        setBuilding(false)
      },
    )
  }

  const handleGenerateAll = () => {
    setGenerating(true)
    setMessages([])
    setError(null)

    const handleEvent = (event: SSEEvent) => {
      const msg = (event.data as { message?: string }).message
      if (msg) setMessages((prev) => [...prev, msg])
    }

    cancelRef.current = generateAllChapters(
      courseId,
      handleEvent,
      async () => {
        await refreshTextbook()
        await refreshCourse()
        setGenerating(false)
      },
      (err) => {
        setError(err.message)
        setGenerating(false)
      },
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        加载中...
      </div>
    )
  }

  // No textbook yet
  if (!textbook) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <svg className="w-16 h-16 mx-auto text-slate-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        <h2 className="text-xl font-semibold text-slate-700 mb-2">
          尚未构建教材大纲
        </h2>
        <p className="text-sm text-slate-400 mb-6">
          系统将根据你的背景和目标，自动研究领域文献并生成结构化的教材大纲
        </p>

        {building ? (
          <div className="text-left max-w-lg mx-auto">
            <StepProgress currentStep={currentStep} completedSteps={completedSteps} />
            <div className="mt-4 bg-slate-900 rounded-lg p-4 max-h-64 overflow-y-auto">
              {messages.map((msg, i) => (
                <p key={i} className="text-xs text-green-400 font-mono leading-relaxed">
                  {msg}
                </p>
              ))}
              {messages.length === 0 && (
                <p className="text-xs text-slate-500 font-mono">等待服务器响应...</p>
              )}
            </div>
          </div>
        ) : (
          <button
            onClick={handleBuildOutline}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            构建教材大纲
          </button>
        )}

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    )
  }

  // Has textbook
  const completedCount = textbook.chapters.filter((c) => c.status === 'completed').length
  const readyOrDoneCount = textbook.chapters.filter((c) => c.has_content).length

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">{textbook.title}</h1>
        <p className="text-sm text-slate-400 mt-1">
          {textbook.field} | {completedCount}/{textbook.chapters.length} 章已完成 | 预计 {textbook.total_estimated_hours.toFixed(1)} 小时
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mb-6">
        {readyOrDoneCount < textbook.chapters.length && (
          <button
            onClick={handleGenerateAll}
            disabled={generating}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? '生成中...' : '一键生成全部内容'}
          </button>
        )}
      </div>

      {/* Generation progress */}
      {generating && messages.length > 0 && (
        <div className="mb-6 bg-slate-900 rounded-lg p-4 max-h-48 overflow-y-auto">
          {messages.map((msg, i) => (
            <p key={i} className="text-xs text-green-400 font-mono leading-relaxed">
              {msg}
            </p>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Chapter list */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
          <h2 className="text-sm font-semibold text-slate-600">章节目录</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {textbook.chapters.map((chapter) => {
            const cfg = chapterStatusConfig[chapter.status] ?? chapterStatusConfig.pending
            return (
              <Link
                key={chapter.id}
                to={`/courses/${courseId}/chapters/${chapter.id}`}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-blue-50/50 transition-colors group"
              >
                {/* Status icon */}
                <StatusIcon status={chapter.status} />

                {/* Number */}
                <span className="text-sm font-mono text-slate-400 w-8 text-right flex-shrink-0">
                  {chapter.chapter_number}
                </span>

                {/* Title + meta */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-slate-800 group-hover:text-blue-600 transition-colors truncate">
                    {chapter.title}
                  </h3>
                  {chapter.key_topics.length > 0 && (
                    <p className="text-xs text-slate-400 mt-0.5 truncate">
                      {chapter.key_topics.join(' / ')}
                    </p>
                  )}
                </div>

                {/* Difficulty */}
                <DifficultyStars level={chapter.difficulty} />

                {/* Estimated hours */}
                <span className="text-xs text-slate-400 w-16 text-right flex-shrink-0">
                  {chapter.estimated_hours.toFixed(1)} 小时
                </span>

                {/* Status label */}
                <span className={`text-xs w-14 text-right flex-shrink-0 ${cfg.color}`}>
                  {cfg.label}
                </span>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}
