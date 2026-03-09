import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchContent, streamLearning } from '../api/client'
import type {
  ResearchSynthesis,
  VerificationReport,
  ResourceCollection,
  SSEEvent,
} from '../types'
import StepProgress from '../components/StepProgress'
import ContentRenderer from '../components/ContentRenderer'

export default function LearningPage() {
  const { conceptId } = useParams<{ conceptId: string }>()
  const navigate = useNavigate()
  const closeRef = useRef<(() => void) | null>(null)

  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [synthesis, setSynthesis] = useState<ResearchSynthesis | null>(null)
  const [verification, setVerification] = useState<VerificationReport | null>(null)
  const [resources, setResources] = useState<ResourceCollection | null>(null)
  const [quizReady, setQuizReady] = useState(false)
  const [practiceReady, setPracticeReady] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])

  useEffect(() => {
    if (!conceptId) return

    let cancelled = false

    async function init() {
      // Check if content already exists
      const existing = await fetchContent(conceptId!)
      if (cancelled) return

      if (existing) {
        setSynthesis(existing)
        setCompletedSteps([1, 2, 3, 4, 5])
        setCurrentStep(5)
        setQuizReady(true)
        setPracticeReady(true)
        setLoading(false)
        return
      }

      // Start SSE stream
      setLoading(false)
      setCurrentStep(1)

      closeRef.current = streamLearning(
        conceptId!,
        (event: SSEEvent) => {
          if (cancelled) return
          handleSSEEvent(event)
        },
        () => {
          // Done
        },
        (err) => {
          if (!cancelled) setError(err.message)
        }
      )
    }

    init().catch((err) => {
      if (!cancelled) {
        setError(err.message)
        setLoading(false)
      }
    })

    return () => {
      cancelled = true
      closeRef.current?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conceptId])

  function handleSSEEvent(event: SSEEvent) {
    const { data } = event

    setLogs((prev) => [
      ...prev,
      `[${event.event}] ${(data.message as string) ?? ''}`,
    ])

    switch (event.event) {
      case 'step_start': {
        const step = data.step as number
        setCurrentStep(step)
        break
      }
      case 'step_complete': {
        const step = data.step as number
        setCompletedSteps((prev) =>
          prev.includes(step) ? prev : [...prev, step]
        )

        if (step === 1 && data.synthesis) {
          setSynthesis(data.synthesis as ResearchSynthesis)
        }
        if (step === 2 && data.verification) {
          setVerification(data.verification as VerificationReport)
        }
        if (step === 3 && data.resources) {
          setResources(data.resources as ResourceCollection)
        }
        if (step === 4) {
          setQuizReady(true)
        }
        if (step === 5) {
          setPracticeReady(true)
        }
        break
      }
      case 'step_progress': {
        // Progress updates during a step
        break
      }
      case 'complete': {
        if (data.synthesis) {
          setSynthesis(data.synthesis as ResearchSynthesis)
        }
        setCompletedSteps([1, 2, 3, 4, 5])
        break
      }
      case 'error': {
        setError((data.message as string) ?? '生成过程出错')
        break
      }
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
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-1">
        学习: {synthesis?.concept_name ?? conceptId}
      </h1>

      {/* Step Progress */}
      <StepProgress currentStep={currentStep} completedSteps={completedSteps} />

      <div className="space-y-6 mt-6">
        {/* Step 1: Research Synthesis */}
        {synthesis && (
          <section>
            <SectionHeader
              step={1}
              title="深度研究内容"
              completed={completedSteps.includes(1)}
            />
            <ContentRenderer synthesis={synthesis} />
          </section>
        )}

        {/* Step 2: Verification */}
        {completedSteps.includes(2) && (
          <section>
            <SectionHeader
              step={2}
              title="准确性验证"
              completed={completedSteps.includes(2)}
            />
            {verification ? (
              <VerificationPanel report={verification} />
            ) : (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-2">
                <span className="text-green-600 font-bold text-lg">✓</span>
                <span className="text-sm text-green-700">内容已通过准确性验证</span>
              </div>
            )}
          </section>
        )}

        {/* Step 3: Resources */}
        {completedSteps.includes(3) && (
          <section>
            <SectionHeader
              step={3}
              title="学习资源"
              completed={completedSteps.includes(3)}
            />
            {resources ? (
              <ResourcePanel collection={resources} />
            ) : (
              <p className="text-sm text-slate-500">资源整理完成</p>
            )}
          </section>
        )}

        {/* Step 4: Quiz Ready */}
        {quizReady && (
          <section>
            <SectionHeader
              step={4}
              title="知识测验"
              completed={completedSteps.includes(4)}
            />
            <div className="bg-white rounded-lg border border-slate-200 p-5 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-700">
                  测验已生成
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  检验你对该概念的理解程度
                </p>
              </div>
              <button
                onClick={() => navigate(`/quiz/${conceptId}`)}
                className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                开始测验
              </button>
            </div>
          </section>
        )}

        {/* Step 5: Practice */}
        {practiceReady && (
          <section>
            <SectionHeader
              step={5}
              title="练习材料"
              completed={completedSteps.includes(5)}
            />
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-700">
                练习材料已生成，包括闪卡和复习资源
              </p>
              <button
                onClick={() => navigate('/review')}
                className="mt-2 text-sm text-green-700 underline hover:text-green-800"
              >
                前往复习 →
              </button>
            </div>
          </section>
        )}

        {/* Live log during generation */}
        {currentStep > 0 && !completedSteps.includes(5) && logs.length > 0 && (
          <div className="bg-slate-900 rounded-lg p-4 max-h-48 overflow-y-auto">
            <p className="text-xs text-slate-500 mb-2">生成日志</p>
            {logs.map((line, i) => (
              <p key={i} className="text-xs text-green-400 font-mono">
                {line}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SectionHeader({
  step,
  title,
  completed,
}: {
  step: number
  title: string
  completed: boolean
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span
        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
          completed
            ? 'bg-green-500 text-white'
            : 'bg-blue-500 text-white'
        }`}
      >
        {completed ? '✓' : step}
      </span>
      <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
    </div>
  )
}

function VerificationPanel({ report }: { report: VerificationReport }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm font-medium text-slate-700">
          整体置信度:
        </span>
        <span
          className={`text-sm font-bold ${
            report.overall_confidence >= 0.8
              ? 'text-green-600'
              : report.overall_confidence >= 0.5
              ? 'text-yellow-600'
              : 'text-red-600'
          }`}
        >
          {Math.round(report.overall_confidence * 100)}%
        </span>
      </div>

      <div className="space-y-2">
        {report.checks.map((check, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-sm p-2 rounded bg-slate-50"
          >
            <span
              className={`flex-shrink-0 mt-0.5 ${
                check.status === 'verified'
                  ? 'text-green-500'
                  : check.status === 'disputed'
                  ? 'text-red-500'
                  : 'text-yellow-500'
              }`}
            >
              {check.status === 'verified'
                ? '✓'
                : check.status === 'disputed'
                ? '✗'
                : '?'}
            </span>
            <div>
              <p className="text-slate-700">{check.claim}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                来源: {check.source} ({Math.round(check.confidence * 100)}%)
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResourcePanel({ collection }: { collection: ResourceCollection }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {collection.resources.map((res, i) => (
        <a
          key={i}
          href={res.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-blue-300 transition-colors"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-blue-600 truncate">
              {res.title}
            </span>
            <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded flex-shrink-0 ml-2">
              {res.type}
            </span>
          </div>
          {res.description && (
            <p className="text-xs text-slate-500 line-clamp-2">
              {res.description}
            </p>
          )}
          <span className="text-xs text-slate-400 mt-1 inline-block">
            难度: {res.difficulty}
          </span>
        </a>
      ))}
    </div>
  )
}
