import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCourse } from '../contexts/CourseContext'
import { fetchChapterContent, streamChapter, deleteChapterContent } from '../api/client'
import type { ResearchSynthesis, ResourceCollection, VerificationReport, SSEEvent } from '../types'
import ContentRenderer from '../components/ContentRenderer'
import StepProgress from '../components/StepProgress'

export default function ChapterPage() {
  const { courseId, textbook, refreshTextbook } = useCourse()
  const { chapterId } = useParams<{ chapterId: string }>()

  const [synthesis, setSynthesis] = useState<ResearchSynthesis | null>(null)
  const [resources, setResources] = useState<ResourceCollection | null>(null)
  const [verification, setVerification] = useState<VerificationReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [streaming, setStreaming] = useState(false)
  const [messages, setMessages] = useState<string[]>([])
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const cancelRef = useRef<(() => void) | null>(null)

  const chapter = textbook?.chapters.find((c) => c.id === chapterId)

  // Find previous and next chapters
  const chapterIdx = textbook?.chapters.findIndex((c) => c.id === chapterId) ?? -1
  const prevChapter = chapterIdx > 0 ? textbook?.chapters[chapterIdx - 1] : null
  const nextChapter = textbook && chapterIdx < textbook.chapters.length - 1 ? textbook.chapters[chapterIdx + 1] : null

  useEffect(() => {
    if (!courseId || !chapterId) return

    // If chapter has content, fetch it
    if (chapter?.has_content) {
      setLoading(true)
      fetchChapterContent(courseId, chapterId)
        .then((data) => {
          if (data) {
            setSynthesis(data.synthesis)
            setResources(data.resources ?? null)
            setVerification(data.verification ?? null)
          }
        })
        .catch((err) => setError(err instanceof Error ? err.message : '加载失败'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }

    return () => {
      cancelRef.current?.()
    }
  }, [courseId, chapterId, chapter?.has_content])

  const handleGenerate = () => {
    if (!courseId || !chapterId) return
    setStreaming(true)
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

    cancelRef.current = streamChapter(
      courseId,
      chapterId,
      handleEvent,
      async () => {
        // Refresh textbook to update chapter status, then load content
        await refreshTextbook()
        const data = await fetchChapterContent(courseId, chapterId)
        if (data) {
          setSynthesis(data.synthesis)
          setResources(data.resources ?? null)
          setVerification(data.verification ?? null)
        }
        setStreaming(false)
      },
      (err) => {
        setError(err.message)
        setStreaming(false)
      },
    )
  }

  const handleDelete = async () => {
    if (!courseId || !chapterId) return
    if (!window.confirm('确定要删除本章已生成的内容吗？删除后需要重新生成。')) return
    setDeleting(true)
    setError(null)
    try {
      await deleteChapterContent(courseId, chapterId)
      setSynthesis(null)
      setResources(null)
      setVerification(null)
      await refreshTextbook()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    } finally {
      setDeleting(false)
    }
  }

  const handleRegenerate = async () => {
    if (!courseId || !chapterId) return
    if (!window.confirm('确定要重新生成本章内容吗？现有内容将被覆盖。')) return
    setDeleting(true)
    setError(null)
    try {
      await deleteChapterContent(courseId, chapterId)
      setSynthesis(null)
      setResources(null)
      setVerification(null)
      await refreshTextbook()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
      setDeleting(false)
      return
    }
    setDeleting(false)
    handleGenerate()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        加载中...
      </div>
    )
  }

  // No content yet (or interrupted)
  if (!chapter?.has_content && !synthesis) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <Link to={`/courses/${courseId}`} className="text-sm text-blue-500 hover:text-blue-600">
            &larr; 返回目录
          </Link>
        </div>

        <div className="text-center py-16">
          <h2 className="text-xl font-semibold text-slate-700 mb-2">
            {chapter ? chapter.title : '未知章节'}
          </h2>
          {chapter?.description && (
            <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
              {chapter.description}
            </p>
          )}

          {streaming ? (
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
            <div className="flex flex-col items-center gap-3">
              {chapter?.status === 'interrupted' && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-sm text-orange-700 mb-2">
                  本章内容生成曾被中断，点击下方按钮继续生成（已完成的步骤将自动跳过）
                </div>
              )}
              <button
                onClick={handleGenerate}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                {chapter?.status === 'interrupted' ? '继续生成' : '生成本章内容'}
              </button>
            </div>
          )}

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Has content
  return (
    <div className="max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to={`/courses/${courseId}`} className="text-sm text-blue-500 hover:text-blue-600">
          &larr; 返回目录
        </Link>
      </div>

      {/* Chapter header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            {chapter ? `第 ${chapter.chapter_number} 章: ${chapter.title}` : '章节内容'}
          </h1>
          {chapter?.description && (
            <p className="text-sm text-slate-400 mt-2">{chapter.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-4">
          <button
            onClick={handleRegenerate}
            disabled={deleting || streaming}
            className="text-xs px-3 py-1.5 rounded-md border border-blue-300 text-blue-600 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {deleting ? '处理中...' : '重新生成'}
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting || streaming}
            className="text-xs px-3 py-1.5 rounded-md border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {deleting ? '删除中...' : '删除内容'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Three-layer content */}
      {synthesis && <ContentRenderer synthesis={synthesis} />}

      {/* Resources */}
      {resources && (() => {
        const allRes = [
          ...resources.papers,
          ...resources.blogs,
          ...resources.videos,
          ...resources.code,
          ...resources.courses,
        ]
        if (allRes.length === 0) return null
        return (
          <div className="mt-8 bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">参考资源</h2>
            <div className="grid gap-3">
              {allRes.map((res, i) => (
                <a
                  key={i}
                  href={res.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg border border-slate-200 p-3 hover:border-blue-300 hover:bg-blue-50/30 transition-colors"
                >
                  <div>
                    <span className="text-sm font-medium text-blue-600">
                      {res.title}
                    </span>
                    {res.description && (
                      <p className="text-xs text-slate-400 mt-0.5">{res.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                    <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                      {res.resource_type}
                    </span>
                    <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                      {res.difficulty}
                    </span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )
      })()}

      {/* Verification */}
      {verification && (
        <div className="mt-6 bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-700">准确性验证</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              verification.hallucination_risk_score <= 0.2
                ? 'bg-green-100 text-green-700'
                : verification.hallucination_risk_score <= 0.5
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {verification.overall_status === 'passed' ? '已通过' :
               verification.overall_status === 'passed_with_warnings' ? '有警告' :
               verification.overall_status === 'failed' ? '未通过' : '待验证'}
            </span>
          </div>
          <div className="space-y-2">
            {verification.checks.slice(0, 8).map((check, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`flex-shrink-0 mt-0.5 ${
                  check.result === 'verified' ? 'text-green-500' :
                  check.result === 'error' ? 'text-red-500' :
                  check.result === 'warning' ? 'text-yellow-500' : 'text-slate-400'
                }`}>
                  {check.result === 'verified' ? '[OK]' :
                   check.result === 'error' ? '[!!]' :
                   check.result === 'warning' ? '[!]' : '[--]'}
                </span>
                <span className="text-slate-600">{check.claim}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom navigation */}
      <div className="mt-10 flex items-center justify-between border-t border-slate-200 pt-6">
        <div>
          {prevChapter && (
            <Link
              to={`/courses/${courseId}/chapters/${prevChapter.id}`}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-blue-600 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <div>
                <p className="text-xs text-slate-400">上一章</p>
                <p className="font-medium">{prevChapter.title}</p>
              </div>
            </Link>
          )}
        </div>

        <Link
          to={`/courses/${courseId}/quiz/${chapterId}`}
          className="bg-green-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
        >
          做测验
        </Link>

        <div>
          {nextChapter && (
            <Link
              to={`/courses/${courseId}/chapters/${nextChapter.id}`}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-blue-600 transition-colors text-right"
            >
              <div>
                <p className="text-xs text-slate-400">下一章</p>
                <p className="font-medium">{nextChapter.title}</p>
              </div>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
